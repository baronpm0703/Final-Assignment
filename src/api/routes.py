import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError

from src.api.models import (
    ChatRequest,
    ChatResponse,
    ConfigResponse,
    ConversationListResponse,
    ConversationMessagesResponse,
    ConversationSummaryResponse,
    CreateConversationResponse,
    HealthResponse,
    MessageResponse,
)
from src.core.errors import AppError, ErrorCode
from src.domain.response import AgentResponse
from src.memory.conversation_memory import ConversationMessage

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


def _resolve_conversation_id(memory, conversation_id: str | None) -> str:
    resolved = (conversation_id or "").strip() or "default"
    memory.create(resolved)
    return resolved


def _conversation_store(request: Request):
    return getattr(request.app.state, "conversation_store", None)


def _hydrate_memory_from_store(memory, store, conversation_id: str) -> None:
    if store is None or memory.get_messages(conversation_id):
        return
    try:
        if store.exists(conversation_id):
            memory.replace_messages(conversation_id, store.get_messages(conversation_id))
    except SQLAlchemyError as exc:
        logger.warning("Failed to hydrate conversation %s: %s", conversation_id, exc)


def _append_message(memory, store, conversation_id: str, role: str, content: str) -> None:
    memory.append(conversation_id, role, content)
    if store is None:
        return
    try:
        store.append_message(conversation_id, role, content)
    except SQLAlchemyError as exc:
        logger.warning("Failed to persist conversation message %s: %s", conversation_id, exc)


def _message_response(message: ConversationMessage) -> MessageResponse:
    return MessageResponse(
        role=message.role,
        content=message.content,
        created_at=message.created_at.isoformat(),
    )


def _memory_summaries(memory) -> list[ConversationSummaryResponse]:
    now = datetime.now(UTC).isoformat()
    summaries = []
    for conversation_id in memory.list_conversations():
        messages = memory.get_messages(conversation_id)
        title = next((message.content[:80] for message in messages if message.role == "user"), None)
        updated_at = messages[-1].created_at.isoformat() if messages else now
        created_at = messages[0].created_at.isoformat() if messages else now
        summaries.append(
            ConversationSummaryResponse(
                conversation_id=conversation_id,
                created_at=created_at,
                updated_at=updated_at,
                message_count=len(messages),
                title=title,
            )
        )
    return sorted(summaries, key=lambda item: item.updated_at, reverse=True)


def _sse_data(event: dict) -> str:
    return f"data: {json.dumps(jsonable_encoder(event), ensure_ascii=False)}\n\n"


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(status="ok", app_env=settings.app_env)


@router.get("/config", response_model=ConfigResponse)
def config(request: Request) -> ConfigResponse:
    settings = request.app.state.settings
    return ConfigResponse(
        app_name=settings.app_name,
        app_env=settings.app_env,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        sql_max_limit=settings.sql_max_limit,
        sql_default_limit=settings.sql_default_limit,
    )


# --- Conversation management ---


@router.post("/conversations", response_model=CreateConversationResponse, status_code=201)
def create_conversation(request: Request) -> CreateConversationResponse:
    """Create a new chat session and return its ID."""
    memory = request.app.state.memory
    store = _conversation_store(request)
    conversation_id = uuid.uuid4().hex[:16]
    memory.create(conversation_id)
    if store is not None:
        try:
            store.create_conversation(conversation_id)
        except SQLAlchemyError as exc:
            logger.warning("Failed to persist conversation %s: %s", conversation_id, exc)
    return CreateConversationResponse(conversation_id=conversation_id)


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(request: Request) -> ConversationListResponse:
    """List all active conversation IDs."""
    memory = request.app.state.memory
    store = _conversation_store(request)
    if store is not None:
        try:
            return ConversationListResponse(
                conversations=[
                    ConversationSummaryResponse(
                        conversation_id=summary.conversation_id,
                        created_at=summary.created_at.isoformat(),
                        updated_at=summary.updated_at.isoformat(),
                        message_count=summary.message_count,
                        title=summary.title,
                    )
                    for summary in store.list_conversations()
                ]
            )
        except SQLAlchemyError as exc:
            logger.warning("Failed to list persisted conversations: %s", exc)
    return ConversationListResponse(conversations=_memory_summaries(memory))


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationMessagesResponse,
)
def get_conversation_messages(
    conversation_id: str, request: Request
) -> ConversationMessagesResponse:
    """Get the message history for a conversation."""
    memory = request.app.state.memory
    store = _conversation_store(request)
    if store is not None:
        try:
            if store.exists(conversation_id):
                messages = store.get_messages(conversation_id)
                memory.replace_messages(conversation_id, messages)
                return ConversationMessagesResponse(
                    conversation_id=conversation_id,
                    messages=[_message_response(msg) for msg in messages],
                )
        except SQLAlchemyError as exc:
            logger.warning("Failed to load persisted conversation %s: %s", conversation_id, exc)
    if not memory.exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = memory.get_messages(conversation_id)
    return ConversationMessagesResponse(
        conversation_id=conversation_id,
        messages=[_message_response(msg) for msg in messages],
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, request: Request) -> None:
    """Delete a conversation and its history."""
    memory = request.app.state.memory
    store = _conversation_store(request)
    deleted_from_memory = memory.delete(conversation_id)
    deleted_from_store = False
    if store is not None:
        try:
            deleted_from_store = store.delete(conversation_id)
        except SQLAlchemyError as exc:
            logger.warning("Failed to delete persisted conversation %s: %s", conversation_id, exc)
    if not (deleted_from_memory or deleted_from_store):
        raise HTTPException(status_code=404, detail="Conversation not found")


# --- Chat ---


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail=ErrorCode.CHAT_EMPTY_MESSAGE.value)

    memory = request.app.state.memory
    agent = request.app.state.agent
    store = _conversation_store(request)
    conversation_id = _resolve_conversation_id(memory, payload.conversation_id)
    _hydrate_memory_from_store(memory, store, conversation_id)
    _append_message(memory, store, conversation_id, "user", message)
    memory_context = memory.build_context(conversation_id).render()

    try:
        response: AgentResponse = agent.answer(message, memory_context=memory_context)
    except AppError as exc:
        raise HTTPException(
            status_code=400, detail={"code": exc.code, "message": exc.message}
        ) from exc

    _append_message(memory, store, conversation_id, "assistant", response.answer)
    return ChatResponse(conversation_id=conversation_id, **response.to_dict())


@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest, request: Request):
    """Stream chat response with status updates (SSE)."""
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail=ErrorCode.CHAT_EMPTY_MESSAGE.value)

    memory = request.app.state.memory
    agent = request.app.state.agent
    store = _conversation_store(request)
    conversation_id = _resolve_conversation_id(memory, payload.conversation_id)

    _hydrate_memory_from_store(memory, store, conversation_id)
    _append_message(memory, store, conversation_id, "user", message)
    memory_context = memory.build_context(conversation_id).render()

    async def event_generator():
        metadata = {"type": "metadata", "conversation_id": conversation_id}
        yield _sse_data(metadata)

        async for event in agent.stream_answer(
            message=message,
            memory_context=memory_context,
        ):
            encoded_event = jsonable_encoder(event)

            yield f"data: {json.dumps(encoded_event, ensure_ascii=False)}\n\n"
            # yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # Lưu assistant response khi kết thúc
            if event.get("type") == "result":
                event = {**event, "conversation_id": conversation_id}
                _append_message(
                    memory,
                    store,
                    conversation_id,
                    "assistant",
                    event.get("answer", ""),
                )

            yield _sse_data(event)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

import json
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from src.api.models import (
    ChatRequest,
    ChatResponse,
    ConfigResponse,
    ConversationListResponse,
    ConversationMessagesResponse,
    CreateConversationResponse,
    HealthResponse,
    MessageResponse,
)
from src.core.errors import AppError, ErrorCode
from src.domain.response import AgentResponse

router = APIRouter(prefix="/api")


def _resolve_conversation_id(memory, conversation_id: str | None) -> str:
    resolved = (conversation_id or "").strip() or "default"
    memory.create(resolved)
    return resolved


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
    conversation_id = uuid.uuid4().hex[:16]
    memory.create(conversation_id)
    return CreateConversationResponse(conversation_id=conversation_id)


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(request: Request) -> ConversationListResponse:
    """List all active conversation IDs."""
    memory = request.app.state.memory
    return ConversationListResponse(conversations=memory.list_conversations())


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationMessagesResponse,
)
def get_conversation_messages(
    conversation_id: str, request: Request
) -> ConversationMessagesResponse:
    """Get the message history for a conversation."""
    memory = request.app.state.memory
    if not memory.exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = memory.get_messages(conversation_id)
    return ConversationMessagesResponse(
        conversation_id=conversation_id,
        messages=[
            MessageResponse(
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at.isoformat(),
            )
            for msg in messages
        ],
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, request: Request) -> None:
    """Delete a conversation and its history."""
    memory = request.app.state.memory
    if not memory.delete(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")


# --- Chat ---


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail=ErrorCode.CHAT_EMPTY_MESSAGE.value)

    memory = request.app.state.memory
    agent = request.app.state.agent
    conversation_id = _resolve_conversation_id(memory, payload.conversation_id)
    memory.append(conversation_id, "user", message)
    memory_context = memory.build_context(conversation_id).render()

    try:
        response: AgentResponse = agent.answer(message, memory_context=memory_context)
    except AppError as exc:
        raise HTTPException(
            status_code=400, detail={"code": exc.code, "message": exc.message}
        ) from exc

    memory.append(conversation_id, "assistant", response.answer)
    return ChatResponse(conversation_id=conversation_id, **response.to_dict())


@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest, request: Request):
    """Stream chat response with status updates (SSE)."""
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail=ErrorCode.CHAT_EMPTY_MESSAGE.value)

    memory = request.app.state.memory
    agent = request.app.state.agent
    conversation_id = _resolve_conversation_id(memory, payload.conversation_id)

    memory.append(conversation_id, "user", message)
    memory_context = memory.build_context(conversation_id).render()

    async def event_generator():
        metadata = {"type": "metadata", "conversation_id": conversation_id}
        yield _sse_data(metadata)

        async for event in agent.stream_answer(
            message=message,
            memory_context=memory_context,
        ):
            if event.get("type") == "result":
                event = {**event, "conversation_id": conversation_id}
                memory.append(conversation_id, "assistant", event.get("answer", ""))

            yield _sse_data(event)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

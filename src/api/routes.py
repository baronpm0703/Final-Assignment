from fastapi import APIRouter, HTTPException, Request

from src.api.models import ChatRequest, ChatResponse, ConfigResponse, HealthResponse
from src.core.errors import AppError, ErrorCode
from src.domain.response import AgentResponse

router = APIRouter(prefix="/api")


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


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail=ErrorCode.CHAT_EMPTY_MESSAGE.value)

    memory = request.app.state.memory
    agent = request.app.state.agent
    memory.append(payload.conversation_id, "user", message)
    memory_context = memory.build_context(payload.conversation_id).render()

    try:
        response: AgentResponse = agent.answer(message, memory_context=memory_context)
    except AppError as exc:
        raise HTTPException(
            status_code=400, detail={"code": exc.code, "message": exc.message}
        ) from exc

    memory.append(payload.conversation_id, "assistant", response.answer)
    return ChatResponse(**response.to_dict())

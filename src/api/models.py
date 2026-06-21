from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None


class VisualizationModel(BaseModel):
    type: str
    title: str
    data: list[dict[str, Any]]


class ChatResponse(BaseModel):
    type: str
    answer: str
    language: str
    conversation_id: str
    visualization: VisualizationModel | None = None
    sql_executed: str | None = None
    reasoning_steps: list[str]
    options: list[str]


class HealthResponse(BaseModel):
    status: str
    app_env: str


class ConfigResponse(BaseModel):
    app_name: str
    app_env: str
    llm_provider: str
    llm_model: str
    sql_max_limit: int
    sql_default_limit: int


# --- Conversation management models ---


class CreateConversationResponse(BaseModel):
    conversation_id: str


class ConversationSummaryResponse(BaseModel):
    conversation_id: str
    created_at: str
    updated_at: str
    message_count: int
    title: str | None = None


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummaryResponse]


class MessageResponse(BaseModel):
    role: str
    content: str
    created_at: str


class ConversationMessagesResponse(BaseModel):
    conversation_id: str
    messages: list[MessageResponse]

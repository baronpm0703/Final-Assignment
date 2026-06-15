from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str = "default"


class VisualizationModel(BaseModel):
    type: str
    title: str
    data: list[dict[str, Any]]


class ChatResponse(BaseModel):
    type: str
    answer: str
    language: str
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

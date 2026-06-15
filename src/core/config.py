from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Call Center Analytics Agent"
    app_env: Literal["local", "test", "prod"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    database_url: PostgresDsn = Field(
        default="postgresql+psycopg://callcenter:callcenter@localhost:5432/callcenter"
    )
    database_readonly_url: PostgresDsn | None = Field(
        default="postgresql+psycopg://callcenter_readonly:callcenter_readonly"
        "@localhost:5432/callcenter"
    )
    sql_max_limit: int = 1000
    sql_default_limit: int = 100

    llm_provider: Literal["mock", "openai", "gemini"] = "mock"
    llm_model: str = "mock:offline"
    openai_api_key: str | None = None
    gemini_api_key: str | None = None

    memory_window_size: int = 6
    memory_compaction_ratio: float = 0.70
    memory_summary_ratio: float = 0.70

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("sql_max_limit")
    @classmethod
    def validate_sql_max_limit(cls, value: int) -> int:
        if value < 1:
            raise ValueError("SQL_MAX_LIMIT must be greater than 0")
        if value > 10_000:
            raise ValueError("SQL_MAX_LIMIT must not exceed 10000")
        return value

    @field_validator("sql_default_limit")
    @classmethod
    def validate_sql_default_limit(cls, value: int) -> int:
        if value < 1:
            raise ValueError("SQL_DEFAULT_LIMIT must be greater than 0")
        return value

    @field_validator("sql_default_limit")
    @classmethod
    def validate_default_within_max(cls, value: int, info) -> int:
        max_limit = info.data.get("sql_max_limit")
        if max_limit is not None and value > max_limit:
            raise ValueError("SQL_DEFAULT_LIMIT must not exceed SQL_MAX_LIMIT")
        return value

    @field_validator("memory_window_size")
    @classmethod
    def validate_memory_window_size(cls, value: int) -> int:
        if value < 2:
            raise ValueError("MEMORY_WINDOW_SIZE must be at least 2")
        return value

    @field_validator("memory_compaction_ratio", "memory_summary_ratio")
    @classmethod
    def validate_memory_ratios(cls, value: float) -> float:
        if value <= 0 or value > 1:
            raise ValueError("Memory ratios must be in the range (0, 1]")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

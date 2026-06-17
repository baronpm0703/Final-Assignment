from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class DomainInfo(BaseModel):
    name: str
    description: str


class KnowledgeConfig(BaseModel):
    root_path: Path


class PromptConfig(BaseModel):
    system_prompt_path: Path


class TableSchemaConfig(BaseModel):
    columns: list[str]

    @field_validator("columns")
    @classmethod
    def validate_columns(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("table schema must include at least one column")
        return value


class SchemaConfig(BaseModel):
    allowed_tables: dict[str, TableSchemaConfig]
    allowed_functions: list[str] = Field(default_factory=list)

    @property
    def allowed_schema(self) -> dict[str, set[str]]:
        return {
            table_name.lower(): {column.lower() for column in table.columns}
            for table_name, table in self.allowed_tables.items()
        }

    @property
    def allowed_function_set(self) -> set[str]:
        return {function.lower() for function in self.allowed_functions}


class RouterConfig(BaseModel):
    intent_utterances_path: Path = Path("config/intent_utterances.json")
    bm25_confidence_threshold: float = 0.55
    llm_fallback_enabled: bool = True


class AgentConfig(BaseModel):
    max_react_iters: int = 8
    max_repeated_tool_calls: int = 2


class ResponseConfig(BaseModel):
    clarification_options: list[str] = Field(default_factory=list)


class DomainConfig(BaseModel):
    domain: DomainInfo
    knowledge: KnowledgeConfig
    prompts: PromptConfig
    schema_: SchemaConfig = Field(alias="schema")
    router: RouterConfig
    agent: AgentConfig = Field(default_factory=AgentConfig)
    response: ResponseConfig = Field(default_factory=ResponseConfig)

    @property
    def schema(self) -> SchemaConfig:
        return self.schema_


def load_domain_config(path: Path | str = Path("config/domain.yaml")) -> DomainConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return DomainConfig.model_validate(raw)


@lru_cache
def get_domain_config(path: str = "config/domain.yaml") -> DomainConfig:
    return load_domain_config(Path(path))

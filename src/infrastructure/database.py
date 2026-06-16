from collections.abc import Sequence
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.core.config import Settings, get_settings
from src.domain.config import DomainConfig, get_domain_config
from src.infrastructure.sql_validator import SqlValidator


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    return create_engine(database_url, echo=echo, pool_pre_ping=True)


class Database:
    def __init__(self, engine: Engine, validator: SqlValidator) -> None:
        self.engine = engine
        self.validator = validator

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        domain_config: DomainConfig | None = None,
    ) -> "Database":
        settings = settings or get_settings()
        domain_config = domain_config or get_domain_config(str(settings.domain_config_path))
        database_url = str(settings.database_readonly_url or settings.database_url)
        engine = create_database_engine(database_url)
        validator = SqlValidator(
            allowed_schema=domain_config.schema.allowed_schema,
            allowed_functions=domain_config.schema.allowed_function_set,
            max_limit=settings.sql_max_limit,
        )
        return cls(engine=engine, validator=validator)

    def execute_select(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        validated = self.validator.validate(sql)
        with self.engine.connect() as connection:
            result = connection.execute(text(validated.sql), parameters or {})
            rows: Sequence[Any] = result.mappings().all()
            return [dict(row) for row in rows]

from dataclasses import dataclass
from typing import Protocol


class SqlExecutor(Protocol):
    def execute_select(
        self,
        sql: str,
        parameters: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        """Validate and execute a read-only SQL query."""


@dataclass(frozen=True)
class ToolResult:
    rows: list[dict[str, object]]
    sql: str

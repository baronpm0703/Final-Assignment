from dataclasses import dataclass, field
from typing import Any, Literal

from src.domain.intent import Language

ResponseType = Literal["answer", "clarification_needed", "out_of_scope", "unsafe"]
VisualizationType = Literal["bar_chart", "line_chart", "pie_chart", "table"]


@dataclass(frozen=True)
class Visualization:
    type: VisualizationType
    title: str
    data: list[dict[str, Any]]


@dataclass(frozen=True)
class AgentResponse:
    type: ResponseType
    answer: str
    language: Language
    visualization: Visualization | None = None
    sql_executed: str | None = None
    reasoning_steps: list[str] = field(default_factory=list)
    options: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "answer": self.answer,
            "language": self.language.value,
            "visualization": None
            if self.visualization is None
            else {
                "type": self.visualization.type,
                "title": self.visualization.title,
                "data": self.visualization.data,
            },
            "sql_executed": self.sql_executed,
            "reasoning_steps": self.reasoning_steps,
            "options": self.options,
        }

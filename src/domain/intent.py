from dataclasses import dataclass
from enum import StrEnum


class Intent(StrEnum):
    DATA_QUERY = "data_query"
    OUT_OF_SCOPE = "out_of_scope"
    CHITCHAT = "chitchat"
    UNSAFE = "unsafe"


class Language(StrEnum):
    VI = "vi"
    EN = "en"


@dataclass(frozen=True)
class IntentResult:
    intent: Intent
    language: Language
    confidence: float
    reason: str

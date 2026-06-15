import json
from pathlib import Path

from src.domain.intent import Intent


class KeywordRules:
    def __init__(self, signals: dict[str, list[str]]) -> None:
        self.signals = {key: [value.lower() for value in values] for key, values in signals.items()}

    @classmethod
    def from_file(cls, path: Path = Path("config/keyword_signals.json")) -> "KeywordRules":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def unsafe_match(self, text: str) -> str | None:
        lowered = text.lower()
        for signal in self.signals.get("unsafe", []):
            if signal in lowered:
                return signal
        return None

    def score(self, text: str, intent: Intent) -> int:
        lowered = text.lower()
        return sum(1 for signal in self.signals.get(intent.value, []) if signal in lowered)

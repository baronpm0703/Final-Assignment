import json
from pathlib import Path

from src.domain.intent import Intent


class IntentUtteranceStore:
    def __init__(self, utterances: dict[Intent, list[str]]) -> None:
        self.utterances = utterances

    @classmethod
    def load(cls, path: Path | str) -> "IntentUtteranceStore":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        utterances: dict[Intent, list[str]] = {}
        for intent_name, examples in raw.items():
            intent = Intent(intent_name)
            if not isinstance(examples, list) or not all(
                isinstance(example, str) for example in examples
            ):
                raise ValueError(f"Intent {intent_name} must contain a list of utterance strings.")
            utterances[intent] = examples
        return cls(utterances)

from src.domain.intent import IntentResult
from src.router.heuristic import HeuristicIntentClassifier
from src.router.language_detector import detect_language
from src.router.rules import KeywordRules


class IntentRouter:
    def __init__(self, classifier: HeuristicIntentClassifier) -> None:
        self.classifier = classifier

    @classmethod
    def default(cls) -> "IntentRouter":
        return cls(HeuristicIntentClassifier(KeywordRules.from_file()))

    def route(self, text: str) -> IntentResult:
        language = detect_language(text)
        intent, confidence, reason = self.classifier.classify(text)
        return IntentResult(
            intent=intent,
            language=language,
            confidence=confidence,
            reason=reason,
        )

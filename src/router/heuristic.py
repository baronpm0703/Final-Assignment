from src.domain.intent import Intent
from src.router.bm25_classifier import BM25IntentClassifier


class HeuristicIntentClassifier:
    def __init__(self, classifier: BM25IntentClassifier) -> None:
        self.classifier = classifier

    def classify(self, text: str) -> tuple[Intent, float, str]:
        result = self.classifier.classify(text)
        return result.intent, result.confidence, result.reason

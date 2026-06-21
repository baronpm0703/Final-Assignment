from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from src.domain.intent import Intent
from src.router.tokenizer import MultilingualTokenizer
from src.router.utterance_store import IntentUtteranceStore


@dataclass(frozen=True)
class IntentClassification:
    intent: Intent
    confidence: float
    reason: str


class BM25IntentClassifier:
    def __init__(
        self,
        utterance_store: IntentUtteranceStore,
        tokenizer: MultilingualTokenizer | None = None,
    ) -> None:
        self.tokenizer = tokenizer or MultilingualTokenizer()
        self._documents: list[list[str]] = []
        self._labels: list[Intent] = []
        self._texts: list[str] = []
        for intent, examples in utterance_store.utterances.items():
            for example in examples:
                tokens = self.tokenizer.tokenize(example)
                if tokens:
                    self._documents.append(tokens)
                    self._labels.append(intent)
                    self._texts.append(example)
        self._bm25 = BM25Okapi(self._documents) if self._documents else None

    def classify(self, text: str) -> IntentClassification:
        query_tokens = self.tokenizer.tokenize(text)
        if not query_tokens or self._bm25 is None:
            return IntentClassification(Intent.OUT_OF_SCOPE, 0.0, "bm25 no tokens")

        scores = self._bm25.get_scores(query_tokens)
        if len(scores) == 0:
            return IntentClassification(Intent.OUT_OF_SCOPE, 0.0, "bm25 empty corpus")

        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
        best_index, best_score = ranked[0]
        if best_score <= 0:
            return IntentClassification(Intent.OUT_OF_SCOPE, 0.0, "bm25 no lexical match")

        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        confidence = self._confidence(float(best_score), float(second_score))
        return IntentClassification(
            intent=self._labels[best_index],
            confidence=confidence,
            reason=(
                f"bm25 confidence={confidence:.3f}; "
                f"matched={self._texts[best_index]!r}"
            ),
        )

    def _confidence(self, best_score: float, second_score: float) -> float:
        score_confidence = best_score / (best_score + 1.0)
        margin_confidence = (best_score - second_score) / (best_score + 1.0)
        return min(0.99, max(0.0, 0.75 * score_confidence + 0.25 * margin_confidence))

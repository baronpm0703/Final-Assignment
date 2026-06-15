from src.domain.intent import Intent
from src.router.rules import KeywordRules


class HeuristicIntentClassifier:
    def __init__(self, rules: KeywordRules) -> None:
        self.rules = rules

    def classify(self, text: str) -> tuple[Intent, float, str]:
        unsafe_signal = self.rules.unsafe_match(text)
        if unsafe_signal:
            return Intent.UNSAFE, 1.0, f"unsafe signal: {unsafe_signal}"

        scores = {
            Intent.DATA_QUERY: self.rules.score(text, Intent.DATA_QUERY),
            Intent.OUT_OF_SCOPE: self.rules.score(text, Intent.OUT_OF_SCOPE),
            Intent.CHITCHAT: self.rules.score(text, Intent.CHITCHAT),
        }
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]

        if best_score == 0:
            return Intent.OUT_OF_SCOPE, 0.4, "no call-center signal"

        if best_intent == Intent.DATA_QUERY and scores[Intent.OUT_OF_SCOPE] > best_score:
            return Intent.OUT_OF_SCOPE, 0.8, "out-of-scope signal dominates"

        confidence = min(0.95, 0.55 + best_score * 0.15)
        return best_intent, confidence, f"keyword score={best_score}"

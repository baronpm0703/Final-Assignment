from src.domain.config import DomainConfig, get_domain_config
from src.domain.intent import IntentResult
from src.infrastructure.llm.ports import ChatCompletionPort
from src.router.bm25_classifier import BM25IntentClassifier
from src.router.heuristic import HeuristicIntentClassifier
from src.router.language_detector import detect_language
from src.router.llm_intent_classifier import LLMIntentClassifier
from src.router.utterance_store import IntentUtteranceStore


class IntentRouter:
    def __init__(
        self,
        classifier: HeuristicIntentClassifier,
        *,
        confidence_threshold: float,
        llm_classifier: LLMIntentClassifier | None = None,
    ) -> None:
        self.classifier = classifier
        self.confidence_threshold = confidence_threshold
        self.llm_classifier = llm_classifier

    @classmethod
    def default(
        cls,
        domain_config: DomainConfig | None = None,
        *,
        llm: ChatCompletionPort | None = None,
        llm_model: str | None = None,
    ) -> "IntentRouter":
        domain_config = domain_config or get_domain_config()
        utterances = IntentUtteranceStore.load(domain_config.router.intent_utterances_path)
        llm_classifier = None
        if domain_config.router.llm_fallback_enabled and llm is not None and llm_model is not None:
            llm_classifier = LLMIntentClassifier(
                llm=llm,
                llm_model=llm_model,
                domain_config=domain_config,
            )
        return cls(
            HeuristicIntentClassifier(BM25IntentClassifier(utterances)),
            confidence_threshold=domain_config.router.bm25_confidence_threshold,
            llm_classifier=llm_classifier,
        )

    def route(self, text: str) -> IntentResult:
        language = detect_language(text)
        intent, confidence, reason = self.classifier.classify(text)
        if confidence < self.confidence_threshold and self.llm_classifier is not None:
            print("Call llm-fallback")
            llm_result = self.llm_classifier.classify(text, heuristic_reason=reason)
            intent, confidence, reason = (
                llm_result.intent,
                llm_result.confidence,
                f"{reason}; {llm_result.reason}",
            )
        return IntentResult(
            intent=intent,
            language=language,
            confidence=confidence,
            reason=reason,
        )

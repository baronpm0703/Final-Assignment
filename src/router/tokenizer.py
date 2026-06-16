import re
import unicodedata
from collections.abc import Callable

TOKEN_PATTERN = re.compile(r"[\w]+", re.UNICODE)
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "by",
    "for",
    "i",
    "is",
    "me",
    "of",
    "the",
    "to",
    "your",
    "ban",
    "bạn",
    "can",
    "cần",
    "cho",
    "cua",
    "của",
    "la",
    "là",
    "toi",
    "tôi",
    "xem",
}


class MultilingualTokenizer:
    def __init__(self, word_tokenize: Callable[[str], list[str]] | None = None) -> None:
        self._word_tokenize = word_tokenize or self._load_vietnamese_tokenizer()

    def tokenize(self, text: str) -> list[str]:
        normalized = unicodedata.normalize("NFKC", text).casefold()
        raw_tokens = self._tokenize_words(normalized)
        tokens: list[str] = []
        for raw_token in raw_tokens:
            parts = TOKEN_PATTERN.findall(raw_token.casefold())
            for part in parts:
                if part in STOPWORDS:
                    continue
                tokens.append(part)
                if "_" in part:
                    tokens.extend(
                        segment
                        for segment in part.split("_")
                        if segment and segment not in STOPWORDS
                    )
        return tokens

    def _tokenize_words(self, text: str) -> list[str]:
        if self._word_tokenize is None:
            return TOKEN_PATTERN.findall(text)

        try:
            tokens = self._word_tokenize(text)
        except Exception:
            return TOKEN_PATTERN.findall(text)

        if isinstance(tokens, str):
            return tokens.split()
        return [str(token) for token in tokens]

    def _load_vietnamese_tokenizer(self) -> Callable[[str], list[str]] | None:
        try:
            from underthesea import word_tokenize
        except ImportError:
            return None
        return word_tokenize

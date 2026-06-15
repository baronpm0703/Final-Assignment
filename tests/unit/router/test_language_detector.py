from src.domain.intent import Language
from src.router.language_detector import detect_language


def test_detects_vietnamese_with_accents() -> None:
    assert detect_language("Hôm qua có bao nhiêu cuộc gọi?") == Language.VI


def test_detects_vietnamese_without_accents() -> None:
    assert detect_language("Hom qua co bao nhieu cuoc goi?") == Language.VI


def test_defaults_to_english() -> None:
    assert detect_language("Show average talk duration by agent") == Language.EN

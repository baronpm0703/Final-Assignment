from src.router.tokenizer import MultilingualTokenizer


def test_tokenizer_keeps_vietnamese_compounds_and_segments() -> None:
    tokenizer = MultilingualTokenizer(lambda text: ["tổng_đài", "SLA20", "agent"])

    tokens = tokenizer.tokenize("Tổng đài SLA20 agent")

    assert "tổng_đài" in tokens
    assert "tổng" in tokens
    assert "đài" in tokens
    assert "sla20" in tokens
    assert "agent" in tokens


def test_tokenizer_falls_back_to_unicode_regex() -> None:
    def broken_tokenizer(_: str) -> list[str]:
        raise RuntimeError("tokenizer unavailable")

    tokenizer = MultilingualTokenizer(broken_tokenizer)

    tokens = tokenizer.tokenize("Average talk duration by agent?")

    assert tokens == ["average", "talk", "duration", "agent"]

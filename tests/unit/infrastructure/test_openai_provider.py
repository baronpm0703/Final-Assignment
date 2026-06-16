from src.infrastructure.llm.openai_provider import _parse_tool_arguments


def test_parse_tool_arguments_accepts_openai_json_string() -> None:
    assert _parse_tool_arguments('{"sql":"SELECT 1"}') == {"sql": "SELECT 1"}


def test_parse_tool_arguments_rejects_invalid_json_string() -> None:
    assert _parse_tool_arguments("{invalid") == {}

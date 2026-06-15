from src.utils.formatting import compact_table, percent, seconds


def test_percent_formats_ratio() -> None:
    assert percent(0.1234) == "12.34%"


def test_seconds_formats_number() -> None:
    assert seconds(42.2) == "42s"


def test_compact_table_formats_rows() -> None:
    output = compact_table([{"name": "A", "count": 2}])

    assert "name | count" in output
    assert "A | 2" in output

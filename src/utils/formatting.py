from typing import Any


def percent(value: float | int | None, *, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{float(value) * 100:.{digits}f}%"


def seconds(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.0f}s"


def compact_table(rows: list[dict[str, Any]], *, max_rows: int = 5) -> str:
    if not rows:
        return "Khong co du lieu."

    columns = list(rows[0].keys())
    lines = [" | ".join(columns)]
    for row in rows[:max_rows]:
        lines.append(" | ".join(str(row.get(column, "")) for column in columns))
    return "\n".join(lines)

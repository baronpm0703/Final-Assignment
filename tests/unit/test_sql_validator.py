import pytest

from src.core.errors import AppError, ErrorCode
from src.infrastructure.sql_validator import SqlValidator


def assert_error_code(sql: str, code: ErrorCode) -> None:
    validator = SqlValidator(max_limit=1000)
    with pytest.raises(AppError) as exc_info:
        validator.validate(sql)
    assert exc_info.value.code == code


def test_allows_basic_select_with_limit() -> None:
    validated = SqlValidator().validate(
        """
        SELECT call_id, calling_number, call_start
        FROM distribution_call
        WHERE call_type = 'Inbound'
        ORDER BY call_start
        LIMIT 100
        """
    )

    assert validated.limit == 100
    assert validated.tables == frozenset({"distribution_call"})


def test_allows_join_and_metric_functions() -> None:
    validated = SqlValidator().validate(
        """
        SELECT
            DATE_TRUNC('month', d.call_start) AS month,
            ROUND(COUNT(DISTINCT a.call_id)::numeric / NULLIF(COUNT(DISTINCT d.call_id), 0), 4)
                AS abandon_sys
        FROM distribution_call d
        LEFT JOIN abandoned_call a ON a.call_id = d.call_id
        GROUP BY month
        ORDER BY month
        LIMIT 12
        """
    )

    assert validated.limit == 12
    assert validated.tables == frozenset({"distribution_call", "abandoned_call"})


def test_blocks_empty_sql() -> None:
    assert_error_code("   ", ErrorCode.SQL_EMPTY)


def test_blocks_multiple_statements() -> None:
    assert_error_code(
        "SELECT call_id FROM distribution_call LIMIT 10; SELECT call_id FROM call_log LIMIT 10",
        ErrorCode.SQL_MULTIPLE_STATEMENTS,
    )


def test_blocks_non_select_statements() -> None:
    assert_error_code("DELETE FROM distribution_call", ErrorCode.SQL_ONLY_SELECT_ALLOWED)


def test_blocks_unknown_table() -> None:
    assert_error_code("SELECT id FROM users LIMIT 10", ErrorCode.SQL_TABLE_NOT_ALLOWED)


def test_blocks_unknown_column() -> None:
    assert_error_code(
        "SELECT password FROM distribution_call LIMIT 10",
        ErrorCode.SQL_COLUMN_NOT_ALLOWED,
    )


def test_blocks_unknown_qualified_column() -> None:
    assert_error_code(
        "SELECT d.password FROM distribution_call d LIMIT 10",
        ErrorCode.SQL_COLUMN_NOT_ALLOWED,
    )


def test_blocks_disallowed_function() -> None:
    assert_error_code(
        "SELECT pg_sleep(1) FROM distribution_call LIMIT 10",
        ErrorCode.SQL_FUNCTION_NOT_ALLOWED,
    )


def test_requires_limit() -> None:
    assert_error_code("SELECT call_id FROM distribution_call", ErrorCode.SQL_LIMIT_REQUIRED)


def test_blocks_limit_above_maximum() -> None:
    assert_error_code(
        "SELECT call_id FROM distribution_call LIMIT 5000",
        ErrorCode.SQL_LIMIT_TOO_HIGH,
    )

from src.core.errors import ERROR_MESSAGES, AppError, ErrorCode


def test_every_error_code_has_message() -> None:
    assert set(ERROR_MESSAGES) == set(ErrorCode)


def test_app_error_uses_default_message() -> None:
    error = AppError(ErrorCode.SQL_EMPTY)

    assert error.code == ErrorCode.SQL_EMPTY
    assert error.message == ERROR_MESSAGES[ErrorCode.SQL_EMPTY]

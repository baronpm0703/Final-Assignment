from enum import StrEnum


class ErrorCode(StrEnum):
    CONFIG_INVALID = "CONFIG_INVALID"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    SQL_EMPTY = "SQL_EMPTY"
    SQL_PARSE_ERROR = "SQL_PARSE_ERROR"
    SQL_ONLY_SELECT_ALLOWED = "SQL_ONLY_SELECT_ALLOWED"
    SQL_MULTIPLE_STATEMENTS = "SQL_MULTIPLE_STATEMENTS"
    SQL_TABLE_NOT_ALLOWED = "SQL_TABLE_NOT_ALLOWED"
    SQL_COLUMN_NOT_ALLOWED = "SQL_COLUMN_NOT_ALLOWED"
    SQL_FUNCTION_NOT_ALLOWED = "SQL_FUNCTION_NOT_ALLOWED"
    SQL_LIMIT_REQUIRED = "SQL_LIMIT_REQUIRED"
    SQL_LIMIT_TOO_HIGH = "SQL_LIMIT_TOO_HIGH"
    LLM_PROVIDER_UNSUPPORTED = "LLM_PROVIDER_UNSUPPORTED"
    LLM_MODEL_NOT_ALLOWED = "LLM_MODEL_NOT_ALLOWED"
    LLM_API_KEY_MISSING = "LLM_API_KEY_MISSING"
    LLM_REQUEST_FAILED = "LLM_REQUEST_FAILED"
    ROUTER_UNSAFE_INPUT = "ROUTER_UNSAFE_INPUT"
    CHAT_EMPTY_MESSAGE = "CHAT_EMPTY_MESSAGE"


ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.CONFIG_INVALID: "Application configuration is invalid.",
    ErrorCode.DATABASE_UNAVAILABLE: "Database is unavailable.",
    ErrorCode.SQL_EMPTY: "SQL query is empty.",
    ErrorCode.SQL_PARSE_ERROR: "SQL query could not be parsed.",
    ErrorCode.SQL_ONLY_SELECT_ALLOWED: "Only read-only SELECT queries are allowed.",
    ErrorCode.SQL_MULTIPLE_STATEMENTS: "Only a single SQL statement is allowed.",
    ErrorCode.SQL_TABLE_NOT_ALLOWED: "SQL references a table outside the configured schema.",
    ErrorCode.SQL_COLUMN_NOT_ALLOWED: "SQL references a column outside the configured schema.",
    ErrorCode.SQL_FUNCTION_NOT_ALLOWED: "SQL uses a function that is not allowed.",
    ErrorCode.SQL_LIMIT_REQUIRED: "SQL query must include a LIMIT clause.",
    ErrorCode.SQL_LIMIT_TOO_HIGH: "SQL query LIMIT exceeds the configured maximum.",
    ErrorCode.LLM_PROVIDER_UNSUPPORTED: "LLM provider is not supported.",
    ErrorCode.LLM_MODEL_NOT_ALLOWED: "LLM model is not allowed.",
    ErrorCode.LLM_API_KEY_MISSING: "LLM provider API key is missing.",
    ErrorCode.LLM_REQUEST_FAILED: "LLM provider request failed.",
    ErrorCode.ROUTER_UNSAFE_INPUT: "Input failed safety checks.",
    ErrorCode.CHAT_EMPTY_MESSAGE: "Chat message must not be empty.",
}


class AppError(Exception):
    def __init__(self, code: ErrorCode, message: str | None = None) -> None:
        self.code = code
        self.message = message or ERROR_MESSAGES[code]
        super().__init__(self.message)

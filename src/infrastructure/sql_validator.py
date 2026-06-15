from dataclasses import dataclass

import sqlglot
from sqlglot import exp

from src.core.errors import AppError, ErrorCode

ALLOWED_SCHEMA: dict[str, set[str]] = {
    "distribution_call": {
        "call_id",
        "calling_number",
        "call_type",
        "queue",
        "agent_id",
        "call_start",
        "call_end",
        "waiting_queue_dur",
        "ring_dur",
        "talk_dur",
        "wrapup_dur",
        "hold_dur",
        "call_dur",
        "agent_disconnect",
    },
    "call_log": {
        "call_id",
        "request_id",
        "request_code",
        "create_date",
        "create_agent",
        "detail",
    },
    "request_code": {"code", "name", "description"},
    "agent": {"agent_id", "agent_name", "agent_tl"},
    "abandoned_call": {
        "call_id",
        "abd_id",
        "abandoned_time",
        "abandoned_type",
        "waiting_dur",
        "ring_dur",
        "call_dur",
        "agent_id",
    },
}

ALLOWED_FUNCTIONS = {
    "avg",
    "cast",
    "coalesce",
    "count",
    "date_trunc",
    "extract",
    "max",
    "min",
    "nullif",
    "round",
    "sum",
    "timestamp_trunc",
}


@dataclass(frozen=True)
class ValidatedSql:
    sql: str
    limit: int
    tables: frozenset[str]


class SqlValidator:
    def __init__(
        self,
        *,
        allowed_schema: dict[str, set[str]] | None = None,
        allowed_functions: set[str] | None = None,
        max_limit: int = 1000,
    ) -> None:
        self.allowed_schema = allowed_schema or ALLOWED_SCHEMA
        self.allowed_functions = allowed_functions or ALLOWED_FUNCTIONS
        self.max_limit = max_limit

    def validate(self, sql: str) -> ValidatedSql:
        raw_sql = sql.strip()
        if not raw_sql:
            raise AppError(ErrorCode.SQL_EMPTY)

        try:
            statements = sqlglot.parse(raw_sql, read="postgres")
        except sqlglot.errors.ParseError as exc:
            raise AppError(ErrorCode.SQL_PARSE_ERROR, str(exc)) from exc

        statements = [statement for statement in statements if statement is not None]
        if len(statements) != 1:
            raise AppError(ErrorCode.SQL_MULTIPLE_STATEMENTS)

        statement = statements[0]
        if not isinstance(statement, exp.Select):
            raise AppError(ErrorCode.SQL_ONLY_SELECT_ALLOWED)

        tables = self._validate_tables(statement)
        aliases = self._collect_select_aliases(statement)
        self._validate_columns(statement, aliases)
        self._validate_functions(statement)
        limit = self._validate_limit(statement)

        return ValidatedSql(
            sql=statement.sql(dialect="postgres"),
            limit=limit,
            tables=frozenset(tables),
        )

    def _validate_tables(self, statement: exp.Expression) -> set[str]:
        tables: set[str] = set()
        for table in statement.find_all(exp.Table):
            table_name = table.name.lower()
            if table_name not in self.allowed_schema:
                raise AppError(
                    ErrorCode.SQL_TABLE_NOT_ALLOWED,
                    f"Table '{table_name}' is not allowed.",
                )
            tables.add(table_name)
        return tables

    def _collect_select_aliases(self, statement: exp.Select) -> set[str]:
        aliases: set[str] = set()
        for expression in statement.expressions:
            if isinstance(expression, exp.Alias) and expression.alias:
                aliases.add(expression.alias.lower())
        return aliases

    def _validate_columns(self, statement: exp.Expression, aliases: set[str]) -> None:
        table_aliases = self._table_aliases(statement)
        all_columns = set().union(*self.allowed_schema.values())

        for column in statement.find_all(exp.Column):
            column_name = column.name.lower()
            qualifier = column.table.lower() if column.table else None

            if qualifier:
                table_name = table_aliases.get(qualifier, qualifier)
                allowed_columns = self.allowed_schema.get(table_name)
                if allowed_columns is None or column_name not in allowed_columns:
                    raise AppError(
                        ErrorCode.SQL_COLUMN_NOT_ALLOWED,
                        f"Column '{column.sql(dialect='postgres')}' is not allowed.",
                    )
                continue

            if column_name not in all_columns and column_name not in aliases:
                raise AppError(
                    ErrorCode.SQL_COLUMN_NOT_ALLOWED,
                    f"Column '{column_name}' is not allowed.",
                )

    def _table_aliases(self, statement: exp.Expression) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for table in statement.find_all(exp.Table):
            table_name = table.name.lower()
            aliases[table_name] = table_name
            if table.alias:
                aliases[table.alias.lower()] = table_name
        return aliases

    def _validate_functions(self, statement: exp.Expression) -> None:
        for function in statement.find_all(exp.Func):
            function_name = function.sql_name().lower()
            if function_name not in self.allowed_functions:
                raise AppError(
                    ErrorCode.SQL_FUNCTION_NOT_ALLOWED,
                    f"Function '{function_name}' is not allowed.",
                )

    def _validate_limit(self, statement: exp.Select) -> int:
        limit_expression = statement.args.get("limit")
        if limit_expression is None:
            raise AppError(ErrorCode.SQL_LIMIT_REQUIRED)

        value_expression = limit_expression.expression
        if value_expression is None:
            raise AppError(ErrorCode.SQL_LIMIT_REQUIRED)

        try:
            limit = int(value_expression.name)
        except (TypeError, ValueError) as exc:
            raise AppError(
                ErrorCode.SQL_LIMIT_REQUIRED,
                "LIMIT must be a positive integer literal.",
            ) from exc

        if limit < 1:
            raise AppError(
                ErrorCode.SQL_LIMIT_REQUIRED,
                "LIMIT must be greater than 0.",
            )
        if limit > self.max_limit:
            raise AppError(
                ErrorCode.SQL_LIMIT_TOO_HIGH,
                f"LIMIT {limit} exceeds maximum {self.max_limit}.",
            )
        return limit

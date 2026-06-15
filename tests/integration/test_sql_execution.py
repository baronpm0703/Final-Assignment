import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from src.core.config import Settings
from src.infrastructure.database import Database, create_database_engine
from src.infrastructure.sql_validator import SqlValidator


@pytest.mark.integration
def test_execute_select_returns_rows_from_postgres() -> None:
    settings = Settings()
    engine = create_database_engine(str(settings.database_url))

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")

    database = Database(engine=engine, validator=SqlValidator(max_limit=settings.sql_max_limit))
    rows = database.execute_select(
        """
        SELECT call_id, calling_number
        FROM distribution_call
        ORDER BY call_id
        LIMIT 5
        """
    )

    assert rows
    assert {"call_id", "calling_number"} <= rows[0].keys()

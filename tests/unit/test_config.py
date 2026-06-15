import pytest
from pydantic import ValidationError

from src.core.config import Settings


def test_settings_defaults_are_valid() -> None:
    settings = Settings()

    assert settings.app_name == "Call Center Analytics Agent"
    assert settings.app_env == "local"
    assert settings.sql_default_limit == 100
    assert settings.sql_max_limit == 1000


def test_sql_limits_must_be_positive() -> None:
    with pytest.raises(ValidationError, match="SQL_MAX_LIMIT"):
        Settings(sql_max_limit=0)

    with pytest.raises(ValidationError, match="SQL_DEFAULT_LIMIT"):
        Settings(sql_default_limit=0)


def test_default_limit_must_not_exceed_max_limit() -> None:
    with pytest.raises(ValidationError, match="SQL_DEFAULT_LIMIT"):
        Settings(sql_max_limit=50, sql_default_limit=100)

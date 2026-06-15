from pathlib import Path

from sqlalchemy import create_engine, text

from src.core.config import get_settings


def main() -> None:
    settings = get_settings()
    sql_path = Path(__file__).parent / "sql" / "init.sql"
    engine = create_engine(str(settings.database_url), isolation_level="AUTOCOMMIT")

    with engine.connect() as connection:
        connection.execute(text(sql_path.read_text(encoding="utf-8")))

    print(f"Initialized database using {sql_path}")


if __name__ == "__main__":
    main()

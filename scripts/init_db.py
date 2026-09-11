"""Create the local SQLite database and the current MVP tables."""

from sqlalchemy import inspect

from postupashki_mvp.database import engine, init_db


def main() -> None:
    init_db()
    tables = inspect(engine).get_table_names()

    print(f"Database: {engine.url}")
    print("Created tables:")
    for table in tables:
        print(f"- {table}")


if __name__ == "__main__":
    main()

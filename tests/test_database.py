from sqlalchemy import create_engine, inspect

from postupashki_mvp import models  # noqa: F401
from postupashki_mvp.database import Base


def test_minimal_schema_is_created() -> None:
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    assert set(inspect(test_engine).get_table_names()) == {
        "events",
        "leads",
        "orders",
        "payments",
        "placements",
    }

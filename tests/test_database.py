import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from postupashki_mvp import models  # noqa: F401
from postupashki_mvp.database import Base
from postupashki_mvp.models import Placement


def test_minimal_schema_is_created() -> None:
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    assert set(inspect(test_engine).get_table_names()) == {
        "events",
        "campaigns",
        "leads",
        "orders",
        "payments",
        "placements",
    }


def test_placement_requires_an_existing_campaign() -> None:
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        session.add(
            Placement(
                placement_id="placement_without_campaign",
                campaign_id="missing_campaign",
                channel_name="Demo channel",
                landing_url="https://example.com",
                is_synthetic=True,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from postupashki_mvp.database import Base
from postupashki_mvp.models import Campaign, Event, Lead, Order, Payment, Placement
from postupashki_mvp.services.analytics import (
    load_campaign_metrics,
    load_funnel_metrics,
)


def test_funnel_deduplicates_visitors_and_uses_global_last_touch() -> None:
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    started_at = datetime(2026, 9, 12, tzinfo=UTC)

    with Session(test_engine) as session:
        session.add_all(
            [
                Campaign(
                    campaign_id="campaign_a",
                    campaign_name="Same display name",
                    is_synthetic=True,
                ),
                Campaign(
                    campaign_id="campaign_b",
                    campaign_name="Same display name",
                    is_synthetic=True,
                ),
            ]
        )
        session.flush()

        session.add_all(
            [
                Placement(
                    placement_id="placement_a",
                    campaign_id="campaign_a",
                    channel_name="Channel A",
                    landing_url="https://example.com/a",
                    cost=Decimal(1000),
                    is_synthetic=True,
                ),
                Placement(
                    placement_id="placement_b",
                    campaign_id="campaign_b",
                    channel_name="Channel B",
                    landing_url="https://example.com/b",
                    cost=Decimal(1000),
                    is_synthetic=True,
                ),
            ]
        )
        session.flush()

        session.add_all(
            [
                Event(
                    event_name="ad_click",
                    occurred_at=started_at,
                    visitor_id="shared_visitor",
                    placement_id="placement_a",
                    is_synthetic=True,
                ),
                Event(
                    event_name="landing_view",
                    occurred_at=started_at + timedelta(minutes=1),
                    visitor_id="shared_visitor",
                    placement_id="placement_a",
                    is_synthetic=True,
                ),
                Event(
                    event_name="ad_click",
                    occurred_at=started_at + timedelta(minutes=2),
                    visitor_id="shared_visitor",
                    placement_id="placement_b",
                    is_synthetic=True,
                ),
                Event(
                    event_name="landing_view",
                    occurred_at=started_at + timedelta(minutes=3),
                    visitor_id="shared_visitor",
                    placement_id="placement_b",
                    is_synthetic=True,
                ),
                Event(
                    event_name="ad_click",
                    occurred_at=started_at + timedelta(minutes=4),
                    visitor_id="campaign_a_only",
                    placement_id="placement_a",
                    is_synthetic=True,
                ),
            ]
        )

        lead = Lead(
            visitor_id="shared_visitor",
            created_at=started_at + timedelta(minutes=10),
            is_synthetic=True,
        )
        session.add(lead)
        session.flush()

        order = Order(
            lead_id=lead.lead_id,
            course_name="Demo course",
            status="paid",
            created_at=started_at + timedelta(minutes=20),
            is_synthetic=True,
        )
        session.add(order)
        session.flush()

        session.add(
            Payment(
                order_id=order.order_id,
                amount=Decimal(8950),
                status="succeeded",
                paid_at=started_at + timedelta(minutes=30),
                is_synthetic=True,
            )
        )
        session.commit()

    all_campaigns = load_funnel_metrics(db_engine=test_engine)
    campaign_a = load_funnel_metrics("campaign_a", test_engine)
    campaign_b = load_funnel_metrics("campaign_b", test_engine)
    campaign_metrics = load_campaign_metrics(test_engine).set_index("campaign_id")

    assert all_campaigns["clicks"] == 3
    assert all_campaigns["click_users"] == 2
    assert all_campaigns["landing_users"] == 1
    assert all_campaigns["leads"] == 1
    assert all_campaigns["orders"] == 1
    assert all_campaigns["payments"] == 1

    assert campaign_a["click_users"] == 2
    assert campaign_a["leads"] == 0
    assert campaign_a["payments"] == 0

    assert campaign_b["click_users"] == 1
    assert campaign_b["leads"] == 1
    assert campaign_b["payments"] == 1

    assert campaign_metrics.loc["campaign_a", "campaign_name"] == "Same display name"
    assert campaign_metrics.loc["campaign_a", "click_users"] == 2
    assert campaign_metrics.loc["campaign_a", "leads"] == 0
    assert campaign_metrics.loc["campaign_a", "attributed_revenue"] == 0

    assert campaign_metrics.loc["campaign_b", "campaign_name"] == "Same display name"
    assert campaign_metrics.loc["campaign_b", "click_users"] == 1
    assert campaign_metrics.loc["campaign_b", "leads"] == 1
    assert campaign_metrics.loc["campaign_b", "payments"] == 1
    assert campaign_metrics.loc["campaign_b", "attributed_revenue"] == 8950

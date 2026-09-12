from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from postupashki_mvp import api
from postupashki_mvp.database import Base
from postupashki_mvp.models import Campaign, Event, Lead, Order, Payment, Placement
from postupashki_mvp.services.attribution import attribute_payments
from postupashki_mvp.services.reporting import (
    CampaignNotFoundError,
    build_analytics_report,
    load_contract_tables,
    load_data_quality_issues,
)


@pytest.fixture
def report_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    click_at = datetime(2026, 1, 1, tzinfo=UTC)
    lead_at = click_at + timedelta(days=1)
    order_at = lead_at + timedelta(hours=1)
    paid_at = order_at + timedelta(hours=1)

    with Session(engine) as session:
        session.add(
            Campaign(
                campaign_id="cmp_demo",
                campaign_name="Demo",
                created_at=click_at,
                is_synthetic=True,
            )
        )
        session.flush()
        session.add(
            Placement(
                placement_id="plc_demo",
                campaign_id="cmp_demo",
                channel_name="Telegram",
                target_product="ML Start",
                landing_url="https://example.com",
                cost=Decimal("100.00"),
                created_at=click_at,
                is_synthetic=True,
            )
        )
        session.flush()
        session.add_all(
            [
                Event(
                    event_id="evt_click",
                    event_name="ad_click",
                    occurred_at=click_at,
                    visitor_id="visitor_demo",
                    placement_id="plc_demo",
                    properties={},
                    is_synthetic=True,
                ),
                Event(
                    event_id="evt_landing",
                    event_name="landing_view",
                    occurred_at=click_at + timedelta(minutes=1),
                    visitor_id="visitor_demo",
                    placement_id="plc_demo",
                    properties={},
                    is_synthetic=True,
                ),
                Event(
                    event_id="evt_course",
                    event_name="course_selected",
                    occurred_at=click_at + timedelta(minutes=2),
                    visitor_id="visitor_demo",
                    placement_id="plc_demo",
                    properties={},
                    is_synthetic=True,
                ),
                Lead(
                    lead_id="lead_demo",
                    lead_token="lead_token_demo",
                    visitor_id="visitor_demo",
                    created_at=lead_at,
                    is_synthetic=True,
                ),
            ]
        )
        session.flush()
        session.add(
            Order(
                order_id="order_demo",
                lead_id="lead_demo",
                course_name="ML Start",
                status="paid",
                created_at=order_at,
                is_synthetic=True,
            )
        )
        session.flush()
        session.add(
            Payment(
                payment_id="payment_demo",
                order_id="order_demo",
                amount=Decimal("250.00"),
                status="succeeded",
                paid_at=paid_at,
                is_synthetic=True,
            )
        )
        session.commit()
    return engine


@pytest.mark.parametrize("model", ["last_touch", "first_touch", "linear"])
def test_unified_report_uses_one_metric_pipeline(report_engine, model) -> None:
    report = build_analytics_report(
        is_synthetic=True,
        attribution_model=model,
        db_engine=report_engine,
    )

    overall = report["overall_funnel"].iloc[0]
    campaign = report["campaign_metrics"].iloc[0]
    placement = report["placement_metrics"].iloc[0]

    assert report["campaigns_count"] == 1
    assert report["placements_count"] == 1
    assert overall.successful_payments == 1
    assert overall.total_revenue == 250
    assert campaign.placements == 1
    assert campaign.attributed_revenue == placement.attributed_revenue == 250
    assert campaign.romi_pct == placement.romi_pct == 150
    assert report["quality_issues"].empty


def test_report_filters_cohort_and_campaign(report_engine) -> None:
    tables = load_contract_tables(report_engine)
    real_payment_attribution = attribute_payments(
        tables["events"],
        tables["leads"],
        tables["orders"],
        tables["payments"],
        tables["placements"],
        is_synthetic=False,
    )
    real = build_analytics_report(
        is_synthetic=False,
        attribution_model="last_touch",
        db_engine=report_engine,
    )
    selected = build_analytics_report(
        is_synthetic=True,
        attribution_model="last_touch",
        campaign_id="cmp_demo",
        db_engine=report_engine,
    )

    assert real_payment_attribution.empty
    assert real["campaigns_count"] == real["placements_count"] == 0
    assert selected["funnel"].iloc[0].campaign_id == "cmp_demo"
    with pytest.raises(CampaignNotFoundError):
        build_analytics_report(
            is_synthetic=True,
            attribution_model="last_touch",
            campaign_id="missing",
            db_engine=report_engine,
        )


def test_analytics_api_contract(monkeypatch, report_engine) -> None:
    real_builder = build_analytics_report

    def test_builder(**kwargs):
        return real_builder(**kwargs, db_engine=report_engine)

    monkeypatch.setattr(api, "build_analytics_report", test_builder)
    monkeypatch.setattr(
        api,
        "load_data_quality_issues",
        lambda **kwargs: load_data_quality_issues(
            **kwargs, db_engine=report_engine
        ),
    )
    client = TestClient(api.app)

    summary = client.get("/analytics/summary").json()
    campaigns = client.get("/analytics/campaigns").json()
    funnel = client.get("/analytics/funnel", params={"campaign_id": "cmp_demo"}).json()
    placements = client.get("/analytics/placements").json()
    quality = client.get("/data-quality/summary").json()

    assert summary["meta"]["attribution_window_days"] == 30
    assert summary["data"]["total_revenue"] == "250.00"
    assert campaigns["data"]["count"] == placements["data"]["count"] == 1
    assert funnel["data"]["stages"][-1]["value"] == 1
    assert quality["data"]["status"] == "ok"
    assert client.get(
        "/analytics/summary", params={"campaign_id": "missing"}
    ).status_code == 404

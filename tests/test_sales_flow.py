from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from postupashki_mvp import api
from postupashki_mvp.database import Base
from postupashki_mvp.models import Event, Lead, Order, Payment


def make_client(monkeypatch) -> tuple[TestClient, sessionmaker]:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    test_session = sessionmaker(bind=test_engine, expire_on_commit=False)
    monkeypatch.setattr(api, "SessionLocal", test_session)
    return TestClient(api.app), test_session


def create_tracking_context(client: TestClient) -> tuple[dict, dict]:
    campaign_response = client.post(
        "/campaigns",
        json={"campaign_name": "Full funnel", "is_synthetic": True},
    )
    campaign = campaign_response.json()
    placement_response = client.post(
        "/placements",
        json={
            "campaign_id": campaign["campaign_id"],
            "channel_name": "Demo channel",
            "target_product": "ML Start",
            "landing_url": "https://example.com/course",
            "cost": 1000,
        },
    )
    placement = placement_response.json()
    click_response = client.get(placement["tracking_url"], follow_redirects=False)
    assert click_response.status_code == 302
    return campaign, placement


def test_sales_flow_writes_contract_v1_events(monkeypatch) -> None:
    client, test_session = make_client(monkeypatch)
    campaign, placement = create_tracking_context(client)
    visitor_id = client.cookies["postupashki_vid"]

    lead_response = client.post(
        "/manager-link",
        json={
            "placement_id": placement["placement_id"],
            "session_id": "session_full_funnel",
            "course_id": "course_ml_start",
            "course_name": "ML Start",
        },
    )
    assert lead_response.status_code == 201
    lead = lead_response.json()
    assert lead["visitor_id"] == visitor_id
    assert lead["manager_click_event_id"]
    assert lead["lead_created_event_id"]

    order_response = client.post(
        "/orders",
        json={
            "lead_token": lead["lead_token"],
            "course_id": "course_ml_start",
            "course_name": "ML Start",
        },
    )
    assert order_response.status_code == 201
    order = order_response.json()
    assert order["event_id"]

    payment_response = client.post(
        "/payments",
        json={"order_id": order["order_id"], "amount": 8950, "currency": "RUB"},
    )
    assert payment_response.status_code == 201
    payment = payment_response.json()
    assert payment["currency"] == "RUB"
    assert payment["event_id"]

    with test_session() as session:
        stored_lead = session.get(Lead, lead["lead_id"])
        stored_order = session.get(Order, order["order_id"])
        stored_payment = session.get(Payment, payment["payment_id"])
        events = session.scalars(select(Event).order_by(Event.occurred_at)).all()

    assert stored_lead is not None
    assert stored_order.status == "paid"
    assert stored_payment.status == "succeeded"
    assert [event.event_name for event in events] == [
        "ad_click",
        "manager_click",
        "lead_created",
        "order_created",
        "payment_succeeded",
    ]

    by_name = {event.event_name: event for event in events}
    for event_name in ("manager_click", "lead_created", "order_created", "payment_succeeded"):
        event = by_name[event_name]
        assert event.visitor_id == visitor_id
        assert event.placement_id == placement["placement_id"]
        assert event.is_synthetic is True
        assert event.properties["lead_id"] == lead["lead_id"]

    assert by_name["order_created"].properties["order_id"] == order["order_id"]
    assert by_name["payment_succeeded"].properties == {
        "lead_id": lead["lead_id"],
        "order_id": order["order_id"],
        "payment_id": payment["payment_id"],
        "amount": "8950",
        "currency": "RUB",
        "status": "succeeded",
        "paid_at": payment["paid_at"],
    }
    assert by_name["ad_click"].properties["campaign_id"] == campaign["campaign_id"]


def test_sales_flow_rejects_duplicates_and_manual_manager_click(monkeypatch) -> None:
    client, _ = make_client(monkeypatch)
    _, placement = create_tracking_context(client)
    lead = client.post(
        "/manager-link",
        json={"placement_id": placement["placement_id"], "course_name": "ML Start"},
    ).json()
    order_payload = {"lead_token": lead["lead_token"], "course_name": "ML Start"}
    order = client.post("/orders", json=order_payload).json()
    payment_payload = {"order_id": order["order_id"], "amount": 8950}

    assert client.post("/orders", json=order_payload).status_code == 409
    assert client.post("/payments", json=payment_payload).status_code == 201
    assert client.post("/payments", json=payment_payload).status_code == 409
    assert (
        client.post(
            "/events",
            json={"event_name": "manager_click", "placement_id": placement["placement_id"]},
        ).status_code
        == 422
    )

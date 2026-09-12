from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from postupashki_mvp import api
from postupashki_mvp.database import Base
from postupashki_mvp.models import Event, Placement


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


def create_campaign(client: TestClient, name: str = "Demo campaign") -> dict:
    response = client.post(
        "/campaigns",
        json={"campaign_name": name, "is_synthetic": True},
    )
    assert response.status_code == 201
    return response.json()


def create_placement(client: TestClient, campaign_id: str) -> dict:
    response = client.post(
        "/placements",
        json={
            "campaign_id": campaign_id,
            "channel_name": "Demo channel",
            "target_product": "ML Start",
            "landing_url": "https://example.com/course",
            "cost": 25000,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_campaign_registry_allows_duplicate_display_names(monkeypatch) -> None:
    client, _ = make_client(monkeypatch)

    first = create_campaign(client, "Same display name")
    second = create_campaign(client, "Same display name")
    response = client.get("/campaigns")

    assert first["campaign_id"] != second["campaign_id"]
    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert {item["campaign_name"] for item in response.json()["items"]} == {"Same display name"}


def test_placement_requires_campaign_and_non_negative_cost(monkeypatch) -> None:
    client, _ = make_client(monkeypatch)
    payload = {
        "campaign_id": "missing_campaign",
        "channel_name": "Demo channel",
        "landing_url": "https://example.com/course",
        "cost": 100,
    }

    response = client.post("/placements", json=payload)
    assert response.status_code == 404
    assert response.json() == {"detail": "Campaign not found"}

    payload["cost"] = -1
    response = client.post("/placements", json=payload)
    assert response.status_code == 422


def test_registry_and_tracking_create_a_linked_click(monkeypatch) -> None:
    client, test_session = make_client(monkeypatch)
    campaign = create_campaign(client)
    placement = create_placement(client, campaign["campaign_id"])

    assert placement["campaign_id"] == campaign["campaign_id"]
    assert placement["campaign_name"] == campaign["campaign_name"]
    assert placement["tracking_url"].endswith(f"/t/{placement['placement_id']}")
    assert placement["cost"] == "25000.00"
    assert placement["is_synthetic"] is True

    listed = client.get(
        "/placements",
        params={"campaign_id": campaign["campaign_id"]},
    )
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert listed.json()["items"][0]["placement_id"] == placement["placement_id"]

    first_click = client.get(placement["tracking_url"], follow_redirects=False)
    second_click = client.get(placement["tracking_url"], follow_redirects=False)

    assert first_click.status_code == second_click.status_code == 302
    assert first_click.headers["location"] == "https://example.com/course"
    assert "postupashki_vid" in client.cookies

    with test_session() as session:
        stored_placement = session.get(Placement, placement["placement_id"])
        events = session.scalars(select(Event).order_by(Event.occurred_at)).all()

    assert stored_placement is not None
    assert stored_placement.is_synthetic is True
    assert len(events) == 2
    assert {event.event_name for event in events} == {"ad_click"}
    assert {event.visitor_id for event in events} == {client.cookies["postupashki_vid"]}
    assert {event.placement_id for event in events} == {placement["placement_id"]}
    assert {event.properties["campaign_id"] for event in events} == {campaign["campaign_id"]}


def test_placement_filter_rejects_unknown_campaign(monkeypatch) -> None:
    client, _ = make_client(monkeypatch)

    response = client.get("/placements", params={"campaign_id": "missing"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Campaign not found"}

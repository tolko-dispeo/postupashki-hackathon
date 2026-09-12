import csv
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROL_DIR = ROOT / "data" / "mock" / "control"
PLACEMENTS_PATH = CONTROL_DIR / "placements.csv"
EVENTS_PATH = CONTROL_DIR / "events.csv"

ALLOWED_EVENTS = {
    "ad_click", "landing_view", "course_view", "course_selected",
    "manager_click", "lead_created", "conversation_started",
    "order_created", "payment_succeeded", "course_access_granted",
}
PLACEMENT_COLUMNS = {
    "placement_id", "campaign_id", "campaign_name", "channel_id",
    "channel_name", "course_id", "course_name", "landing_url",
    "published_at", "cost", "is_synthetic",
}
EVENT_COLUMNS = {
    "event_id", "scenario_id", "occurred_at", "event_name", "visitor_id",
    "session_id", "placement_id", "properties", "is_synthetic",
}
PROJECT_CUTOFF = datetime(2026, 9, 12, 23, 59, 59, tzinfo=timezone.utc)
FULL_FUNNEL = [
    "ad_click", "landing_view", "course_view", "course_selected",
    "manager_click", "lead_created", "conversation_started",
    "order_created", "payment_succeeded", "course_access_granted",
]


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def parse_utc(value):
    assert value.endswith("Z"), f"Timestamp must end with Z: {value}"
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo == timezone.utc
    return parsed


def parsed_events():
    events = read_csv(EVENTS_PATH)
    for event in events:
        event["parsed_properties"] = json.loads(event["properties"])
    return events


def test_required_columns_are_present():
    with PLACEMENTS_PATH.open(encoding="utf-8", newline="") as file:
        placement_header = set(csv.DictReader(file).fieldnames or [])
    with EVENTS_PATH.open(encoding="utf-8", newline="") as file:
        event_header = set(csv.DictReader(file).fieldnames or [])
    assert PLACEMENT_COLUMNS <= placement_header
    assert EVENT_COLUMNS <= event_header


def test_primary_identifiers_are_unique():
    placements = read_csv(PLACEMENTS_PATH)
    events = read_csv(EVENTS_PATH)
    placement_ids = [row["placement_id"] for row in placements]
    event_ids = [row["event_id"] for row in events]
    assert len(placement_ids) == len(set(placement_ids))
    assert len(event_ids) == len(set(event_ids))


def test_only_contract_v1_events_are_used():
    event_names = {row["event_name"] for row in read_csv(EVENTS_PATH)}
    assert event_names == ALLOWED_EVENTS


def test_event_placements_exist_and_were_published_first():
    placements = {row["placement_id"]: row for row in read_csv(PLACEMENTS_PATH)}
    for event in read_csv(EVENTS_PATH):
        assert event["placement_id"] in placements
        assert parse_utc(placements[event["placement_id"]]["published_at"]) < parse_utc(event["occurred_at"])


def test_properties_are_valid_json_objects():
    for event in read_csv(EVENTS_PATH):
        assert isinstance(json.loads(event["properties"]), dict)


def test_events_are_chronological_inside_each_scenario():
    by_scenario = defaultdict(list)
    for event in read_csv(EVENTS_PATH):
        by_scenario[event["scenario_id"]].append(parse_utc(event["occurred_at"]))
    assert all(times == sorted(times) for times in by_scenario.values())


def test_control_dates_are_not_later_than_project_cutoff():
    placements = read_csv(PLACEMENTS_PATH)
    events = read_csv(EVENTS_PATH)
    assert all(parse_utc(row["published_at"]) <= PROJECT_CUTOFF for row in placements)
    assert all(parse_utc(row["occurred_at"]) <= PROJECT_CUTOFF for row in events)


def test_scenario_01_contains_the_full_funnel_in_order():
    event_names = [
        row["event_name"]
        for row in read_csv(EVENTS_PATH)
        if row["scenario_id"] == "scenario_01_full_funnel"
    ]
    assert event_names == FULL_FUNNEL


def test_stage_identifiers_and_relationships_are_present():
    events = parsed_events()
    leads = {e["parsed_properties"]["lead_id"]: e for e in events if e["event_name"] == "lead_created"}
    orders = {e["parsed_properties"]["order_id"]: e for e in events if e["event_name"] == "order_created"}

    for event in events:
        name = event["event_name"]
        properties = event["parsed_properties"]
        if name in {"lead_created", "conversation_started", "order_created", "payment_succeeded", "course_access_granted"}:
            assert properties.get("lead_id") in leads
        if name in {"order_created", "payment_succeeded", "course_access_granted"}:
            assert properties.get("order_id") in orders
        if name in {"payment_succeeded", "course_access_granted"}:
            assert properties.get("payment_id")
        if name == "order_created":
            assert leads[properties["lead_id"]]["visitor_id"] == event["visitor_id"]
        if name == "payment_succeeded":
            order = orders[properties["order_id"]]
            assert order["parsed_properties"]["lead_id"] == properties["lead_id"]


def test_successful_payments_and_expected_revenue():
    payments = [e for e in parsed_events() if e["event_name"] == "payment_succeeded"]
    assert len(payments) == 2
    assert sum(e["parsed_properties"]["amount"] for e in payments) == 85_800
    for payment in payments:
        properties = payment["parsed_properties"]
        assert properties["status"] == "succeeded"
        assert properties["amount"] > 0
        assert properties["currency"] == "RUB"
        assert properties["paid_at"]
        assert parse_utc(properties["paid_at"]) == parse_utc(payment["occurred_at"])


def test_expected_control_counts():
    placements = read_csv(PLACEMENTS_PATH)
    events = read_csv(EVENTS_PATH)
    assert len(placements) == 5
    assert len({row["campaign_id"] for row in placements}) == 2
    assert len({row["scenario_id"] for row in events}) == 4
    assert sum(row["event_name"] == "lead_created" for row in events) == 3
    assert sum(row["event_name"] == "order_created" for row in events) == 2
    assert sum(row["event_name"] == "payment_succeeded" for row in events) == 2


def test_all_rows_are_synthetic_and_placements_are_valid():
    placements = read_csv(PLACEMENTS_PATH)
    events = read_csv(EVENTS_PATH)
    assert all(row["is_synthetic"] == "true" for row in placements)
    assert all(row["is_synthetic"] == "true" for row in events)
    assert all(float(row["cost"]) >= 0 for row in placements)
    assert all(row["landing_url"] for row in placements)


def test_scenario_02_encodes_expected_last_touch_fixture():
    events = [e for e in parsed_events() if e["scenario_id"] == "scenario_02_multi_touch"]
    clicks = [e for e in events if e["event_name"] == "ad_click"]
    lead = next(e for e in events if e["event_name"] == "lead_created")
    payment = next(e for e in events if e["event_name"] == "payment_succeeded")
    assert len({event["visitor_id"] for event in events}) == 1
    assert [event["placement_id"] for event in clicks] == ["pl_001", "pl_005"]
    assert len({event["session_id"] for event in clicks}) == 2
    eligible = [
        e for e in clicks
        if timedelta(0) <= parse_utc(lead["occurred_at"]) - parse_utc(e["occurred_at"]) <= timedelta(days=30)
    ]
    assert max(eligible, key=lambda row: row["occurred_at"])["placement_id"] == "pl_005"
    assert payment["placement_id"] == "pl_005"

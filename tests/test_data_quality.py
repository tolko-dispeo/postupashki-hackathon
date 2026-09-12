import pandas as pd
import pytest

from postupashki_mvp.services.data_quality import (
    IDS,
    ISSUE_COLUMNS,
    normalize_tables,
    validate_data_quality,
)


@pytest.fixture
def valid_tables():
    rows = {
        "campaigns": [{"campaign_id": "c", "campaign_name": "Campaign"}],
        "placements": [{"placement_id": "p", "campaign_id": "c", "cost": 100}],
        "events": [
            {
                "event_id": "e",
                "event_name": "ad_click",
                "visitor_id": "v",
                "session_id": None,
                "placement_id": "p",
                "properties": {"lead_id": "l"},
                "occurred_at": "2026-08-01T10:00:00Z",
            }
        ],
        "leads": [{"lead_id": "l", "visitor_id": "v", "created_at": "2026-08-02"}],
        "orders": [{"order_id": "o", "lead_id": "l", "created_at": "2026-08-03"}],
        "payments": [
            {
                "payment_id": "pay",
                "order_id": "o",
                "amount": 500,
                "status": "succeeded",
                "paid_at": "2026-08-04",
            }
        ],
    }
    return {
        name: pd.DataFrame([{**r, "is_synthetic": False} for r in rs]) for name, rs in rows.items()
    }


def rules(tables, **kwargs):
    return validate_data_quality(tables, now="2026-09-12", **kwargs).rule_id.tolist()


def test_valid_data_and_input_immutability(valid_tables):
    before = {name: frame.copy(deep=True) for name, frame in valid_tables.items()}
    result = validate_data_quality(valid_tables, now="2026-09-12")
    assert result.empty
    assert list(result.columns) == ISSUE_COLUMNS
    for name, frame in before.items():
        pd.testing.assert_frame_equal(frame, valid_tables[name])


@pytest.mark.parametrize("table", list(IDS))
def test_duplicate_ids(valid_tables, table):
    valid_tables[table] = pd.concat([valid_tables[table]] * 2, ignore_index=True)
    assert "duplicate_id" in rules(valid_tables)


@pytest.mark.parametrize(
    "table,field",
    [
        ("placements", "campaign_id"),
        ("events", "placement_id"),
        ("orders", "lead_id"),
        ("payments", "order_id"),
    ],
)
def test_broken_references(valid_tables, table, field):
    valid_tables[table].loc[0, field] = "missing"
    assert "unknown_reference" in rules(valid_tables)


@pytest.mark.parametrize("value", [None, "", "bad", 0, -1, float("inf"), float("nan"), True])
def test_invalid_payment_amount(valid_tables, value):
    valid_tables["payments"]["amount"] = pd.Series([value], dtype=object)
    assert "invalid_payment_amount" in rules(valid_tables)


@pytest.mark.parametrize(
    "table,column,value,rule",
    [
        ("events", "event_name", "click", "unknown_event_name"),
        ("events", "visitor_id", "  ", "missing_visitor_id"),
        ("payments", "paid_at", None, "succeeded_without_paid_at"),
        ("payments", "paid_at", "2026-08-02", "payment_before_order"),
        ("orders", "created_at", "2026-08-01", "order_before_lead"),
        ("events", "occurred_at", "2026-08-03", "ad_click_after_lead"),
        ("events", "occurred_at", "bad", "invalid_timestamp"),
        ("events", "properties", "[]", "invalid_properties"),
        ("placements", "cost", -1, "invalid_cost"),
    ],
)
def test_quality_rules(valid_tables, table, column, value, rule):
    valid_tables[table].loc[0, column] = value
    assert rule in rules(valid_tables)


@pytest.mark.parametrize("value", [None, "false", "true", "0", "", 2, float("nan")])
def test_unknown_synthetic(valid_tables, value):
    valid_tables["events"]["is_synthetic"] = pd.Series([value], dtype=object)
    assert "unknown_is_synthetic" in rules(valid_tables)


def test_mixed_cohorts_and_explicit_filter(valid_tables):
    valid_tables["campaigns"] = pd.concat(
        [valid_tables["campaigns"], pd.DataFrame([{"campaign_id": "demo", "is_synthetic": True}])]
    )
    assert "mixed_real_synthetic" in rules(valid_tables)
    assert "mixed_real_synthetic" not in rules(valid_tables, is_synthetic=False)


def test_cross_cohort_reference(valid_tables):
    valid_tables["payments"].loc[0, "is_synthetic"] = True
    assert "cross_cohort_reference" in rules(valid_tables, is_synthetic=True)


def test_future_is_warning(valid_tables):
    valid_tables["payments"].loc[0, "paid_at"] = "2030-01-01"
    issues = validate_data_quality(valid_tables, now="2026-09-12")
    assert set(issues.severity) == {"warning"}
    assert set(issues.rule_id) == {"future_date"}


def test_properties_json_links_and_unrelated_later_click(valid_tables):
    valid_tables["events"].loc[0, "properties"] = '{"payment_id": "missing"}'
    assert "unknown_reference" in rules(valid_tables)
    valid_tables["events"].loc[0, "properties"] = "{}"
    valid_tables["events"].loc[0, "occurred_at"] = "2026-08-05"
    assert "ad_click_after_lead" not in rules(valid_tables)


def test_empty_and_missing_columns(valid_tables):
    assert validate_data_quality({}).empty
    assert set(normalize_tables({})) == set(IDS)
    valid_tables["events"] = valid_tables["events"].drop(columns=["event_id", "properties"])
    found = rules(valid_tables)
    assert "missing_column" in found
    assert "missing_id" in found


def test_timezone_normalization(valid_tables):
    valid_tables["events"].loc[0, "occurred_at"] = "2026-08-02T02:00:00+03:00"
    assert "ad_click_after_lead" not in rules(valid_tables)

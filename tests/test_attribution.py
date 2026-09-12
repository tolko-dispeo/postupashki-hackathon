from decimal import Decimal

import pandas as pd
import pytest

from postupashki_mvp.services.attribution import (
    attribute_leads,
    attribute_payments,
    attribution_summary,
)


def make_data():
    events = pd.DataFrame(
        [
            {
                "event_id": "e1",
                "occurred_at": "2026-09-01T10:00:00Z",
                "event_name": "ad_click",
                "visitor_id": "v1",
                "session_id": "s1",
                "placement_id": "p1",
                "properties": {},
                "is_synthetic": False,
            },
            {
                "event_id": "e2",
                "occurred_at": "2026-09-05T10:00:00Z",
                "event_name": "ad_click",
                "visitor_id": "v1",
                "session_id": "s2",
                "placement_id": "p2",
                "properties": {},
                "is_synthetic": False,
            },
            {
                "event_id": "e3",
                "occurred_at": "2026-09-06T10:00:00Z",
                "event_name": "ad_click",
                "visitor_id": "v1",
                "session_id": "s3",
                "placement_id": "p3",
                "properties": {},
                "is_synthetic": False,
            },
            {
                "event_id": "e4",
                "occurred_at": "2026-09-07T10:00:00Z",
                "event_name": "landing_view",
                "visitor_id": "v1",
                "session_id": "s3",
                "placement_id": "p3",
                "properties": {},
                "is_synthetic": False,
            },
            {
                "event_id": "e5",
                "occurred_at": "2026-09-08T10:00:00Z",
                "event_name": "ad_click",
                "visitor_id": "v1",
                "session_id": "s4",
                "placement_id": "p4",
                "properties": {},
                "is_synthetic": False,
            },
            {
                "event_id": "e6",
                "occurred_at": "2026-08-01T10:00:00Z",
                "event_name": "ad_click",
                "visitor_id": "v1",
                "session_id": "s0",
                "placement_id": "p5",
                "properties": {},
                "is_synthetic": False,
            },
        ]
    )
    
    leads = pd.DataFrame(
        [
            {
                "lead_id": "l1",
                "visitor_id": "v1",
                "created_at": "2026-09-06T12:00:00Z",
                "is_synthetic": False,
            },
            {
                "lead_id": "l2",
                "visitor_id": "v2",
                "created_at": "2026-09-06T12:00:00Z",
                "is_synthetic": False,
            },
        ]
    )

    orders = pd.DataFrame(
        [
            {
                "order_id": "o1",
                "lead_id": "l1",
                "is_synthetic": False,
            },
            {
                "order_id": "o2",
                "lead_id": "l2",
                "is_synthetic": False,
            },
        ]
    )

    payments = pd.DataFrame(
        [
            {
                "payment_id": "pay1",
                "order_id": "o1",
                "status": "succeeded",
                "amount": "1000.00",
                "paid_at": "2026-09-06T12:05:00Z",
                "is_synthetic": False,
            },
            {
                "payment_id": "pay2",
                "order_id": "o2",
                "status": "succeeded",
                "amount": "500.00",
                "paid_at": "2026-09-06T12:05:00Z",
                "is_synthetic": False,
            },
            {
                "payment_id": "pay3",
                "order_id": "o1",
                "status": "failed",
                "amount": "700.00",
                "paid_at": "2026-09-06T12:05:00Z",
                "is_synthetic": False,
            },
            {
                "payment_id": "pay4",
                "order_id": "o1",
                "status": "succeeded",
                "amount": "0.00",
                "paid_at": "2026-09-06T12:05:00Z",
                "is_synthetic": False,
            },
            {
                "payment_id": "pay5",
                "order_id": "o1",
                "status": "succeeded",
                "amount": "-10.00",
                "paid_at": "2026-09-06T12:05:00Z",
                "is_synthetic": False,
            },
        ]
    )

    placements = pd.DataFrame(
        [
            {"placement_id": "p1", "campaign_id": "c1", "is_synthetic": False},
            {"placement_id": "p2", "campaign_id": "c2", "is_synthetic": False},
            {"placement_id": "p3", "campaign_id": "c3", "is_synthetic": False},
            {"placement_id": "p4", "campaign_id": "c4", "is_synthetic": False},
            {"placement_id": "p5", "campaign_id": "c5", "is_synthetic": False},
        ]
    )

    return events, leads, orders, payments, placements


def test_one_click_before_lead():
    events, leads, orders, payments, placements = make_data()

    events = events[events["event_id"] == "e1"]

    result = attribute_payments(
        events,
        leads,
        orders,
        payments,
        placements,
        is_synthetic=False,
    )

    row = result[result["payment_id"] == "pay1"].iloc[0]

    assert row["campaign_id"] == "c1"
    assert row["placement_id"] == "p1"
    assert row["weight"] == 1.0
    assert row["attribution_status"] == "attributed"
    assert row["attributed_revenue"] == Decimal("1000.00")


def test_last_touch_uses_latest_click():
    events, leads, orders, payments, placements = make_data()

    result = attribute_payments(
        events,
        leads,
        orders,
        payments,
        placements,
        model="last_touch",
        is_synthetic=False,
    )

    row = result[result["payment_id"] == "pay1"].iloc[0]

    assert row["campaign_id"] == "c3"
    assert row["placement_id"] == "p3"


def test_first_touch_uses_earliest_click():
    events, leads, orders, payments, placements = make_data()

    result = attribute_payments(
        events,
        leads,
        orders,
        payments,
        placements,
        model="first_touch",
        is_synthetic=False,
    )

    row = result[result["payment_id"] == "pay1"].iloc[0]

    assert row["campaign_id"] == "c1"
    assert row["placement_id"] == "p1"


def test_linear_splits_revenue_between_clicks():
    events, leads, orders, payments, placements = make_data()

    result = attribute_payments(
        events,
        leads,
        orders,
        payments,
        placements,
        model="linear",
        is_synthetic=False,
    )

    rows = result[result["payment_id"] == "pay1"]

    assert len(rows) == 3
    assert rows["weight"].sum() == pytest.approx(1.0)

    attributed = sum(rows["attributed_revenue"])

    assert attributed == Decimal("1000.00")


def test_old_click_is_excluded():
    events, leads, orders, payments, placements = make_data()

    events = events[events["event_id"] == "e6"]

    result = attribute_payments(
        events,
        leads,
        orders,
        payments,
        placements,
        is_synthetic=False,
    )

    row = result[result["payment_id"] == "pay1"].iloc[0]

    assert row["attribution_status"] == "unattributed"
    assert row["weight"] == 0.0
    assert row["attributed_revenue"] == Decimal("0.00")


def test_click_after_lead_is_excluded():
    events, leads, orders, payments, placements = make_data()

    events = events[events["event_id"] == "e5"]

    result = attribute_payments(
        events,
        leads,
        orders,
        payments,
        placements,
        is_synthetic=False,
    )

    row = result[result["payment_id"] == "pay1"].iloc[0]

    assert row["attribution_status"] == "unattributed"


def test_payment_without_ad_touch_is_unattributed():
    events, leads, orders, payments, placements = make_data()

    result = attribute_payments(
        events,
        leads,
        orders,
        payments,
        placements,
        is_synthetic=False,
    )

    row = result[result["payment_id"] == "pay2"].iloc[0]

    assert row["attribution_status"] == "unattributed"
    assert row["attributed_revenue"] == Decimal("0.00")


def test_failed_zero_and_negative_payments_are_excluded():
    events, leads, orders, payments, placements = make_data()

    result = attribute_payments(
        events,
        leads,
        orders,
        payments,
        placements,
        is_synthetic=False,
    )

    assert "pay3" not in result["payment_id"].values
    assert "pay4" not in result["payment_id"].values
    assert "pay5" not in result["payment_id"].values


def test_attribution_does_not_create_extra_revenue():
    events, leads, orders, payments, placements = make_data()

    result = attribute_payments(
        events,
        leads,
        orders,
        payments,
        placements,
        model="linear",
        is_synthetic=False,
    )

    summary = attribution_summary(result)

    assert summary["attributed_revenue"] + summary["unattributed_revenue"] \
        == summary["total_revenue"]


def test_linear_weights_sum_to_one_per_payment():
    events, leads, orders, payments, placements = make_data()

    result = attribute_payments(
        events,
        leads,
        orders,
        payments,
        placements,
        model="linear",
        is_synthetic=False,
    )
    
    weights = (
        result[result["attribution_status"] == "attributed"]
        .groupby("payment_id")["weight"]
        .sum()
    )

    for payment_id, weight in weights.items():
        assert weight == pytest.approx(1.0)


def test_same_timestamp_uses_event_id_as_stable_tiebreaker():
    events, leads, orders, payments, placements = make_data()
    
    extra = pd.DataFrame(
        [
            {
                "event_id": "e0",
                "occurred_at": "2026-09-06T10:00:00Z",
                "event_name": "ad_click",
                "visitor_id": "v1",
                "session_id": "sx",
                "placement_id": "p1",
                "properties": {},
                "is_synthetic": False,
            }
        ]
    )
    
    events = pd.concat([events, extra], ignore_index=True)
    
    result = attribute_payments(
        events,
        leads,
        orders,
        payments,
        placements,
        model="first_touch",
        is_synthetic=False,
    )
    
    row = result[result["payment_id"] == "pay1"].iloc[0]

    assert row["placement_id"] == "p1"


def test_repeated_run_is_identical():
    events, leads, orders, payments, placements = make_data()

    result1 = attribute_payments(
        events,
        leads,
        orders,
        payments,
        placements,
        model="linear",
        is_synthetic=False,
    )

    result2 = attribute_payments(
        events,
        leads,
        orders,
        payments,
        placements,
        model="linear",
        is_synthetic=False,
    )

    pd.testing.assert_frame_equal(
        result1.reset_index(drop=True),
        result2.reset_index(drop=True),
    )
    
def test_unpaid_lead_is_attributed():
    events, leads, orders, payments, placements = make_data()

    result = attribute_leads(
        events,
        leads,
        placements,
        model="last_touch",
        is_synthetic=False,
    )

    row = result[result["lead_id"] == "l1"].iloc[0]

    assert row["payment_id"] is None
    assert row["attribution_status"] == "attributed"
    assert row["campaign_id"] == "c3"
    assert row["placement_id"] == "p3"
    assert row["weight"] == 1.0
    assert row["payment_amount"] is None
    assert row["attributed_revenue"] is None


def test_lead_without_click_is_unattributed():
    events, leads, orders, payments, placements = make_data()

    result = attribute_leads(
        events,
        leads,
        placements,
        model="last_touch",
        is_synthetic=False,
    )

    row = result[result["lead_id"] == "l2"].iloc[0]

    assert row["attribution_status"] == "unattributed"
    assert row["weight"] == 0.0
    assert row["campaign_id"] is None
    assert row["placement_id"] is None


def test_lead_last_touch_uses_latest_click():
    events, leads, orders, payments, placements = make_data()

    result = attribute_leads(
        events,
        leads,
        placements,
        model="last_touch",
        is_synthetic=False,
    )

    row = result[result["lead_id"] == "l1"].iloc[0]

    assert row["campaign_id"] == "c3"
    assert row["placement_id"] == "p3"


def test_lead_first_touch_uses_earliest_click():
    events, leads, orders, payments, placements = make_data()

    result = attribute_leads(
        events,
        leads,
        placements,
        model="first_touch",
        is_synthetic=False,
    )

    row = result[result["lead_id"] == "l1"].iloc[0]

    assert row["campaign_id"] == "c1"
    assert row["placement_id"] == "p1"


def test_lead_linear_weights_sum_to_one():
    events, leads, orders, payments, placements = make_data()

    result = attribute_leads(
        events,
        leads,
        placements,
        model="linear",
        is_synthetic=False,
    )

    weights = (
        result[result["attribution_status"] == "attributed"]
        .groupby("lead_id")["weight"]
        .sum()
    )

    for lead_id, weight in weights.items():
        assert weight == pytest.approx(1.0)


def test_synthetic_and_real_not_mixed():
    events, leads, orders, payments, placements = make_data()

    synthetic_event = pd.DataFrame(
        [
            {
                "event_id": "e_synth",
                "occurred_at": "2026-09-06T09:00:00Z",
                "event_name": "ad_click",
                "visitor_id": "v3",
                "session_id": "s_synth",
                "placement_id": "p1",
                "properties": {},
                "is_synthetic": True,
            }
        ]
    )
    events = pd.concat([events, synthetic_event], ignore_index=True)

    synthetic_lead = pd.DataFrame(
        [
            {
                "lead_id": "l_synth",
                "visitor_id": "v3",
                "created_at": "2026-09-06T12:00:00Z",
                "is_synthetic": True,
            }
        ]
    )
    leads = pd.concat([leads, synthetic_lead], ignore_index=True)

    real_result = attribute_leads(
        events,
        leads,
        placements,
        model="last_touch",
        is_synthetic=False,
    )
    synthetic_result = attribute_leads(
        events,
        leads,
        placements,
        model="last_touch",
        is_synthetic=True,
    )

    assert "l_synth" not in real_result["lead_id"].values
    assert "l1" not in synthetic_result["lead_id"].values
    assert set(synthetic_result["lead_id"]) == {"l_synth"}
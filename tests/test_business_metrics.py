import pandas as pd
import pytest

from postupashki_mvp.services.business_metrics import (
    ATTRIBUTION_COLUMNS,
    calculate_business_metrics,
)


@pytest.fixture
def dataset():
    rows = {
        "campaigns": [
            {"campaign_id": c, "campaign_name": "Same display name"} for c in ["a", "b", "zero"]
        ],
        "placements": [
            {"placement_id": c, "campaign_id": c, "cost": cost}
            for c, cost in [("a", 100), ("b", 200), ("zero", 0)]
        ],
        "events": [],
        "leads": [
            {"lead_id": c, "visitor_id": v, "created_at": "2026-08-31"}
            for c, v in [("a", "shared"), ("b", "other"), ("organic", "organic")]
        ],
        "orders": [
            {"order_id": c, "lead_id": c, "created_at": "2026-09-01"} for c in ["a", "b", "organic"]
        ],
        "payments": [
            {
                "payment_id": c,
                "order_id": c,
                "amount": amount,
                "status": "succeeded",
                "paid_at": "2026-09-02",
            }
            for c, amount in [("a", 500), ("b", 800), ("organic", 300)]
        ],
    }
    for placement, visitor, names in [
        ("a", "shared", ["ad_click", "landing_view", "course_view", "course_selected"]),
        ("b", "shared", ["ad_click"]),
        ("b", "other", ["ad_click", "landing_view", "course_selected"]),
    ]:
        for name in names:
            rows["events"].append(
                {
                    "event_id": str(len(rows["events"])),
                    "event_name": name,
                    "visitor_id": visitor,
                    "placement_id": placement,
                    "session_id": None,
                    "properties": {},
                    "occurred_at": "2026-08-01",
                }
            )
    tables = {
        name: pd.DataFrame([{**r, "is_synthetic": False} for r in rs]) for name, rs in rows.items()
    }
    attribution = pd.DataFrame(
        [
            {
                "payment_id": c,
                "lead_id": c,
                "campaign_id": c,
                "placement_id": c,
                "attribution_model": "last_touch",
                "weight": 1.0,
                "payment_amount": amount,
                "attributed_revenue": amount,
                "attribution_status": "attributed",
            }
            for c, amount in [("a", 500), ("b", 800)]
        ]
    )
    return tables, attribution


def calculate(dataset, **kwargs):
    return calculate_business_metrics(
        *dataset, is_synthetic=False, attribution_model=kwargs.get("model", "last_touch")
    )


def test_campaign_formulas_and_global_deduplication(dataset):
    result = calculate(dataset)
    campaigns = result["campaign_metrics"].set_index("campaign_id")
    a, b = campaigns.loc["a"], campaigns.loc["b"]
    assert a.clicks == 1 and b.clicks == 2
    assert a.unique_click_users == 1 and b.unique_click_users == 2
    assert a.course_users == 1  # view + selected are one visitor
    assert a.click_to_landing_pct == 100 and b.click_to_landing_pct == 50
    assert a.landing_to_course_pct == a.course_to_lead_pct == 100
    assert a.lead_to_order_pct == a.order_to_payment_pct == 100
    assert a.cpl == a.cpo == a.cac == 100
    assert b.cpl == b.cpo == b.cac == 200
    assert a.romi_pct == 400 and b.romi_pct == 300
    assert a.average_payment == 500 and b.average_payment == 800
    total = result["overall_funnel"].iloc[0]
    assert total.unique_click_users == 2  # sum of campaigns would be three
    assert total.clicks == 3
    assert total.leads == total.orders == total.successful_payments == 3
    assert total.total_revenue == 1600
    assert total.attributed_revenue == 1300 and total.unattributed_revenue == 300
    assert result["unattributed_payments"].payment_id.tolist() == ["organic"]


def test_zero_denominators_are_literal_none(dataset):
    zero = calculate(dataset)["campaign_metrics"].set_index("campaign_id").loc["zero"]
    for metric in [
        "cpl",
        "cpo",
        "cac",
        "average_payment",
        "romi_pct",
        "click_to_landing_pct",
        "landing_to_course_pct",
        "course_to_lead_pct",
        "lead_to_order_pct",
        "order_to_payment_pct",
    ]:
        assert zero[metric] is None
    assert zero.successful_payments == zero.leads == zero.orders == zero.cost == 0


@pytest.mark.parametrize(
    "touch,expected",
    [
        ("2026-08-01", 500),
        ("2026-07-31T23:59:59Z", 0),
        ("2026-08-31", 500),
        ("2026-08-31T00:00:01Z", 0),
    ],
)
def test_thirty_day_window_is_inclusive_and_anchored_to_lead(dataset, touch, expected):
    tables, _ = dataset
    tables["events"].loc[tables["events"].placement_id == "a", "occurred_at"] = touch
    a = calculate(dataset)["campaign_metrics"].set_index("campaign_id").loc["a"]
    assert a.attributed_revenue == expected


def test_non_click_is_not_an_advertising_touch(dataset):
    tables, _ = dataset
    tables["events"].loc[0, "event_name"] = "landing_view"
    assert calculate(dataset)["campaign_metrics"].iloc[0].attributed_revenue == 0


def test_linear_equivalents_and_revenue_conservation(dataset):
    tables, attr = dataset
    attr["attribution_model"] = "linear"
    attr.loc[0, ["weight", "attributed_revenue"]] = [0.5, 250]
    extra = attr.iloc[0].copy()
    extra[["campaign_id", "placement_id"]] = ["b", "b"]
    attr = pd.concat([attr, extra.to_frame().T], ignore_index=True)
    result = calculate((tables, attr), model="linear")
    campaigns = result["campaign_metrics"].set_index("campaign_id")
    assert campaigns.loc["a", "successful_payments"] == 1
    assert campaigns.loc["b", "successful_payments"] == 2
    assert campaigns.payment_equivalents.sum() == 2
    assert campaigns.loc["a", "cac"] == 200
    assert campaigns.loc["a", "average_payment"] == 500
    assert campaigns.loc["a", "order_to_payment_pct"] == 50
    assert campaigns.attributed_revenue.sum() == 1300
    assert result["overall_funnel"].iloc[0].successful_payments == 3


def test_explicit_unattributed_and_missing_attribution(dataset):
    tables, attr = dataset
    attr.loc[0, ["campaign_id", "placement_id", "attribution_status", "attributed_revenue"]] = [
        None,
        None,
        "unattributed",
        0,
    ]
    result = calculate((tables, attr))
    assert result["unattributed_payments"].unattributed_revenue.sum() == 800
    result = calculate((tables, pd.DataFrame()))
    assert result["campaign_metrics"].attributed_revenue.sum() == 0
    assert result["unattributed_payments"].unattributed_revenue.sum() == 1600


def test_unpaid_lead_assignment_is_consumed_without_inventing_attribution(dataset):
    tables, attr = dataset
    tables["payments"] = tables["payments"].iloc[0:0]
    attr = attr.iloc[[0]].copy()
    attr[["payment_id", "payment_amount", "attributed_revenue"]] = None
    result = calculate((tables, attr))["campaign_metrics"].iloc[0]
    assert result.leads == result.orders == 1
    assert result.successful_payments == 0


def test_only_succeeded_payments_count(dataset):
    tables, _ = dataset
    tables["payments"].loc[0, ["status", "paid_at"]] = ["pending", None]
    result = calculate(dataset)
    assert result["campaign_metrics"].iloc[0].successful_payments == 0
    assert result["overall_funnel"].iloc[0].total_revenue == 1100


def test_real_synthetic_filters_and_no_input_mutation(dataset):
    tables, attr = dataset
    originals = {name: frame.copy(deep=True) for name, frame in tables.items()}
    for name, frame in originals.items():
        demo = frame.copy(deep=True)
        for col in demo.columns:
            if col.endswith("_id"):
                demo[col] = demo[col].map(lambda v: v + "_demo" if isinstance(v, str) else v)
        demo["is_synthetic"] = True
        if name == "payments":
            demo["amount"] *= 2
        tables[name] = pd.concat([frame, demo], ignore_index=True)
    before = {name: frame.copy(deep=True) for name, frame in tables.items()}
    assert calculate(dataset)["overall_funnel"].iloc[0].total_revenue == 1600
    synthetic = calculate_business_metrics(
        tables, attr, is_synthetic=True, attribution_model="last_touch"
    )
    assert synthetic["overall_funnel"].iloc[0].total_revenue == 3200
    for name in tables:
        pd.testing.assert_frame_equal(before[name], tables[name])
    with pytest.raises(TypeError, match="explicitly"):
        calculate_business_metrics(tables, attr, is_synthetic=None, attribution_model="last_touch")


@pytest.mark.parametrize(
    "column,value",
    [
        ("weight", 2),
        ("weight", -1),
        ("weight", float("nan")),
        ("payment_amount", 1),
        ("attributed_revenue", 1),
        ("lead_id", "b"),
        ("campaign_id", "b"),
        ("payment_id", "unknown"),
        ("attribution_status", "bad"),
    ],
)
def test_malformed_attribution_is_rejected(dataset, column, value):
    _, attr = dataset
    attr.loc[0, column] = value
    with pytest.raises(ValueError):
        calculate(dataset)


def test_duplicate_and_overallocated_attribution(dataset):
    tables, attr = dataset
    with pytest.raises(ValueError, match="Duplicate"):
        calculate((tables, pd.concat([attr, attr.iloc[[0]]])))
    extra = attr.iloc[0].copy()
    extra[["campaign_id", "placement_id"]] = ["b", "b"]
    with pytest.raises(ValueError, match="exceed"):
        calculate((tables, pd.concat([attr, extra.to_frame().T])))


def test_missing_columns_invalid_inputs_and_empty_output(dataset):
    tables, attr = dataset
    with pytest.raises(ValueError, match="columns"):
        calculate((tables, attr.drop(columns=["weight"])))
    tables["payments"].loc[0, "order_id"] = "broken"
    with pytest.raises(ValueError, match="unknown_reference"):
        calculate(dataset)
    result = calculate(({}, pd.DataFrame(columns=ATTRIBUTION_COLUMNS)))
    assert result["campaign_metrics"].empty
    assert result["overall_funnel"].iloc[0].successful_payments == 0
    assert result["overall_funnel"].iloc[0].romi_pct is None


def test_models_are_selected_explicitly(dataset):
    tables, attr = dataset
    another = attr.copy()
    another["attribution_model"] = "first_touch"
    result = calculate((tables, pd.concat([attr, another])))
    assert result["campaign_metrics"].attributed_revenue.sum() == 1300

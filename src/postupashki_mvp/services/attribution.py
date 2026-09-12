from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

import pandas as pd


AttributionModel = Literal["last_touch", "first_touch", "linear"]

SUPPORTED_MODELS = {"last_touch", "first_touch", "linear"}
SUCCESS_STATUS = "succeeded"
TOUCH_EVENT = "ad_click"


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def _money(value) -> Decimal:
    return _to_decimal(value).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _properties_value(properties, key):
    if isinstance(properties, dict):
        return properties.get(key)
    return None


def _get_event_property(events: pd.DataFrame, key: str) -> pd.Series:
    if "properties" not in events.columns:
        return pd.Series([None] * len(events), index=events.index)

    return events["properties"].apply(
        lambda value: _properties_value(value, key)
    )


def _prepare_events(events: pd.DataFrame) -> pd.DataFrame:
    result = events.copy()

    result["occurred_at"] = pd.to_datetime(
        result["occurred_at"],
        utc=True,
    )

    if "event_id" not in result.columns:
        raise ValueError("events must contain event_id")

    if "event_name" not in result.columns:
        raise ValueError("events must contain event_name")

    if "visitor_id" not in result.columns:
        raise ValueError("events must contain visitor_id")

    return result


def _prepare_leads(leads: pd.DataFrame) -> pd.DataFrame:
    result = leads.copy()

    required = {"lead_id", "visitor_id", "created_at"}
    missing = required - set(result.columns)

    if missing:
        raise ValueError(
            f"leads missing required columns: {sorted(missing)}"
        )

    result["created_at"] = pd.to_datetime(
        result["created_at"],
        utc=True,
    )

    return result


def _prepare_orders(orders: pd.DataFrame) -> pd.DataFrame:
    result = orders.copy()

    required = {"order_id", "lead_id"}
    missing = required - set(result.columns)

    if missing:
        raise ValueError(
            f"orders missing required columns: {sorted(missing)}"
        )

    return result


def _prepare_payments(payments: pd.DataFrame) -> pd.DataFrame:
    result = payments.copy()

    required = {
        "payment_id",
        "order_id",
        "status",
        "amount",
        "paid_at",
    }
    missing = required - set(result.columns)

    if missing:
        raise ValueError(
            f"payments missing required columns: {sorted(missing)}"
        )

    result["paid_at"] = pd.to_datetime(
        result["paid_at"],
        utc=True,
        errors="coerce",
    )

    result["amount_decimal"] = result["amount"].apply(_money)

    return result


def _prepare_placements(placements: pd.DataFrame) -> pd.DataFrame:
    result = placements.copy()

    required = {"placement_id", "campaign_id"}
    missing = required - set(result.columns)

    if missing:
        raise ValueError(
            f"placements missing required columns: {sorted(missing)}"
        )

    return result


def _sort_touches(touches: pd.DataFrame) -> pd.DataFrame:
    return touches.sort_values(
        ["occurred_at", "event_id"],
        kind="mergesort",
    ).reset_index(drop=True)


def _select_touches(
    touches: pd.DataFrame,
    model: AttributionModel,
) -> pd.DataFrame:
    touches = _sort_touches(touches)

    if model == "first_touch":
        selected = touches.iloc[[0]].copy()
        selected["weight"] = 1.0
        return selected

    if model == "last_touch":
        selected = touches.iloc[[-1]].copy()
        selected["weight"] = 1.0
        return selected

    if model == "linear":
        selected = touches.copy()
        selected["weight"] = 1.0 / len(selected)
        return selected

    raise ValueError(
        f"Unknown attribution model: {model}. "
        f"Expected one of {sorted(SUPPORTED_MODELS)}."
    )


def attribute_payments(
    events,
    leads,
    orders,
    payments,
    placements,
    model="last_touch",
    window_days=30,
):
    """
    Атрибутирует успешные оплаты рекламным кликам.

    Допустимое касание:
        event_name == "ad_click".

    Окно атрибуции:
        [lead_created_at - window_days, lead_created_at].

    К учёту принимаются только клики, произошедшие не позже момента
    создания лида включительно.

    Оплаты, для которых допустимое рекламное касание не найдено,
    возвращаются со статусом ``unattributed`` и не удаляются из выборки.

    :returns: DataFrame, содержащий как минимум столбцы
        ``payment_id``, ``lead_id``, ``campaign_id``, ``placement_id``,
        ``attribution_model``, ``weight``, ``payment_amount``,
        ``attributed_revenue``, ``attribution_status``.
    """
    if model not in SUPPORTED_MODELS:
        raise ValueError(
            f"Unknown attribution model: {model}. "
            f"Expected one of {sorted(SUPPORTED_MODELS)}."
        )

    if window_days < 0:
        raise ValueError("window_days must be non-negative")

    events = _prepare_events(events)
    leads = _prepare_leads(leads)
    orders = _prepare_orders(orders)
    payments = _prepare_payments(payments)
    placements = _prepare_placements(placements)

    ad_clicks = events[
        events["event_name"] == TOUCH_EVENT
    ].copy()

    ad_clicks = ad_clicks.merge(
        placements[["placement_id", "campaign_id"]],
        on="placement_id",
        how="left",
        validate="many_to_one",
    )

    payments = payments.merge(
        orders[["order_id", "lead_id"]],
        on="order_id",
        how="left",
        validate="many_to_one",
    )

    payments = payments.merge(
        leads[["lead_id", "visitor_id", "created_at"]],
        on="lead_id",
        how="left",
        validate="many_to_one",
    )

    successful = payments[
        (payments["status"] == SUCCESS_STATUS)
        & (payments["amount_decimal"] > Decimal("0.00"))
        & payments["paid_at"].notna()
    ].copy()

    rows = []

    for _, payment in successful.iterrows():
        payment_id = payment["payment_id"]
        lead_id = payment["lead_id"]
        visitor_id = payment["visitor_id"]
        lead_created_at = payment["created_at"]
        amount = payment["amount_decimal"]

        if pd.isna(lead_created_at) or pd.isna(visitor_id):
            eligible = ad_clicks.iloc[0:0].copy()
        else:
            window_start = (
                lead_created_at
                - pd.Timedelta(days=window_days)
            )

            eligible = ad_clicks[
                (ad_clicks["visitor_id"] == visitor_id)
                & (ad_clicks["occurred_at"] >= window_start)
                & (ad_clicks["occurred_at"] <= lead_created_at)
            ].copy()

        if eligible.empty:
            rows.append(
                {
                    "payment_id": payment_id,
                    "lead_id": lead_id,
                    "campaign_id": None,
                    "placement_id": None,
                    "attribution_model": model,
                    "weight": 0.0,
                    "payment_amount": amount,
                    "attributed_revenue": Decimal("0.00"),
                    "attribution_status": "unattributed",
                }
            )
            continue

        selected = _select_touches(eligible, model)

        for index, (_, touch) in enumerate(selected.iterrows()):
            weight = float(touch["weight"])

            if index == len(selected) - 1:
                attributed = amount - sum(
                    row["attributed_revenue"]
                    for row in rows
                    if row["payment_id"] == payment_id
                )
            else:
                attributed = _money(
                    amount * _to_decimal(weight)
                )

            rows.append(
                {
                    "payment_id": payment_id,
                    "lead_id": lead_id,
                    "campaign_id": touch["campaign_id"],
                    "placement_id": touch["placement_id"],
                    "attribution_model": model,
                    "weight": weight,
                    "payment_amount": amount,
                    "attributed_revenue": _money(attributed),
                    "attribution_status": "attributed",
                }
            )

    result = pd.DataFrame(
        rows,
        columns=[
            "payment_id",
            "lead_id",
            "campaign_id",
            "placement_id",
            "attribution_model",
            "weight",
            "payment_amount",
            "attributed_revenue",
            "attribution_status",
        ],
    )

    if result.empty:
        return result

    return result


def attribution_summary(
    attribution_result: pd.DataFrame,
) -> dict:
    """
    Build summary metrics from attribute_payments() output.
    """
    if attribution_result.empty:
        return {
            "successful_payments": 0,
            "total_revenue": Decimal("0.00"),
            "attributed_payments": 0,
            "attributed_revenue": Decimal("0.00"),
            "unattributed_payments": 0,
            "unattributed_revenue": Decimal("0.00"),
            "attribution_coverage_pct": 0.0,
        }

    payment_level = (
        attribution_result
        .groupby(
            ["payment_id", "attribution_status"],
            as_index=False,
        )
        .agg(
            payment_amount=("payment_amount", "first"),
            attributed_revenue=("attributed_revenue", "sum"),
        )
    )

    successful_payments = len(payment_level)

    total_revenue = sum(
        (
            _to_decimal(value)
            for value in payment_level["payment_amount"]
        ),
        Decimal("0.00"),
    )

    attributed = payment_level[
        payment_level["attribution_status"] == "attributed"
    ]

    unattributed = payment_level[
        payment_level["attribution_status"] == "unattributed"
    ]

    attributed_payments = len(attributed)
    unattributed_payments = len(unattributed)

    attributed_revenue = sum(
        (
            _to_decimal(value)
            for value in attributed["attributed_revenue"]
        ),
        Decimal("0.00"),
    )

    unattributed_revenue = sum(
        (
            _to_decimal(value)
            for value in unattributed["payment_amount"]
        ),
        Decimal("0.00"),
    )

    coverage = (
        attributed_revenue / total_revenue * Decimal("100")
        if total_revenue > 0
        else Decimal("0")
    )

    return {
        "successful_payments": successful_payments,
        "total_revenue": _money(total_revenue),
        "attributed_payments": attributed_payments,
        "attributed_revenue": _money(attributed_revenue),
        "unattributed_payments": unattributed_payments,
        "unattributed_revenue": _money(unattributed_revenue),
        "attribution_coverage_pct": float(coverage),
    }
    
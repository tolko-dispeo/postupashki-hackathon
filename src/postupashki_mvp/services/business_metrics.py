"""Independent Contract v1 campaign tables consuming externally supplied attribution."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping
from datetime import timedelta

import pandas as pd

from .data_quality import (
    IDS,
    missing,
    normalize_tables,
    number,
    synthetic_flag,
    timestamp,
    validate_data_quality,
)

ATTRIBUTION_COLUMNS = [
    "payment_id",
    "lead_id",
    "campaign_id",
    "placement_id",
    "attribution_model",
    "weight",
    "payment_amount",
    "attributed_revenue",
    "attribution_status",
]
COUNT_COLUMNS = [
    "clicks",
    "unique_click_users",
    "landing_users",
    "course_users",
    "leads",
    "orders",
    "successful_payments",
]
RATIO_COLUMNS = [
    "click_to_landing_pct",
    "landing_to_course_pct",
    "course_to_lead_pct",
    "lead_to_order_pct",
    "order_to_payment_pct",
    "cpl",
    "cpo",
    "cac",
    "average_payment",
    "romi_pct",
]
METRIC_COLUMNS = (
    COUNT_COLUMNS
    + [
        "lead_equivalents",
        "order_equivalents",
        "payment_equivalents",
        "attributed_revenue",
        "cost",
    ]
    + RATIO_COLUMNS
)


def _ratio(numerator, denominator, scale=1):
    return numerator / denominator * scale if denominator else None


def _ratios(row, *, linear):
    leads = row["lead_equivalents"] if linear else row["leads"]
    orders = row["order_equivalents"] if linear else row["orders"]
    payments = row["payment_equivalents"] if linear else row["successful_payments"]
    for name, numerator, denominator in (
        ("click_to_landing_pct", row["landing_users"], row["unique_click_users"]),
        ("landing_to_course_pct", row["course_users"], row["landing_users"]),
        ("course_to_lead_pct", leads, row["course_users"]),
        ("lead_to_order_pct", orders, leads),
        ("order_to_payment_pct", payments, row["orders"]),
    ):
        row[name] = _ratio(numerator, denominator, 100)
    row.update(
        cpl=_ratio(row["cost"], leads),
        cpo=_ratio(row["cost"], orders),
        cac=_ratio(row["cost"], payments),
        average_payment=_ratio(row["attributed_revenue"], payments),
        romi_pct=_ratio(row["attributed_revenue"] - row["cost"], row["cost"], 100),
    )
    return row


def _funnel(events, leads, orders, payments):
    def users(names):
        return len({r["visitor_id"] for r in events if r["event_name"] in names})

    return {
        "clicks": sum(r["event_name"] == "ad_click" for r in events),
        "unique_click_users": users({"ad_click"}),
        "landing_users": users({"landing_view"}),
        "course_users": users({"course_view", "course_selected"}),
        "leads": len(set(leads)),
        "orders": len(set(orders)),
        "successful_payments": len(set(payments)),
    }


def calculate_business_metrics(
    tables: Mapping[str, pd.DataFrame],
    attribution: pd.DataFrame,
    *,
    is_synthetic: bool,
    attribution_model: str,
) -> dict[str, pd.DataFrame]:
    """Return campaign_metrics, overall_funnel and unattributed_payments DataFrames.

    Requires an explicit cohort and model. Attribution is never inferred. For
    unpaid leads, the attribution producer may supply lead-level rows using the
    same columns with payment_id/payment_amount/attributed_revenue null.
    See docs/data_quality_rules.md for the full input/output and formula contract.
    """
    if not isinstance(is_synthetic, bool):
        raise TypeError("Select is_synthetic=True or False explicitly")
    if not isinstance(attribution_model, str) or not attribution_model.strip():
        raise ValueError("Select an attribution_model explicitly")
    frames = normalize_tables(tables)
    # Invalid cohort markers cannot safely be filtered out as if they were real.
    for name, frame in frames.items():
        if "is_synthetic" not in frame or any(
            synthetic_flag(v) is None for v in frame["is_synthetic"]
        ):
            raise ValueError(f"Unknown is_synthetic in {name}")
    selected = {
        name: f.loc[f["is_synthetic"].map(synthetic_flag) == is_synthetic].copy()
        for name, f in frames.items()
    }
    issues = validate_data_quality(selected, is_synthetic=is_synthetic)
    errors = issues.loc[issues["severity"] == "error"]
    if not errors.empty:
        raise ValueError("Invalid input tables: " + ", ".join(sorted(set(errors.rule_id))))
    records = {name: f.to_dict("records") for name, f in selected.items()}
    index = {name: {r[IDS[name]]: r for r in rs} for name, rs in records.items()}
    payments = {
        pid: r
        for pid, r in index["payments"].items()
        if r["status"] == "succeeded"
        and number(r["amount"]) > 0
        and not pd.isna(timestamp(r["paid_at"]))
    }

    attr = pd.DataFrame(attribution).copy(deep=True)
    if not attr.empty and set(ATTRIBUTION_COLUMNS) - set(attr.columns):
        raise ValueError("Missing agreed attribution columns")
    if attr.empty:
        attr = pd.DataFrame(columns=ATTRIBUTION_COLUMNS)
    attr = attr.loc[attr.attribution_model == attribution_model]
    all_payments = {r["payment_id"]: r for r in frames["payments"].to_dict("records")}
    all_leads = {r["lead_id"]: r for r in frames["leads"].to_dict("records")}
    candidate_touches = set()
    clicks_by_visitor = defaultdict(list)
    for event in records["events"]:
        if event["event_name"] == "ad_click" and not missing(event["placement_id"]):
            clicks_by_visitor[event["visitor_id"]].append(event)
    for lead in records["leads"]:
        end = timestamp(lead["created_at"]).to_pydatetime()
        for event in clicks_by_visitor[lead["visitor_id"]]:
            touch = timestamp(event["occurred_at"]).to_pydatetime()
            if end - timedelta(days=30) <= touch <= end:
                candidate_touches.add((lead["lead_id"], event["placement_id"]))

    campaign_leads = defaultdict(set)
    campaign_payments = defaultdict(set)
    revenue = defaultdict(float)
    equivalents = defaultdict(float)
    credited = defaultdict(float)
    supplied_weights = defaultdict(float)
    # Keep distributions separate: payments must never multiply a lead's weight.
    lead_allocations = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    seen = set()
    for row in attr.to_dict("records"):
        pid, lid = row["payment_id"], row["lead_id"]
        lead_only = missing(pid)
        if lead_only:
            source = all_leads.get(lid)
        else:
            source = all_payments.get(pid)
        if source is None:
            raise ValueError("Attribution references an unknown payment or lead")
        if synthetic_flag(source["is_synthetic"]) != is_synthetic:
            continue
        if not lead_only:
            payment = index["payments"][pid]
            expected_lead = index["orders"][payment["order_id"]]["lead_id"]
            if lid != expected_lead:
                raise ValueError("Attribution lead_id disagrees with payment -> order -> lead")
            amount = number(row["payment_amount"])
            if amount is None or not math.isclose(amount, number(payment["amount"]), abs_tol=1e-8):
                raise ValueError("Attribution payment_amount disagrees with payment")
        status = row["attribution_status"]
        if status not in {"attributed", "unattributed"}:
            raise ValueError("Unknown attribution_status")
        weight = number(row["weight"])
        if weight is None or not 0 <= weight <= 1:
            raise ValueError("Attribution weight must be finite and within [0, 1]")
        cid, placement = row["campaign_id"], row["placement_id"]
        identity = (
            None if lead_only else pid,
            lid,
            None if missing(cid) else cid,
            None if missing(placement) else placement,
        )
        if identity in seen:
            raise ValueError("Duplicate attribution allocation")
        seen.add(identity)
        supplied_weights[("lead" if lead_only else "payment", lid if lead_only else pid)] += weight
        allocation = lead_allocations[lid][None if lead_only else pid]
        if status == "unattributed":
            if not missing(cid) or not missing(placement) or number(row["attributed_revenue"]) != 0:
                raise ValueError(
                    "Unattributed rows require null campaign/placement and zero revenue"
                )
            continue
        if cid not in index["campaigns"] or placement not in index["placements"]:
            raise ValueError("Unknown or cross-cohort attribution campaign/placement")
        if index["placements"][placement]["campaign_id"] != cid:
            raise ValueError("Attribution campaign_id disagrees with placement")
        if weight <= 0:
            raise ValueError("Attributed rows require positive weight")
        if not lead_only:
            share = number(row["attributed_revenue"])
            if share is None or not math.isclose(share, amount * weight, abs_tol=1e-8):
                raise ValueError("attributed_revenue must equal payment_amount * weight")
        elif not all(missing(row[c]) for c in ("payment_amount", "attributed_revenue")):
            raise ValueError("Lead-only attribution must have null payment amounts")
        # Invalid temporal assignments are left unattributed, never reassigned.
        if (lid, placement) not in candidate_touches:
            continue
        campaign_leads[cid].add(lid)
        allocation[cid] += weight
        if not lead_only and pid in payments:
            campaign_payments[cid].add(pid)
            revenue[cid] += share
            equivalents[cid] += weight
            credited[pid] += weight
    if any(value > 1 + 1e-9 for value in supplied_weights.values()):
        raise ValueError("Attribution weights exceed one per payment/lead and model")

    rows = []
    linear = attribution_model == "linear"
    lead_weights = {}
    if linear:
        for lid, sources in lead_allocations.items():
            if None in sources:
                # Explicit lead-level attribution is authoritative, including unpaid leads.
                lead_weights[lid] = sources[None]
            else:
                # Backward compatibility: consume one supplied distribution, not its
                # sum over payments. Conflicting distributions need lead-level input.
                distributions = list(sources.values())
                weights = distributions[0]
                if any(
                    any(
                        not math.isclose(weights.get(cid, 0), other.get(cid, 0), abs_tol=1e-9)
                        for cid in weights.keys() | other.keys()
                    )
                    for other in distributions[1:]
                ):
                    raise ValueError("Conflicting payment weights require lead-level attribution")
                lead_weights[lid] = weights
    for cid, campaign in index["campaigns"].items():
        placements = {r["placement_id"] for r in records["placements"] if r["campaign_id"] == cid}
        events = [r for r in records["events"] if r["placement_id"] in placements]
        orders = [r["order_id"] for r in records["orders"] if r["lead_id"] in campaign_leads[cid]]
        row = _funnel(events, campaign_leads[cid], orders, campaign_payments[cid])
        row.update(
            campaign_id=cid,
            campaign_name=campaign.get("campaign_name"),
            is_synthetic=is_synthetic,
            attribution_model=attribution_model,
            cost=sum(number(index["placements"][p]["cost"]) for p in placements),
            lead_equivalents=(
                sum(weights.get(cid, 0) for weights in lead_weights.values())
                if linear else row["leads"]
            ),
            order_equivalents=(
                sum(lead_weights.get(r["lead_id"], {}).get(cid, 0) for r in records["orders"])
                if linear else row["orders"]
            ),
            payment_equivalents=equivalents[cid],
            attributed_revenue=revenue[cid],
        )
        rows.append(_ratios(row, linear=linear))
    unattributed = []
    for pid, payment in payments.items():
        residual = max(0.0, 1 - credited[pid])
        if residual > 1e-9:
            unattributed.append(
                {
                    "payment_id": pid,
                    "lead_id": index["orders"][payment["order_id"]]["lead_id"],
                    "attribution_model": attribution_model,
                    "is_synthetic": is_synthetic,
                    "attribution_status": "unattributed",
                    "payment_amount": number(payment["amount"]),
                    "unattributed_weight": residual,
                    "unattributed_revenue": number(payment["amount"]) * residual,
                }
            )
    total = _funnel(records["events"], index["leads"], index["orders"], payments)
    total.update(
        is_synthetic=is_synthetic,
        attribution_model=attribution_model,
        payment_equivalents=sum(credited.values()),
        attributed_revenue=sum(revenue.values()),
        total_revenue=sum(number(r["amount"]) for r in payments.values()),
        unattributed_revenue=sum(r["unattributed_revenue"] for r in unattributed),
        cost=sum(number(r["cost"]) for r in records["placements"]),
    )
    # Overall payment conversion/economics use actual distinct successful payments.
    _ratios(total, linear=False)
    total["average_payment"] = _ratio(total["total_revenue"], total["successful_payments"])
    return {
        "campaign_metrics": pd.DataFrame(
            rows,
            columns=[
                "campaign_id",
                "campaign_name",
                "is_synthetic",
                "attribution_model",
                *METRIC_COLUMNS,
            ],
            dtype=object,
        ),
        "overall_funnel": pd.DataFrame([total], dtype=object),
        "unattributed_payments": pd.DataFrame(
            unattributed,
            columns=[
                "payment_id",
                "lead_id",
                "attribution_model",
                "is_synthetic",
                "attribution_status",
                "payment_amount",
                "unattributed_weight",
                "unattributed_revenue",
            ],
            dtype=object,
        ),
    }

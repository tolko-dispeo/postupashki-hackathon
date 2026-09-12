"""Read-only, row-level validation of Contract v1 DataFrames (no database access)."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping

import pandas as pd

EVENT_NAMES = frozenset(
    {
        "ad_click",
        "landing_view",
        "course_view",
        "course_selected",
        "lead_created",
        "manager_click",
        "conversation_started",
        "order_created",
        "payment_succeeded",
        "course_access_granted",
    }
)
IDS = {
    name: name[:-1] + "_id"
    for name in ("campaigns", "placements", "events", "leads", "orders", "payments")
}
REQUIRED = {
    "campaigns": {"campaign_id", "is_synthetic"},
    "placements": {"placement_id", "campaign_id", "cost", "is_synthetic"},
    "events": {
        "event_id",
        "occurred_at",
        "event_name",
        "visitor_id",
        "session_id",
        "placement_id",
        "properties",
        "is_synthetic",
    },
    "leads": {"lead_id", "visitor_id", "created_at", "is_synthetic"},
    "orders": {"order_id", "lead_id", "created_at", "is_synthetic"},
    "payments": {"payment_id", "order_id", "amount", "status", "paid_at", "is_synthetic"},
}
ISSUE_COLUMNS = ["rule_id", "severity", "table_name", "entity_id", "message"]


def missing(value):
    return (
        value is None
        or (isinstance(value, str) and not value.strip())
        or (not isinstance(value, (dict, list)) and bool(pd.isna(value)))
    )


def synthetic_flag(value):
    """Accept booleans and numeric 0/1, never truthiness of strings or nulls."""
    if missing(value) or isinstance(value, str):
        return None
    return bool(value) if value in (True, False) else None


def timestamp(value):
    if missing(value) or isinstance(value, (int, float, bool)):
        return pd.NaT
    return pd.to_datetime(value, errors="coerce", utc=True)


def number(value):
    try:
        result = float(value)
        return result if not isinstance(value, bool) and math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


def properties(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else None
        except (ValueError, TypeError):
            pass
    return None


def normalize_tables(tables: Mapping[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Copy caller data; a missing/columnless empty table represents zero rows."""
    result = {}
    for name, columns in REQUIRED.items():
        frame = pd.DataFrame(tables.get(name, [])).copy(deep=True)
        if frame.empty:
            for column in columns - set(frame.columns):
                frame[column] = pd.Series(dtype=object)
        result[name] = frame
    return result


def validate_data_quality(
    tables: Mapping[str, pd.DataFrame], *, is_synthetic: bool | None = None, now=None
) -> pd.DataFrame:
    """Return concrete errors/warnings; validate raw data before any cohort filtering.

    An explicit ``is_synthetic`` suppresses only the mixed-data warning. Other
    issues still refer to the original input, including the other cohort.
    """
    if is_synthetic is not None and not isinstance(is_synthetic, bool):
        raise ValueError("is_synthetic must be True, False or None")
    frames = normalize_tables(tables)
    current = pd.Timestamp.now(tz="UTC") if now is None else timestamp(now)
    if pd.isna(current):
        raise ValueError("now must be a valid timestamp")
    issues = []

    def add(rule, table, entity, message, severity="error"):
        issues.append([rule, severity, table, entity, message])

    rows = {}
    flags = set()
    for name, frame in frames.items():
        for column in sorted(REQUIRED[name] - set(frame.columns)):
            add("missing_column", name, None, f"Required column {column} is missing")
        rows[name] = frame.to_dict("records")
        key = IDS[name]
        if key in frame:
            for value in frame.loc[frame[key].duplicated(keep=False), key].drop_duplicates():
                if not missing(value):
                    add("duplicate_id", name, value, f"Duplicate {key}")
        for row in rows[name]:
            entity = row.get(key)
            if missing(entity):
                add("missing_id", name, None, f"Empty {key}")
            flag = synthetic_flag(row.get("is_synthetic"))
            if flag is None:
                add("unknown_is_synthetic", name, entity, "Expected boolean or numeric 0/1")
            else:
                flags.add(flag)
            for column in ("created_at", "occurred_at", "paid_at"):
                if column not in row:
                    continue
                value = row[column]
                parsed = timestamp(value)
                if pd.isna(parsed):
                    if column != "paid_at" or not missing(value):
                        add("invalid_timestamp", name, entity, f"Invalid {column}")
                elif parsed > current:
                    add("future_date", name, entity, f"{column} is in the future", "warning")
    if len(flags) > 1 and is_synthetic is None:
        add(
            "mixed_real_synthetic",
            "dataset",
            None,
            "Select an explicit is_synthetic filter before calculating metrics",
            "warning",
        )

    indexes = {
        name: {r.get(IDS[name]): r for r in records if not missing(r.get(IDS[name]))}
        for name, records in rows.items()
    }

    def link(name, row, field, target, optional=False):
        value = row.get(field)
        if optional and missing(value):
            return None
        parent = indexes[target].get(value)
        if parent is None:
            add("unknown_reference", name, row.get(IDS[name]), f"Unknown {field}: {value}")
        elif synthetic_flag(parent.get("is_synthetic")) != synthetic_flag(row.get("is_synthetic")):
            add(
                "cross_cohort_reference",
                name,
                row.get(IDS[name]),
                f"{field} links different real/synthetic cohorts",
            )
        return parent

    for name, field, target in (
        ("placements", "campaign_id", "campaigns"),
        ("events", "placement_id", "placements"),
        ("orders", "lead_id", "leads"),
        ("payments", "order_id", "orders"),
    ):
        for row in rows[name]:
            parent = link(name, row, field, target, optional=name == "events")
            if parent and name in ("orders", "payments"):
                child_time = timestamp(row.get("paid_at" if name == "payments" else "created_at"))
                if child_time < timestamp(parent.get("created_at")):
                    add(
                        "payment_before_order" if name == "payments" else "order_before_lead",
                        name,
                        row[IDS[name]],
                        "Child timestamp precedes parent creation",
                    )

    for row in rows["placements"]:
        cost = number(row.get("cost"))
        if cost is None or cost < 0:
            add(
                "invalid_cost",
                "placements",
                row.get("placement_id"),
                "Cost must be finite and non-negative",
            )
    for row in rows["payments"]:
        amount = number(row.get("amount"))
        if amount is None or amount <= 0:
            add(
                "invalid_payment_amount",
                "payments",
                row.get("payment_id"),
                "Amount must be finite and positive",
            )
        if row.get("status") == "succeeded" and pd.isna(timestamp(row.get("paid_at"))):
            add(
                "succeeded_without_paid_at",
                "payments",
                row.get("payment_id"),
                "Succeeded payment requires valid paid_at",
            )

    for row in rows["events"]:
        entity = row.get("event_id")
        if row.get("event_name") not in EVENT_NAMES:
            add("unknown_event_name", "events", entity, "Event name is not in Contract v1")
        if missing(row.get("visitor_id")):
            add("missing_visitor_id", "events", entity, "User event requires visitor_id")
        props = properties(row.get("properties"))
        if props is None:
            add("invalid_properties", "events", entity, "Expected object or JSON object")
            continue
        for field, target in (
            ("lead_id", "leads"),
            ("order_id", "orders"),
            ("payment_id", "payments"),
        ):
            value = row.get(field)
            if missing(value):
                value = props.get(field)
            if not missing(value):
                parent = link("events", {**row, field: value}, field, target)
                if field == "lead_id" and parent:
                    if parent.get("visitor_id") != row.get("visitor_id"):
                        add(
                            "lead_visitor_mismatch",
                            "events",
                            entity,
                            "Event and referenced lead have different visitors",
                        )
                    if row.get("event_name") == "ad_click" and timestamp(
                        row.get("occurred_at")
                    ) > timestamp(parent.get("created_at")):
                        add(
                            "ad_click_after_lead",
                            "events",
                            entity,
                            "Explicitly linked advertising click is after lead creation",
                        )
    visitors = {
        (r.get("visitor_id"), synthetic_flag(r.get("is_synthetic")))
        for r in rows["events"]
        if not missing(r.get("visitor_id"))
    }
    for row in rows["leads"]:
        if missing(row.get("visitor_id")):
            add("missing_visitor_id", "leads", row.get("lead_id"), "Lead requires visitor_id")
        elif (row["visitor_id"], synthetic_flag(row.get("is_synthetic"))) not in visitors:
            add(
                "lead_without_event",
                "leads",
                row.get("lead_id"),
                "No event for this visitor and cohort; lead may be organic",
                "warning",
            )
    return pd.DataFrame(issues, columns=ISSUE_COLUMNS)

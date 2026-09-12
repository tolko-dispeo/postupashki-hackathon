"""Unified read-only analytics assembled from the application database."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
from sqlalchemy import select
from sqlalchemy.engine import Engine

from postupashki_mvp.database import engine as application_engine
from postupashki_mvp.models import Campaign, Event, Lead, Order, Payment, Placement

from .attribution import SUPPORTED_MODELS, attribute_leads, attribute_payments
from .business_metrics import METRIC_COLUMNS, calculate_business_metrics
from .data_quality import normalize_tables, synthetic_flag, validate_data_quality

TABLE_MODELS = {
    "campaigns": Campaign,
    "placements": Placement,
    "events": Event,
    "leads": Lead,
    "orders": Order,
    "payments": Payment,
}


class CampaignNotFoundError(ValueError):
    """Raised when a requested campaign is absent from the selected cohort."""


def load_contract_tables(db_engine: Engine = application_engine) -> dict[str, pd.DataFrame]:
    """Read all Contract v1 tables without changing application data."""
    with db_engine.connect() as connection:
        return {
            name: pd.read_sql_query(select(model.__table__), connection)
            for name, model in TABLE_MODELS.items()
        }


def load_data_quality_issues(
    *, is_synthetic: bool, db_engine: Engine = application_engine
) -> pd.DataFrame:
    """Validate one cohort without requiring attribution or valid business metrics."""
    tables = load_contract_tables(db_engine)
    return validate_data_quality(
        _cohort_tables(tables, is_synthetic),
        is_synthetic=is_synthetic,
    ).reset_index(drop=True)


def _cohort_tables(
    tables: Mapping[str, pd.DataFrame], is_synthetic: bool
) -> dict[str, pd.DataFrame]:
    normalized = normalize_tables(tables)
    return {
        name: frame.loc[
            frame["is_synthetic"].map(synthetic_flag) == is_synthetic
        ].copy()
        for name, frame in normalized.items()
    }


def _campaign_metrics(
    metrics: pd.DataFrame, placements: pd.DataFrame
) -> pd.DataFrame:
    counts = (
        placements.groupby("campaign_id", as_index=False)
        .agg(placements=("placement_id", "nunique"))
    )
    result = metrics.merge(counts, on="campaign_id", how="left")
    result["placements"] = result["placements"].fillna(0).astype(int)
    return result


def _placement_metrics(
    tables: Mapping[str, pd.DataFrame],
    attribution: pd.DataFrame,
    *,
    is_synthetic: bool,
    attribution_model: str,
) -> pd.DataFrame:
    """Reuse the verified campaign formulas with each placement as a group."""
    selected = _cohort_tables(tables, is_synthetic)
    placements = selected["placements"].copy()
    if placements.empty:
        return pd.DataFrame(
            columns=[
                "placement_id",
                "campaign_id",
                "channel_name",
                "target_product",
                "landing_url",
                "is_synthetic",
                "attribution_model",
                *METRIC_COLUMNS,
            ]
        )

    pseudo_campaigns = placements[
        ["placement_id", "channel_name", "created_at", "is_synthetic"]
    ].rename(
        columns={
            "placement_id": "campaign_id",
            "channel_name": "campaign_name",
        }
    )
    pseudo_placements = placements.copy()
    pseudo_placements["campaign_id"] = pseudo_placements["placement_id"]

    pseudo_attribution = attribution.copy()
    attributed = pseudo_attribution["attribution_status"] == "attributed"
    pseudo_attribution.loc[attributed, "campaign_id"] = pseudo_attribution.loc[
        attributed, "placement_id"
    ]

    pseudo_tables = {
        **selected,
        "campaigns": pseudo_campaigns,
        "placements": pseudo_placements,
    }
    metrics = calculate_business_metrics(
        pseudo_tables,
        pseudo_attribution,
        is_synthetic=is_synthetic,
        attribution_model=attribution_model,
    )["campaign_metrics"].rename(
        columns={
            "campaign_id": "placement_id",
            "campaign_name": "_placement_metric_name",
        }
    )

    dimensions = placements[
        [
            "placement_id",
            "campaign_id",
            "channel_name",
            "target_product",
            "landing_url",
        ]
    ].merge(
        selected["campaigns"][["campaign_id", "campaign_name"]],
        on="campaign_id",
        how="left",
        validate="many_to_one",
    )
    return dimensions.merge(
        metrics.drop(columns="_placement_metric_name"),
        on="placement_id",
        how="left",
        validate="one_to_one",
    )


def build_analytics_report(
    *,
    is_synthetic: bool,
    attribution_model: str,
    campaign_id: str | None = None,
    db_engine: Engine = application_engine,
) -> dict[str, object]:
    """Build one consistent report for API and dashboard consumers."""
    if not isinstance(is_synthetic, bool):
        raise TypeError("Select is_synthetic=True or False explicitly")
    if attribution_model not in SUPPORTED_MODELS:
        raise ValueError(
            f"Unknown attribution model: {attribution_model}. "
            f"Expected one of {sorted(SUPPORTED_MODELS)}."
        )

    tables = load_contract_tables(db_engine)
    selected = _cohort_tables(tables, is_synthetic)

    if campaign_id is not None and campaign_id not in set(
        selected["campaigns"]["campaign_id"]
    ):
        raise CampaignNotFoundError(
            f"Campaign {campaign_id!r} was not found in the selected data cohort"
        )

    lead_attribution = attribute_leads(
        tables["events"],
        tables["leads"],
        tables["placements"],
        model=attribution_model,
        window_days=30,
        is_synthetic=is_synthetic,
    )
    payment_attribution = attribute_payments(
        tables["events"],
        tables["leads"],
        tables["orders"],
        tables["payments"],
        tables["placements"],
        model=attribution_model,
        window_days=30,
        is_synthetic=is_synthetic,
    )
    attribution = pd.concat(
        [lead_attribution, payment_attribution], ignore_index=True
    )
    business = calculate_business_metrics(
        tables,
        attribution,
        is_synthetic=is_synthetic,
        attribution_model=attribution_model,
    )

    campaign_metrics = _campaign_metrics(
        business["campaign_metrics"], selected["placements"]
    )
    placement_metrics = _placement_metrics(
        tables,
        attribution,
        is_synthetic=is_synthetic,
        attribution_model=attribution_model,
    )

    if campaign_id is None:
        funnel = business["overall_funnel"].copy()
    else:
        campaign_metrics = campaign_metrics.loc[
            campaign_metrics["campaign_id"] == campaign_id
        ].copy()
        placement_metrics = placement_metrics.loc[
            placement_metrics["campaign_id"] == campaign_id
        ].copy()
        funnel = campaign_metrics.copy()

    quality_issues = validate_data_quality(
        selected,
        is_synthetic=is_synthetic,
    )
    return {
        "campaign_metrics": campaign_metrics.reset_index(drop=True),
        "placement_metrics": placement_metrics.reset_index(drop=True),
        "funnel": funnel.reset_index(drop=True),
        "overall_funnel": business["overall_funnel"].reset_index(drop=True),
        "unattributed_payments": business["unattributed_payments"].reset_index(
            drop=True
        ),
        "payment_attribution": payment_attribution.reset_index(drop=True),
        "quality_issues": quality_issues.reset_index(drop=True),
        "campaigns_count": int(
            selected["campaigns"]["campaign_id"].nunique()
            if campaign_id is None
            else 1
        ),
        "placements_count": int(placement_metrics["placement_id"].nunique()),
    }

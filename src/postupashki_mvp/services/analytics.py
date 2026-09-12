"""Read-only queries used by the marketing dashboard."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from postupashki_mvp.database import engine as application_engine

PLACEMENT_METRICS_QUERY = text(
    """
    WITH event_metrics AS (
        SELECT
            placement_id,
            SUM(CASE WHEN event_name = 'ad_click' THEN 1 ELSE 0 END) AS clicks,
            COUNT(DISTINCT CASE WHEN event_name = 'ad_click' THEN visitor_id END)
                AS click_users,
            COUNT(DISTINCT CASE WHEN event_name = 'landing_view' THEN visitor_id END)
                AS landing_users,
            COUNT(DISTINCT CASE WHEN event_name = 'course_selected' THEN visitor_id END)
                AS course_users
        FROM events
        WHERE placement_id IS NOT NULL
        GROUP BY placement_id
    ),
    candidate_lead_touches AS (
        SELECT
            leads.lead_id,
            events.event_id,
            events.placement_id,
            ROW_NUMBER() OVER (
                PARTITION BY leads.lead_id
                ORDER BY events.occurred_at DESC, events.event_id DESC
            ) AS touch_number
        FROM leads
        JOIN events ON events.visitor_id = leads.visitor_id
        WHERE events.event_name = 'ad_click'
          AND events.placement_id IS NOT NULL
          AND events.occurred_at <= leads.created_at
          AND events.occurred_at >= datetime(leads.created_at, '-30 days')
    ),
    attributed_leads AS (
        SELECT lead_id, placement_id
        FROM candidate_lead_touches
        WHERE touch_number = 1
    ),
    sales_metrics AS (
        SELECT
            attributed_leads.placement_id,
            COUNT(DISTINCT attributed_leads.lead_id) AS leads,
            COUNT(DISTINCT orders.order_id) AS orders,
            COUNT(
                DISTINCT CASE
                    WHEN payments.status = 'succeeded' THEN payments.payment_id
                END
            ) AS payments,
            COALESCE(
                SUM(
                    CASE
                        WHEN payments.status = 'succeeded' THEN payments.amount
                        ELSE 0
                    END
                ),
                0
            ) AS attributed_revenue
        FROM attributed_leads
        LEFT JOIN orders ON orders.lead_id = attributed_leads.lead_id
        LEFT JOIN payments ON payments.order_id = orders.order_id
        GROUP BY attributed_leads.placement_id
    )
    SELECT
        placements.placement_id,
        placements.channel_name,
        placements.campaign_name,
        placements.target_product,
        CAST(placements.cost AS REAL) AS cost,
        placements.is_synthetic,
        COALESCE(event_metrics.clicks, 0) AS clicks,
        COALESCE(event_metrics.click_users, 0) AS click_users,
        COALESCE(event_metrics.landing_users, 0) AS landing_users,
        COALESCE(event_metrics.course_users, 0) AS course_users,
        COALESCE(sales_metrics.leads, 0) AS leads,
        COALESCE(sales_metrics.orders, 0) AS orders,
        COALESCE(sales_metrics.payments, 0) AS payments,
        COALESCE(sales_metrics.attributed_revenue, 0) AS attributed_revenue
    FROM placements
    LEFT JOIN event_metrics
        ON event_metrics.placement_id = placements.placement_id
    LEFT JOIN sales_metrics
        ON sales_metrics.placement_id = placements.placement_id
    ORDER BY attributed_revenue DESC
    """
)


CAMPAIGN_METRICS_QUERY = text(
    """
    WITH placement_metrics AS (
        SELECT
            campaign_name,
            COUNT(*) AS placements,
            SUM(CAST(cost AS REAL)) AS cost
        FROM placements
        GROUP BY campaign_name
    ),
    event_metrics AS (
        SELECT
            placements.campaign_name,
            SUM(CASE WHEN events.event_name = 'ad_click' THEN 1 ELSE 0 END) AS clicks,
            COUNT(
                DISTINCT CASE
                    WHEN events.event_name = 'ad_click' THEN events.visitor_id
                END
            ) AS click_users,
            COUNT(
                DISTINCT CASE
                    WHEN events.event_name = 'landing_view' THEN events.visitor_id
                END
            ) AS landing_users,
            COUNT(
                DISTINCT CASE
                    WHEN events.event_name = 'course_selected' THEN events.visitor_id
                END
            ) AS course_users
        FROM placements
        LEFT JOIN events ON events.placement_id = placements.placement_id
        GROUP BY placements.campaign_name
    ),
    candidate_lead_touches AS (
        SELECT
            leads.lead_id,
            events.event_id,
            events.placement_id,
            ROW_NUMBER() OVER (
                PARTITION BY leads.lead_id
                ORDER BY events.occurred_at DESC, events.event_id DESC
            ) AS touch_number
        FROM leads
        JOIN events ON events.visitor_id = leads.visitor_id
        WHERE events.event_name = 'ad_click'
          AND events.placement_id IS NOT NULL
          AND events.occurred_at <= leads.created_at
          AND events.occurred_at >= datetime(leads.created_at, '-30 days')
    ),
    attributed_leads AS (
        SELECT lead_id, placement_id
        FROM candidate_lead_touches
        WHERE touch_number = 1
    ),
    sales_metrics AS (
        SELECT
            placements.campaign_name,
            COUNT(DISTINCT attributed_leads.lead_id) AS leads,
            COUNT(DISTINCT orders.order_id) AS orders,
            COUNT(
                DISTINCT CASE
                    WHEN payments.status = 'succeeded' THEN payments.payment_id
                END
            ) AS payments,
            COALESCE(
                SUM(
                    CASE
                        WHEN payments.status = 'succeeded' THEN payments.amount
                        ELSE 0
                    END
                ),
                0
            ) AS attributed_revenue
        FROM attributed_leads
        JOIN placements
            ON placements.placement_id = attributed_leads.placement_id
        LEFT JOIN orders ON orders.lead_id = attributed_leads.lead_id
        LEFT JOIN payments ON payments.order_id = orders.order_id
        GROUP BY placements.campaign_name
    )
    SELECT
        placement_metrics.campaign_name,
        placement_metrics.placements,
        placement_metrics.cost,
        COALESCE(event_metrics.clicks, 0) AS clicks,
        COALESCE(event_metrics.click_users, 0) AS click_users,
        COALESCE(event_metrics.landing_users, 0) AS landing_users,
        COALESCE(event_metrics.course_users, 0) AS course_users,
        COALESCE(sales_metrics.leads, 0) AS leads,
        COALESCE(sales_metrics.orders, 0) AS orders,
        COALESCE(sales_metrics.payments, 0) AS payments,
        COALESCE(sales_metrics.attributed_revenue, 0) AS attributed_revenue
    FROM placement_metrics
    LEFT JOIN event_metrics
        ON event_metrics.campaign_name = placement_metrics.campaign_name
    LEFT JOIN sales_metrics
        ON sales_metrics.campaign_name = placement_metrics.campaign_name
    ORDER BY attributed_revenue DESC
    """
)


FUNNEL_METRICS_QUERY = text(
    """
    WITH event_metrics AS (
        SELECT
            SUM(CASE WHEN events.event_name = 'ad_click' THEN 1 ELSE 0 END) AS clicks,
            COUNT(
                DISTINCT CASE
                    WHEN events.event_name = 'ad_click' THEN events.visitor_id
                END
            ) AS click_users,
            COUNT(
                DISTINCT CASE
                    WHEN events.event_name = 'landing_view' THEN events.visitor_id
                END
            ) AS landing_users,
            COUNT(
                DISTINCT CASE
                    WHEN events.event_name = 'course_selected' THEN events.visitor_id
                END
            ) AS course_users
        FROM events
        JOIN placements ON placements.placement_id = events.placement_id
        WHERE :campaign_name IS NULL
           OR placements.campaign_name = :campaign_name
    ),
    candidate_lead_touches AS (
        SELECT
            leads.lead_id,
            events.event_id,
            events.placement_id,
            ROW_NUMBER() OVER (
                PARTITION BY leads.lead_id
                ORDER BY events.occurred_at DESC, events.event_id DESC
            ) AS touch_number
        FROM leads
        JOIN events ON events.visitor_id = leads.visitor_id
        WHERE events.event_name = 'ad_click'
          AND events.placement_id IS NOT NULL
          AND events.occurred_at <= leads.created_at
          AND events.occurred_at >= datetime(leads.created_at, '-30 days')
    ),
    attributed_leads AS (
        SELECT lead_id, placement_id
        FROM candidate_lead_touches
        WHERE touch_number = 1
    ),
    sales_metrics AS (
        SELECT
            COUNT(DISTINCT attributed_leads.lead_id) AS leads,
            COUNT(DISTINCT orders.order_id) AS orders,
            COUNT(
                DISTINCT CASE
                    WHEN payments.status = 'succeeded' THEN payments.payment_id
                END
            ) AS payments
        FROM attributed_leads
        JOIN placements
            ON placements.placement_id = attributed_leads.placement_id
        LEFT JOIN orders ON orders.lead_id = attributed_leads.lead_id
        LEFT JOIN payments ON payments.order_id = orders.order_id
        WHERE :campaign_name IS NULL
           OR placements.campaign_name = :campaign_name
    )
    SELECT
        COALESCE(event_metrics.clicks, 0) AS clicks,
        COALESCE(event_metrics.click_users, 0) AS click_users,
        COALESCE(event_metrics.landing_users, 0) AS landing_users,
        COALESCE(event_metrics.course_users, 0) AS course_users,
        COALESCE(sales_metrics.leads, 0) AS leads,
        COALESCE(sales_metrics.orders, 0) AS orders,
        COALESCE(sales_metrics.payments, 0) AS payments
    FROM event_metrics
    CROSS JOIN sales_metrics
    """
)


def load_placement_metrics(db_engine: Engine = application_engine) -> pd.DataFrame:
    """Return one dashboard row per advertising placement."""
    with db_engine.connect() as connection:
        return pd.read_sql_query(PLACEMENT_METRICS_QUERY, connection)


def load_campaign_metrics(db_engine: Engine = application_engine) -> pd.DataFrame:
    """Return correctly de-duplicated metrics grouped by campaign."""
    with db_engine.connect() as connection:
        return pd.read_sql_query(CAMPAIGN_METRICS_QUERY, connection)


def load_funnel_metrics(
    campaign_name: str | None = None,
    db_engine: Engine = application_engine,
) -> dict[str, int]:
    """Return de-duplicated funnel totals for all or one campaign."""
    with db_engine.connect() as connection:
        row = connection.execute(
            FUNNEL_METRICS_QUERY,
            {"campaign_name": campaign_name},
        ).mappings().one()

    return {metric: int(value or 0) for metric, value in row.items()}

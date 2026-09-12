from decimal import Decimal

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import text

from postupashki_mvp.database import engine


DASHBOARD_QUERY = text(
    """
    WITH event_metrics AS (
        SELECT
            placement_id,

            SUM(
                CASE WHEN event_name = 'ad_click'
                THEN 1 ELSE 0 END
            ) AS clicks,

            COUNT(
                DISTINCT CASE WHEN event_name = 'ad_click'
                THEN visitor_id END
            ) AS click_users,

            COUNT(
                DISTINCT CASE WHEN event_name = 'landing_view'
                THEN visitor_id END
            ) AS landing_users,

            COUNT(
                DISTINCT CASE WHEN event_name = 'course_selected'
                THEN visitor_id END
            ) AS course_users

        FROM events
        WHERE placement_id IS NOT NULL
        GROUP BY placement_id
    ),

    candidate_lead_touches AS (
        SELECT
            leads.lead_id,
            events.placement_id,

            ROW_NUMBER() OVER (
                PARTITION BY leads.lead_id
                ORDER BY events.occurred_at DESC
            ) AS touch_number

        FROM leads
        JOIN events
            ON events.visitor_id = leads.visitor_id

        WHERE events.event_name = 'ad_click'
          AND events.placement_id IS NOT NULL
          AND events.occurred_at <= leads.created_at
          AND events.occurred_at >= datetime(
              leads.created_at,
              '-30 days'
          )
    ),

    attributed_leads AS (
        SELECT
            lead_id,
            placement_id
        FROM candidate_lead_touches
        WHERE touch_number = 1
    ),

    sales_metrics AS (
        SELECT
            attributed_leads.placement_id,

            COUNT(
                DISTINCT attributed_leads.lead_id
            ) AS leads,

            COUNT(
                DISTINCT orders.order_id
            ) AS orders,

            COUNT(
                DISTINCT CASE
                    WHEN payments.status = 'succeeded'
                    THEN payments.payment_id
                END
            ) AS payments,

            COALESCE(
                SUM(
                    CASE
                        WHEN payments.status = 'succeeded'
                        THEN payments.amount
                        ELSE 0
                    END
                ),
                0
            ) AS attributed_revenue

        FROM attributed_leads

        LEFT JOIN orders
            ON orders.lead_id = attributed_leads.lead_id

        LEFT JOIN payments
            ON payments.order_id = orders.order_id

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
        COALESCE(
            sales_metrics.attributed_revenue,
            0
        ) AS attributed_revenue

    FROM placements

    LEFT JOIN event_metrics
        ON event_metrics.placement_id =
           placements.placement_id

    LEFT JOIN sales_metrics
        ON sales_metrics.placement_id =
           placements.placement_id

    ORDER BY attributed_revenue DESC
    """
)


def load_data() -> pd.DataFrame:
    with engine.connect() as connection:
        return pd.read_sql_query(
            DASHBOARD_QUERY,
            connection,
        )


def format_money(value: float) -> str:
    return f"{value:,.0f} ₽".replace(",", " ")


st.set_page_config(
    page_title="Поступашки — Marketing Measurement",
    layout="wide",
)

st.title("Поступашки — Marketing Measurement MVP")

st.caption(
    "Атрибуция: last-touch · Окно: 30 дней · "
    "Текущие данные: synthetic"
)

data = load_data()

if data.empty:
    st.warning("В базе пока нет рекламных размещений")
    st.stop()

numeric_columns = [
    "cost",
    "clicks",
    "click_users",
    "landing_users",
    "course_users",
    "leads",
    "orders",
    "payments",
    "attributed_revenue",
]

data[numeric_columns] = data[numeric_columns].fillna(0)

data["romi_pct"] = data.apply(
    lambda row: (
        (row["attributed_revenue"] - row["cost"])
        / row["cost"]
        * 100
    )
    if row["cost"] > 0
    else None,
    axis=1,
)
data["click_to_lead_pct"] = data.apply(
    lambda row: (
        row["leads"] / row["click_users"] * 100
    )
    if row["click_users"] > 0
    else None,
    axis=1,
)

# Конверсия из лида в успешную оплату.
data["lead_to_payment_pct"] = data.apply(
    lambda row: (
        row["payments"] / row["leads"] * 100
    )
    if row["leads"] > 0
    else None,
    axis=1,
)

# сколько рекламных рублей приходится на одну оплату.
data["cac"] = data.apply(
    lambda row: (
        row["cost"] / row["payments"]
    )
    if row["payments"] > 0
    else None,
    axis=1,
)
total_cost = float(data["cost"].sum())
total_revenue = float(data["attributed_revenue"].sum())

total_romi = None
if total_cost > 0:
    total_romi = (
        (Decimal(str(total_revenue)) - Decimal(str(total_cost)))
        / Decimal(str(total_cost))
        * 100
    )

first_row = st.columns(4)

first_row[0].metric(
    "Размещения",
    len(data),
)

first_row[1].metric(
    "Рекламные клики",
    int(data["clicks"].sum()),
)

first_row[2].metric(
    "Лиды",
    int(data["leads"].sum()),
)

first_row[3].metric(
    "Оплаты",
    int(data["payments"].sum()),
)

second_row = st.columns(3)

second_row[0].metric(
    "Выручка",
    format_money(total_revenue),
)

second_row[1].metric(
    "Расходы",
    format_money(total_cost),
)

second_row[2].metric(
    "ROMI_attr",
    f"{total_romi:.2f}%"
    if total_romi is not None
    else "—",
)

st.subheader("Воронка")

funnel = pd.DataFrame(
    {
        "Этап": [
            "Кликнувшие посетители",
            "Посетители сайта",
            "Выбрали курс",
            "Лиды",
            "Заказы",
            "Оплаты",
        ],
        "Количество": [
            int(data["click_users"].sum()),
            int(data["landing_users"].sum()),
            int(data["course_users"].sum()),
            int(data["leads"].sum()),
            int(data["orders"].sum()),
            int(data["payments"].sum()),
        ],
    }
)

figure = go.Figure(
    go.Funnel(
        y=funnel["Этап"],
        x=funnel["Количество"],
        textinfo="value+percent initial",
    )
)

st.plotly_chart(
    figure,
    use_container_width=True,
)

st.subheader("Эффективность размещений")

table = data[
    [
        "channel_name",
        "campaign_name",
        "target_product",
        "click_users",
        "leads",
        "payments",
        "click_to_lead_pct",
        "lead_to_payment_pct",
        "attributed_revenue",
        "cost",
        "cac",
        "romi_pct",
        "is_synthetic",
    ]
].copy()

table = table.rename(
    columns={
        "channel_name": "Канал",
        "campaign_name": "Кампания",
        "target_product": "Продукт",
        "click_users": "Кликнувшие",
        "leads": "Лиды",
        "payments": "Оплаты",
        "click_to_lead_pct": "Клик → лид, %",
        "lead_to_payment_pct": "Лид → оплата, %",
        "attributed_revenue": "Выручка",
        "cost": "Расходы",
        "cac": "CAC",
        "romi_pct": "ROMI, %",
        "is_synthetic": "Synthetic",
    }
)

# Красивое округление метрик.
table["Клик → лид, %"] = table["Клик → лид, %"].round(1)
table["Лид → оплата, %"] = table["Лид → оплата, %"].round(1)
table["ROMI, %"] = table["ROMI, %"].round(1)

# Денежные показатели форматируем для чтения.
table["Выручка"] = table["Выручка"].apply(format_money)
table["Расходы"] = table["Расходы"].apply(format_money)

table["CAC"] = table["CAC"].apply(
    lambda value: (
        format_money(value)
        if pd.notna(value)
        else "—"
    )
)

st.dataframe(
    table,
    hide_index=True,
    use_container_width=True,
)
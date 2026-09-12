from decimal import Decimal

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from postupashki_mvp.services.analytics import (
    load_campaign_metrics,
    load_funnel_metrics,
    load_placement_metrics,
)

ALL_CAMPAIGNS = "Все кампании"


def format_money(value: float) -> str:
    return f"{value:,.0f} ₽".replace(",", " ")


def data_kind_label(data: pd.DataFrame) -> str:
    values = set(data["is_synthetic"].astype(bool))
    if values == {True}:
        return "synthetic"
    if values == {False}:
        return "real"
    return "mixed"


def add_derived_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    metrics = metrics.copy()
    metrics["romi_pct"] = metrics.apply(
        lambda row: (
            (row["attributed_revenue"] - row["cost"]) / row["cost"] * 100
            if row["cost"] > 0
            else None
        ),
        axis=1,
    )
    metrics["click_to_lead_pct"] = metrics.apply(
        lambda row: row["leads"] / row["click_users"] * 100
        if row["click_users"] > 0
        else None,
        axis=1,
    )
    metrics["lead_to_payment_pct"] = metrics.apply(
        lambda row: row["payments"] / row["leads"] * 100
        if row["leads"] > 0
        else None,
        axis=1,
    )
    metrics["cac"] = metrics.apply(
        lambda row: row["cost"] / row["payments"] if row["payments"] > 0 else None,
        axis=1,
    )
    return metrics


st.set_page_config(
    page_title="Поступашки — Marketing Measurement",
    layout="wide",
)

st.title("Поступашки — Marketing Measurement MVP")

data = load_placement_metrics()
campaign_data = load_campaign_metrics()

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
campaign_data[numeric_columns] = campaign_data[numeric_columns].fillna(0)

data = add_derived_metrics(data)
campaign_data = add_derived_metrics(campaign_data)

campaign_names = sorted(data["campaign_name"].dropna().unique().tolist())

st.sidebar.header("Фильтры")
selected_campaign = st.sidebar.selectbox(
    "Рекламная кампания",
    [ALL_CAMPAIGNS, *campaign_names],
)

campaign_filter = None if selected_campaign == ALL_CAMPAIGNS else selected_campaign

selected_data = (
    data
    if campaign_filter is None
    else data[data["campaign_name"] == campaign_filter].copy()
)

funnel_metrics = load_funnel_metrics(campaign_filter)

st.caption(
    "Атрибуция: last-touch · Окно: 30 дней · "
    f"Данные: {data_kind_label(selected_data)} · Срез: {selected_campaign}"
)

total_cost = float(selected_data["cost"].sum())
total_revenue = float(selected_data["attributed_revenue"].sum())

total_romi = None
if total_cost > 0:
    total_romi = (
        (Decimal(str(total_revenue)) - Decimal(str(total_cost)))
        / Decimal(str(total_cost))
        * 100
    )

first_row = st.columns(5)
first_row[0].metric("Кампании", selected_data["campaign_name"].nunique())
first_row[1].metric("Размещения", len(selected_data))
first_row[2].metric("Рекламные клики", funnel_metrics["clicks"])
first_row[3].metric("Лиды", funnel_metrics["leads"])
first_row[4].metric("Оплаты", funnel_metrics["payments"])

second_row = st.columns(3)
second_row[0].metric("Выручка", format_money(total_revenue))
second_row[1].metric("Расходы", format_money(total_cost))
second_row[2].metric(
    "ROMI_attr",
    f"{total_romi:.2f}%" if total_romi is not None else "—",
)

st.subheader(f"Воронка: {selected_campaign}")

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
            funnel_metrics["click_users"],
            funnel_metrics["landing_users"],
            funnel_metrics["course_users"],
            funnel_metrics["leads"],
            funnel_metrics["orders"],
            funnel_metrics["payments"],
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

st.plotly_chart(figure, use_container_width=True)

st.subheader("Сравнение кампаний")

campaign_ranking = campaign_data.sort_values(
    ["romi_pct", "attributed_revenue"],
    ascending=[False, False],
).reset_index(drop=True)

comparison_left, comparison_right = st.columns(2)

money_figure = go.Figure(
    data=[
        go.Bar(
            name="Выручка",
            x=campaign_ranking["campaign_name"],
            y=campaign_ranking["attributed_revenue"],
            hovertemplate="%{x}<br>Выручка: %{y:,.0f} ₽<extra></extra>",
        ),
        go.Bar(
            name="Расходы",
            x=campaign_ranking["campaign_name"],
            y=campaign_ranking["cost"],
            hovertemplate="%{x}<br>Расходы: %{y:,.0f} ₽<extra></extra>",
        ),
    ]
)
money_figure.update_layout(
    title="Выручка и расходы",
    barmode="group",
    yaxis_title="Рубли",
    legend_title_text="",
)
comparison_left.plotly_chart(money_figure, use_container_width=True)

romi_colors = [
    "#2E8B57" if value >= 0 else "#C44E52"
    for value in campaign_ranking["romi_pct"]
]

romi_figure = go.Figure(
    go.Bar(
        x=campaign_ranking["campaign_name"],
        y=campaign_ranking["romi_pct"],
        marker_color=romi_colors,
        text=campaign_ranking["romi_pct"].round(1),
        texttemplate="%{text}%",
        hovertemplate="%{x}<br>ROMI: %{y:.1f}%<extra></extra>",
    )
)
romi_figure.add_hline(y=0, line_width=1, line_color="#808080")
romi_figure.update_layout(
    title="ROMI по кампаниям",
    yaxis_title="ROMI, %",
)
comparison_right.plotly_chart(romi_figure, use_container_width=True)

campaign_table = campaign_ranking[
    [
        "campaign_name",
        "placements",
        "click_users",
        "leads",
        "payments",
        "click_to_lead_pct",
        "lead_to_payment_pct",
        "attributed_revenue",
        "cost",
        "cac",
        "romi_pct",
    ]
].copy()

campaign_table = campaign_table.rename(
    columns={
        "campaign_name": "Кампания",
        "placements": "Размещения",
        "click_users": "Кликнувшие",
        "leads": "Лиды",
        "payments": "Оплаты",
        "click_to_lead_pct": "Клик → лид, %",
        "lead_to_payment_pct": "Лид → оплата, %",
        "attributed_revenue": "Выручка",
        "cost": "Расходы",
        "cac": "CAC",
        "romi_pct": "ROMI, %",
    }
)

campaign_table["Клик → лид, %"] = campaign_table["Клик → лид, %"].round(1)
campaign_table["Лид → оплата, %"] = campaign_table["Лид → оплата, %"].round(1)
campaign_table["ROMI, %"] = campaign_table["ROMI, %"].round(1)
campaign_table["Выручка"] = campaign_table["Выручка"].apply(format_money)
campaign_table["Расходы"] = campaign_table["Расходы"].apply(format_money)
campaign_table["CAC"] = campaign_table["CAC"].apply(
    lambda value: format_money(value) if pd.notna(value) else "—"
)

st.dataframe(campaign_table, hide_index=True, use_container_width=True)

st.subheader("Эффективность размещений")

table = selected_data[
    [
        "placement_id",
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
        "placement_id": "Placement ID",
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

table["Клик → лид, %"] = table["Клик → лид, %"].round(1)
table["Лид → оплата, %"] = table["Лид → оплата, %"].round(1)
table["ROMI, %"] = table["ROMI, %"].round(1)
table["Выручка"] = table["Выручка"].apply(format_money)
table["Расходы"] = table["Расходы"].apply(format_money)
table["CAC"] = table["CAC"].apply(
    lambda value: format_money(value) if pd.notna(value) else "—"
)

st.dataframe(table, hide_index=True, use_container_width=True)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from postupashki_mvp.services.reporting import build_analytics_report

ALL_CAMPAIGNS = "Все кампании"


def format_money(value: float) -> str:
    return f"{value:,.0f} ₽".replace(",", " ")


def add_display_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    metrics = metrics.copy()
    metrics["click_to_lead_pct"] = metrics.apply(
        lambda row: (
            row["lead_equivalents"] / row["unique_click_users"] * 100
            if row["unique_click_users"] > 0
            else None
        ),
        axis=1,
    )
    metrics["lead_to_payment_pct"] = metrics.apply(
        lambda row: (
            row["payment_equivalents"] / row["lead_equivalents"] * 100
            if row["lead_equivalents"] > 0
            else None
        ),
        axis=1,
    )
    metrics["click_users"] = metrics["unique_click_users"]
    metrics["payments"] = metrics["successful_payments"]
    return metrics


st.set_page_config(
    page_title="Поступашки — Marketing Measurement",
    layout="wide",
)

st.title("Поступашки — Marketing Measurement MVP")

st.sidebar.header("Фильтры")
data_kind = st.sidebar.selectbox(
    "Тип данных",
    ["synthetic", "real"],
    format_func=lambda value: "Синтетические" if value == "synthetic" else "Реальные",
)
attribution_model = st.sidebar.selectbox(
    "Модель атрибуции",
    ["last_touch", "first_touch", "linear"],
    format_func={
        "last_touch": "Последнее касание",
        "first_touch": "Первое касание",
        "linear": "Линейная",
    }.get,
)

report = build_analytics_report(
    is_synthetic=data_kind == "synthetic",
    attribution_model=attribution_model,
)
data = add_display_metrics(report["placement_metrics"])
campaign_data = add_display_metrics(report["campaign_metrics"])

if data.empty:
    st.warning(f"В базе пока нет размещений в срезе «{data_kind}»")
    st.stop()

numeric_columns = [
    "cost",
    "clicks",
    "unique_click_users",
    "click_users",
    "landing_users",
    "course_users",
    "leads",
    "lead_equivalents",
    "orders",
    "order_equivalents",
    "successful_payments",
    "payments",
    "payment_equivalents",
    "attributed_revenue",
    "click_to_landing_pct",
    "landing_to_course_pct",
    "course_to_lead_pct",
    "lead_to_order_pct",
    "order_to_payment_pct",
    "click_to_lead_pct",
    "lead_to_payment_pct",
    "cpl",
    "cpo",
    "cac",
    "average_payment",
    "romi_pct",
]

for metrics in (data, campaign_data):
    metrics[numeric_columns] = metrics[numeric_columns].apply(
        pd.to_numeric,
        errors="coerce",
    )

count_columns = [
    "cost",
    "clicks",
    "unique_click_users",
    "click_users",
    "landing_users",
    "course_users",
    "leads",
    "lead_equivalents",
    "orders",
    "order_equivalents",
    "successful_payments",
    "payments",
    "payment_equivalents",
    "attributed_revenue",
]
data[count_columns] = data[count_columns].fillna(0)
campaign_data[count_columns] = campaign_data[count_columns].fillna(0)

campaign_options = (
    campaign_data[["campaign_id", "campaign_name"]]
    .sort_values(["campaign_name", "campaign_id"])
    .to_dict("records")
)
campaign_labels = {
    row["campaign_id"]: f"{row['campaign_name']} · {row['campaign_id']}" for row in campaign_options
}

selected_campaign = st.sidebar.selectbox(
    "Рекламная кампания",
    [None, *campaign_labels],
    format_func=lambda campaign_id: (
        ALL_CAMPAIGNS if campaign_id is None else campaign_labels[campaign_id]
    ),
)

selected_data = (
    data if selected_campaign is None else data[data["campaign_id"] == selected_campaign].copy()
)

funnel_metrics = (
    report["overall_funnel"].iloc[0]
    if selected_campaign is None
    else campaign_data.loc[campaign_data["campaign_id"] == selected_campaign].iloc[0]
)
selected_campaign_label = (
    ALL_CAMPAIGNS if selected_campaign is None else campaign_labels[selected_campaign]
)

st.caption(
    f"Атрибуция: {attribution_model} · Окно: 30 дней · "
    f"Данные: {data_kind} · Срез: {selected_campaign_label}"
)

total_cost = float(selected_data["cost"].sum())
total_revenue = float(selected_data["attributed_revenue"].sum())
total_romi = (total_revenue - total_cost) / total_cost * 100 if total_cost > 0 else None

first_row = st.columns(5)
first_row[0].metric("Кампании", selected_data["campaign_id"].nunique())
first_row[1].metric("Размещения", len(selected_data))
first_row[2].metric("Рекламные клики", int(funnel_metrics["clicks"]))
first_row[3].metric("Лиды", int(funnel_metrics["leads"]))
first_row[4].metric("Оплаты", int(funnel_metrics["successful_payments"]))

second_row = st.columns(3)
second_row[0].metric("Выручка", format_money(total_revenue))
second_row[1].metric("Расходы", format_money(total_cost))
second_row[2].metric(
    "ROMI_attr",
    f"{total_romi:.2f}%" if total_romi is not None else "—",
)

st.subheader(f"Воронка: {selected_campaign_label}")

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
            int(funnel_metrics["unique_click_users"]),
            int(funnel_metrics["landing_users"]),
            int(funnel_metrics["course_users"]),
            int(funnel_metrics["leads"]),
            int(funnel_metrics["orders"]),
            int(funnel_metrics["successful_payments"]),
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
campaign_ranking["campaign_label"] = campaign_ranking.apply(
    lambda row: f"{row['campaign_name']} · {row['campaign_id']}",
    axis=1,
)

comparison_left, comparison_right = st.columns(2)

money_figure = go.Figure(
    data=[
        go.Bar(
            name="Выручка",
            x=campaign_ranking["campaign_label"],
            y=campaign_ranking["attributed_revenue"],
            hovertemplate="%{x}<br>Выручка: %{y:,.0f} ₽<extra></extra>",
        ),
        go.Bar(
            name="Расходы",
            x=campaign_ranking["campaign_label"],
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

romi_colors = ["#2E8B57" if value >= 0 else "#C44E52" for value in campaign_ranking["romi_pct"]]

romi_figure = go.Figure(
    go.Bar(
        x=campaign_ranking["campaign_label"],
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
        "campaign_id",
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
        "campaign_id": "Campaign ID",
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
        "campaign_id",
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
        "campaign_id": "Campaign ID",
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
table["CAC"] = table["CAC"].apply(lambda value: format_money(value) if pd.notna(value) else "—")

st.dataframe(table, hide_index=True, use_container_width=True)

quality_issues = report["quality_issues"]
errors_count = int((quality_issues["severity"] == "error").sum())
warnings_count = int((quality_issues["severity"] == "warning").sum())

st.subheader("Качество данных")
if errors_count:
    st.error(f"Найдено ошибок: {errors_count}; предупреждений: {warnings_count}")
elif warnings_count:
    st.warning(f"Ошибок нет; предупреждений: {warnings_count}")
else:
    st.success("Проверки качества данных пройдены")

if not quality_issues.empty:
    st.dataframe(quality_issues, hide_index=True, use_container_width=True)

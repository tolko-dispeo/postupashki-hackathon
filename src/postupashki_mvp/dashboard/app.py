"""Temporary dashboard shell; charts will be connected after the data mart exists."""

import streamlit as st

st.set_page_config(page_title="Поступашки — Marketing Measurement", layout="wide")
st.title("Поступашки — Marketing Measurement MVP")
st.info("Каркас запущен. Следующий шаг — подключить витрину воронки и ROMI.")

left, middle, right = st.columns(3)
left.metric("Размещения", "—")
middle.metric("Лиды", "—")
right.metric("ROMI", "—")

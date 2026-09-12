import {
  money,
  percent,
  count,
  escape,
  models,
  paymentLabel,
  proportion,
  finite,
} from "../utils/formatters.js";
import { sortMetrics } from "../utils/filters.js";
import { icon, hint, badge, empty, errorState } from "./ui.js";
const kpis = [
  ["total_revenue", "Общая выручка", money, "Все успешные оплаты"],
  [
    "attributed_revenue",
    "Атрибутированная выручка",
    money,
    "Связана с рекламными касаниями",
  ],
  ["cost", "Расходы на рекламу", money, "По рекламным размещениям"],
  ["romi_pct", "ROMI", percent, "По атрибутированной выручке"],
  ["campaigns", "Кампании", count],
  ["placements", "Размещения", count],
  ["clicks", "Рекламные клики", count],
  ["leads", "Лиды", count],
  ["successful_payments", "Успешные оплаты", count],
  ["cac", "CAC", money],
  ["unattributed_revenue", "Неатрибутированная выручка", money],
  ["attribution_coverage_pct", "Покрытие атрибуции", percent],
];
const tips = {
  cac: "В MVP CAC означает стоимость успешной оплаты: расходы / оплаты.",
  romi_pct:
    "(атрибутированная выручка − расходы) / расходы × 100%. Это revenue-based proxy, а не прибыль и не причинный эффект.",
  attribution_coverage_pct:
    "Доля общей выручки, связанная с рекламными касаниями.",
  unattributed_revenue:
    "Успешные оплаты или доли оплат без подходящего рекламного касания.",
};
export function renderCards(data) {
  return `<div class="kpi-grid">${kpis.map(([key, label, format, caption], i) => `<article class="metric-card ${i < 4 ? "major" : ""} ${key === "attributed_revenue" ? "accent" : ""}"><div class="metric-label">${escape(label)} ${tips[key] ? hint(tips[key]) : ""}</div><div class="metric-value ${key === "romi_pct" ? tone(data[key]) : ""}">${format(data[key])}</div>${caption ? `<div class="metric-caption">${key === "romi_pct" && finite(data[key]) !== null ? badge(data[key] >= 0 ? "Выше расходов" : "Ниже расходов", data[key] >= 0 ? "positive" : "negative") : escape(caption)}</div>` : ""}</article>`).join("")}</div>`;
}
function tone(value) {
  return finite(value) === null
    ? "muted"
    : Number(value) < 0
      ? "negative"
      : "positive";
}
export function renderFunnel(data) {
  const stages = data.stages || [];
  const max = Math.max(1, ...stages.map((s) => finite(s.value) || 0));
  return `<div class="panel-head"><div><h2>Воронка привлечения</h2><p>От первого клика до оплаты</p></div>${badge("6 этапов")}</div><div class="funnel" role="table" aria-label="Этапы воронки"><div class="funnel-heading" role="row"><span>Этап</span><span>Всего</span><span>От первого</span><span>От предыдущего</span></div>${stages.map((s, i) => `<div class="funnel-row" role="row"><div class="stage"><span class="stage-index">${String(i + 1).padStart(2, "0")}</span><div><span>${escape(s.label)}</span><div class="stage-track"><span style="width:${Math.max(0, ((finite(s.value) || 0) / max) * 100)}%;opacity:${1 - i * 0.1}"></span></div></div></div><strong>${count(s.value)}</strong><span>${percent(proportion(s.value, stages[0]?.value))}</span><span>${i ? percent(proportion(s.value, stages[i - 1].value)) : "—"}</span></div>`).join("")}</div>`;
}
export function renderQuality(data) {
  return `<div class="panel-head"><div class="quality-title">${icon("shield")}<h2>Качество данных</h2></div>${badge(data.status === "ok" ? "Проблем не найдено" : data.status === "error" ? `${data.errors_count} ошибок` : `${data.warnings_count} предупреждений`, data.status === "ok" ? "positive" : data.status === "error" ? "negative" : "warning")}</div><p class="quality-description">${data.status === "ok" ? "Проверки не выявили нарушений в выбранном наборе." : `Ошибок: ${count(data.errors_count)} · Предупреждений: ${count(data.warnings_count)}. Проверьте детали перед принятием решений.`}</p><details><summary>Показать детали</summary><div class="table-scroll"><table><thead><tr><th>Правило</th><th>Уровень</th><th>Таблица</th><th>ID сущности</th><th>Сообщение</th></tr></thead><tbody>${data.issues.map((i) => `<tr><td>${escape(i.rule_id)}</td><td>${badge(i.severity, i.severity === "error" ? "negative" : "warning")}</td><td>${escape(i.table_name)}</td><td class="technical">${escape(i.entity_id)}</td><td>${escape(i.message)}</td></tr>`).join("") || '<tr><td colspan="5">Проблем не найдено</td></tr>'}</tbody></table></div></details>`;
}
export function renderCampaigns(data, model, sort) {
  const payment =
    model === "linear" ? "payment_equivalents" : "successful_payments";
  const rows = sortMetrics(
    data.items.map((r) => ({
      ...r,
      click_to_lead_pct:
        r.click_to_lead_pct ?? proportion(r.leads, r.unique_click_users),
      lead_to_payment_pct:
        r.lead_to_payment_pct ?? proportion(r[payment], r.leads),
    })),
    sort.key,
    sort.direction,
  );
  const cols = [
    ["campaign_name", "Кампания", (v) => escape(v)],
    ["campaign_id", "Campaign ID", (v) => escape(v)],
    ["placements", "Размещения", count],
    ["unique_click_users", "Кликнувшие", count],
    ["leads", "Лиды", count],
    ["orders", "Заказы", count],
    [payment, paymentLabel(model), count],
    ["click_to_lead_pct", "Клик → лид", percent],
    ["lead_to_payment_pct", "Лид → оплата", percent],
    ["attributed_revenue", "Выручка", money],
    ["cost", "Расходы", money],
    ["cpl", "CPL", money],
    ["cpo", "CPO", money],
    ["cac", "CAC", money],
    ["romi_pct", "ROMI", percent],
  ];
  return `<div class="panel-head"><div><h2>Кампании</h2><p>Показатели по выбранной модели атрибуции</p></div>${badge(`${data.count} кампании`)}</div>${rows.length ? `<div class="table-scroll"><table class="metrics-table"><thead><tr>${cols.map(([k, l]) => `<th scope="col" aria-sort="${sort.key === k ? (sort.direction === "asc" ? "ascending" : "descending") : "none"}"><button data-sort="${k}">${l}<span aria-hidden="true">${sort.key === k ? (sort.direction === "asc" ? "↑" : "↓") : "↕"}</span></button></th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${cols.map(([k, , format], i) => `<td class="${i === 0 ? "name-cell" : i === 1 ? "technical" : k === "romi_pct" ? tone(r[k]) : "numeric"}">${format(r[k])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>` : empty("Кампаний с аналитическими данными для этого среза нет.")}`;
}
export function renderPlacements(data, model) {
  const payment =
    model === "linear" ? "payment_equivalents" : "successful_payments";
  const cols = [
    ["placement_id", "Placement ID", escape],
    ["channel_name", "Канал", escape],
    ["campaign_name", "Кампания", escape],
    ["target_product", "Продукт", escape],
    ["unique_click_users", "Кликнувшие", count],
    ["leads", "Лиды", count],
    ["orders", "Заказы", count],
    [payment, paymentLabel(model), count],
    ["attributed_revenue", "Выручка", money],
    ["cost", "Расходы", money],
    ["cac", "CAC", money],
    ["romi_pct", "ROMI", percent],
    ["is_synthetic", "Тип данных", (v) => badge(v ? "synthetic" : "real")],
  ];
  return `<div class="panel-head"><div><h2>Размещения</h2><p>Эффективность рекламных площадок</p></div>${badge(`${data.count} размещений`)}</div>${data.items.length ? `<div class="table-scroll"><table><thead><tr>${cols.map(([, l]) => `<th scope="col">${l}</th>`).join("")}</tr></thead><tbody>${data.items.map((r) => `<tr>${cols.map(([k, , format]) => `<td class="${k === "placement_id" ? "technical" : k === "romi_pct" ? tone(r[k]) : ""}">${format(r[k])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>` : empty("У выбранной кампании пока нет размещений с аналитикой.")}`;
}
export function renderAnalytics(results, filters, sort) {
  const get = (key, render) =>
    results[key].status === "fulfilled"
      ? render(results[key].value.data)
      : errorState(results[key].reason);
  const quality =
    results.quality.status === "fulfilled" ? results.quality.value.data : null;
  const noData =
    results.summary.status === "fulfilled" &&
    results.summary.value.data.campaigns === 0;
  return `${quality?.status === "error" ? '<div class="banner error" role="alert">Метрики могут быть некорректны: обнаружены ошибки качества данных.</div>' : ""}${results.quality.status === "rejected" ? '<div class="banner warning">Качество данных не удалось проверить. Доступные метрики показаны без подтверждения качества.</div>' : ""}${noData ? empty(filters.data_kind === "real" ? "Реальные данные пока не загружены. Выберите synthetic-режим для демонстрации." : "Для выбранного среза ещё нет аналитических данных. Новые записи реестра появятся в аналитике после сбора событий.", `<button class="button secondary" data-action="reset">Показать все synthetic-данные</button>`) : ""}${get("summary", renderCards)}<div class="analysis-grid"><section class="panel funnel-panel">${get("funnel", renderFunnel)}</section><section class="panel charts-panel"><div class="panel-head"><div><h2>Выручка и расходы</h2><p>Сравнение кампаний · ${escape(models[filters.attribution_model])}</p></div></div>${results.campaigns.status === "fulfilled" && results.campaigns.value.data.items.length ? '<div class="chart-wrap"><canvas id="money-chart" role="img" aria-label="Выручка и расходы по кампаниям. Значения доступны в таблице кампаний ниже."></canvas></div><div class="chart-subtitle">ROMI по кампаниям</div><div class="chart-wrap small"><canvas id="romi-chart" role="img" aria-label="ROMI по кампаниям, значения и знак доступны в таблице ниже."></canvas></div>' : results.campaigns.status === "rejected" ? errorState(results.campaigns.reason) : empty("Нет данных для сравнения.")}</section></div><section class="panel quality-panel">${get("quality", renderQuality)}</section><section class="panel">${get("campaigns", (d) => renderCampaigns(d, filters.attribution_model, sort))}</section><section class="panel">${get("placements", (d) => renderPlacements(d, filters.attribution_model))}</section>`;
}

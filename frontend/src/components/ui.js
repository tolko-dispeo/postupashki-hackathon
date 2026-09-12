import { escape } from "../utils/formatters.js";
const paths = {
  chart: "M4 19V12m8 7V5m8 14V9",
  grid: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
  refresh:
    "M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-1l2 3M4 15l2 3a7 7 0 0 0 12-1",
  plus: "M12 5v14M5 12h14",
  arrow: "M7 17 17 7M7 7h10v10",
  check: "m5 12 4 4L19 6",
  info: "M12 11v6M12 7h.01",
  copy: "M9 9h11v11H9zM15 5V3H3v12h2",
  close: "m6 6 12 12M6 18 18 6",
  shield: "m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z",
  chevron: "m9 5 7 7-7 7",
  wallet: "M3 6h18v14H3zM3 6V3h15v3M16 12h5v4h-5z",
};
export function icon(name) {
  return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.info}"/></svg>`;
}
export function hint(text) {
  return `<span class="hint" tabindex="0" role="note" aria-label="${escape(text)}">${icon("info")}<span class="hint-text">${escape(text)}</span></span>`;
}
export function empty(text, action = "") {
  return `<div class="empty-state">${icon("chart")}<strong>Пока нет данных</strong><p>${escape(text)}</p>${action}</div>`;
}
export function errorState(error) {
  return `<div class="error-state" role="alert"><strong>Не удалось загрузить данные</strong><p>${escape(error?.message || "Попробуйте ещё раз.")}</p><button class="button secondary" data-action="refresh">${icon("refresh")}Повторить</button></div>`;
}
export function toast(message, kind = "success") {
  const root = document.querySelector("#toasts");
  const item = document.createElement("div");
  item.className = `toast ${kind}`;
  item.textContent = message;
  root.append(item);
  setTimeout(() => item.remove(), 6500);
}
export function badge(text, kind = "neutral") {
  return `<span class="badge ${kind}">${escape(text)}</span>`;
}

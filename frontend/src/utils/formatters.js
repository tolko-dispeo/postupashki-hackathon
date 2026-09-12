export const DASH = "—";
export function finite(value) {
  if (
    value === null ||
    value === undefined ||
    typeof value === "boolean" ||
    (typeof value === "string" && !value.trim())
  )
    return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}
export function money(value) {
  const n = finite(value);
  return n === null
    ? DASH
    : new Intl.NumberFormat("ru-RU", {
        style: "currency",
        currency: "RUB",
        maximumFractionDigits: 2,
      }).format(n);
}
export function percent(value) {
  const n = finite(value);
  return n === null
    ? DASH
    : `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(n)}%`;
}
export function count(value) {
  const n = finite(value);
  return n === null
    ? DASH
    : new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(n);
}
export function date(value) {
  const d = new Date(value);
  return !value || Number.isNaN(d.getTime())
    ? DASH
    : new Intl.DateTimeFormat("ru-RU", {
        day: "numeric",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      }).format(d);
}
export function escape(value = "") {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
}
export function safeUrl(value) {
  try {
    const u = new URL(value);
    return ["http:", "https:"].includes(u.protocol) ? u.href : "";
  } catch {
    return "";
  }
}
export const models = {
  last_touch: "Последнее касание",
  first_touch: "Первое касание",
  linear: "Линейная",
};
export const paymentLabel = (model) =>
  model === "linear" ? "Эквивалент оплат" : "Оплаты";
// Presentation-only stage proportions; revenue, attribution and economics come from API.
export function proportion(value, denominator) {
  const v = finite(value),
    d = finite(denominator);
  return v === null || d === null || d === 0 ? null : (v / d) * 100;
}

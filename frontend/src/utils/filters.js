export const defaults = {
  data_kind: "synthetic",
  attribution_model: "last_touch",
  campaign_id: "",
};
export function normalizeFilters(input = {}) {
  const f = { ...defaults, ...input };
  if (
    !["synthetic", "real"].includes(f.data_kind) ||
    !["last_touch", "first_touch", "linear"].includes(f.attribution_model)
  )
    throw new Error("Недопустимый фильтр");
  return { ...f, campaign_id: String(f.campaign_id || "") };
}
export function filterItems(items, input) {
  const f = normalizeFilters(input);
  return items.filter(
    (r) =>
      r.is_synthetic === (f.data_kind === "synthetic") &&
      (!f.campaign_id || r.campaign_id === f.campaign_id),
  );
}
export function queryFilters(input) {
  const f = normalizeFilters(input);
  const p = new URLSearchParams({
    data_kind: f.data_kind,
    attribution_model: f.attribution_model,
  });
  if (f.campaign_id) p.set("campaign_id", f.campaign_id);
  return p.toString();
}
export function sortMetrics(items, key = "romi_pct", direction = "desc") {
  const sign = direction === "asc" ? 1 : -1;
  return [...items].sort((a, b) => {
    if (a[key] == null && b[key] != null) return 1;
    if (b[key] == null && a[key] != null) return -1;
    const av = Number(a[key]),
      bv = Number(b[key]);
    const diff =
      typeof a[key] === "string" && !Number.isFinite(av)
        ? String(a[key]).localeCompare(String(b[key]), "ru")
        : av - bv;
    return (
      sign * diff ||
      Number(b.attributed_revenue || 0) - Number(a.attributed_revenue || 0)
    );
  });
}

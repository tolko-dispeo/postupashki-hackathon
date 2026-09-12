import { escape, models } from "../utils/formatters.js";
import { icon } from "./ui.js";
export function renderFilters(f, campaigns) {
  return `<div class="filter-group"><span class="filter-label" id="cohort-label">Данные</span><div class="segmented" role="group" aria-labelledby="cohort-label">${["synthetic", "real"].map((v) => `<label class="segment ${f.data_kind === v ? "selected" : ""}"><input type="radio" name="data_kind" value="${v}" ${f.data_kind === v ? "checked" : ""}>${v === "synthetic" ? "Synthetic" : "Real"}</label>`).join("")}</div></div><label class="filter-group"><span class="filter-label">Модель атрибуции</span><select name="attribution_model">${Object.entries(
    models,
  )
    .map(
      ([k, v]) =>
        `<option value="${k}" ${k === f.attribution_model ? "selected" : ""}>${v}</option>`,
    )
    .join(
      "",
    )}</select></label><label class="filter-group campaign-filter"><span class="filter-label">Кампания</span><select name="campaign_id"><option value="">Все кампании</option>${campaigns
    .filter((c) => c.is_synthetic === (f.data_kind === "synthetic"))
    .map(
      (c) =>
        `<option value="${escape(c.campaign_id)}" ${c.campaign_id === f.campaign_id ? "selected" : ""}>${escape(c.campaign_name)}</option>`,
    )
    .join(
      "",
    )}</select></label><button class="button ghost reset" data-action="reset">${icon("refresh")}Сбросить фильтры</button>`;
}

import { escape, money, date, safeUrl } from "../utils/formatters.js";
import { badge, icon, empty, errorState } from "./ui.js";
export function renderRegistry(
  campaignsResult,
  placementsResult,
  filters,
  highlight,
  created,
) {
  const campaigns =
    campaignsResult.status === "fulfilled"
      ? campaignsResult.value.items.filter(
          (c) => c.is_synthetic === (filters.data_kind === "synthetic"),
        )
      : [];
  const placements =
    placementsResult.status === "fulfilled"
      ? placementsResult.value.items.filter(
          (p) =>
            p.is_synthetic === (filters.data_kind === "synthetic") &&
            (!filters.campaign_id || p.campaign_id === filters.campaign_id),
        )
      : [];
  const link = (url) =>
    safeUrl(url)
      ? `<a href="${escape(safeUrl(url))}" target="_blank" rel="noopener noreferrer">${escape(url)}</a>`
      : "—";
  return `${created ? `<div class="created-link banner success"><div><strong>${icon("check")} Размещение создано</strong><p>Tracking-ссылка</p><input aria-label="Созданная tracking-ссылка" readonly value="${escape(created.tracking_url)}"></div><button class="button secondary" data-copy="${escape(created.tracking_url)}">${icon("copy")}Скопировать ссылку</button></div>` : ""}<section class="panel"><div class="panel-head"><div><h2>Рекламные кампании</h2><p>Объединяйте размещения по продукту или запуску</p></div><button class="button primary" data-action="new-campaign">${icon("plus")}Новая кампания</button></div>${campaignsResult.status === "rejected" ? errorState(campaignsResult.reason) : campaigns.length ? `<div class="table-scroll"><table><thead><tr><th>Кампания</th><th>Campaign ID</th><th>Размещения</th><th>Тип данных</th><th>Создана</th><th>Действие</th></tr></thead><tbody>${campaigns.map((c) => `<tr class="${highlight === c.campaign_id ? "highlight" : ""}"><td class="name-cell">${escape(c.campaign_name)}</td><td class="technical">${escape(c.campaign_id)}</td><td>${c.placements_count}</td><td>${badge(c.is_synthetic ? "synthetic" : "real")}</td><td>${date(c.created_at)}</td><td><button class="button ghost" data-view-campaign="${escape(c.campaign_id)}">Показать размещения ${icon("chevron")}</button></td></tr>`).join("")}</tbody></table></div>` : empty(filters.data_kind === "real" ? "Реальные кампании пока не созданы." : "Создайте первую кампанию, чтобы добавить рекламные размещения.")}</section><section class="panel"><div class="panel-head"><div><h2>Рекламные размещения</h2><p>Площадки, расходы и ссылки для отслеживания</p></div><button class="button primary" data-action="new-placement" ${campaigns.length ? "" : 'disabled title="Сначала создайте кампанию выбранного типа данных"'}>${icon("plus")}Новое размещение</button></div>${placementsResult.status === "rejected" ? errorState(placementsResult.reason) : placements.length ? `<div class="table-scroll"><table><thead><tr><th>Канал</th><th>Placement ID</th><th>Кампания</th><th>Продукт</th><th>Расходы</th><th>Landing URL</th><th>Tracking URL</th><th>Действие</th></tr></thead><tbody>${placements.map((p) => `<tr class="${highlight === p.placement_id ? "highlight" : ""}"><td class="name-cell">${escape(p.channel_name)}</td><td class="technical">${escape(p.placement_id)}</td><td>${escape(p.campaign_name)}</td><td>${escape(p.target_product) || "—"}</td><td>${money(p.cost)}</td><td class="url-cell">${link(p.landing_url)}</td><td class="url-cell">${link(p.tracking_url)}</td><td><button class="button ghost" data-copy="${escape(p.tracking_url)}" aria-label="Скопировать tracking-ссылку ${escape(p.channel_name)}">${icon("copy")}Копировать</button></td></tr>`).join("")}</tbody></table></div>` : empty("У выбранной кампании пока нет размещений. Добавьте площадку и получите tracking-ссылку.")}</section>`;
}

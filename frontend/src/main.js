import "./styles.css";
import { api } from "./api/index.js";
import { defaults, normalizeFilters } from "./utils/filters.js";
import { models, escape, date } from "./utils/formatters.js";
import { renderFilters } from "./components/filters.js";
import { renderAnalytics } from "./components/analytics.js";
import { drawCharts, destroyCharts } from "./components/charts.js";
import { renderRegistry } from "./components/registry.js";
import { openRegistryForm } from "./components/forms.js";
import { icon, hint, toast } from "./components/ui.js";
import { copyTrackingLink } from "./components/clipboard.js";

let filters = { ...defaults },
  view = "analytics",
  campaigns = [],
  revision = 0,
  results,
  highlight = "",
  created = null;
let sort = { key: "romi_pct", direction: "desc" };
document.querySelector("#app").innerHTML =
  `<header class="topbar"><div class="topbar-inner"><a class="brand" href="#analytics" aria-label="Поступашки — главная"><span class="brand-mark">п<span>↗</span></span><span><strong>поступашки</strong><small>MARKETING MEASUREMENT</small></span></a><nav aria-label="Разделы приложения"><button class="nav-button active" data-view="analytics" aria-current="page">${icon("chart")}Аналитика</button><button class="nav-button" data-view="registry">${icon("grid")}Реестр рекламы</button></nav><div class="header-actions"><span class="source-badge"><i></i>${api.source === "mock" ? "Mock" : "API"}</span><span class="avatar" aria-label="Рабочее пространство Поступашки">П</span></div></div></header><main id="main"><div class="page-heading"><div><p class="eyebrow">Рабочее пространство / <span id="breadcrumb">Аналитика</span></p><h1 id="page-title">Маркетинг в цифрах</h1><p id="page-description">От рекламного клика до оплаты — вся картина в одном месте.</p></div><button class="button secondary" data-action="refresh">${icon("refresh")}<span>Обновить данные</span></button></div><section class="filters" aria-label="Фильтры аналитики"></section><div class="method-row"><span id="method"></span>${hint("Атрибуция распределяет наблюдаемую выручку, но не доказывает причинный эффект рекламы.")}<span id="updated"></span></div><div class="load-status" role="status" aria-live="polite"></div><div id="content" aria-busy="true"><div class="skeleton-grid">${Array.from({ length: 4 }, () => '<div class="skeleton"></div>').join("")}</div><div class="skeleton large"></div></div><footer><span>Поступашки <span class="footer-dot">·</span> Marketing Measurement MVP</span><span>Атрибуция ≠ причинный эффект</span>${api.source === "mock" ? '<details class="demo-controls"><summary>Демо-сценарии</summary><label>Сценарий <select id="scenario"><option value="default">Обычная аналитика</option><option value="zero">Нулевые показатели</option><option value="empty">Пустой реестр</option><option value="error-quality">Ошибка качества данных</option><option value="network-error">Источник недоступен</option></select></label><p>Новые записи хранятся до перезагрузки страницы. Tracking-ссылки требуют backend.</p></details>' : ""}</footer></main>`;
function updateFilters() {
  const active = document.activeElement;
  const restore = active?.closest(".filters")
    ? { name: active.name, value: active.value }
    : null;
  document.querySelector(".filters").innerHTML = renderFilters(
    filters,
    campaigns,
  );
  if (restore)
    [...document.querySelectorAll(".filters [name]")]
      .find((el) => el.name === restore.name && el.value === restore.value)
      ?.focus();
  document.querySelector("#method").textContent =
    `Модель: ${models[filters.attribution_model].toLowerCase()} · Окно: 30 дней · Данные: ${filters.data_kind}`;
}
function paintAnalytics() {
  document.querySelector("#content").innerHTML = renderAnalytics(
    results,
    filters,
    sort,
  );
  if (results.campaigns.status === "fulfilled")
    drawCharts(results.campaigns.value.data.items, filters.attribution_model);
}
async function refresh() {
  const ticket = ++revision;
  const selected = { ...filters };
  const selectedView = view;
  const content = document.querySelector("#content");
  content.setAttribute("aria-busy", "true");
  content.classList.add("loading");
  document.querySelector(".load-status").textContent = "Обновляем данные…";
  document
    .querySelectorAll('[data-action="refresh"]')
    .forEach((b) => (b.disabled = true));
  const calls =
    selectedView === "analytics"
      ? {
          summary: () => api.getSummary(selected),
          campaigns: () => api.getCampaignMetrics(selected),
          funnel: () => api.getFunnel(selected),
          placements: () => api.getPlacementMetrics(selected),
          quality: () => api.getDataQuality(selected),
          registry: () => api.getCampaigns(),
        }
      : {
          registry: () => api.getCampaigns(),
          placements: () => api.getPlacements(selected.campaign_id),
        };
  const settled = await Promise.allSettled(
    Object.values(calls).map((fn) => Promise.resolve().then(fn)),
  );
  if (ticket !== revision) return;
  results = Object.fromEntries(
    Object.keys(calls).map((key, i) => [key, settled[i]]),
  );
  if (results.registry.status === "fulfilled")
    campaigns = results.registry.value.items;
  updateFilters();
  destroyCharts();
  // Refuse mismatched analytic metadata to avoid silently displaying another cohort/model.
  if (selectedView === "analytics")
    for (const [key, r] of Object.entries(results)) {
      if (key === "registry" || r.status !== "fulfilled") continue;
      const meta = r.value.meta;
      if (
        meta?.data_kind !== selected.data_kind ||
        meta?.attribution_model !== selected.attribution_model ||
        meta?.attribution_window_days !== 30
      )
        results[key] = {
          status: "rejected",
          reason: new Error(
            "Ответ источника не соответствует выбранным фильтрам или окну атрибуции.",
          ),
        };
    }
  if (selectedView === "analytics") {
    paintAnalytics();
    const meta =
      results.summary.status === "fulfilled"
        ? results.summary.value.meta
        : null;
    document.querySelector("#updated").textContent = meta
      ? `Данные на ${date(meta.generated_at)}`
      : "";
    if (results.registry.status === "rejected")
      toast(
        "Список кампаний недоступен. Обновите данные, чтобы загрузить фильтр.",
        "warning",
      );
  } else {
    content.innerHTML = renderRegistry(
      results.registry,
      results.placements,
      filters,
      highlight,
      created,
    );
    document.querySelector("#updated").textContent =
      api.source === "mock" ? "Изменения сохраняются в текущей сессии" : "";
  }
  content.classList.remove("loading");
  content.setAttribute("aria-busy", "false");
  document.querySelector(".load-status").textContent = "";
  document
    .querySelectorAll('[data-action="refresh"]')
    .forEach((b) => (b.disabled = false));
}
function setView(next) {
  view = next;
  document.querySelectorAll("[data-view]").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === view);
    if (b.dataset.view === view) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  });
  document.querySelector("#breadcrumb").textContent =
    view === "analytics" ? "Аналитика" : "Реестр рекламы";
  document.querySelector("#page-title").textContent =
    view === "analytics" ? "Маркетинг в цифрах" : "Реестр рекламы";
  document.querySelector("#page-description").textContent =
    view === "analytics"
      ? "От рекламного клика до оплаты — вся картина в одном месте."
      : "Кампании, площадки и tracking-ссылки для ваших запусков.";
  refresh();
}
document.addEventListener("change", (event) => {
  if (event.target.closest(".filters")) {
    const { name, value } = event.target;
    if (name === "data_kind" || name === "campaign_id") created = null;
    filters = normalizeFilters({
      ...filters,
      [name]: value,
      ...(name === "data_kind" ? { campaign_id: "" } : {}),
    });
    updateFilters();
    refresh();
  }
  if (event.target.id === "scenario") {
    api.setScenario(event.target.value);
    created = null;
    highlight = "";
    filters = { ...defaults };
    refresh();
  }
});
document.addEventListener("click", async (event) => {
  const b = event.target.closest("button,a.brand");
  if (!b) return;
  if (b.matches("a.brand")) {
    event.preventDefault();
    setView("analytics");
    return;
  }
  if (b.dataset.view) {
    setView(b.dataset.view);
    return;
  }
  if (b.dataset.sort) {
    sort = {
      key: b.dataset.sort,
      direction:
        sort.key === b.dataset.sort && sort.direction === "desc"
          ? "asc"
          : "desc",
    };
    paintAnalytics();
    document.querySelector(`[data-sort="${sort.key}"]`)?.focus();
    return;
  }
  if (b.dataset.viewCampaign) {
    filters = { ...filters, campaign_id: b.dataset.viewCampaign };
    updateFilters();
    await refresh();
    return;
  }
  if (b.dataset.copy) {
    await copyTrackingLink(b);
    return;
  }
  const action = b.dataset.action;
  if (action === "refresh") refresh();
  if (action === "reset") {
    filters = { ...defaults };
    updateFilters();
    refresh();
  }
  if (action === "new-campaign" || action === "new-placement")
    openRegistryForm(
      action === "new-campaign" ? "campaign" : "placement",
      api,
      campaigns,
      filters,
      async (row, type) => {
        highlight = type === "campaign" ? row.campaign_id : row.placement_id;
        created = type === "placement" ? row : null;
        filters = {
          ...filters,
          data_kind: row.is_synthetic ? "synthetic" : "real",
          campaign_id: row.campaign_id,
        };
        await refresh();
      },
    );
});
updateFilters();
refresh().catch((error) => toast(escape(error.message), "error"));

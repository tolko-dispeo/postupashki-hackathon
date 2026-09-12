import { normalizeFilters } from "../utils/filters.js";
import { validateCampaign, validatePlacement } from "../utils/validators.js";
import { ApiError } from "./http-client.js";

export function createMockClient({
  fetcher = globalThis.fetch,
  delay = 180,
  scenario = "default",
} = {}) {
  let dataPromise;
  let campaigns = [],
    placements = [];
  let currentScenario = scenario;
  async function load() {
    if (currentScenario === "network-error")
      throw new ApiError(
        "Демонстрация: источник данных недоступен. Выберите другой сценарий или повторите запрос.",
      );
    if (delay) await new Promise((resolve) => setTimeout(resolve, delay));
    if (!dataPromise)
      dataPromise = Promise.all(
        ["summary", "campaigns", "placements", "funnel", "data-quality"].map(
          async (name) => {
            const response = await fetcher(
              `${import.meta.env.BASE_URL || "/"}mock/${name}.json`,
            );
            if (!response.ok)
              throw new ApiError(
                "Не удалось загрузить демонстрационные данные",
              );
            return [name, await response.json()];
          },
        ),
      )
        .then(Object.fromEntries)
        .catch((error) => {
          dataPromise = undefined;
          throw error;
        });
    return dataPromise;
  }
  async function analytic(name, input) {
    const f = normalizeFilters(input);
    const files = await load();
    const saved =
      files[name].snapshots[f.attribution_model][f.campaign_id || "all"];
    const blank =
      f.data_kind === "real" || currentScenario === "empty" || !saved;
    let data;
    if (blank || currentScenario === "zero") {
      data =
        name === "summary"
          ? structuredClone(files.summary.empty)
          : name === "funnel"
            ? {
                campaign_id: f.campaign_id || null,
                stages: files.funnel.snapshots.last_touch.all.data.stages.map(
                  (s) => ({ ...s, value: 0 }),
                ),
              }
            : name === "data-quality"
              ? { status: "ok", errors_count: 0, warnings_count: 0, issues: [] }
              : { items: [], count: 0 };
      if (currentScenario === "zero" && !blank) {
        if (name === "summary")
          data = {
            ...data,
            campaigns: saved.data.campaigns,
            placements: saved.data.placements,
          };
        if (name === "campaigns" || name === "placements")
          data = {
            count: saved.data.count,
            items: saved.data.items.map((row) =>
              Object.fromEntries(
                Object.entries(row).map(([key, value]) => [
                  key,
                  [
                    "cost",
                    "attributed_revenue",
                    "total_revenue",
                    "unattributed_revenue",
                  ].includes(key)
                    ? "0.00"
                    : [
                          "cpl",
                          "cpo",
                          "cac",
                          "romi_pct",
                          "click_to_lead_pct",
                          "lead_to_payment_pct",
                        ].includes(key)
                      ? null
                      : typeof value === "number" && key !== "placements"
                        ? 0
                        : value,
                ]),
              ),
            ),
          };
      }
    } else data = structuredClone(saved.data);
    if (
      name === "data-quality" &&
      currentScenario === "error-quality" &&
      !blank
    )
      data = {
        status: "error",
        errors_count: 1,
        warnings_count: 0,
        issues: [
          {
            rule_id: "unknown_reference",
            severity: "error",
            table_name: "payments",
            entity_id: "pay_demo_error",
            message:
              "Оплата ссылается на неизвестный заказ. Проверьте загрузку заказов.",
          },
        ],
      };
    return {
      meta: {
        data_kind: f.data_kind,
        attribution_model: f.attribution_model,
        attribution_window_days: 30,
        generated_at: files.summary.snapshots.last_touch.all.meta.generated_at,
      },
      data,
    };
  }
  async function getCampaigns() {
    const files = await load();
    const items = [
      ...(currentScenario === "empty" ? [] : files.campaigns.registry),
      ...campaigns,
    ].map((c) => ({
      ...c,
      placements_count:
        c.placements_count +
        placements.filter((p) => p.campaign_id === c.campaign_id).length,
    }));
    return { items: structuredClone(items), count: items.length };
  }
  async function getPlacements(id) {
    const files = await load();
    const items = [
      ...(currentScenario === "empty" ? [] : files.placements.registry),
      ...placements,
    ].filter((p) => !id || p.campaign_id === id);
    return { items: structuredClone(items), count: items.length };
  }
  return {
    source: "mock",
    setScenario(value) {
      currentScenario = value;
    },
    getSummary: (f) => analytic("summary", f),
    getCampaignMetrics: (f) => analytic("campaigns", f),
    getPlacementMetrics: (f) => analytic("placements", f),
    getFunnel: (f) => analytic("funnel", f),
    getDataQuality: (f) => analytic("data-quality", f),
    getCampaigns,
    getPlacements,
    async createCampaign(p) {
      const errors = validateCampaign(p, "mock");
      if (Object.keys(errors).length)
        throw new ApiError("Проверьте поля формы", 422, errors);
      const all = await getCampaigns();
      if (
        all.items.some(
          (c) =>
            c.campaign_name.toLowerCase() ===
            p.campaign_name.trim().toLowerCase(),
        )
      )
        throw new ApiError("Кампания с таким названием уже существует", 409, {
          campaign_name: "Выберите другое название",
        });
      const c = {
        campaign_id: `cmp_${crypto.randomUUID()}`,
        campaign_name: p.campaign_name.trim(),
        is_synthetic: true,
        placements_count: 0,
        created_at: new Date().toISOString(),
      };
      campaigns.push(c);
      return structuredClone(c);
    },
    async createPlacement(p) {
      const errors = validatePlacement(p);
      if (Object.keys(errors).length)
        throw new ApiError("Проверьте поля формы", 422, errors);
      const c = (await getCampaigns()).items.find(
        (c) => c.campaign_id === p.campaign_id,
      );
      if (!c) throw new ApiError("Кампания не найдена", 404);
      const id = `plc_${crypto.randomUUID()}`;
      const row = {
        ...p,
        channel_name: p.channel_name.trim(),
        target_product: p.target_product?.trim() || null,
        placement_id: id,
        campaign_name: c.campaign_name,
        is_synthetic: c.is_synthetic,
        cost: Number(p.cost).toFixed(2),
        created_at: new Date().toISOString(),
        tracking_url: `http://127.0.0.1:8000/t/${id}`,
      };
      placements.push(row);
      return structuredClone(row);
    },
  };
}

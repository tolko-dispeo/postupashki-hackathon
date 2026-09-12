import { queryFilters } from "../utils/filters.js";
export class ApiError extends Error {
  constructor(message, status = 0, fields = {}) {
    super(message);
    this.status = status;
    this.fields = fields;
  }
}
export function normalizeError(body, status) {
  const detail = body?.detail;
  let message = typeof detail === "string" ? detail : detail?.message;
  const fields = {};
  if (Array.isArray(detail)) {
    for (const row of detail)
      if (row.loc?.length && row.msg) fields[row.loc.at(-1)] = row.msg;
    message = "Проверьте заполнение полей";
  }
  const translations = {
    "Campaign not found": "Кампания не найдена",
    "Placement not found": "Размещение не найдено",
    "Campaign already exists": "Кампания уже существует",
  };
  return new ApiError(
    translations[message] ||
      message ||
      "Не удалось выполнить запрос. Попробуйте ещё раз.",
    status,
    fields,
  );
}
export function createHttpClient(
  baseUrl,
  fetcher = globalThis.fetch,
  timeout = 12000,
) {
  const base = String(baseUrl || "").replace(/\/$/, "");
  async function request(path, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetcher(`${base}${path}`, {
        ...options,
        signal: controller.signal,
        headers: {
          Accept: "application/json",
          ...(options.body ? { "Content-Type": "application/json" } : {}),
        },
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) throw normalizeError(body, response.status);
      if (!body || typeof body !== "object")
        throw new ApiError("Сервер вернул неожиданный формат данных");
      return body;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(
        "Не удалось связаться с сервером. Проверьте подключение и повторите запрос.",
      );
    } finally {
      clearTimeout(timer);
    }
  }
  const analytics = (path) => (filters) =>
    request(`${path}?${queryFilters(filters)}`);
  return {
    source: "api",
    getSummary: analytics("/analytics/summary"),
    getCampaignMetrics: analytics("/analytics/campaigns"),
    getFunnel: analytics("/analytics/funnel"),
    getPlacementMetrics: analytics("/analytics/placements"),
    getDataQuality: analytics("/data-quality/summary"),
    getCampaigns: () => request("/campaigns"),
    getPlacements: (id) =>
      request(
        `/placements${id ? `?${new URLSearchParams({ campaign_id: id })}` : ""}`,
      ),
    createCampaign: (payload) =>
      request("/campaigns", { method: "POST", body: JSON.stringify(payload) }),
    createPlacement: (payload) =>
      request("/placements", { method: "POST", body: JSON.stringify(payload) }),
  };
}

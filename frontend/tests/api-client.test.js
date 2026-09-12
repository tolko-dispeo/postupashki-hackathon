import { readFile } from "node:fs/promises";
import { it, expect, vi } from "vitest";
import { createClient } from "../src/api/index.js";
import { createMockClient } from "../src/api/mock-client.js";
import { createHttpClient, normalizeError } from "../src/api/http-client.js";
const fetchMock = async (url) => ({
  ok: true,
  json: async () =>
    JSON.parse(
      await readFile(new URL(`../public${url}`, import.meta.url), "utf8"),
    ),
});
const client = () => createMockClient({ fetcher: fetchMock, delay: 0 });
it("allows building a registry from the empty scenario", async () => {
  const c = client();
  c.setScenario("empty");
  const row = await c.createCampaign({
    campaign_name: "First",
    is_synthetic: true,
  });
  expect((await c.getCampaigns()).items).toEqual([row]);
  const p = await c.createPlacement({
    campaign_id: row.campaign_id,
    channel_name: "Channel",
    landing_url: "https://example.com",
    cost: 0,
  });
  expect((await c.getPlacements(row.campaign_id)).items).toEqual([p]);
});
it("zero scenario retains campaigns with missing ratios and zero money", async () => {
  const c = client();
  c.setScenario("zero");
  const summary = (await c.getSummary({})).data;
  const rows = (await c.getCampaignMetrics({})).data.items;
  expect(rows).toHaveLength(summary.campaigns);
  expect(
    rows.every(
      (r) => r.romi_pct === null && r.cost === "0.00" && r.leads === 0,
    ),
  ).toBe(true);
  expect((await c.getSummary({ data_kind: "real" })).data.campaigns).toBe(0);
});
it("selects source without falling back", () => {
  expect(createClient({ VITE_DATA_SOURCE: "mock" }).source).toBe("mock");
  expect(createClient({ VITE_DATA_SOURCE: "api" }).source).toBe("api");
  expect(() => createClient({ VITE_DATA_SOURCE: "other" })).toThrow();
});
it.each([
  { detail: "Campaign not found" },
  { detail: { code: "campaign_not_found", message: "Campaign not found" } },
])("normalizes FastAPI error %s", (body) => {
  const e = normalizeError(body, 404);
  expect(e.message).toBe("Кампания не найдена");
  expect(e.status).toBe(404);
});
it("normalizes validation fields and unknown bodies", () => {
  expect(
    normalizeError(
      { detail: [{ loc: ["body", "cost"], msg: "Invalid value" }] },
      422,
    ).fields,
  ).toEqual({ cost: "Invalid value" });
  expect(normalizeError({}, 500).message).toBe(
    "Не удалось выполнить запрос. Попробуйте ещё раз.",
  );
});
it("sends cohort and model in the HTTP adapter", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => ({ data: {} }) });
  await createHttpClient("http://localhost:8000/", fetcher).getSummary({
    data_kind: "real",
    attribution_model: "linear",
    campaign_id: "a b",
  });
  expect(fetcher.mock.calls[0][0]).toBe(
    "http://localhost:8000/analytics/summary?data_kind=real&attribution_model=linear&campaign_id=a+b",
  );
});
it.each([404, 409, 422])(
  "propagates status %s and preserves payload",
  async (status) => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: false,
      status,
      json: async () => ({ detail: "Rejected" }),
    });
    const payload = { campaign_name: "Test", is_synthetic: true };
    await expect(
      createHttpClient("", fetcher).createCampaign(payload),
    ).rejects.toMatchObject({ status });
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual(payload);
  },
);
it("does not switch to mock on network failure", async () => {
  await expect(
    createHttpClient("", () =>
      Promise.reject(new Error("network")),
    ).getCampaigns(),
  ).rejects.toThrow("Не удалось связаться");
});
it("does not lose monetary precision by parsing money in the adapter", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => ({ cost: "8950.00" }) });
  expect((await createHttpClient("", fetcher).createPlacement({})).cost).toBe(
    "8950.00",
  );
});
it("real is empty with real metadata", async () => {
  const c = client();
  expect((await c.getSummary({ data_kind: "real" })).data.campaigns).toBe(0);
  expect((await c.getFunnel({ data_kind: "real" })).meta.data_kind).toBe(
    "real",
  );
  expect(
    (await c.getCampaignMetrics({ data_kind: "real" })).data.items,
  ).toEqual([]);
});
it.each(["last_touch", "first_touch", "linear"])(
  "uses consistent precomputed snapshots for %s",
  async (model) => {
    const c = client();
    const f = { attribution_model: model };
    const summary = (await c.getSummary(f)).data;
    const campaigns = (await c.getCampaignMetrics(f)).data.items;
    const placements = (await c.getPlacementMetrics(f)).data.items;
    expect(
      campaigns.reduce((s, r) => s + Number(r.attributed_revenue), 0) +
        Number(summary.unattributed_revenue),
    ).toBe(Number(summary.total_revenue));
    expect(campaigns.reduce((s, r) => s + r.payment_equivalents, 0)).toBe(
      summary.payment_equivalents,
    );
    expect(summary.unique_click_users).toBeLessThan(
      campaigns.reduce((s, r) => s + r.unique_click_users, 0),
    );
    for (const r of campaigns) {
      const ps = placements.filter((p) => p.campaign_id === r.campaign_id);
      expect(ps.reduce((s, p) => s + Number(p.attributed_revenue), 0)).toBe(
        Number(r.attributed_revenue),
      );
      expect(
        (await c.getFunnel({ ...f, campaign_id: r.campaign_id })).data.stages[0]
          .value,
      ).toBe(r.unique_click_users);
    }
  },
);
it("switching model changes the distribution", async () => {
  const c = client();
  const f = { campaign_id: "cmp_autumn_ml" };
  expect(
    (await c.getSummary({ ...f, attribution_model: "first_touch" })).data
      .attributed_revenue,
  ).not.toBe((await c.getSummary(f)).data.attributed_revenue);
  expect(
    (await c.getSummary({ ...f, attribution_model: "linear" })).data
      .payment_equivalents,
  ).toBe(9.5);
});
it("creates a campaign and placement only in client memory", async () => {
  const c = client();
  const row = await c.createCampaign({
    campaign_name: " Новая ",
    is_synthetic: true,
  });
  const p = await c.createPlacement({
    campaign_id: row.campaign_id,
    channel_name: "Канал",
    landing_url: "https://example.com",
    cost: 5000,
  });
  expect(p.tracking_url).toContain(`/t/${p.placement_id}`);
  expect((await c.getPlacements(row.campaign_id)).items).toHaveLength(1);
  expect(
    (await c.getCampaigns()).items.find(
      (i) => i.campaign_id === row.campaign_id,
    ).placements_count,
  ).toBe(1);
  expect((await client().getCampaigns()).count).toBe(3);
});
it("mock surfaces duplicate and missing parent errors", async () => {
  const c = client();
  await expect(
    c.createCampaign({
      campaign_name: "Осенний запуск ML",
      is_synthetic: true,
    }),
  ).rejects.toMatchObject({ status: 409 });
  await expect(
    c.createPlacement({
      campaign_id: "missing",
      channel_name: "Канал",
      landing_url: "https://example.com",
      cost: 1,
    }),
  ).rejects.toMatchObject({ status: 404 });
});
it("supports explicit demo states and retry after network errors", async () => {
  const c = client();
  c.setScenario("error-quality");
  expect((await c.getDataQuality({})).data.status).toBe("error");
  c.setScenario("zero");
  expect((await c.getSummary({})).data.romi_pct).toBeNull();
  c.setScenario("empty");
  expect((await c.getCampaigns()).count).toBe(0);
  c.setScenario("network-error");
  await expect(c.getSummary({})).rejects.toThrow();
  c.setScenario("default");
  expect((await c.getCampaigns()).count).toBe(3);
});

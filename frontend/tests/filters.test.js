import { it, expect } from "vitest";
import {
  normalizeFilters,
  filterItems,
  queryFilters,
  sortMetrics,
} from "../src/utils/filters.js";
it("defaults to synthetic last touch", () => {
  expect(normalizeFilters()).toEqual({
    data_kind: "synthetic",
    attribution_model: "last_touch",
    campaign_id: "",
  });
});
it.each(["last_touch", "first_touch", "linear"])("supports model %s", (model) =>
  expect(queryFilters({ attribution_model: model })).toContain(
    `attribution_model=${model}`,
  ),
);
it("keeps campaign IDs and cohorts isolated", () => {
  const rows = [
    { campaign_id: "a", is_synthetic: true },
    { campaign_id: "b", is_synthetic: true },
    { campaign_id: "a", is_synthetic: false },
  ];
  expect(filterItems(rows, { campaign_id: "a" })).toEqual([rows[0]]);
  expect(filterItems(rows, { data_kind: "real" })).toEqual([rows[2]]);
});
it.each([{ data_kind: "mixed" }, { attribution_model: "made_up" }])(
  "rejects unsupported filter %s",
  (f) => expect(() => normalizeFilters(f)).toThrow(),
);
it("encodes query strings", () =>
  expect(queryFilters({ campaign_id: "a&b" })).toContain("campaign_id=a%26b"));
it("sorts nulls last and revenue as numeric secondary key", () => {
  const rows = [
    { romi_pct: null },
    { romi_pct: 10, attributed_revenue: "9.00" },
    { romi_pct: 10, attributed_revenue: "100.00" },
    { romi_pct: -5 },
  ];
  expect(sortMetrics(rows)[0].attributed_revenue).toBe("100.00");
  expect(sortMetrics(rows).at(-1).romi_pct).toBeNull();
  expect(sortMetrics(rows, "romi_pct", "asc")[0].romi_pct).toBe(-5);
  expect(rows[0].romi_pct).toBeNull();
});

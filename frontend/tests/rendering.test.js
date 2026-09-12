import { it, expect } from "vitest";
import {
  renderCards,
  renderCampaigns,
  renderFunnel,
  renderQuality,
} from "../src/components/analytics.js";
it("never renders non-finite numbers in metric cards", () => {
  expect(
    renderCards({ cac: Infinity, romi_pct: NaN, total_revenue: null }),
  ).not.toMatch(/NaN|Infinity/);
});
it("does not disguise linear equivalents as physical payments", () => {
  const html = renderCampaigns(
    {
      count: 1,
      items: [
        {
          campaign_id: "c",
          campaign_name: "x",
          payment_equivalents: 0.5,
          successful_payments: 1,
        },
      ],
    },
    "linear",
    { key: "romi_pct", direction: "desc" },
  );
  expect(html).toContain("Эквивалент оплат");
  expect(html).toContain("0,5");
});
it("renders actual non-monotonic funnel", () => {
  const html = renderFunnel({
    stages: [
      { value: 10, label: "Первый" },
      { value: 20, label: "Второй" },
    ],
  });
  expect(html).toContain("200%");
  expect(html).toContain("<strong>20</strong>");
});
it("escapes quality messages from server", () => {
  const html = renderQuality({
    status: "error",
    errors_count: 1,
    warnings_count: 0,
    issues: [
      { rule_id: "x", message: "<script>alert(1)</script>", severity: "error" },
    ],
  });
  expect(html).not.toContain("<script>");
  expect(html).toContain("&lt;script&gt;");
});

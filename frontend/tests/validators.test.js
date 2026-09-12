import { it, expect } from "vitest";
import {
  validateCampaign,
  validatePlacement,
} from "../src/utils/validators.js";
const valid = {
  campaign_id: "a",
  channel_name: "Канал",
  landing_url: "https://example.com",
  cost: 0,
};
it("accepts a valid zero-cost placement", () =>
  expect(validatePlacement(valid)).toEqual({}));
it.each(["ftp://example.com", "javascript:alert(1)", "example.com", ""])(
  "rejects URL %s",
  (url) =>
    expect(validatePlacement({ ...valid, landing_url: url })).toHaveProperty(
      "landing_url",
    ),
);
it.each([NaN, Infinity, -1, "", null, true])("rejects cost %s", (cost) =>
  expect(validatePlacement({ ...valid, cost })).toHaveProperty("cost"),
);
it("rejects whitespace-only names", () => {
  expect(
    validateCampaign({ campaign_name: "  ", is_synthetic: true }),
  ).toHaveProperty("campaign_name");
  expect(validatePlacement({ ...valid, channel_name: " " })).toHaveProperty(
    "channel_name",
  );
});
it("enforces maximum lengths", () => {
  expect(
    validateCampaign({ campaign_name: "a".repeat(256), is_synthetic: true }),
  ).toHaveProperty("campaign_name");
  expect(
    validatePlacement({ ...valid, target_product: "a".repeat(256) }),
  ).toHaveProperty("target_product");
});
it("restricts mock creations to synthetic", () => {
  expect(
    validateCampaign(
      { campaign_name: "Кампания", is_synthetic: false },
      "mock",
    ),
  ).toHaveProperty("is_synthetic");
  expect(
    validateCampaign({ campaign_name: "Кампания", is_synthetic: false }, "api"),
  ).toEqual({});
});

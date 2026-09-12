import { describe, it, expect } from "vitest";
import {
  money,
  percent,
  count,
  finite,
  date,
  escape,
  safeUrl,
  paymentLabel,
  proportion,
} from "../src/utils/formatters.js";
describe("presentation values", () => {
  it("formats rubles in Russian without changing the source", () => {
    expect(money("8950.00").replace(/\s/g, " ")).toBe("8 950,00 ₽");
    expect(money(0)).toContain("0,00");
  });
  it("formats fractions and negative percentages", () => {
    expect(percent(-26.286)).toBe("-26,3%");
    expect(count(0.5)).toBe("0,5");
  });
  it.each([
    null,
    undefined,
    "",
    NaN,
    Infinity,
    -Infinity,
    "NaN",
    "Infinity",
    true,
  ])("renders missing or invalid %s as a dash", (v) => {
    for (const formatter of [money, percent, count])
      expect(formatter(v)).toBe("—");
    expect(finite(v)).toBeNull();
  });
  it("uses payment equivalents only in linear label", () => {
    expect(paymentLabel("linear")).toBe("Эквивалент оплат");
    expect(paymentLabel("last_touch")).toBe("Оплаты");
  });
  it("shows non-monotonic funnels without clamping conversions", () => {
    expect(proportion(120, 100)).toBe(120);
    expect(proportion(1, 0)).toBeNull();
    expect(proportion(null, 10)).toBeNull();
  });
  it("escapes user content and refuses executable links", () => {
    expect(escape('<img onerror="x">')).toBe(
      "&lt;img onerror=&quot;x&quot;&gt;",
    );
    expect(safeUrl("javascript:alert(1)")).toBe("");
    expect(safeUrl("https://example.com")).toBe("https://example.com/");
  });
  it("handles absent dates", () => {
    expect(date(null)).toBe("—");
    expect(date("invalid")).toBe("—");
  });
});

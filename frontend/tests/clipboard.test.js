// @vitest-environment jsdom
import { afterEach, it, expect, vi } from "vitest";
import { copyTrackingLink } from "../src/components/clipboard.js";
afterEach(() => {
  document.body.innerHTML = "";
});
function setup() {
  document.body.innerHTML =
    '<div><button data-copy="https://example.com/t/1">Копировать</button></div><div id="toasts"></div>';
  return document.querySelector("button");
}
it("copies the exact tracking URL and announces success", async () => {
  const button = setup();
  const clipboard = { writeText: vi.fn().mockResolvedValue() };
  await copyTrackingLink(button, clipboard);
  expect(clipboard.writeText).toHaveBeenCalledWith("https://example.com/t/1");
  expect(document.querySelector("#toasts").textContent).toContain(
    "скопирована",
  );
  expect(button.disabled).toBe(false);
});
it("provides a focused manual fallback when permission is denied", async () => {
  const button = setup();
  const clipboard = {
    writeText: vi.fn().mockRejectedValue(new Error("denied")),
  };
  await copyTrackingLink(button, clipboard);
  expect(document.activeElement.value).toBe("https://example.com/t/1");
  expect(document.activeElement.selectionEnd).toBe(
    document.activeElement.value.length,
  );
  expect(document.querySelector("#toasts").textContent).toContain("вручную");
  expect(button.disabled).toBe(false);
  await copyTrackingLink(button, clipboard);
  expect(document.querySelectorAll(".copy-fallback")).toHaveLength(1);
});

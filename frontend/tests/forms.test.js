// @vitest-environment jsdom
import { beforeEach, afterEach, it, expect, vi } from "vitest";
import { openRegistryForm } from "../src/components/forms.js";

beforeEach(() => {
  document.body.innerHTML =
    '<button id="opener">Открыть</button><div id="toasts"></div>';
  document.querySelector("#opener").focus();
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function () {
    this.open = false;
    this.dispatchEvent(new Event("close"));
  };
});
afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});
const submit = () =>
  document
    .querySelector("form")
    .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
it("blocks invalid input before sending and focuses the error", () => {
  const api = { source: "mock", createCampaign: vi.fn() };
  openRegistryForm("campaign", api, [], { data_kind: "synthetic" }, vi.fn());
  document.querySelector('[name="campaign_name"]').value = "   ";
  submit();
  expect(api.createCampaign).not.toHaveBeenCalled();
  expect(document.activeElement.name).toBe("campaign_name");
  expect(document.activeElement.getAttribute("aria-invalid")).toBe("true");
});
it.each([404, 409, 422])(
  "preserves input on server error %s and allows retry",
  async (status) => {
    const api = {
      source: "api",
      createCampaign: vi.fn().mockRejectedValue({
        status,
        message: "Ошибка сервера",
        fields: { campaign_name: "Проверьте название" },
      }),
    };
    openRegistryForm("campaign", api, [], { data_kind: "real" }, vi.fn());
    document.querySelector('[name="campaign_name"]').value = "Моя кампания";
    submit();
    await vi.waitFor(() =>
      expect(document.querySelector('[type="submit"]').disabled).toBe(false),
    );
    expect(document.querySelector('[name="campaign_name"]').value).toBe(
      "Моя кампания",
    );
    expect(document.querySelector('[role="alert"]').textContent).toBe(
      "Ошибка сервера",
    );
    expect(api.createCampaign).toHaveBeenCalledWith({
      campaign_name: "Моя кампания",
      is_synthetic: false,
    });
  },
);
it("prevents duplicate submission and restores focus after success", async () => {
  let finish;
  const api = {
    source: "mock",
    createCampaign: vi.fn(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    ),
  };
  const created = vi.fn();
  openRegistryForm("campaign", api, [], { data_kind: "synthetic" }, created);
  document.querySelector('[name="campaign_name"]').value = "Новая";
  submit();
  submit();
  expect(api.createCampaign).toHaveBeenCalledTimes(1);
  expect(document.querySelector('[type="submit"]').disabled).toBe(true);
  finish({ campaign_id: "new", is_synthetic: true });
  await vi.waitFor(() => expect(created).toHaveBeenCalledTimes(1));
  expect(document.querySelector("dialog")).toBeNull();
  expect(document.activeElement.id).toBe("opener");
});

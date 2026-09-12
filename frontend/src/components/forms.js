import { escape } from "../utils/formatters.js";
import { validateCampaign, validatePlacement } from "../utils/validators.js";
import { icon, toast } from "./ui.js";
export function openRegistryForm(type, api, campaigns, filters, onCreated) {
  const previous = document.activeElement;
  const dialog = document.createElement("dialog");
  dialog.className = "form-dialog";
  dialog.setAttribute("aria-labelledby", "form-title");
  const field = (name, label, input) =>
    `<label class="form-field" for="field-${name}">${label}</label>${input}<p class="field-error" id="error-${name}"></p>`;
  const attr = (name) =>
    `id="field-${name}" name="${name}" aria-describedby="error-${name}"`;
  const campaign = type === "campaign";
  const eligible = campaigns.filter(
    (c) => c.is_synthetic === (filters.data_kind === "synthetic"),
  );
  dialog.innerHTML = `<div class="dialog-heading"><div><p class="eyebrow">Реестр рекламы</p><h2 id="form-title">${campaign ? "Новая кампания" : "Новое размещение"}</h2></div><button class="button icon-button" type="button" data-close aria-label="Закрыть форму">${icon("close")}</button></div><form novalidate><p class="form-intro">${campaign ? "Дайте кампании название, понятное вашей команде." : "Укажите рекламную площадку. После создания вы получите tracking-ссылку."}</p>${campaign ? `${field("campaign_name", "Название кампании *", `<input ${attr("campaign_name")} maxlength="255" autocomplete="off" placeholder="Например, осенний запуск ML" required>`)}${field("is_synthetic", "Тип данных", `<select ${attr("is_synthetic")}><option value="true">Synthetic — демонстрационные</option><option value="false" ${api.source === "mock" ? "disabled" : ""} ${filters.data_kind === "real" && api.source === "api" ? "selected" : ""}>Real — реальные</option></select>`)}${api.source === "mock" ? '<p class="form-help">В mock-режиме создаются только synthetic-кампании.</p>' : ""}` : `${field("campaign_id", "Кампания *", `<select ${attr("campaign_id")} required><option value="">Выберите кампанию</option>${eligible.map((c) => `<option value="${escape(c.campaign_id)}" ${c.campaign_id === filters.campaign_id ? "selected" : ""}>${escape(c.campaign_name)}</option>`).join("")}</select>`)}${field("channel_name", "Название канала *", `<input ${attr("channel_name")} maxlength="255" placeholder="Например, Data Science Jobs" required>`)}${field("target_product", "Продукт", `<input ${attr("target_product")} maxlength="255" placeholder="Например, ML Start">`)}${field("landing_url", "Посадочная страница *", `<input ${attr("landing_url")} type="url" placeholder="https://postupashki.ru/" required>`)}${field("cost", "Расходы, ₽ *", `<input ${attr("cost")} type="number" min="0" step="0.01" inputmode="decimal" placeholder="0.00" required>`)}`}<div class="form-server-error" role="alert"></div><div class="dialog-actions"><button type="button" class="button secondary" data-close>Отмена</button><button type="submit" class="button primary">${campaign ? "Создать кампанию" : "Создать размещение"}</button></div></form>`;
  document.body.append(dialog);
  dialog.showModal();
  dialog.addEventListener("keydown", (event) => {
    if (event.key !== "Tab") return;
    const targets = [
      ...dialog.querySelectorAll(
        "button:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex='0']",
      ),
    ];
    const first = targets[0],
      last = targets.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  });
  dialog.addEventListener("close", () => {
    dialog.remove();
    previous?.focus();
  });
  dialog
    .querySelectorAll("[data-close]")
    .forEach((b) => b.addEventListener("click", () => dialog.close()));
  let submitting = false;
  dialog.querySelector("form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (submitting) return;
    const form = event.target;
    const raw = Object.fromEntries(new FormData(form));
    const payload = campaign
      ? {
          campaign_name: raw.campaign_name.trim(),
          is_synthetic: raw.is_synthetic === "true",
        }
      : {
          ...raw,
          channel_name: raw.channel_name.trim(),
          target_product: raw.target_product.trim() || null,
          landing_url: raw.landing_url.trim(),
        };
    const showErrors = (errors) => {
      form
        .querySelectorAll(".field-error")
        .forEach((e) => (e.textContent = ""));
      form
        .querySelectorAll("[aria-invalid]")
        .forEach((e) => e.removeAttribute("aria-invalid"));
      for (const [key, message] of Object.entries(errors)) {
        const e = form.querySelector(`#error-${key}`);
        if (e) {
          e.textContent = message;
          form.elements[key]?.setAttribute("aria-invalid", "true");
        }
      }
      form.querySelector("[aria-invalid]")?.focus();
    };
    const errors = campaign
      ? validateCampaign(payload, api.source)
      : validatePlacement(payload);
    showErrors(errors);
    if (Object.keys(errors).length) return;
    if (!campaign) payload.cost = Number(payload.cost);
    submitting = true;
    const submit = form.querySelector('[type="submit"]');
    submit.disabled = true;
    submit.textContent = "Создаём…";
    form.querySelector(".form-server-error").textContent = "";
    try {
      const row =
        await api[campaign ? "createCampaign" : "createPlacement"](payload);
      dialog.close();
      toast(campaign ? "Кампания создана" : "Размещение создано");
      await onCreated(row, type);
    } catch (error) {
      if (dialog.isConnected) {
        showErrors(error.fields || {});
        form.querySelector(".form-server-error").textContent = error.message;
      }
    } finally {
      submitting = false;
      if (dialog.isConnected) {
        submit.disabled = false;
        submit.textContent = campaign
          ? "Создать кампанию"
          : "Создать размещение";
      }
    }
  });
}

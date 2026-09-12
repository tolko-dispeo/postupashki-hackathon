import { safeUrl } from "./formatters.js";
export function validateCampaign(p, source = "api") {
  const e = {};
  if (!p.campaign_name?.trim()) e.campaign_name = "Введите название кампании";
  else if (p.campaign_name.length > 255)
    e.campaign_name = "Не более 255 символов";
  if (
    typeof p.is_synthetic !== "boolean" ||
    (source === "mock" && !p.is_synthetic)
  )
    e.is_synthetic = "В демонстрации доступны только synthetic-кампании";
  return e;
}
export function validatePlacement(p) {
  const e = {};
  if (!p.campaign_id?.trim()) e.campaign_id = "Выберите кампанию";
  if (!p.channel_name?.trim()) e.channel_name = "Введите название канала";
  else if (p.channel_name.length > 255)
    e.channel_name = "Не более 255 символов";
  if ((p.target_product || "").length > 255)
    e.target_product = "Не более 255 символов";
  if (!safeUrl(p.landing_url))
    e.landing_url = "Введите полный адрес с http:// или https://";
  if (
    p.cost == null ||
    typeof p.cost === "boolean" ||
    String(p.cost).trim() === "" ||
    !Number.isFinite(Number(p.cost)) ||
    Number(p.cost) < 0
  )
    e.cost = "Расходы должны быть конечным числом не меньше нуля";
  return e;
}

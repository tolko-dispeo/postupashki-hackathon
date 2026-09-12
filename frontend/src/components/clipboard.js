import { toast } from "./ui.js";

export async function copyTrackingLink(
  button,
  clipboard = navigator.clipboard,
) {
  button.disabled = true;
  try {
    await clipboard.writeText(button.dataset.copy);
    toast("Tracking-ссылка скопирована");
  } catch {
    toast(
      "Не удалось скопировать ссылку. Выделите её и скопируйте вручную.",
      "warning",
    );
    let input = button.parentElement.querySelector(".copy-fallback");
    if (!input) {
      input = document.createElement("input");
      input.className = "copy-fallback";
      input.readOnly = true;
      input.setAttribute("aria-label", "Ссылка для ручного копирования");
      button.after(input);
    }
    input.value = button.dataset.copy;
    input.focus();
    input.select();
  } finally {
    button.disabled = false;
  }
}

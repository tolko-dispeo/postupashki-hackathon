import {
  Chart,
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from "chart.js";
import { money, percent, models } from "../utils/formatters.js";
Chart.register(
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
);
let charts = [];
export function destroyCharts() {
  charts.forEach((c) => c.destroy());
  charts = [];
}
export function drawCharts(items, model) {
  destroyCharts();
  const canvas = document.querySelector("#money-chart");
  if (!canvas) return;
  const labels = items.map((r) => r.campaign_name);
  const base = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
      legend: {
        position: "bottom",
        labels: {
          usePointStyle: true,
          pointStyle: "rectRounded",
          boxWidth: 9,
          padding: 16,
          color: "#667085",
          font: { size: 11 },
        },
      },
      tooltip: {
        callbacks: {
          title: (rows) => `${labels[rows[0].dataIndex]} · ${models[model]}`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        border: { display: false },
        ticks: {
          color: "#667085",
          font: { size: 10 },
          callback(_value, index) {
            return labels[index]
              .replace("Осенний запуск", "Запуск")
              .replace("Карьерный интенсив", "Карьера");
          },
        },
      },
      y: {
        border: { display: false },
        grid: { color: "#edf0f5" },
        ticks: {
          color: "#667085",
          font: { size: 10 },
          callback: (v) => `${Number(v) / 1000} тыс.`,
        },
      },
    },
  };
  charts.push(
    new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Атрибутированная выручка",
            data: items.map((r) => r.attributed_revenue),
            backgroundColor: "#2563eb",
            borderRadius: 4,
            maxBarThickness: 30,
          },
          {
            label: "Расходы",
            data: items.map((r) => r.cost),
            backgroundColor: "#cbd5e1",
            borderRadius: 4,
            maxBarThickness: 30,
          },
        ],
      },
      options: {
        ...base,
        plugins: {
          ...base.plugins,
          tooltip: {
            callbacks: {
              ...base.plugins.tooltip.callbacks,
              label: (ctx) => `${ctx.dataset.label}: ${money(ctx.raw)}`,
            },
          },
        },
      },
    }),
  );
  charts.push(
    new Chart(document.querySelector("#romi-chart"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            // A tiny gray marker at the baseline keeps missing values discoverable.
            // The tooltip always reads the original value, so null stays a dash.
            data: items.map((r) => r.romi_pct ?? 0),
            minBarLength: 3,
            backgroundColor: items.map((r) =>
              r.romi_pct === null
                ? "#98a2b3"
                : r.romi_pct < 0
                  ? "#b42318"
                  : "#15803d",
            ),
            borderRadius: 4,
            maxBarThickness: 40,
          },
        ],
      },
      options: {
        ...base,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              ...base.plugins.tooltip.callbacks,
              label: (ctx) => `ROMI: ${percent(items[ctx.dataIndex].romi_pct)}`,
            },
          },
        },
        scales: {
          ...base.scales,
          y: {
            ...base.scales.y,
            beginAtZero: true,
            grid: {
              color: (ctx) => (ctx.tick.value === 0 ? "#667085" : "#edf0f5"),
              lineWidth: (ctx) => (ctx.tick.value === 0 ? 1.5 : 1),
            },
            ticks: { ...base.scales.y.ticks, callback: (v) => `${v}%` },
          },
        },
      },
    }),
  );
}

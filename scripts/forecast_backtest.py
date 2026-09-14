"""Run: python scripts/forecast_backtest.py --input ... --data-kind real --output ..."""

import argparse
import hashlib
import html
import io
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from postupashki_mvp.services.forecasting import evaluate_forecast, prepare_daily_revenue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--data-kind", choices=["real", "synthetic"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--horizon", type=int, default=7)
    parser.add_argument("--min-train-days", type=int, default=14)
    parser.add_argument("--fill-missing-zero", action="store_true")
    args = parser.parse_args()
    input_bytes = args.input.read_bytes()
    frame = pd.read_csv(io.BytesIO(input_bytes))
    daily = prepare_daily_revenue(frame, fill_missing=args.fill_missing_zero)
    result = evaluate_forecast(daily, horizon=args.horizon, min_train_days=args.min_train_days)
    summary = result["summary"]
    summary.update({
        "data_kind": args.data_kind,
        "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "fill_missing_zero": args.fill_missing_zero,
    })
    args.output.mkdir(parents=True, exist_ok=True)
    for name in ("predictions", "metrics", "forecast"):
        result[name].to_csv(args.output / f"{name}.csv", index=False)
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    plot = go.Figure()
    plot.add_scatter(x=daily.index, y=daily.values, name="Факт")
    held = result["predictions"].query("phase == 'holdout'")
    for model, group in held.groupby("model"):
        plot.add_scatter(x=group.date, y=group.predicted, name=f"Backtest: {model}")
    plot.add_scatter(
        x=result["forecast"].date, y=result["forecast"].predicted_revenue,
        name="Прогноз", line={"dash": "dash"},
    )
    plot.add_vrect(
        x0=summary["holdout_start"], x1=summary["history_end"],
        fillcolor="#7767ff", opacity=0.08, line_width=0,
    )
    plot.update_layout(
        template="plotly_white", yaxis_title="Выручка, единицы CSV", height=440,
        margin={"l": 65, "r": 20, "t": 25, "b": 110},
        legend={"orientation": "h", "y": -0.22, "x": 0},
        font={"family": "Arial", "color": "#071426"},
    )
    selected = html.escape(summary["selected_model"])
    metrics = result["metrics"].copy()
    metrics["phase"] = metrics["phase"].replace({
        "validation": "Выбор модели", "holdout": "Отложенная неделя"
        if args.horizon == 7 else "Отложенный период",
    })
    metrics = metrics.rename(columns={"phase": "Период", "model": "Модель",
                                      "mae": "MAE", "rmse": "RMSE",
                                      "wape_pct": "WAPE, %", "bias": "Смещение"})
    metrics = metrics.astype(object).where(metrics.notna(), "не определено")
    future = result["forecast"].rename(columns={
        "date": "Дата", "model": "Модель", "predicted_revenue": "Прогноз выручки",
    })
    report = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Поступашки: forecast / backtest</title>
<style>*{{box-sizing:border-box}}body{{font:16px/1.6 system-ui;margin:0;
color:#071426;background:#f7f8fc}}main{{max-width:1150px;margin:auto;padding:32px 24px}}
h1{{font-size:clamp(26px,4vw,42px);line-height:1.18}}h2{{margin-top:32px}}
.eyebrow{{color:#526378;font-size:13px;letter-spacing:.1em}}
.table-wrap{{overflow-x:auto;border:1px solid #d9e1ea;border-radius:10px;background:white}}
table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:12px 16px;
text-align:left;white-space:nowrap}}th{{background:#071426;color:white}}
tr:nth-child(even){{background:#eef3f8}}aside{{background:#eef3f8;padding:18px;
border-left:4px solid #35c2d6;border-radius:6px}}.chart{{background:white;
border-radius:12px;overflow:hidden}}.kpis{{display:grid;grid-template-columns:repeat(3,1fr);
gap:14px;margin:24px 0}}.kpi{{padding:18px;background:white;border:1px solid #d9e1ea;
border-radius:10px}}.kpi strong{{font-size:24px;display:block}}.muted{{color:#536477}}
@media(max-width:600px){{main{{padding:20px 12px}}.kpis{{grid-template-columns:1fr}}
td,th{{padding:10px}}}}@media print{{.table-wrap{{overflow:visible}}main{{padding:0}}}}
</style></head><body><main><p class="eyebrow">ПОСТУПАШКИ / FORECAST &amp; BACKTEST</p>
<h1>Прогноз дневной выручки и backtest</h1>
<aside>Данные: <b>{args.data_kind}</b>. Горизонт: {args.horizon} дней.
Это прогноз временного ряда, а не оценка причинного эффекта рекламы.
Synthetic проверяет работу метода, но не качество прогноза реальных продаж.</aside>
<div class="kpis"><div class="kpi">История<strong>{summary['history_days']} дней</strong></div>
<div class="kpi">MAE на holdout<strong>{summary['holdout_mae']:,.2f}</strong></div>
<div class="kpi">Прогноз за {args.horizon} дней<strong>{summary['forecast_total']:,.2f}</strong></div></div>
<p class="muted">История: {summary['history_start']} — {summary['history_end']}.
Прогноз строится на конец этой истории, а не на текущую дату. Денежные значения
выражены в единицах входного CSV.</p>
<h2>Метод проверки</h2><p>Обучение расширяется по времени. Выбор модели: минимальный MAE
на {summary['validation_folds']} последовательных validation-окнах.
Последние {args.horizon} дней отложены для финального backtest и не участвуют в выборе.
Модель: <b>{selected}</b>. Будущий прогноз использует всю доступную историю.</p>
<div class="chart">{plot.to_html(full_html=False, include_plotlyjs=True, config={'responsive': True, 'displaylogo': False})}</div>
<p class="muted">Выделенный период: финальный holdout. Пунктир: будущий прогноз.</p>
<h2>Ошибки моделей</h2><div class="table-wrap" tabindex="0" aria-label="Сравнение моделей">{metrics.to_html(index=False, float_format=lambda v: f'{v:,.2f}', na_rep='не определено')}</div>
<p>MAE и RMSE выражены в единицах выручки. WAPE = Σ|ошибка| / Σ|факт| × 100%.
При нулевой сумме факта WAPE не определён. Bias = среднее (прогноз − факт).</p>
<h2>Прогноз на следующие дни</h2><div class="table-wrap" tabindex="0" aria-label="Прогноз по дням">{future.to_html(index=False, float_format=lambda v: f'{v:,.2f}')}</div>
<h2>Ограничения</h2><p>Нет признаков будущих кампаний, расходов, цен и запусков курсов.
Прогноз не обосновывает перераспределение рекламного бюджета. Отрицательное улучшение
относительно weekly_naive означает проигрыш базовой модели. Прогнозные интервалы
не заявляются: для оценки их покрытия требуется отдельная проверка.</p></main></body></html>"""
    (args.output / "report.html").write_text(report, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

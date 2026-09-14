"""Run: python scripts/forecast_backtest.py --input ... --data-kind real --output ..."""

import argparse
import hashlib
import html
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
    frame = pd.read_csv(args.input)
    daily = prepare_daily_revenue(frame, fill_missing=args.fill_missing_zero)
    result = evaluate_forecast(daily, horizon=args.horizon, min_train_days=args.min_train_days)
    summary = result["summary"]
    summary.update({
        "data_kind": args.data_kind,
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
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
    plot.update_layout(template="plotly_white", yaxis_title="Выручка, единицы входного CSV")
    selected = html.escape(summary["selected_model"])
    report = f"""<!doctype html><html lang="ru"><meta charset="utf-8">
<title>Поступашки: forecast / backtest</title>
<style>body{{font:16px system-ui;max-width:1150px;margin:40px auto;color:#071426}}
table{{border-collapse:collapse}}td,th{{padding:8px 15px;border:1px solid #ddd}}
aside{{background:#eef3f8;padding:18px}}h1,h2{{color:#071426}}</style>
<h1>Прогноз дневной выручки и backtest</h1>
<aside>Данные: <b>{args.data_kind}</b>. Горизонт: {args.horizon} дней.
Это прогноз временного ряда, а не оценка причинного эффекта рекламы.
Synthetic проверяет работу метода, но не качество прогноза реальных продаж.</aside>
<h2>Метод проверки</h2><p>Обучение расширяется по времени. Выбор модели: минимальный MAE
на {summary['validation_folds']} последовательных validation-окнах.
Последние {args.horizon} дней отложены для финального backtest и не участвуют в выборе.
Модель: <b>{selected}</b>. Будущий прогноз использует всю доступную историю.</p>
{plot.to_html(full_html=False, include_plotlyjs=True)}
<h2>Ошибки моделей</h2>{result['metrics'].to_html(index=False, float_format=lambda v: f'{v:,.2f}', na_rep='не определено')}
<p>MAE и RMSE выражены в единицах выручки. WAPE = Σ|ошибка| / Σ|факт| × 100%.
При нулевой сумме факта WAPE не определён. Bias = среднее (прогноз − факт).</p>
<h2>Прогноз на следующие дни</h2>{result['forecast'].to_html(index=False, float_format=lambda v: f'{v:,.2f}')}
<h2>Ограничения</h2><p>Нет признаков будущих кампаний, расходов, цен и запусков курсов.
Прогноз не обосновывает перераспределение рекламного бюджета. Отрицательное улучшение
относительно weekly_naive означает проигрыш базовой модели. Прогнозные интервалы
не заявляются: для оценки их покрытия требуется отдельная проверка.</p></html>"""
    (args.output / "report.html").write_text(report, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

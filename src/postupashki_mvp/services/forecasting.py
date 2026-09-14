"""Daily revenue forecasts with chronological model selection and a final holdout."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

MODELS = ("last_value", "weekly_naive", "weekday_mean")


def prepare_daily_revenue(frame: pd.DataFrame, *, fill_missing: bool = False) -> pd.Series:
    """Aggregate date/revenue rows; gaps are errors unless explicitly declared zero days."""
    if not {"date", "revenue"}.issubset(frame.columns) or frame.empty:
        raise ValueError("Input must contain nonempty date and revenue columns")
    dates = pd.to_datetime(frame["date"], errors="raise", utc=True).dt.normalize()
    amounts = pd.to_numeric(frame["revenue"], errors="raise")
    if dates.isna().any() or not np.isfinite(amounts).all() or (amounts < 0).any():
        raise ValueError("Dates and nonnegative revenue must be finite and non-null")
    series = pd.Series(amounts.to_numpy(dtype=float), index=pd.DatetimeIndex(dates))
    series = series.groupby(level=0).sum().sort_index()
    if not np.isfinite(series).all():
        raise ValueError("Daily revenue overflow")
    calendar = pd.date_range(series.index.min(), series.index.max(), freq="D")
    if len(calendar) != len(series) and not fill_missing:
        raise ValueError("Missing dates: provide zero days or explicitly enable fill_missing")
    return series.reindex(calendar, fill_value=0.0).rename("revenue")


def predict(train: pd.Series, horizon: int, model: str) -> np.ndarray:
    """Fixed-origin forecast. Never reads actual values inside the forecast horizon."""
    if model not in MODELS or horizon < 1 or len(train) < 7:
        raise ValueError("Known model, positive horizon and at least seven training days required")
    if model == "last_value":
        return np.repeat(float(train.iloc[-1]), horizon)
    if model == "weekly_naive":
        return np.resize(train.iloc[-7:].to_numpy(dtype=float), horizon)
    recent = train.iloc[-28:]
    by_weekday = recent.groupby(recent.index.dayofweek).mean()
    future = pd.date_range(train.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D")
    return np.array([by_weekday[day.dayofweek] for day in future], dtype=float)


def error_metrics(actual, predicted) -> dict:
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    errors = predicted - actual
    denominator = float(np.abs(actual).sum())
    return {
        "mae": float(np.abs(errors).mean()),
        "rmse": float(np.sqrt(np.square(errors).mean())),
        "wape_pct": float(np.abs(errors).sum() / denominator * 100) if denominator else None,
        "bias": float(errors.mean()),
    }


def evaluate_forecast(
    daily: pd.Series, *, horizon: int = 7, min_train_days: int = 14
) -> dict:
    """Select by rolling validation MAE; evaluate once on the untouched last horizon."""
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be a positive integer")
    if (isinstance(min_train_days, bool)
            or not isinstance(min_train_days, int) or min_train_days < 7):
        raise ValueError("min_train_days must be at least seven")
    # Apply the same contract to direct callers as to the CLI.
    daily = prepare_daily_revenue(pd.DataFrame({"date": daily.index, "revenue": daily.values}))
    if len(daily) < min_train_days + 2 * horizon:
        raise ValueError("Need training history, at least one validation fold and final holdout")
    holdout_start = len(daily) - horizon
    origins = list(range(min_train_days, holdout_start - horizon + 1, horizon))
    rows = []
    for phase, starts in (("validation", origins), ("holdout", [holdout_start])):
        for fold, start in enumerate(starts, 1):
            train, actual = daily.iloc[:start], daily.iloc[start:start + horizon]
            for model in MODELS:
                predictions = predict(train, horizon, model)
                for step, (date, value, estimate) in enumerate(
                    zip(actual.index, actual.values, predictions, strict=True), 1
                ):
                    rows.append({
                        "phase": phase, "fold": fold, "model": model,
                        "origin": train.index[-1].date().isoformat(),
                        "date": date.date().isoformat(), "step": step,
                        "actual": float(value), "predicted": float(estimate),
                    })
    predictions = pd.DataFrame(rows)
    metrics = pd.DataFrame([
        {"phase": phase, "model": model, **error_metrics(group.actual, group.predicted)}
        for (phase, model), group in predictions.groupby(["phase", "model"], sort=False)
    ])
    validation = metrics[metrics.phase == "validation"].set_index("model")
    # Stable tie-breaking favours the first (simplest) model, never the holdout winner.
    selected = min(MODELS, key=lambda model: validation.loc[model, "mae"])
    future_dates = pd.date_range(
        daily.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D"
    )
    future = pd.DataFrame({
        "date": future_dates.strftime("%Y-%m-%d"), "model": selected,
        "predicted_revenue": predict(daily, horizon, selected),
    })
    holdout = metrics[metrics.phase == "holdout"].set_index("model")
    base_mae = float(holdout.loc["weekly_naive", "mae"])
    selected_mae = float(holdout.loc[selected, "mae"])
    summary = {
        "target": "daily_revenue", "horizon_days": horizon,
        "history_start": daily.index[0].date().isoformat(),
        "history_end": daily.index[-1].date().isoformat(), "history_days": len(daily),
        "validation_folds": len(origins), "min_train_days": min_train_days,
        "holdout_start": daily.index[holdout_start].date().isoformat(),
        "selected_model": selected, "selection_metric": "validation_mae",
        "holdout_mae": selected_mae,
        "holdout_improvement_vs_weekly_naive_pct": (
            100 * (base_mae - selected_mae) / base_mae if base_mae else None
        ),
        "forecast_total": float(future.predicted_revenue.sum()),
    }
    assert math.isfinite(summary["forecast_total"])
    return {"predictions": predictions, "metrics": metrics, "forecast": future, "summary": summary}

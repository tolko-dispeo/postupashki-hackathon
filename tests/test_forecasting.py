import numpy as np
import pandas as pd
import pytest

from postupashki_mvp.services.forecasting import (
    evaluate_forecast,
    predict,
    prepare_daily_revenue,
)


def series(values):
    return pd.Series(values, index=pd.date_range("2026-01-01", periods=len(values)))


def test_constant_forecast_has_zero_error():
    result = evaluate_forecast(series([10.0] * 42))
    assert (result["metrics"].mae == 0).all()
    assert result["forecast"].predicted_revenue.tolist() == [10.0] * 7


def test_weekly_pattern_is_preserved_beyond_one_week():
    train = series([1, 2, 3, 4, 5, 6, 7] * 4)
    assert predict(train, 15, "weekly_naive").tolist() == [1, 2, 3, 4, 5, 6, 7] * 2 + [1]
    assert predict(train, 15, "weekday_mean").tolist() == [1, 2, 3, 4, 5, 6, 7] * 2 + [1]


def test_holdout_cannot_change_selection_or_holdout_predictions():
    history = series([100, 20, 30, 50, 70, 80, 10] * 8)
    first = evaluate_forecast(history)
    history.iloc[-7:] = 999999
    second = evaluate_forecast(history)
    assert first["summary"]["selected_model"] == second["summary"]["selected_model"]
    pd.testing.assert_frame_equal(
        first["predictions"].drop(columns="actual"),
        second["predictions"].drop(columns="actual"),
    )
    assert (pd.to_datetime(first["predictions"].origin)
            < pd.to_datetime(first["predictions"].date)).all()


def test_zero_revenue_has_undefined_wape_and_finite_forecast():
    result = evaluate_forecast(series([0] * 28))
    assert result["metrics"].wape_pct.isna().all()
    assert np.isfinite(result["forecast"].predicted_revenue).all()
    assert result["summary"]["holdout_improvement_vs_weekly_naive_pct"] is None


def test_unsorted_intraday_rows_are_aggregated():
    frame = pd.DataFrame({"date": ["2026-01-02", "2026-01-01", "2026-01-01"],
                          "revenue": [4, 2, 3]})
    assert prepare_daily_revenue(frame).tolist() == [5, 4]


def test_gaps_require_explicit_permission():
    frame = pd.DataFrame({"date": ["2026-01-01", "2026-01-03"], "revenue": [3, 7]})
    with pytest.raises(ValueError, match="Missing dates"):
        prepare_daily_revenue(frame)
    assert prepare_daily_revenue(frame, fill_missing=True).tolist() == [3, 0, 7]


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_revenue_rejected(value):
    with pytest.raises(ValueError):
        prepare_daily_revenue(pd.DataFrame({"date": ["2026-01-01"], "revenue": [value]}))


@pytest.mark.parametrize("length", [0, 7, 27])
def test_insufficient_history_rejected(length):
    with pytest.raises(ValueError):
        evaluate_forecast(series([10] * length))


def test_fold_windows_do_not_overlap_and_future_starts_after_history():
    result = evaluate_forecast(series(list(range(56))))
    rows = result["predictions"].query("model == 'last_value'")
    assert rows.date.is_unique
    assert result["forecast"].date.iloc[0] == "2026-02-26"
    assert len(result["forecast"]) == 7

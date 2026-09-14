import numpy as np
import pandas as pd
import pytest

from postupashki_mvp.services.forecasting import (
    error_metrics,
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


def test_error_formulas_against_hand_calculation():
    result = error_metrics([0, 10, 20], [3, 7, 26])
    assert result["mae"] == 4
    assert result["rmse"] == pytest.approx(np.sqrt(18))
    assert result["wape_pct"] == 40
    assert result["bias"] == 2


@pytest.mark.parametrize("horizon", [True, 0, -2, 2.5])
def test_invalid_horizons(horizon):
    with pytest.raises(ValueError):
        evaluate_forecast(series([1] * 40), horizon=horizon)


@pytest.mark.parametrize("days", [True, 0, 6, 14.5])
def test_invalid_training_lengths(days):
    with pytest.raises(ValueError):
        evaluate_forecast(series([1] * 40), min_train_days=days)


@pytest.mark.parametrize("actual,predicted", [([], []), ([1], [1, 2]),
                                            ([float("nan")], [1])])
def test_invalid_metric_vectors(actual, predicted):
    with pytest.raises(ValueError):
        error_metrics(actual, predicted)


def test_numeric_date_does_not_become_epoch_nanoseconds():
    with pytest.raises(ValueError, match="ISO"):
        prepare_daily_revenue(pd.DataFrame({"date": [20260101], "revenue": [1]}))


def test_rmse_does_not_overflow_when_squaring_large_values():
    assert error_metrics([0, 0], [1e160, 1e160])["rmse"] == 1e160


def test_each_validation_origin_cannot_read_its_future():
    history = series(np.arange(64) * 100.0)
    original = evaluate_forecast(history)["predictions"]
    for start in [14, 21, 28, 35, 42, 49]:
        changed = history.copy()
        changed.iloc[start:] = 123456
        updated = evaluate_forecast(changed)["predictions"]
        cutoff = history.index[start - 1].date().isoformat()
        pd.testing.assert_frame_equal(
            original[original.origin <= cutoff].drop(columns="actual"),
            updated[updated.origin <= cutoff].drop(columns="actual"),
        )

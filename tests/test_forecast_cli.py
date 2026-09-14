"""CLI integration: CSV -> forecast artifacts, including zero and invalid inputs."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def run_cli(source, output, *options):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/forecast_backtest.py"),
         "--input", str(source), "--output", str(output), "--data-kind", "synthetic",
         *options], env=env, capture_output=True, text=True, encoding="utf-8", timeout=60,
        check=False,
    )


@pytest.mark.parametrize("zero", [False, True])
def test_cli_creates_consistent_offline_report(tmp_path, zero):
    source = tmp_path / "daily.csv"
    frame = pd.read_csv(ROOT / "data/mock/forecast/daily_revenue.csv")
    if zero:
        frame["revenue"] = 0
    frame.to_csv(source, index=False)
    output = tmp_path / "report"
    result = run_cli(source, output)
    assert result.returncode == 0, result.stderr
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["input_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    forecasts = pd.read_csv(output / "forecast.csv")
    assert len(forecasts) == 7
    assert forecasts.predicted_revenue.sum() == pytest.approx(summary["forecast_total"])
    assert {p.name for p in output.iterdir()} == {
        "forecast.csv", "predictions.csv", "metrics.csv", "summary.json", "report.html",
    }
    report = (output / "report.html").read_text(encoding="utf-8")
    assert 'name="viewport"' in report
    assert "overflow-x:auto" in report
    assert "Plotly.newPlot" in report
    assert '<script src="https://' not in report
    assert "не определено" in report if zero else "Отложенная неделя" in report
    before = (output / "summary.json").read_bytes()
    assert run_cli(source, output).returncode == 0
    assert before == (output / "summary.json").read_bytes()


def test_invalid_csv_fails_before_creating_output(tmp_path):
    source = tmp_path / "bad.csv"
    source.write_text("date,revenue\n2026-01-01,-1\n", encoding="utf-8")
    output = tmp_path / "report"
    assert run_cli(source, output).returncode != 0
    assert not output.exists()

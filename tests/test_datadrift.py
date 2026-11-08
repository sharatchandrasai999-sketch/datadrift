"""Tests for datadrift."""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from datadrift.detect import DriftError, compare, format_text, load_csv

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _write_csv(path, rows, columns):
    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)


def test_detects_added_column(tmp_path):
    base = tmp_path / "base.csv"
    cur = tmp_path / "cur.csv"
    _write_csv(base, [{"a": 1, "b": 2}], ["a", "b"])
    _write_csv(cur, [{"a": 1, "b": 2, "c": 3}], ["a", "b", "c"])
    assert compare(base, cur)["added_columns"] == ["c"]


def test_detects_removed_column(tmp_path):
    base = tmp_path / "base.csv"
    cur = tmp_path / "cur.csv"
    _write_csv(base, [{"a": 1, "b": 2}], ["a", "b"])
    _write_csv(cur, [{"a": 1}], ["a"])
    assert compare(base, cur)["removed_columns"] == ["b"]


def test_detects_type_change(tmp_path):
    base = tmp_path / "base.csv"
    cur = tmp_path / "cur.csv"
    _write_csv(base, [{"plan": "basic"}, {"plan": "premium"}], ["plan"])
    _write_csv(cur, [{"plan": 0}, {"plan": 1}], ["plan"])
    changes = compare(base, cur)["type_changes"]
    assert len(changes) == 1
    assert changes[0]["column"] == "plan"
    assert changes[0]["baseline"] == "str"  # pandas 3 reads text columns as str
    assert changes[0]["current"] == "int64"


def test_flags_drifted_column_and_not_stable_one(tmp_path):
    base = tmp_path / "base.csv"
    cur = tmp_path / "cur.csv"
    rows_base = [{"spend": 50 + i % 3, "age": 30 + i % 5} for i in range(20)]
    rows_cur = [{"spend": 80 + i % 3, "age": 30 + i % 5} for i in range(20)]
    _write_csv(base, rows_base, ["spend", "age"])
    _write_csv(cur, rows_cur, ["spend", "age"])
    report = compare(base, cur, threshold=0.2)
    by_col = {row["column"]: row for row in report["numeric_drift"]}
    assert by_col["spend"]["drift"] is True
    assert by_col["spend"]["drift_score"] > 0.2
    assert by_col["age"]["drift"] is False


def test_row_counts_reported(tmp_path):
    base = tmp_path / "base.csv"
    cur = tmp_path / "cur.csv"
    _write_csv(base, [{"a": i} for i in range(10)], ["a"])
    _write_csv(cur, [{"a": i} for i in range(7)], ["a"])
    report = compare(base, cur)
    assert report["baseline_rows"] == 10
    assert report["current_rows"] == 7


def test_all_nan_baseline_column_does_not_crash(tmp_path):
    base = tmp_path / "base.csv"
    cur = tmp_path / "cur.csv"
    base_df = pd.DataFrame({"x": [float("nan")] * 5, "y": [1, 2, 3, 4, 5]})
    cur_df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [1, 2, 3, 4, 5]})
    base_df.to_csv(base, index=False)
    cur_df.to_csv(cur, index=False)
    report = compare(base, cur)
    by_col = {row["column"]: row for row in report["numeric_drift"]}
    assert by_col["x"]["drift"] is False  # std treated as 1.0, mean NaN -> score 0
    assert by_col["x"]["drift_score"] == 0.0


def test_missing_file_errors_cleanly():
    with pytest.raises(DriftError, match="not found"):
        compare("no-such-baseline.csv", "no-such-current.csv")


def test_empty_csv_errors_cleanly(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    base = tmp_path / "base.csv"
    _write_csv(base, [{"a": 1}], ["a"])
    with pytest.raises(DriftError, match="empty"):
        compare(empty, base)


def test_cli_text_and_json_on_examples(tmp_path):
    text = subprocess.run(
        [sys.executable, "-m", "datadrift", str(EXAMPLES / "baseline.csv"), str(EXAMPLES / "current.csv")],
        capture_output=True,
        text=True,
    )
    assert text.returncode == 0, text.stderr
    assert "Added columns" in text.stdout and "region" in text.stdout
    assert "Removed columns" in text.stdout and "tenure_months" in text.stdout
    assert "plan: str -> int64" in text.stdout
    assert "DRIFT" in text.stdout
    assert "Baseline rows: 20" in text.stdout

    js = subprocess.run(
        [sys.executable, "-m", "datadrift", str(EXAMPLES / "baseline.csv"),
         str(EXAMPLES / "current.csv"), "--format", "json"],
        capture_output=True,
        text=True,
    )
    assert js.returncode == 0, js.stderr
    report = json.loads(js.stdout)
    assert report["added_columns"] == ["region"]
    assert report["removed_columns"] == ["tenure_months"]
    by_col = {row["column"]: row for row in report["numeric_drift"]}
    assert by_col["monthly_spend"]["drift"] is True
    assert by_col["age"]["drift"] is False


def test_cli_missing_file_exits_nonzero(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "datadrift", str(tmp_path / "missing.csv"), str(tmp_path / "also-missing.csv")],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "error" in result.stderr

"""Compare a baseline CSV against a current CSV.

Reports added/removed columns, dtype changes, and per-column numeric drift
measured as |mean_current - mean_baseline| / std_baseline (std of 0 or NaN
is treated as 1.0 so an all-NaN baseline column cannot crash the report).
"""

import math

import pandas as pd


class DriftError(ValueError):
    """Raised when a CSV cannot be read or is empty."""


def load_csv(path):
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        raise DriftError(f"file not found: {path}") from None
    except pd.errors.EmptyDataError:
        raise DriftError(f"empty CSV file: {path}") from None
    if df.empty or len(df.columns) == 0:
        raise DriftError(f"empty CSV file: {path}")
    return df


def _numeric_drift(baseline, current, column, threshold):
    base = baseline[column]
    cur = current[column]
    base_mean = float(base.mean())
    base_std = float(base.std())
    cur_mean = float(cur.mean())
    cur_std = float(cur.std())
    # All-NaN (or constant) baseline: std is NaN or 0 -> use 1.0, no crash.
    if math.isnan(base_std) or base_std == 0:
        base_std = 1.0
    if math.isnan(base_mean) or math.isnan(cur_mean):
        score = 0.0
    else:
        score = abs(cur_mean - base_mean) / base_std
    return {
        "column": column,
        "baseline_mean": round(base_mean, 4) if not math.isnan(base_mean) else None,
        "baseline_std": round(base_std, 4) if not math.isnan(base_std) else None,
        "current_mean": round(cur_mean, 4) if not math.isnan(cur_mean) else None,
        "current_std": round(cur_std, 4) if not math.isnan(cur_std) else None,
        "drift_score": round(score, 4),
        "drift": score > threshold,
    }


def compare(baseline_path, current_path, threshold=0.2):
    baseline = load_csv(baseline_path)
    current = load_csv(current_path)

    base_cols = list(baseline.columns)
    cur_cols = list(current.columns)

    added = [c for c in cur_cols if c not in base_cols]
    removed = [c for c in base_cols if c not in cur_cols]

    type_changes = []
    for col in base_cols:
        if col in cur_cols and str(baseline[col].dtype) != str(current[col].dtype):
            type_changes.append(
                {
                    "column": col,
                    "baseline": str(baseline[col].dtype),
                    "current": str(current[col].dtype),
                }
            )

    numeric_drift = []
    for col in base_cols:
        if col in cur_cols and pd.api.types.is_numeric_dtype(baseline[col]) \
                and pd.api.types.is_numeric_dtype(current[col]):
            numeric_drift.append(_numeric_drift(baseline, current, col, threshold))

    return {
        "baseline_rows": len(baseline),
        "current_rows": len(current),
        "added_columns": added,
        "removed_columns": removed,
        "type_changes": type_changes,
        "numeric_drift": numeric_drift,
        "threshold": threshold,
    }


def format_text(report):
    lines = ["Dataset drift report", "====================", ""]
    lines.append("Summary")
    lines.append("-------")
    lines.append(f"Baseline rows: {report['baseline_rows']}")
    lines.append(f"Current rows:  {report['current_rows']}")
    lines.append(f"Threshold:     {report['threshold']}")
    lines.append(f"Drifted columns: {sum(1 for n in report['numeric_drift'] if n['drift'])}")
    lines.append("")

    lines.append("Added columns")
    lines.append("-------------")
    lines.append(", ".join(report["added_columns"]) or "(none)")
    lines.append("")

    lines.append("Removed columns")
    lines.append("---------------")
    lines.append(", ".join(report["removed_columns"]) or "(none)")
    lines.append("")

    lines.append("Type changes")
    lines.append("------------")
    if report["type_changes"]:
        for change in report["type_changes"]:
            lines.append(f"{change['column']}: {change['baseline']} -> {change['current']}")
    else:
        lines.append("(none)")
    lines.append("")

    lines.append("Numeric drift")
    lines.append("-------------")
    if report["numeric_drift"]:
        lines.append(f"{'column':<16}{'base mean':>12}{'base std':>10}{'cur mean':>12}{'cur std':>10}{'score':>8}  flag")
        for row in report["numeric_drift"]:
            flag = "DRIFT" if row["drift"] else "ok"
            lines.append(
                f"{row['column']:<16}{row['baseline_mean']:>12}{row['baseline_std']:>10}"
                f"{row['current_mean']:>12}{row['current_std']:>10}{row['drift_score']:>8}  {flag}"
            )
    else:
        lines.append("(no shared numeric columns)")
    return "\n".join(lines) + "\n"

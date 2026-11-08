# DataDrift

Compare two CSVs and report schema changes and numeric drift.

## What it does

- Lists columns added in the current file and removed from the baseline.
- Lists columns whose dtype changed (e.g. `str` → `int64` under pandas 3).
- For numeric columns present in both files, reports the mean and standard
  deviation of each, and flags `DRIFT` when
  `|mean_current − mean_baseline| / std_baseline` exceeds the threshold
  (default 0.2). A baseline std of 0 or NaN (e.g. an all-NaN column) is
  treated as 1.0 so the report never crashes on degenerate data.
- Reports the row count of both files.

No accuracy claims are made: the drift score is a simple standardized
mean shift, not a statistical test.

## Install

```bash
pip install -e .
```

Requires pandas.

## Usage

```bash
datadrift examples/baseline.csv examples/current.csv
datadrift examples/baseline.csv examples/current.csv --threshold 0.5 --format json
```

## Example output

```
Dataset drift report
====================

Summary
-------
Baseline rows: 20
Current rows:  20
Threshold:     0.2
Drifted columns: 1

Added columns
-------------
region

Removed columns
---------------
tenure_months

Type changes
------------
plan: str -> int64

Numeric drift
-------------
column             base mean  base std    cur mean   cur std   score  flag
customer_id             10.5    5.9161        10.5    5.9161     0.0  ok
age                    35.65    5.9141       35.65    5.7972     0.0  ok
monthly_spend          49.25    2.1227      79.809    1.8445 14.3962  DRIFT
```

## Tests

```bash
python -m pytest
```

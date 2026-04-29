# Cafe Sales — Dirty Data Cleaning + EDA

> **Cleaned 10,000 rows of dirty cafe POS transactions and ran exploratory analysis.** Three forms of missingness (`NaN`, `"ERROR"`, `"UNKNOWN"`) were normalized; ~1.4k field-level gaps were recovered using a deterministic item–price map plus the `Total = Qty × Price` identity — no statistical imputation.

**Type:** #DataCleaning #EDA | **Tools:** #Python #pandas #matplotlib #seaborn #Jupyter #uv #KaggleHub | **Period:** `Jan 2023 – Dec 2023`

---

## Key Insights

**1. Salad leads revenue, Coffee leads volume** — Coffee sold the most units (3,878) but generated only $7,756. Salad sold 3,815 units yet brought in $19,075 — 2.5× Coffee's revenue — purely from its $5 unit price. Volume KPIs and revenue KPIs disagree on this menu.

**2. No seasonality, no day-of-week pattern** — Monthly revenue stayed in a $6.2k–$7.0k band across 2023 (CV ~3%); day-of-week revenue was near-uniform ($10.9k–$11.7k). Likely reflects the dataset's synthetic origin rather than real café behavior.

**3. Cleaning was deterministic, not statistical** — Each menu item has a single fixed price. That fact + algebraic identity recovered 479 prices, 468 items, 479 totals, 456 quantities, and 48 prices without any mean/mode imputation. Residual NaN is single-digit on numeric fields.

---

## Overview

A public Kaggle dataset (`ahmedmohamed2003/cafe-sales-dirty-data-for-cleaning-training`) was deliberately corrupted with mixed missingness sentinels and provided as a cleaning exercise. The goal was to produce a defensible cleaned version plus exploratory analysis covering revenue, item performance, and time patterns. The cleaning strategy audited dirtiness at the value-token level (not just `isnull()`), exploited the deterministic item–price relationship, and applied the `Total = Quantity × Price` identity to fill cells without statistical guessing. The cleaned 10,000-row CSV has single-digit residual NaN on numeric fields; remaining gaps are in `Item` (501 rows where `Price Per Unit` was ambiguous) and `Transaction Date` (460 rows that failed to parse).

---

## Data Source

| Field | Details |
|-------|---------|
| **Source** | Kaggle — `ahmedmohamed2003/cafe-sales-dirty-data-for-cleaning-training` |
| **Access** | KaggleHub (`kagglehub.dataset_download(...)`) |
| **Format** | CSV |
| **Size** | 10,000 rows × 8 columns (~550 KB raw, ~725 KB cleaned) |
| **Period** | 2023-01-01 – 2023-12-31 |
| **Key fields** | `Transaction ID`, `Item`, `Quantity`, `Price Per Unit`, `Total Spent`, `Payment Method`, `Location`, `Transaction Date` |

---

## Limitations

- Residual `"Unknown"` in `Payment Method` (32%) and `Location` (40%) blocks reliable segmentation along those dimensions.
- `Item` cannot be inferred from `Price Per Unit` when the price is $3 (Cake / Juice) or $4 (Sandwich / Smoothie) — 501 rows still NaN on `Item`.
- 460 rows have unparseable dates and are excluded from time-based analysis.
- Flat monthly + day-of-week patterns most likely reflect the synthetic generator; do not extrapolate to a real café.

---

## Files

| File | Description |
|------|-------------|
| [`notebooks/cafe_eda.ipynb`](notebooks/cafe_eda.ipynb) | Full executable cleaning + EDA notebook with rendered outputs |
| [`scripts/pipeline.py`](scripts/pipeline.py) | Standalone CLI pipeline — produces processed CSV + all figures |
| [`scripts/build_notebook.py`](scripts/build_notebook.py) | Generator that builds the notebook from a cell list |
| [`reports/REPORT_TEMPLATE.md`](reports/REPORT_TEMPLATE.md) | Final EDA report (insights, metrics, limitations) |
| [`reports/PROCESS_REPORT.md`](reports/PROCESS_REPORT.md) | Junior-DA process write-up to senior reviewer |
| [`data/raw/dirty_cafe_sales.csv`](data/raw/) | Raw Kaggle download (gitignored — pull via `kagglehub`) |
| [`data/processed/clean_cafe_sales.csv`](data/processed/) | Cleaned output (gitignored — produced by pipeline) |
| [`visuals/`](visuals/) | 8 PNG figures: missingness, item revenue/units, monthly + day-of-week, payment/location mix, distributions |

---

## Reproducing

```bash
# 1. install deps with uv
uv sync

# 2. download raw data via kagglehub (public dataset, no auth needed)
uv run python -c "import kagglehub, shutil, pathlib; \
  src = kagglehub.dataset_download('ahmedmohamed2003/cafe-sales-dirty-data-for-cleaning-training'); \
  dst = pathlib.Path('data/raw'); dst.mkdir(parents=True, exist_ok=True); \
  shutil.copy(f'{src}/dirty_cafe_sales.csv', dst / 'dirty_cafe_sales.csv')"

# 3. run cleaning + EDA pipeline (produces processed CSV + visuals/*.png)
uv run python scripts/pipeline.py

# 4. or execute the notebook end-to-end
uv run jupyter nbconvert --to notebook --execute notebooks/cafe_eda.ipynb --output cafe_eda.ipynb
```

For private Kaggle datasets, copy `.env_example` to `.env` and set `KAGGLE_USERNAME` + `KAGGLE_KEY` (the existing `KAGGLE_API_TOKEN` placeholder is a stub for future use — `kagglehub` reads the standard Kaggle env vars).

---

*Author: **jack2000-dev** | Last updated: April 2026*

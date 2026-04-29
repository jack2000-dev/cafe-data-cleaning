# Cafe Sales — Dirty Data Cleaning + EDA

> *Cleaned 10,000 rows of dirty cafe POS data (literal `ERROR` / `UNKNOWN` / NaN) by combining a fixed item–price map with the `Total = Quantity × Price` identity, recovering ~1.4k field-level gaps, then ran exploratory analysis on the calendar-2023 transactions.*

**Type:** #DataCleaning #EDA | **Tools:** #Python #pandas #matplotlib #seaborn #Jupyter #uv #KaggleHub | **Period:** `2023-01-01 – 2023-12-31`

---

## Key Insights

**1. Dirtiness was structured, not random** — Missingness took three forms (`NaN`, the string `"ERROR"`, the string `"UNKNOWN"`). `Location` (~40%) and `Payment Method` (~32%) were the worst offenders; `Item` was ~10% missing. Treating all three forms uniformly was the first unlock.

**2. The item–price relationship is deterministic** — Each of the 8 menu items has exactly one unit price (Coffee=$2, Tea=$1.50, Cookie=$1, Cake=$3, Juice=$3, Sandwich=$4, Smoothie=$4, Salad=$5). That fact + the algebraic identity `Total = Qty × Price` reconstructed 479 missing prices, 468 missing items, 479 missing totals, 456 missing quantities, and 48 missing prices — without any statistical imputation.

**3. Coffee leads on units, Salad leads on revenue** — Coffee sold 3,878 units (top) but generated only $7,756 in revenue. Salad sold 3,815 units but produced $19,075 — 2.5× Coffee — purely from the $5 unit price. Volume-led KPIs and revenue-led KPIs tell different stories on this menu.

**4. No seasonality, no day-of-week pattern** — Monthly revenue stayed in a tight $6.2k–$7.0k band across 2023 (CV ~3%). Day-of-week revenue is near-uniform ($10.9k–$11.7k). The data behaves like a synthetic / smoothed sample — there's nothing to chase here.

**5. Segmentation is constrained by residual gaps** — Even after cleaning, 32% of `Payment Method` and 40% of `Location` rows are `Unknown`. Splits along those dimensions are noisy and shouldn't be used for decisions without acknowledging the gap.

---

## Overview

A public Kaggle dataset of cafe transactions was deliberately corrupted with mixed missingness sentinels (`ERROR`, `UNKNOWN`, `NaN`) and given as a cleaning exercise. The task: produce a defensible clean version + exploratory analysis. The approach was to audit dirtiness at the value-token level (not just `isnull()`), exploit the deterministic item–price relationship to fill cells without statistical guessing, and then run standard EDA on the surviving signal. The outcome: a 10,000-row processed CSV with single-digit residual NaN in numeric fields, plus 8 figures covering missingness, item performance, time patterns, and distributions.

---

## Data Source

| Field | Details |
|-------|---------|
| **Source** | Kaggle — `ahmedmohamed2003/cafe-sales-dirty-data-for-cleaning-training` |
| **Access** | KaggleHub (`kagglehub.dataset_download(...)`) |
| **Format** | CSV |
| **Size** | 10,000 rows × 8 columns (~550 KB raw) |
| **Period** | 2023-01-01 – 2023-12-31 |
| **Key fields** | `Transaction ID`, `Item`, `Quantity`, `Price Per Unit`, `Total Spent`, `Payment Method`, `Location`, `Transaction Date` |

### Cleaning Recovery Summary

| Step | Fields recovered |
|------|------------------|
| `Price Per Unit` filled from `Item` (using fixed price map) | 479 |
| `Item` filled from `Price Per Unit` (only when price is unambiguous) | 468 |
| `Total Spent` derived from `Qty × Price` | 479 |
| `Quantity` derived from `Total / Price` | 456 |
| `Price Per Unit` derived from `Total / Qty` | 48 |
| `Payment Method` filled with `"Unknown"` | 3,178 |
| `Location` filled with `"Unknown"` | 3,961 |

**Residual NaN after cleaning:** `Item` 501 · `Quantity` 23 · `Price Per Unit` 6 · `Total Spent` 23 · `Transaction Date` 460.

---

## Headline Numbers (post-clean, n=9,479 revenue-valid rows)

| Metric | Value |
|--------|------:|
| Total revenue | **$83,828** |
| Total units | **28,638** |
| Mean ticket | **$8.84** |
| Median ticket | **$7.50** |
| Top item by revenue | **Salad — $19,075** |
| Top item by units | **Coffee — 3,878** |
| Best month | **October — $7,040** |
| Worst month | **February — $6,172** |

---

## Visualizations

All figures live in [`/visuals/`](../visuals/).

| File | What it shows |
|------|---------------|
| `missingness_after_clean.png` | Residual NaN by column post-cleaning |
| `revenue_by_item.png` | Revenue by menu item |
| `units_by_item.png` | Units sold by menu item |
| `monthly_revenue.png` | Monthly revenue trend across 2023 |
| `revenue_by_dow.png` | Revenue by day of week |
| `payment_location_mix.png` | Payment method + location distributions |
| `ticket_quantity_dist.png` | Ticket-size + quantity distributions |

---

## Limitations

- Residual `Unknown` in `Payment Method` (32%) and `Location` (40%) prevents reliable segmentation along those dimensions.
- Item imputation from price is only valid for prices that map to a single item ($2 → Coffee, $1.50 → Tea, $1 → Cookie, $5 → Salad). $3 (Cake/Juice) and $4 (Sandwich/Smoothie) cannot be disambiguated, so 501 rows still have NaN `Item`.
- 460 rows have unparseable / missing dates and are excluded from time-based analysis.
- Dataset is described as a cleaning exercise; the absence of seasonality + day-of-week effect suggests the underlying generator was uniform, so don't extrapolate "no seasonality" to a real cafe.

---

## Files

| File | Description |
|------|-------------|
| [`notebooks/cafe_eda.ipynb`](../notebooks/cafe_eda.ipynb) | Full cleaning + EDA notebook with executed outputs |
| [`scripts/pipeline.py`](../scripts/pipeline.py) | Standalone cleaning + EDA pipeline (CLI runnable) |
| [`scripts/build_notebook.py`](../scripts/build_notebook.py) | Generator that produces the notebook from cell list |
| [`data/raw/dirty_cafe_sales.csv`](../data/raw/dirty_cafe_sales.csv) | Raw Kaggle download (gitignored) |
| [`data/processed/clean_cafe_sales.csv`](../data/processed/clean_cafe_sales.csv) | Cleaned output (gitignored) |
| [`reports/PROCESS_REPORT.md`](./PROCESS_REPORT.md) | Junior-DA process write-up to senior |
| [`visuals/*.png`](../visuals/) | Figures referenced above |

---

*Author: **jack2000-dev** | Last updated: April 2026*

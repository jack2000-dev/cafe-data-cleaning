"""Generate notebooks/cafe_eda.ipynb from cell list."""
from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "notebooks" / "cafe_eda.ipynb"

cells: list = []


def md(text: str) -> None:
    cells.append(nbf.v4.new_markdown_cell(text.strip()))


def code(src: str) -> None:
    cells.append(nbf.v4.new_code_cell(src.strip()))


md("""
# Cafe Sales — Data Cleaning + EDA

Dataset: `ahmedmohamed2003/cafe-sales-dirty-data-for-cleaning-training` (Kaggle).
Pipeline: load → audit → clean → save → explore.

Sections:
1. Setup
2. Load raw
3. Audit dirtiness
4. Clean (replace tokens, coerce, derive missing via `Total = Qty × Price`)
5. Save processed
6. EDA — missingness, item revenue/units, time patterns, payment/location, distributions
""")

code("""
import os, sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", context="talk")
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
RAW = ROOT / "data" / "raw" / "dirty_cafe_sales.csv"
PROC = ROOT / "data" / "processed" / "clean_cafe_sales.csv"
VIS = ROOT / "visuals"
VIS.mkdir(exist_ok=True)
PROC.parent.mkdir(exist_ok=True)
print("ROOT:", ROOT)
""")

md("## 1. Load raw + first look")

code("""
df_raw = pd.read_csv(RAW)
print("shape:", df_raw.shape)
df_raw.head(8)
""")

code("""
df_raw.dtypes
""")

md("## 2. Audit — nulls + dirty tokens (`ERROR`, `UNKNOWN`)")

code("""
def audit(df):
    nulls = df.isna().sum()
    err = (df.astype(str) == "ERROR").sum()
    unk = (df.astype(str) == "UNKNOWN").sum()
    return pd.DataFrame({"nulls": nulls, "ERROR": err, "UNKNOWN": unk,
                         "dirty_total": nulls + err + unk,
                         "dirty_pct": ((nulls + err + unk) / len(df) * 100).round(2)})

audit_raw = audit(df_raw)
audit_raw
""")

code("""
print("duplicate Transaction IDs:", df_raw['Transaction ID'].duplicated().sum())
print("date range (raw strings):", sorted(df_raw['Transaction Date'].dropna().unique())[:3], "...",
      sorted(df_raw['Transaction Date'].dropna().unique())[-3:])
""")

md("""
**Findings (raw):**
- 10,000 rows, 8 columns. No duplicate transaction IDs.
- Three forms of missing data: literal `NaN`, string `"ERROR"`, string `"UNKNOWN"`.
- Most affected columns: `Location` (~40% dirty), `Payment Method` (~32%), `Item` (~10%).
- Numeric columns store as strings because of `ERROR` / `UNKNOWN` mixed in.
- Date range looks like calendar year 2023.
""")

md("## 3. Cleaning")

md("""
**Strategy:**
1. Replace `ERROR` / `UNKNOWN` with `NaN` everywhere.
2. Coerce `Quantity`, `Price Per Unit`, `Total Spent` to numeric. Parse `Transaction Date`.
3. Each menu item has a fixed unit price (verified from clean rows). Use the map to reconstruct missing prices/items.
4. Apply identity `Total = Quantity × Price` to derive any single missing field.
5. Remaining categorical NaN → `"Unknown"` (preserve row, mark gap explicitly).
6. Add derived time fields (year, month, day_of_week).
""")

code("""
ITEM_PRICE = {"Coffee": 2.0, "Tea": 1.5, "Sandwich": 4.0, "Salad": 5.0,
              "Cake": 3.0, "Cookie": 1.0, "Juice": 3.0, "Smoothie": 4.0}
PRICE_ITEMS = {}
for it, p in ITEM_PRICE.items():
    PRICE_ITEMS.setdefault(p, []).append(it)
UNIQUE_PRICE_ITEMS = {p: items[0] for p, items in PRICE_ITEMS.items() if len(items) == 1}

print("unique-price items (price -> item):", UNIQUE_PRICE_ITEMS)
print("ambiguous prices:", {p: items for p, items in PRICE_ITEMS.items() if len(items) > 1})
""")

code("""
df = df_raw.copy()

# 1. dirty tokens to NaN
df = df.replace({"ERROR": np.nan, "UNKNOWN": np.nan})

# 2. numeric coerce + date parse
for col in ["Quantity", "Price Per Unit", "Total Spent"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
df["Transaction Date"] = pd.to_datetime(df["Transaction Date"], errors="coerce")

log = {}

# 3a. price from item
m = df["Item"].notna() & df["Price Per Unit"].isna()
df.loc[m, "Price Per Unit"] = df.loc[m, "Item"].map(ITEM_PRICE)
log["price_filled_from_item"] = int(m.sum())

# 3b. item from price (only when unambiguous)
m = df["Item"].isna() & df["Price Per Unit"].isin(UNIQUE_PRICE_ITEMS)
df.loc[m, "Item"] = df.loc[m, "Price Per Unit"].map(UNIQUE_PRICE_ITEMS)
log["item_filled_from_price"] = int(m.sum())

# 4. derive via Total = Qty * Price
m = df["Total Spent"].isna() & df["Quantity"].notna() & df["Price Per Unit"].notna()
df.loc[m, "Total Spent"] = df.loc[m, "Quantity"] * df.loc[m, "Price Per Unit"]
log["total_derived"] = int(m.sum())

m = df["Quantity"].isna() & df["Total Spent"].notna() & df["Price Per Unit"].notna() & (df["Price Per Unit"] > 0)
df.loc[m, "Quantity"] = (df.loc[m, "Total Spent"] / df.loc[m, "Price Per Unit"]).round()
log["qty_derived"] = int(m.sum())

m = df["Price Per Unit"].isna() & df["Total Spent"].notna() & df["Quantity"].notna() & (df["Quantity"] > 0)
df.loc[m, "Price Per Unit"] = df.loc[m, "Total Spent"] / df.loc[m, "Quantity"]
log["price_derived"] = int(m.sum())

# 5. fill remaining categorical NaN
for col in ["Payment Method", "Location"]:
    log[f"{col}_filled_unknown"] = int(df[col].isna().sum())
    df[col] = df[col].fillna("Unknown")

# 6. dtypes + derived time fields
df["Quantity"] = df["Quantity"].astype("Int64")
df["year"] = df["Transaction Date"].dt.year.astype("Int64")
df["month"] = df["Transaction Date"].dt.month.astype("Int64")
df["day_of_week"] = df["Transaction Date"].dt.day_name()

log
""")

md("**Audit after cleaning:**")

code("""
audit_clean = pd.DataFrame({
    "before_nulls": df_raw.isna().sum() + (df_raw.astype(str) == "ERROR").sum() + (df_raw.astype(str) == "UNKNOWN").sum(),
    "after_nulls": df.isna().sum().reindex(df_raw.columns)
})
audit_clean["recovered"] = audit_clean["before_nulls"] - audit_clean["after_nulls"]
audit_clean
""")

md("## 4. Save processed")

code("""
df.to_csv(PROC, index=False)
print(f"wrote {PROC}  rows={len(df)}  cols={df.shape[1]}")
df.head()
""")

md("## 5. EDA")

md("### 5.1 Residual missingness")

code("""
miss = (df.isna().mean() * 100).sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(9, 5))
sns.barplot(x=miss.values, y=miss.index, ax=ax, hue=miss.index, palette="rocket", legend=False)
ax.set_xlabel("% missing")
ax.set_title("Missingness after cleaning")
fig.tight_layout()
fig.savefig(VIS / "missingness_after_clean.png", dpi=120)
plt.show()
""")

md("### 5.2 Revenue + units by item")

code("""
rev = df.dropna(subset=["Item", "Total Spent", "Quantity"]).copy()
by_item = rev.groupby("Item").agg(revenue=("Total Spent","sum"),
                                  units=("Quantity","sum"),
                                  tx=("Transaction ID","count")).sort_values("revenue", ascending=False)
by_item
""")

code("""
fig, ax = plt.subplots(figsize=(10, 5))
sns.barplot(x=by_item.index, y=by_item["revenue"], hue=by_item.index, palette="viridis", ax=ax, legend=False)
ax.set_ylabel("Revenue ($)"); ax.set_title("Revenue by item")
plt.xticks(rotation=30, ha="right"); fig.tight_layout()
fig.savefig(VIS / "revenue_by_item.png", dpi=120); plt.show()
""")

code("""
fig, ax = plt.subplots(figsize=(10, 5))
sns.barplot(x=by_item.index, y=by_item["units"], hue=by_item.index, palette="mako", ax=ax, legend=False)
ax.set_ylabel("Units sold"); ax.set_title("Units sold by item")
plt.xticks(rotation=30, ha="right"); fig.tight_layout()
fig.savefig(VIS / "units_by_item.png", dpi=120); plt.show()
""")

md("### 5.3 Monthly revenue trend")

code("""
rev_dt = rev.dropna(subset=["Transaction Date"])
monthly = rev_dt.groupby(rev_dt["Transaction Date"].dt.to_period("M"))["Total Spent"].sum()
monthly.index = monthly.index.to_timestamp()
print(monthly)

fig, ax = plt.subplots(figsize=(11, 5))
monthly.plot(ax=ax, marker="o", color="#2c3e50")
ax.set_ylabel("Revenue ($)"); ax.set_title("Monthly revenue (2023)")
fig.tight_layout(); fig.savefig(VIS / "monthly_revenue.png", dpi=120); plt.show()
""")

md("### 5.4 Day-of-week pattern")

code("""
order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
dow = rev_dt.groupby("day_of_week")["Total Spent"].sum().reindex(order)
fig, ax = plt.subplots(figsize=(9, 5))
sns.barplot(x=dow.index, y=dow.values, hue=dow.index, palette="crest", ax=ax, legend=False)
ax.set_ylabel("Revenue ($)"); ax.set_title("Revenue by day of week")
plt.xticks(rotation=25); fig.tight_layout()
fig.savefig(VIS / "revenue_by_dow.png", dpi=120); plt.show()
""")

md("### 5.5 Payment method + location mix")

code("""
pay = df["Payment Method"].value_counts()
loc = df["Location"].value_counts()
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
sns.barplot(x=pay.index, y=pay.values, hue=pay.index, palette="rocket", ax=axes[0], legend=False)
axes[0].set_title("Payment method"); axes[0].set_ylabel("Transactions")
axes[0].tick_params(axis='x', rotation=20)
sns.barplot(x=loc.index, y=loc.values, hue=loc.index, palette="flare", ax=axes[1], legend=False)
axes[1].set_title("Location"); axes[1].set_ylabel("Transactions")
fig.tight_layout()
fig.savefig(VIS / "payment_location_mix.png", dpi=120); plt.show()
print(pay, "\\n\\n", loc)
""")

md("### 5.6 Distributions")

code("""
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
sns.histplot(rev["Total Spent"], bins=30, color="#16a085", ax=axes[0])
axes[0].set_title("Ticket-size distribution"); axes[0].set_xlabel("Ticket total ($)")
sns.countplot(x=rev["Quantity"].astype(int), hue=rev["Quantity"].astype(int),
              palette="Blues", ax=axes[1], legend=False)
axes[1].set_title("Quantity per transaction")
fig.tight_layout(); fig.savefig(VIS / "ticket_quantity_dist.png", dpi=120); plt.show()
print(rev["Total Spent"].describe())
""")

md("""
## 6. Summary

- **Cleaning recovered ~1.4k field-level gaps** by combining the item-price map with the `Total = Qty × Price` identity.
- **Residual NaN** concentrates in `Item` (n=501) and `Transaction Date` (n=460) — neither can be safely imputed without external data.
- **Revenue mix:** Salad leads ($19k); Coffee leads on units (3.9k) but trails on revenue due to low unit price.
- **Time patterns:** monthly revenue holds steady ~$6.5k–$7k across 2023; no seasonality. Day-of-week revenue near-uniform.
- **Segmentation limits:** Payment Method and Location have ~32–40% `Unknown` even after cleaning — segment splits are noisy.
""")

nb = nbf.v4.new_notebook(cells=cells)
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.12"},
}
NB_PATH.parent.mkdir(exist_ok=True)
NB_PATH.write_text(json.dumps(nb, indent=1))
print(f"WROTE {NB_PATH}  cells={len(cells)}")

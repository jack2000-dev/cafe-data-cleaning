"""Cafe sales: clean dirty data + run EDA. Saves processed CSV + PNG figures."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "dirty_cafe_sales.csv"
PROCESSED = ROOT / "data" / "processed" / "clean_cafe_sales.csv"
VISUALS = ROOT / "visuals"
STATS_JSON = ROOT / "reports" / "_stats.json"

VISUALS.mkdir(exist_ok=True)
PROCESSED.parent.mkdir(exist_ok=True)

ITEM_PRICE = {
    "Coffee": 2.0,
    "Tea": 1.5,
    "Sandwich": 4.0,
    "Salad": 5.0,
    "Cake": 3.0,
    "Cookie": 1.0,
    "Juice": 3.0,
    "Smoothie": 4.0,
}
PRICE_ITEMS: dict[float, list[str]] = {}
for it, p in ITEM_PRICE.items():
    PRICE_ITEMS.setdefault(p, []).append(it)

DIRTY_TOKENS = {"ERROR", "UNKNOWN", "", " "}


def load_raw() -> pd.DataFrame:
    return pd.read_csv(RAW)


def audit(df: pd.DataFrame) -> dict:
    nulls = df.isna().sum()
    dirty_counts = {}
    for col in df.columns:
        s = df[col].astype(str)
        dirty_counts[col] = int(s.isin({"ERROR", "UNKNOWN"}).sum())
    return {
        "shape": list(df.shape),
        "nulls": {c: int(nulls[c]) for c in df.columns},
        "dirty_tokens": dirty_counts,
        "duplicate_tx_ids": int(df["Transaction ID"].duplicated().sum()),
    }


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    log: dict = {"steps": []}

    # 1. dirty tokens -> NaN
    for col in ["Item", "Quantity", "Price Per Unit", "Total Spent",
                "Payment Method", "Location", "Transaction Date"]:
        before = out[col].isna().sum()
        out[col] = out[col].replace({"ERROR": np.nan, "UNKNOWN": np.nan})
        after = out[col].isna().sum()
        log["steps"].append({"col": col, "tokens_to_nan": int(after - before)})

    # 2. numeric coerce
    for col in ["Quantity", "Price Per Unit", "Total Spent"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    # 3. date parse
    out["Transaction Date"] = pd.to_datetime(out["Transaction Date"], errors="coerce")

    # 4. impute price from item
    mask = out["Item"].notna() & out["Price Per Unit"].isna()
    out.loc[mask, "Price Per Unit"] = out.loc[mask, "Item"].map(ITEM_PRICE)
    log["price_filled_from_item"] = int(mask.sum())

    # 5. impute item from price (only when price maps to single item)
    unique_price_items = {p: its[0] for p, its in PRICE_ITEMS.items() if len(its) == 1}
    mask = out["Item"].isna() & out["Price Per Unit"].isin(unique_price_items)
    out.loc[mask, "Item"] = out.loc[mask, "Price Per Unit"].map(unique_price_items)
    log["item_filled_from_price"] = int(mask.sum())

    # 6. derive total / qty / price using identity Total = Qty * Price
    mask = out["Total Spent"].isna() & out["Quantity"].notna() & out["Price Per Unit"].notna()
    out.loc[mask, "Total Spent"] = out.loc[mask, "Quantity"] * out.loc[mask, "Price Per Unit"]
    log["total_derived"] = int(mask.sum())

    mask = out["Quantity"].isna() & out["Total Spent"].notna() & out["Price Per Unit"].notna() & (out["Price Per Unit"] > 0)
    out.loc[mask, "Quantity"] = (out.loc[mask, "Total Spent"] / out.loc[mask, "Price Per Unit"]).round()
    log["qty_derived"] = int(mask.sum())

    mask = out["Price Per Unit"].isna() & out["Total Spent"].notna() & out["Quantity"].notna() & (out["Quantity"] > 0)
    out.loc[mask, "Price Per Unit"] = out.loc[mask, "Total Spent"] / out.loc[mask, "Quantity"]
    log["price_derived"] = int(mask.sum())

    # 7. fill remaining categorical NaN with "Unknown"
    for col in ["Payment Method", "Location"]:
        n = out[col].isna().sum()
        out[col] = out[col].fillna("Unknown")
        log[f"{col}_filled_unknown"] = int(n)

    # 8. enforce dtypes
    out["Quantity"] = out["Quantity"].astype("Int64")

    # 9. derived time fields
    out["year"] = out["Transaction Date"].dt.year.astype("Int64")
    out["month"] = out["Transaction Date"].dt.month.astype("Int64")
    out["day_of_week"] = out["Transaction Date"].dt.day_name()

    log["final_nulls"] = {c: int(out[c].isna().sum()) for c in out.columns}
    log["final_shape"] = list(out.shape)
    return out, log


def eda(df: pd.DataFrame) -> dict:
    sns.set_theme(style="whitegrid", context="talk")
    stats: dict = {}

    # Filter rows with valid total + item for revenue analysis
    rev = df.dropna(subset=["Item", "Total Spent", "Quantity"]).copy()
    stats["rows_valid_for_revenue"] = int(len(rev))
    stats["total_revenue"] = float(rev["Total Spent"].sum())
    stats["mean_ticket"] = float(rev["Total Spent"].mean())
    stats["median_ticket"] = float(rev["Total Spent"].median())
    stats["total_units"] = int(rev["Quantity"].sum())

    # 1. missingness heatmap (raw vs clean handled outside)
    miss = df.isna().mean().sort_values(ascending=False) * 100
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(x=miss.values, y=miss.index, ax=ax, color="#c0392b")
    ax.set_xlabel("% missing")
    ax.set_title("Missingness after cleaning")
    fig.tight_layout()
    fig.savefig(VISUALS / "missingness_after_clean.png", dpi=120)
    plt.close(fig)

    # 2. revenue by item
    by_item = rev.groupby("Item").agg(
        revenue=("Total Spent", "sum"),
        units=("Quantity", "sum"),
        tx=("Transaction ID", "count"),
    ).sort_values("revenue", ascending=False)
    stats["by_item"] = by_item.to_dict(orient="index")

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(x=by_item.index, y=by_item["revenue"], ax=ax, palette="viridis")
    ax.set_ylabel("Revenue ($)")
    ax.set_title("Revenue by item")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(VISUALS / "revenue_by_item.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(x=by_item.index, y=by_item["units"], ax=ax, palette="mako")
    ax.set_ylabel("Units sold")
    ax.set_title("Units sold by item")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(VISUALS / "units_by_item.png", dpi=120)
    plt.close(fig)

    # 3. monthly revenue trend
    rev_dt = rev.dropna(subset=["Transaction Date"])
    monthly = rev_dt.groupby(rev_dt["Transaction Date"].dt.to_period("M"))["Total Spent"].sum()
    monthly.index = monthly.index.to_timestamp()
    stats["monthly_revenue"] = {str(k.date()): float(v) for k, v in monthly.items()}

    fig, ax = plt.subplots(figsize=(11, 5))
    monthly.plot(ax=ax, marker="o", color="#2c3e50")
    ax.set_ylabel("Revenue ($)")
    ax.set_title("Monthly revenue")
    fig.tight_layout()
    fig.savefig(VISUALS / "monthly_revenue.png", dpi=120)
    plt.close(fig)

    # 4. payment method mix
    pay = df["Payment Method"].value_counts(dropna=False)
    stats["payment_mix"] = pay.to_dict()
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(x=pay.index, y=pay.values, ax=ax, palette="rocket")
    ax.set_ylabel("Transactions")
    ax.set_title("Payment method mix")
    plt.xticks(rotation=20)
    fig.tight_layout()
    fig.savefig(VISUALS / "payment_mix.png", dpi=120)
    plt.close(fig)

    # 5. location mix
    loc = df["Location"].value_counts(dropna=False)
    stats["location_mix"] = loc.to_dict()
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.barplot(x=loc.index, y=loc.values, ax=ax, palette="flare")
    ax.set_ylabel("Transactions")
    ax.set_title("Location mix")
    fig.tight_layout()
    fig.savefig(VISUALS / "location_mix.png", dpi=120)
    plt.close(fig)

    # 6. day-of-week pattern
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow = rev_dt.groupby("day_of_week")["Total Spent"].sum().reindex(dow_order)
    stats["dow_revenue"] = {k: float(v) for k, v in dow.items()}
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(x=dow.index, y=dow.values, ax=ax, palette="crest")
    ax.set_ylabel("Revenue ($)")
    ax.set_title("Revenue by day of week")
    plt.xticks(rotation=25)
    fig.tight_layout()
    fig.savefig(VISUALS / "revenue_by_dow.png", dpi=120)
    plt.close(fig)

    # 7. ticket-size distribution
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.histplot(rev["Total Spent"], bins=30, ax=ax, color="#16a085")
    ax.set_xlabel("Ticket total ($)")
    ax.set_title("Ticket-size distribution")
    fig.tight_layout()
    fig.savefig(VISUALS / "ticket_size_hist.png", dpi=120)
    plt.close(fig)

    # 8. quantity distribution
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.countplot(x=rev["Quantity"].astype(int), ax=ax, palette="Blues")
    ax.set_xlabel("Quantity")
    ax.set_title("Quantity per transaction")
    fig.tight_layout()
    fig.savefig(VISUALS / "quantity_dist.png", dpi=120)
    plt.close(fig)

    return stats


def main() -> None:
    raw = load_raw()
    raw_audit = audit(raw)
    cleaned, clean_log = clean(raw)
    cleaned.to_csv(PROCESSED, index=False)
    stats = eda(cleaned)
    out = {"raw_audit": raw_audit, "clean_log": clean_log, "eda": stats}
    STATS_JSON.write_text(json.dumps(out, indent=2, default=str))
    print(f"WROTE {PROCESSED}  rows={len(cleaned)}")
    print(f"WROTE {STATS_JSON}")


if __name__ == "__main__":
    main()

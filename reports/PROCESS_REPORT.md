# Process Report — Cafe Sales Cleaning + EDA

**To:** Senior Data Analyst
**From:** Junior Data Analyst (jack2000-dev)
**Date:** 2026-04-29
**Re:** How I tackled the dirty cafe sales dataset — methodology, decisions, what I'd flag

---

## TL;DR

I cleaned a 10,000-row Kaggle "dirty cafe sales" dataset and ran exploratory analysis. The headline:

- Three forms of missingness (`NaN`, `"ERROR"`, `"UNKNOWN"`) were normalized to NaN before anything else.
- Each menu item has a fixed unit price, which I used as a deterministic lookup to recover ~1,400 missing cells without statistical imputation.
- Categorical gaps in `Payment Method` (32%) and `Location` (40%) were filled with `"Unknown"` rather than dropped or guessed — those rows still carry valid revenue/item info.
- The cleaned data shows no seasonality and a near-uniform day-of-week pattern, which I think reflects the synthetic generator more than a real café — flagging that in the limitations section.

I'd like a sanity check on three calls in particular: (1) whether `"Unknown"` as a category is the right approach versus dropping rows, (2) whether the Item-from-Price imputation should be more conservative, and (3) whether the residual 501 NaN `Item` rows should be excluded from revenue totals (currently they are).

---

## 1. Setup + tooling

Used **`uv`** for environment management as you suggested. Single `pyproject.toml`, locked deps in `uv.lock`. Stack: `pandas`, `numpy`, `matplotlib`, `seaborn`, `jupyter`, `kagglehub`, `python-dotenv`.

Pulled the dataset via the official `kagglehub` SDK rather than the legacy Kaggle CLI:

```python
import kagglehub
path = kagglehub.dataset_download("ahmedmohamed2003/cafe-sales-dirty-data-for-cleaning-training")
```

The dataset is public so no auth was needed — the `KAGGLE_API_TOKEN` in `.env` wasn't read. I left the `.env_example` reference in place for future private datasets.

I copied the file from `kagglehub`'s cache into `data/raw/dirty_cafe_sales.csv` so the project is self-contained — the cache directory isn't a stable source and shouldn't be assumed to exist on another machine.

---

## 2. Initial audit — what does "dirty" actually mean here?

Before writing any cleaning code I ran a value-level audit. Looking only at `df.isna()` would have undercounted: the dataset uses **three** different sentinels for missing data.

| Form | Where it shows up |
|------|-------------------|
| `NaN` | Standard pandas missing value |
| `"ERROR"` | Mixed into every column except `Transaction ID` |
| `"UNKNOWN"` | Same — mixed into every column except `Transaction ID` |

Counts per column (raw):

| Column | NaN | ERROR | UNKNOWN | Total dirty |
|--------|----:|------:|--------:|------------:|
| Transaction ID | 0 | 0 | 0 | **0** |
| Item | 333 | ? | ? | **969** |
| Quantity | 138 | — | — | **479** |
| Price Per Unit | 179 | — | — | **533** |
| Total Spent | 173 | — | — | **502** |
| Payment Method | 2,579 | — | — | **3,178** |
| Location | 3,265 | — | — | **3,961** |
| Transaction Date | 159 | — | — | **460** |

(Detail counts in `reports/_stats.json`.)

Two takeaways drove the cleaning strategy:

1. **No duplicate transaction IDs**, so I never need to deduplicate.
2. **Numeric columns are stored as strings** because of mixed `ERROR`/`UNKNOWN` tokens — meaning a naive `df["Total Spent"].astype(float)` would crash. The fix has to come *before* dtype coercion.

---

## 3. Cleaning strategy

I avoided statistical imputation (mean/mode/KNN) wherever a deterministic rule was available. Reason: the dataset has structural facts I can lean on, and statistical fills would just smear them.

### Step 1 — normalize sentinels
```python
df = df.replace({"ERROR": np.nan, "UNKNOWN": np.nan})
```
Now every kind of missingness is a single thing. Everything downstream gets simpler.

### Step 2 — coerce dtypes
```python
for col in ["Quantity", "Price Per Unit", "Total Spent"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
df["Transaction Date"] = pd.to_datetime(df["Transaction Date"], errors="coerce")
```
`errors="coerce"` is doing the work — anything that fails to parse becomes NaN, which is what I want at this stage.

### Step 3 — verify the item–price relationship before I rely on it
This was the key decision. I checked the clean subset:

```
          nunique  min  max  mean
Item
Cake            1  3.0  3.0   3.0
Coffee          1  2.0  2.0   2.0
Cookie          1  1.0  1.0   1.0
Juice           1  3.0  3.0   3.0
Salad           1  5.0  5.0   5.0
Sandwich        1  4.0  4.0   4.0
Smoothie        1  4.0  4.0   4.0
Tea             1  1.5  1.5   1.5
```

`nunique = 1` for every item — prices don't vary. That makes the item→price mapping safe to use as a lookup. I hardcoded it:

```python
ITEM_PRICE = {"Coffee": 2.0, "Tea": 1.5, "Sandwich": 4.0, "Salad": 5.0,
              "Cake": 3.0, "Cookie": 1.0, "Juice": 3.0, "Smoothie": 4.0}
```

**Caveat I want flagged:** the reverse map (price → item) is *not* unique. $3 maps to both Cake and Juice; $4 to both Sandwich and Smoothie. So I can only impute `Item` from `Price Per Unit` when the price uniquely identifies the item ($1, $1.50, $2, $5). For $3 and $4 prices, `Item` stays NaN.

### Step 4 — apply deterministic fills

Order matters. I went:

1. `Price Per Unit` from `Item` (fills 479 cells)
2. `Item` from `Price Per Unit` where unambiguous (fills 468 cells)
3. `Total Spent` from `Quantity × Price Per Unit` (fills 479 cells)
4. `Quantity` from `Total / Price` (fills 456 cells, rounded)
5. `Price Per Unit` from `Total / Quantity` (fills 48 cells)

Steps 3–5 use the algebraic identity `Total = Qty × Price`. As long as any two of the three are present, the third is recoverable.

### Step 5 — handle categoricals that can't be derived
`Payment Method` and `Location` have no structural relationship to other columns. Filling them with `"Unknown"` is a deliberate choice rather than dropping the rows: those rows still have valid revenue, item, and date data. Dropping them would discard ~30–40% of the dataset for analysis questions that don't need those fields.

### Step 6 — derived time fields
Added `year`, `month`, `day_of_week` for grouping convenience.

**Final residual NaN:** Item 501 · Qty 23 · Price 6 · Total 23 · Date 460. Single-digit residuals on numerics; the bigger gaps (Item, Date) are intrinsically unrecoverable without external data.

---

## 4. EDA approach

I kept this descriptive — the dataset has no obvious hypothesis to test, and the brief asked for pure EDA. The notebook walks through:

1. **Missingness post-clean** — confirms the cleaning held.
2. **Revenue + units by item** — flagged the divergence between volume leader (Coffee) and revenue leader (Salad).
3. **Monthly trend** — looked for seasonality. Found none ($6.2k–$7.0k all year, CV ~3%).
4. **Day-of-week** — looked for weekday/weekend split. Found none (range $10.9k–$11.7k).
5. **Payment + location mix** — three near-balanced payment methods (Cash/Card/Wallet ~2.3k each), two near-balanced locations (Takeaway ≈ In-store ~3k each).
6. **Distributions** — ticket size right-skewed, mean $8.84 vs median $7.50; quantities range 1–5 with no clear mode.

All eight figures are PNGs in `visuals/`.

---

## 5. What I'd flag for review

1. **The "no seasonality" finding is suspicious.** Real cafés have weekday rush patterns and month-to-month variation. The flatness here likely reflects the dataset's synthetic origin. I'd recommend we **not** present this to stakeholders as a real-world finding without that caveat.

2. **`Item`-from-`Price` imputation could be too aggressive.** I only impute when the price→item mapping is unique, but even then I'm assuming the price is correctly recorded. If a row had a corrupted price + correct item missing, my fill propagates an error. The volume here is small (468 cells) so impact is bounded, but I want your view on whether to drop those imputations and leave `Item` NaN.

3. **Treatment of `Unknown` categoricals in revenue totals.** Currently the headline `total_revenue = $83,828` includes rows where `Payment Method` or `Location` is `Unknown` but `Item`/`Total Spent` are valid. I think this is right (revenue is revenue regardless of how it was paid), but want to confirm the convention before reporting it externally.

4. **501 rows still have NaN `Item`** even after cleaning. They're excluded from revenue/unit aggregates because the groupby drops them. That's $4–5k of revenue we're not attributing — visible as a reconciliation gap. Should I add a "Item: Unknown" bucket to the revenue chart for transparency?

---

## 6. Reproducibility notes

- One-shot reproduction: `uv sync && uv run python scripts/pipeline.py` regenerates the processed CSV and all figures.
- Notebook reproduction: `uv run jupyter nbconvert --to notebook --execute notebooks/cafe_eda.ipynb` re-runs the notebook end to end.
- Raw data is gitignored per project convention; I did not commit the CSV. Anyone cloning the repo runs the kagglehub download once, the rest is deterministic.

---

## 7. Open questions for you

- Do you want a `data/external/` lookup table version of `ITEM_PRICE` instead of a hardcoded dict in code? (My instinct: yes for any real engagement, no for this exercise.)
- Should the pipeline have a CLI flag for "strict mode" that drops rows instead of filling `Unknown`? Useful if downstream consumers need clean joins.
- Any preference on plot styling — current is `seaborn whitegrid + talk context`. Happy to switch to whatever the team standard is.

Thanks for reviewing. Diff is in the branch; happy to walk through any section live.

— Junior DA

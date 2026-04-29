# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

Single-purpose data analysis project: clean a deliberately-corrupted Kaggle cafe-sales dataset and produce an EDA report. Not a long-lived application — the deliverables are the cleaned CSV, executed notebook, figures, and Markdown reports under `reports/`. Read `README.md` and `reports/PROCESS_REPORT.md` for the analytical narrative.

## Environment

- Managed by **uv** (`pyproject.toml` + `uv.lock`, Python ≥3.12). Do not invent a `requirements.txt`; add deps with `uv add <pkg>`.
- The dataset is a **public** Kaggle dataset. `kagglehub.dataset_download(...)` works without auth. The `KAGGLE_API_TOKEN` in `.env` is a placeholder for future private datasets — `kagglehub` itself reads `KAGGLE_USERNAME` / `KAGGLE_KEY`, not `KAGGLE_API_TOKEN`.
- Raw + processed CSVs are gitignored. They must be regenerated locally; do not commit them.

## Commands

```bash
# install deps
uv sync

# download raw dataset into data/raw/dirty_cafe_sales.csv
uv run python -c "import kagglehub, shutil, pathlib; \
  src = kagglehub.dataset_download('ahmedmohamed2003/cafe-sales-dirty-data-for-cleaning-training'); \
  dst = pathlib.Path('data/raw'); dst.mkdir(parents=True, exist_ok=True); \
  shutil.copy(f'{src}/dirty_cafe_sales.csv', dst / 'dirty_cafe_sales.csv')"

# run end-to-end pipeline (CLI) — writes data/processed/clean_cafe_sales.csv,
# visuals/*.png, reports/_stats.json
uv run python scripts/pipeline.py

# regenerate the notebook from the cell-list source
uv run python scripts/build_notebook.py

# execute the notebook in place (refresh embedded outputs)
uv run jupyter nbconvert --to notebook --execute notebooks/cafe_eda.ipynb --output cafe_eda.ipynb
```

There is no test suite, linter, or build step configured — don't fabricate one.

## Architecture

Two parallel runnables share the same logic, by design:

1. **`scripts/pipeline.py`** — CLI source of truth. Functions `load_raw → audit → clean → eda → main`. Writes processed CSV, all PNGs, and `reports/_stats.json`.
2. **`notebooks/cafe_eda.ipynb`** — narrative version with embedded outputs.
3. **`scripts/build_notebook.py`** — generator that constructs the `.ipynb` from a literal cell list using `nbformat`. Run it whenever the notebook structure needs to change.

**Drift risk:** the cleaning logic lives in two places (`pipeline.py` and the cell list inside `build_notebook.py`). When the cleaning rules change, edit both. The notebook on disk is generated output; do not hand-edit it — re-run `build_notebook.py` then `nbconvert --execute`.

### Cleaning logic — load-bearing facts

The cleaning is **deterministic, not statistical**. Two structural facts make this possible:

1. The dataset uses three sentinels for missing data: `NaN`, the string `"ERROR"`, and the string `"UNKNOWN"`. All three must be normalized to `NaN` *before* dtype coercion, otherwise `pd.to_numeric` and friends will fail. `df.replace({"ERROR": np.nan, "UNKNOWN": np.nan})` is the first cleaning step for that reason.

2. Each menu item has exactly one unit price (verified — `nunique == 1` per item across clean rows). The hardcoded `ITEM_PRICE` dict is the lookup; combined with the algebraic identity `Total = Quantity × Price`, any single missing field among `Item / Quantity / Price / Total` is recoverable.

   **Asymmetry to remember:** `Item → Price` is unique, but `Price → Item` is not — `$3` maps to both Cake and Juice, `$4` to both Sandwich and Smoothie. The code only imputes `Item` from `Price` when the price uniquely identifies the item ($1, $1.50, $2, $5). Don't "fix" this to be more aggressive.

3. `Payment Method` and `Location` have no structural relationship to other columns. They are filled with the literal string `"Unknown"` rather than dropped, so revenue/item analysis can keep those rows. Treat `"Unknown"` as a real category in mixes and segment splits.

### Layout

```
data/raw/         # gitignored; populated by kagglehub download
data/processed/   # gitignored; produced by pipeline.py
notebooks/        # cafe_eda.ipynb (generated, executed)
scripts/          # pipeline.py + build_notebook.py
reports/          # REPORT_TEMPLATE.md (final EDA report — name kept for legacy),
                  # PROCESS_REPORT.md (junior-DA write-up), _stats.json
visuals/          # PNGs produced by pipeline.py / notebook
docs/ queries/    # scaffolded but unused for this project
```

`reports/REPORT_TEMPLATE.md` contains the final report, not a template — the original template was overwritten per the project brief. If you need the empty template back, recover it from git history (`git show a8f2081:reports/REPORT_TEMPLATE.md`).

## Conventions

- All paths in scripts resolve from `Path(__file__).resolve().parent.parent` so they work regardless of CWD. Preserve that pattern.
- Plot styling: `seaborn` `whitegrid` + `talk` context, PNGs at `dpi=120`, save to `visuals/`. Use `hue=...` + `legend=False` with `sns.barplot` to avoid the deprecation warning that appears when passing `palette` without `hue`.
- `Quantity` is stored as `Int64` (nullable) — keep it that way; switching to plain `int` will fail on residual NaN rows.

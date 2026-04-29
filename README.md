# [Project Title]

> **DELETE THIS: This is a template with pre-filled example. Replace this with your own project title and period. Project title: Customer Churn Analysis — Q3 2024**

> *Analyzed 12 months of subscription data to identify why churn spiked 23% in Q3 — pricing changes, not product issues, were the main driver.*

**Type:** #EDA #SQL | **Tools:** #Python #PostgreSQL #Tableau | **Period:** `Jan 2023 – Sep 2024`

---

## Key Insights

**1. Pricing change drove 60% of churn** — Customers on the legacy plan churned at 3× the rate after the June price increase. Churn was concentrated in the first 30 days post-change, not spread evenly across the quarter.

**2. High-value customers were most affected** — Users spending $200+/month had a 34% churn rate vs. 12% for lower-tier users. Losing this segment disproportionately impacted revenue.

**3. Churn was regional, not global** — The spike was isolated to the North America segment. APAC and EMEA churn rates stayed flat, suggesting the pricing change hit USD-billed accounts hardest.

---

## Overview

<!-- Context → Problem → Approach → Outcome. 3–4 sentences. -->

A SaaS company saw its quarterly churn rate jump from 8% to 23% in Q3 2024 following a platform-wide pricing restructure. The goal was to determine whether churn was driven by the price change, product dissatisfaction, or seasonal behavior. Transaction and support ticket data across 18 months were analyzed at customer and regional level. The analysis found that pricing — not product quality — was the primary driver, specifically affecting high-value customers on legacy billing plans.

---

## Data Source

| Field | Details |
|-------|---------|
| **Source** | Internal CRM export + PostgreSQL subscription database |
| **Format** | CSV + SQL tables |
| **Size** | ~85,000 rows, 14 columns |
| **Period** | Jan 2023 – Sep 2024 |
| **Key fields** | `customer_id`, `plan_type`, `billing_region`, `churn_date`, `monthly_spend` |

---

## Limitations

- Churn reason was self-reported by ~40% of users only — the rest were inferred from behavioral signals.
- Cannot distinguish voluntary churn from payment failures without access to the billing system.
- No A/B test data available — causal claims about pricing are correlational, not confirmed.

---

## Files

| File | Description |
|------|-------------|
| [`notebooks/churn_eda.ipynb`] | Full exploratory analysis with visualizations |
| [`queries/churn_by_segment.sql`] | Segmentation queries by region and plan type |
| [`reports/churn_summary_Q3.pdf`] | Executive summary (2 pages) |
| [`visuals/churn_dashboard.png`] | Tableau dashboard screenshot |

---

*Author: **jack2000-dev** | Last updated: April 2024*
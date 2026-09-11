# Data Source Notes — Adzuna Jobs API

## 1. Source Overview

- **API:** Adzuna Jobs API (`https://api.adzuna.com/v1/api/jobs/{country}/search/{page}`)
- **Country:** United Kingdom (`gb`)
- **Search term(s):** `data engineer`
- **Auth:** `app_id` + `app_key` (free tier, ~1,000 calls/month)
- **Response format:** JSON, paginated
- **Max results per page:** 50 (API limit)
- **Results per page used in sample pull:** 50
- **Docs:** https://developer.adzuna.com/activedocs

**Known limitation:** the `what` parameter searches across title *and* description,
not title alone — so results include noisy/partial title matches. Considered
adding `title_only` param to tighten results; decided to keep full search and
handle title cleanup in `transform.py` instead, since real-world postings are
messy anyway.

*See [`exploration/inspect_api_response.py`](../exploration/inspect_api_response.py) for the
sample data pulled and inspected to reach this decision.*

---

## 2. Field Inventory

| Field | Raw type | Keep? | Notes / cleaning needed |
|---|---|---|---|
| `id` | string | Yes | Use as primary key instead of generating our own |
| `title` | string | Yes | 98% clean (49/50, n=50) - legitimate variants(seniority, tech stack, domain). 1 outlier matched via description, not title. Light filtering sufficient, not heavy normalization. |
| `company.display_name` | nested string | Yes | Flatten from nested dict → `company_name` |
| `location.display_name` | nested string | Yes | Flatten → `location_name` |
| `location.area` | nested list | No (for now) | Full hierarchy (country→region→city→district); more granularity than current questions need |
| `category.label` | nested string | Yes | Human-readable category, flatten → `category_label`. n=50: 96% "IT Jobs", 4% "Engineering Jobs" — low diversity, expected given role-specific search term. |
| `category.tag` | nested string | Yes | Machine-readable slug, flatten → `category_tag`. Same distribution as label. |
| `contract_time` | string | Yes | 60% missing (n = 50). Non-null values are clean (`full_time`, `part_time`). Fill missing with `"not_specified` in transform step rather than dropping rows |
| `contract_type` | string | Yes | 70% missing (n=50, worse than `contract_time`'s 60%). Values: permanent (13), contract (2). Distinct dimension from `contract_time` (employment basis vs. hours). Fill missing with "not_specified", same pattern as `contract_time`. Given majority missing, findings should be reported as "of postings that specify, X% are permanent" — not treated as representative of the full market. |
| `salary_min` | float | Yes | 0% missing (n=50). Often equals `salary_max` |
| `salary_max` | float | Yes | 0% missing (n=50). Often equals `salary_min` |
| `salary_is_predicted` | string (0/1) | Yes | **Critical field** — raw value is a string. Must cast via int first then boolean. Distinguishes real employer-stated salaries from Adzuna's estimates. |
| `description` | string | Yes | **Hard-capped at exactly 500 characters by the API (confirmed: mean=500, std=0, n=50)** — not natural text length, a fixed truncation limit. Ends mid-sentence, often before reaching role/skill content. Not used in current analysis questions. Kept for potential future use (full-description fetch via `redirect_url`) — not relied upon for any current field. |
| `created` | string | Yes | Parsed with Python's `datetime.fromisoformat()` |
| `latitude` / `longitude` | float | Maybe | Not needed for current questions; kept optionally for a future map view |
| `adref` | string | No | Adzuna internal reference token |
| `__CLASS__` | string | No | Adzuna internal metadata |
| `redirect_url` | string | Yes | Kept for traceability — link back to original posting. Not used in current analysis questions, but useful for verification and potential future dashboard use. |
---

## 3. Data Quality Findings

*(Checked on sample of n=50 records)*

- Missing salary_min: 0%
- Missing salary_max: 0%
- Missing contract_time: 60%
- Missing contract_type: 70%
- % of records where `salary_is_predicted` = 1: 44%
- Any duplicate `id`s across pages/pulls: 0
- Category distribution: 96% "IT Jobs" (48), 4% "Engineering Jobs" (2). 
  Low diversity is expected — search term "data engineer" is inherently 
  IT-adjacent, not a sampling issue. Category-based comparison questions 
  won't have much variance in this dataset.
- Title noise observed (examples of messy/irrelevant matches): 49/50 (98%) are clearly relevant "Data Engineer" variants. 1 outlier: "Chief Engineer, Data Centre Engineering Operations, Data Centre Engineering Operations"

---

## 4. Target Schema (post-cleaning)

**`jobs` table**
```
jobs
─────────────────────────────
id                  TEXT PRIMARY KEY
title               TEXT
company_name        TEXT
location_name       TEXT
category_label      TEXT
category_tag        TEXT
contract_time       TEXT
contract_type       TEXT
salary_min          NUMERIC
salary_max          NUMERIC
salary_is_predicted BOOLEAN
created             TIMESTAMP
redirect_url        TEXT
description         TEXT      -- kept, not used in current analysis
```

---

## 5. Known Limitations

- UK-only data; not representative of other job markets. UK was chosen 
  for stronger documentation and a clearer free-tier limit, prioritizing 
  learning the ETL mechanics over broader geographic coverage.
- Free tier caps requests at ~1,000/month — search scope kept narrow 
  (1 country, 1–2 search terms).
- `salary_is_predicted` means a meaningful share (44%, n=50) of salary 
  data is an estimate, not a stated figure — reported/filtered separately 
  in analysis.
- `contract_time` is missing on 60% of postings (n=50) — filled as 
  "not_specified" rather than dropped; treat as a data gap, not signal.
- `contract_type` is missing on 70% of postings (n=50) — even higher than `contract_time`. Of the 30% that specify a value, most are "permanent" (13) vs. "contract" (2), but this sample is too small to generalize. Filled as "not_specified" rather than dropped; treat any contract-type finding as describing only the subset of postings that disclosed it, not the full market.
- Title matching is keyword-based (title + description), not exact — 
  produced minimal noise in practice (2%, n=50), so light filtering was 
  sufficient rather than heavy normalization.

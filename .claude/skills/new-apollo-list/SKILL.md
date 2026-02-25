---
name: new-apollo-list
description: Run a full Apollo lead generation campaign — scrape, deduplicate, filter, and export to Google Sheets. Use when the user wants to scrape leads from an Apollo URL.
argument-hint: "client_name apollo_url target_leads"
disable-model-invocation: true
---

## Objective

Scrape leads from an Apollo search URL, deduplicate across campaigns, apply quality filters (with user approval), and export a clean list to Google Sheets.

## Inputs

Parse from `$ARGUMENTS`. Ask the user for anything missing:

- **Client name** (required) — must exist in `campaigns/`. If not, suggest `/onboard-new-client` first.
- **Apollo URL** (required) — full `https://app.apollo.io/#/people?...` URL
- **Target lead count** (required) — e.g. 2000
- **Scrapers** (optional) — user picks after seeing the rundown (default: all)
- **Enrichment** (optional) — `none` (default), `industry only`, `full`

## Procedure

Read `directives/lead_generation_v5_optimized.md` for the **complete workflow** — follow it step by step.

Key steps:
1. Verify client exists in `campaigns/{client}/client.json`
2. Pre-flight: parse Apollo URL, resolve industry hex IDs
3. **Present scraper rundown to user** — show ALL scrapers with:
   - Filter support (what each handles vs drops)
   - Cost estimate (from `scraper_registry.py`)
   - Time estimate (from `scraper_registry.py`)
   - Notes (cookies needed, min leads, etc.)
4. **User picks which scrapers to run** (default: all)
5. Run ALL selected scrapers in parallel
6. Merge & internal deduplication
7. Cross-campaign deduplication (if client has existing campaigns)
8. Industry relevance filter (if multi-scraper)
9. Quality filter — run analyzer, **present report to user, let them choose filters**
10. Export to Google Sheets
11. Update `client.json` with campaign metadata

## Scraper Rundown Format

Present a **detailed per-scraper breakdown** to the user before scraping. Do NOT use a summary table with "All OK" — show the actual values.

### How to gather the data

1. Run `py execution/filter_gap_analyzer.py --apollo-url "URL"` to get filter support status
2. Use `estimate_time()` and `estimate_cost()` from `scraper_registry.py` for cost/time
3. Use `get_default_target()` from `scraper_registry.py` to get the actual lead count each scraper will request (accounts for min/max clamping)
4. Use `scraper_registry.py` entries to check `location_transform`, `industry_taxonomy`, `industry_transform` per scraper

### Format: one section per scraper

For EACH scraper, present:

```
### SCRAPER_NAME | X,XXX leads | ~$X.XX | ~XX min | notes

Filters that will be sent:
- Titles: CEO, Owner, Director, ...
- Seniority: owner, founder, c_suite, director
- Industries: Construction, Building Materials, ... (taxonomy version)
- Location: Italy (location type + transform)
- Company size: 1-10, 11-50, 51-200, 201-500
- Keywords: HVAC, heating, ventilation, ...
- Dropped: email_status (not supported — hardcoded to validated)
```

Key details to include per scraper:
- **Lead count**: The actual number that will be requested (after min/max clamping). E.g. "1,000 leads" or "1,000 leads (min 1000)" if target was below minimum.
- **Filters**: List every active filter with its actual values. Show transforms (e.g. "italy" lowercase, or V2 industry names). If a filter is dropped or post-filtered, say so explicitly.
- **Cost + time**: From registry helpers
- **Notes**: Cookies needed, minimum lead count, etc.

After all scrapers, show:
```
TOTAL (all 3): ~$X.XX | parallel time: ~XX min (= slowest scraper)
```

Then ask which scrapers to run.

## Primary Scripts

- `execution/fast_lead_orchestrator.py` — main pipeline orchestrator (runs end-to-end)
- `execution/scraper_olympus_b2b_finder.py` — Apollo scraper (needs cookies)
- `execution/scraper_codecrafter.py` — Apollo scraper (fastest)
- `execution/scraper_peakydev.py` — Apollo scraper (cheapest, min 1000 leads)
- `execution/lead_quality_analyzer.py` — quality analysis
- `execution/lead_filter.py` — apply filters
- `execution/google_sheets_exporter.py` — export to Sheets

## Decision Points

- **Cookie failure** (Olympus, exit code 2): In parallel mode, other scrapers continue. Alert user that Olympus failed. If Olympus was the only selected scraper, the run fails — ask user to refresh cookies.
- **Industry hex IDs unresolved**: Alert user, ask them to check Apollo sidebar for industry names.
- **Quality filter results**: Always present the report and let user choose which filters to apply. NEVER apply without approval.

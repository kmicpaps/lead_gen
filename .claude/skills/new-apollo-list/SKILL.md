---
name: new-apollo-list
description: Run a full Apollo lead generation campaign — scrape, deduplicate, filter, and export to Google Sheets. Use when the user wants to scrape leads from an Apollo URL.
argument-hint: [client_name] [apollo_url] [target_leads]
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(py execution/*)
---

## Objective

Scrape leads from an Apollo search URL, deduplicate across campaigns, apply quality filters (with user approval), and export a clean list to Google Sheets.

## Inputs

Parse from `$ARGUMENTS`. Ask the user for anything missing:

- **Client name** (required) — must exist in `campaigns/`. If not, suggest `/onboard-new-client` first.
- **Apollo URL** (required) — full `https://app.apollo.io/#/people?...` URL
- **Target lead count** (required) — e.g. 2000
- **Scrapers** (optional) — `all` (default), `skip olympus`, or specific: `codecrafter`, `peakydev`
- **Enrichment** (optional) — `none` (default), `industry only`, `full`

## Procedure

Read `directives/lead_generation_v5_optimized.md` for the **complete workflow** — follow it step by step.

Key steps:
1. Verify client exists in `campaigns/{client}/client.json`
2. Pre-flight: parse Apollo URL, resolve industry hex IDs, show filter mapping per scraper
3. Run Olympus scraper first (always)
4. If Olympus gets enough leads → skip to dedup
5. If not → calculate gap, run backup scrapers in parallel with oversample multipliers
6. Post-scrape filter enforcement on backup scraper output
7. Merge & internal deduplication
8. Cross-campaign deduplication (if client has existing campaigns)
9. Industry relevance filter (if multi-scraper)
10. Quality filter — run analyzer, **present report to user, let them choose filters**
11. Export to Google Sheets
12. Update `client.json` with campaign metadata

## Primary Scripts

- `execution/fast_lead_orchestrator.py` — main pipeline orchestrator (can run end-to-end)
- `execution/scraper_olympus_b2b_finder.py` — primary Apollo scraper
- `execution/scraper_codecrafter.py` — backup scraper
- `execution/scraper_peakydev.py` — backup scraper (minimum 1000 leads)
- `execution/lead_quality_analyzer.py` — quality analysis
- `execution/lead_filter.py` — apply filters
- `execution/google_sheets_exporter.py` — export to Sheets

## Decision Points

- **Cookie failure** (exit code 2): STOP immediately. Alert user. Ask: refresh cookies or continue with backups? NEVER silently fall back.
- **Industry hex IDs unresolved**: Alert user, ask them to check Apollo sidebar for industry names.
- **Non-enforceable filters on backup scrapers**: Warn user before spending credits.
- **Quality filter results**: Always present the report and let user choose which filters to apply. NEVER apply without approval.

---
name: find-more-leads
description: Rescrape an existing Apollo list to find NEW leads that weren't in previous campaigns. Deduplicates against all prior results.
argument-hint: [client_name] [apollo_url]
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(py execution/*)
---

## Objective

Run scrapers again on an Apollo URL that was already used, deduplicate against ALL previous campaigns for this client, and export only the truly new leads.

## Inputs

Parse from `$ARGUMENTS`. Ask for anything missing:

- **Client name** (required) — must have existing campaigns in `campaigns/`
- **Apollo URL** (required) — the same or similar URL from the original campaign
- **Target leads per scraper** (optional, default 5000) — aim high since heavy dedup is expected
- **Scrapers** (optional) — `all` (default), or specific ones

## Procedure

Read `directives/lead_generation_v5_optimized.md` for the full pipeline workflow.

This follows the same pipeline as `/new-apollo-list` with key differences:

1. **Create a NEW campaign folder** — never merge into the old one. Use a new date suffix.
2. Run ALL selected scrapers in parallel (same as `/new-apollo-list`)
3. Merge & internal dedup
4. **Cross-campaign dedup against ALL existing campaigns** — this is the critical step
5. Quality filter the remaining new leads
6. Export only the truly new leads to Google Sheets

## Key Expectations

- **40-70% overlap is normal** — set this expectation with the user upfront
- The more previous campaigns exist, the more dedup will remove
- High target count compensates for expected overlap
- Report the breakdown: total scraped → duplicates removed → truly new

## Primary Scripts

- `execution/fast_lead_orchestrator.py` — main pipeline
- `execution/cross_campaign_deduplicator.py` — cross-campaign dedup
- `execution/google_sheets_exporter.py` — export

## Decision Points

- Same as `/new-apollo-list` (cookie failure, hex IDs, quality filters)
- If overlap is >80%, suggest the user try different Apollo filters or a different search approach

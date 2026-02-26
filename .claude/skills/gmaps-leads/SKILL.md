---
name: gmaps-leads
description: Scrape local businesses from Google Maps by location and niche, evaluate websites (PageSpeed), and export scored leads to Google Sheets.
argument-hint: [client_name] [location] [niches...]
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(py execution/*)
---

## Objective

Scrape businesses from Google Maps for specific niches in a given location, optionally extract website contact info, and export scored leads to Google Sheets.

## Inputs

Parse from `$ARGUMENTS`. Ask for anything missing:

- **Client name** (required)
- **Location** (required) — city, region, or country (e.g. "Riga", "Latvia", "Auckland")
- **Niches** (required) — as `label:search_term` pairs or plain terms (e.g. "lawyers, accountants" or "juristi:juristi, frizieris:frizieris")
- **Max results per niche** (optional, default 500)
- **Evaluate websites** (optional, default no) — pass `--evaluate-websites` to enable PageSpeed scoring and website insights
- **Country code** (optional, default `lv`) — pass `--country XX` for non-Latvia locations (e.g. `--country nz` for Auckland)
- **Google Sheet URL** (optional — for appending to existing sheet)

## Procedure

Read `directives/gmaps_scored_pipeline.md` for the full workflow.

Key steps:
1. Validate client exists
2. Assemble niche list as `label:search_term` pairs
3. Run `execution/gmaps_scored_pipeline.py` with assembled flags
4. Pre-test runs automatically (10 leads/term) — if 0 results, suggest alternatives
5. Full scrape runs after pre-test passes
6. Website contact extraction (if enabled)
7. Export to Google Sheets (3 tabs: cold_calling, cold_email_scored, summary)

## Critical Rules

- **NEVER substitute the user's search terms** — use EXACTLY what they provide in `--niches`
- Pre-test aborts on 0 results to prevent wasting Apify credits
- Google Maps has ~120 results per search query — use specific niches for better results
- For Latvia: use Latvian-language terms (juristi, frizieris, būvniecība). English terms often return 0.

## Key Flags

| Flag | Default | Notes |
|------|---------|-------|
| `--country` | `lv` | Country code — MUST change for non-Latvia locations (e.g. `nz` for Auckland) |
| `--language` | `en` | Search language |
| `--evaluate-websites` | off | Enable PageSpeed scoring + website insights |
| `--no-pre-test` | off | Skip pre-test validation (use when terms are already verified) |
| `--skip-scrape` | off | Load from existing JSON (for re-runs or re-scoring) |
| `--workers` | 5 | Parallel workers for website evaluation |

## Primary Scripts

- `execution/gmaps_scored_pipeline.py` — main pipeline (handles scraping, splitting, scoring, export)
- `execution/scrape_gmaps_contact.py` — underlying Apify scraper
- `execution/gmaps_niche_scraper.py` — alternative niche-by-niche interactive pipeline

## Decision Points

- **0 results on pre-test**: Suggest alternative search terms. Ask user before retrying.
- **Low results (<20 per niche)**: Warn user the niche may be too specific or term may be wrong.

---
name: gmaps-leads
description: Scrape local businesses from Google Maps by location and niche, evaluate websites (PageSpeed), and export scored leads to Google Sheets.
argument-hint: [client_name] [location] [business types...]
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(py execution/*)
---

## Objective

Scrape businesses from Google Maps for specific niches in a given location, split into cold calling and cold email streams, optionally score websites, and export to Google Sheets.

## Inputs

Parse from `$ARGUMENTS`. Ask for anything missing:

- **Client name** (required)
- **Location** (required) -- city, region, or country (e.g. "Riga", "Latvia", "Auckland")
- **Business types** (required) -- plain language, any language (e.g. "beauty salons, lawyers, plumbers")
- **Max results per niche** (optional, default 500)
- **Website enrichment** (optional, default YES) -- scrapes business websites to find more emails, owner info, etc. Adds ~$2/1K leads but significantly improves email yield. Skip only if cost-sensitive.
- **Score websites** (optional, default no) -- enables PageSpeed scoring and website insights (for web design/SEO offers)
- **Google Sheet URL** (optional -- creates new sheet if omitted)

**Note:** The AI auto-derives the 2-letter country code from the location (Latvia -> lv, Auckland -> nz, Berlin -> de, etc.). Do not ask the user for it.

## Procedure

Read `directives/gmaps_lead_scraping.md` for the full workflow and all CLI commands.

### Phase 1: Setup
1. Validate client exists in `campaigns/{client_id}/client.json`
2. Auto-derive 2-letter country code from the user's location (e.g. "Riga" or "Latvia" -> `lv`, "Auckland" -> `nz`, "Berlin" -> `de`)
3. Create working directory: `.tmp/gmaps_{client_id}_{YYYYMMDD}/`

### Phase 2: Keyword Discovery
1. For each business type the user wants, generate 3-5 candidate search terms (local language + English + synonyms)
2. Test each candidate: `py execution/scrape_gmaps_contact.py --search "TERM" --limit 10 --country {code}`
3. Pick the best term per niche (most results, 0 = drop)
4. Show user: term, result count, categories found. **Wait for confirmation.**

### Phase 3: Scrape
1. For each confirmed niche, run: `py execution/scrape_gmaps_contact.py --search "TERM" --limit {limit} --country {code}`
2. Tag each lead with its niche label
3. Combine all niche results into one file

### Phase 4: Process
1. Dedup: `py execution/gmaps_dedup.py --input combined.json --output deduped.json`
2. Website enrichment (default ON): `py execution/gmaps_website_enricher.py --input deduped.json --output enriched.json --workers 5`
3. Split: `py execution/lead_splitter.py --input enriched.json --output-dir .tmp/gmaps_{client}/`
4. If user wants PageSpeed scoring: `py execution/website_evaluator.py --input cold_email.json --output cold_email_scored.json --workers 5`

### Phase 5: Export
1. Export: `py execution/gmaps_sheets_exporter.py --cold-calling cold_calling.json --cold-email cold_email.json --all-leads deduped.json --niches {labels} --total-scraped {pre_dedup_count}`
2. Report results + Sheet link to user
3. Save campaign to `campaigns/{client_id}/google_maps_lists/{campaign_name}/`

## Critical Rules

- **NEVER substitute the user's business types** -- discover the right search terms, but respect what they asked for
- **Always test terms first** -- show results before committing budget
- **Local language terms beat English** for non-English countries
- Auto-create Google Sheet if no URL provided

## Primary Scripts

- `execution/scrape_gmaps_contact.py` -- Apify Google Maps scraper
- `execution/gmaps_dedup.py` -- Deduplicate by place_id + name|address
- `execution/gmaps_website_enricher.py` -- Batch website enrichment (more emails)
- `execution/lead_splitter.py` -- Split into cold_calling / cold_email / no_contact
- `execution/website_evaluator.py` -- PageSpeed scoring + CMS detection
- `execution/extract_website_contacts.py` -- Single-URL contact extraction (used by enricher)
- `execution/gmaps_sheets_exporter.py` -- 3-tab Google Sheet export (auto-creates)

## Decision Points

- **0 results on term test**: Try local language, broader category, singular/plural. Ask user before retrying.
- **Low results (<20)**: Warn user the niche may be too specific.
- **User skips scoring**: Export without PageSpeed columns (they'll be empty in the sheet).

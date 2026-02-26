---
name: quality-filter
description: Analyze a scraped lead list for quality issues and apply user-chosen filters (email, phone, title, industry, country).
argument-hint: [lead_file_path] [apollo_url]
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(py execution/lead_quality_analyzer.py *), Bash(py execution/lead_filter.py *), Bash(py execution/industry_relevance_filter.py *)
---

## Objective

Analyze lead quality, present a detailed report with filter options, let the user choose which filters to apply, then produce a cleaned lead file.

## Inputs

Parse from `$ARGUMENTS`. Ask for anything missing:

- **Lead file path** (required) — path to JSON file, or describe which campaign/list
- **Apollo URL** (optional but recommended) — provides context for title/industry matching

## Procedure

Read `directives/lead_quality_filtering.md` for the full workflow.

### Step 1: Analyze

```bash
py execution/lead_quality_analyzer.py \
    --apollo-url "APOLLO_URL" \
    --leads path/to/leads.json \
    --output-dir path/to/campaign_dir
```

### Step 2: Present Report

Show the user:
- Email coverage (valid/invalid/missing)
- Phone code breakdown (by country)
- Title distribution (matching vs non-matching)
- Industry breakdown
- Recommended filters with impact counts (how many leads each filter removes)

### Step 3: User Chooses Filters

Present a numbered menu. Let user pick. Common filters:
- `--require-email` — remove leads without email
- `--require-country COUNTRY_NAME` — keep only leads in specific country (e.g. "Italy", "Latvia")
- `--remove-phone-discrepancies` — remove leads with phone from wrong country
- `--exclude-titles-builtin` — exclude individual contributors (keeps managers, directors, C-level)
- `--include-industries LIST` — pipe-separated (`|`) industry whitelist (e.g. `"Retail|Construction|Glass, Ceramics & Concrete"`)
- `--exclude-industries LIST` — pipe-separated (`|`) industry blacklist (e.g. `"Farming|Gambling & Casinos"`)
- `--require-website` — remove leads without website
- `--remove-foreign-tld` — remove leads with domain TLD mismatching target country

### Step 4: Apply

```bash
py execution/lead_filter.py \
    --input leads.json \
    --output-dir path/to/output_dir \
    [user-chosen flags]
```

### Step 5: Report Results

Show stage-by-stage counts: input → after each filter → final output.

## Critical Rule

**NEVER apply filters without user approval.** Always present the analysis first and wait for the user to choose.

## Primary Scripts

- `execution/lead_quality_analyzer.py` — generates the quality report
- `execution/lead_filter.py` — applies chosen filters
- `execution/industry_relevance_filter.py` — AI-powered industry scoring (if multi-scraper campaign)

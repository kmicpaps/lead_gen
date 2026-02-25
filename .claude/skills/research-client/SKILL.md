---
name: research-client
description: Analyze a company's website to understand their business, generate an ICP, and suggest Apollo filters. Use when onboarding a new client or researching a prospect.
argument-hint: [website_url]
allowed-tools: Read, Grep, Glob, Bash(py execution/client_discovery.py *)
---

## Objective

Scrape and analyze a company's website to understand what they do, who they serve, and what kind of leads they need. Produces an ICP (Ideal Customer Profile) with Apollo filter suggestions.

## Inputs

Parse from `$ARGUMENTS`:

- **Website URL** (required) — e.g. `https://example.com`
- **Company name** (optional) — inferred from website if not provided
- **Notes** (optional) — any context from initial conversation

## Procedure

Read `directives/client_discovery.md` for the full process.

Key steps:
1. Run multi-page website scraping + AI analysis:
   ```bash
   py execution/client_discovery.py --url WEBSITE_URL
   ```
2. Present findings to user:
   - Business summary (what they do, who they serve, value proposition)
   - Recommended ICP (target titles, industries, company sizes, locations)
   - Suggested Apollo filter configuration
3. Ask user to review and modify before saving
4. If user wants to proceed to onboarding, suggest `/onboard-new-client`

## Primary Scripts

- `execution/client_discovery.py` — multi-page website scraper + AI analyzer

## Output

- Business analysis summary
- Draft ICP with Apollo filter recommendations
- Draft `client.json` ready for onboarding

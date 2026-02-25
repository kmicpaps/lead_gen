---
name: build-apollo-url
description: Convert a natural language description of desired leads into a working Apollo search URL. Use when the user describes who they want to target but doesn't have an Apollo URL yet.
argument-hint: [description of desired leads]
allowed-tools: Read, Grep, Glob, Bash(py execution/apollo_url_builder.py *), Bash(py execution/apollo_url_parser.py *), Bash(py execution/filter_gap_analyzer.py *), Bash(py execution/apollo_industry_resolver.py *)
---

## Objective

Take a natural language description of desired leads and produce a working Apollo search URL with the right filters (titles, seniority, industries, locations, company size).

## Inputs

Parse from `$ARGUMENTS` — the user's description of who they want. Examples:
- "construction company owners in Latvia, 10-50 employees"
- "HR directors at mid-size tech companies in Nordics"
- "marketing agency founders in Poland"

If the description is too vague, ask for:
- Target titles/roles
- Industries
- Locations
- Company size range

## Procedure

Read `directives/apollo_url_crafter.md` for the full workflow.

Key steps:
1. Extract structured filters from the user's description
2. Map to Apollo filter parameters using the directive's reference tables
3. Save draft to `.tmp/url_draft.json`
4. Run: `py execution/apollo_url_builder.py --from-json .tmp/url_draft.json --validate`
5. Present the URL + filter summary to the user
6. User opens URL in Apollo's browser UI, refines filters visually
7. User pastes refined URL back
8. Run filter gap analysis: `py execution/filter_gap_analyzer.py --apollo-url "URL"`
9. When ready, transition to `/new-apollo-list` for scraping

## Primary Scripts

- `execution/apollo_url_builder.py` — builds URL from structured filters
- `execution/apollo_url_parser.py` — parses existing URL into components
- `execution/filter_gap_analyzer.py` — shows what each scraper supports vs drops
- `execution/apollo_industry_resolver.py` — resolves industry hex IDs to text names

## Tips

- This is Step 0 before any scraping campaign
- Use `py execution/apollo_url_builder.py --list-industries` to see all available industry filters
- After the user refines in Apollo, the gap analysis shows which scraper can handle which filters

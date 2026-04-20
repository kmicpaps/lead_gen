---
name: apollo-backup
description: Run the backup Apollo pipeline -- usamamern RapidAPI scrape + email-finder enrichment + xmiso verification. Use when primary Apollo scrapers (Olympus/CodeCrafter/PeakyDev) are unavailable, niche markets where they return too few leads, or verified-email-only campaigns. Separate from main flow because it costs 5-10x more per lead and requires paid subscriptions to usamamern (RapidAPI) + Apify credits.
argument-hint: "client_name apollo_url"
disable-model-invocation: true
---

## Objective

Scrape leads via the backup Apollo pipeline (sequential enrichment) and export a tiered list (A/B/C/D) to a Google Sheet. Use only when the primary parallel scrapers are unavailable or producing poor results.

## Inputs

Parse from `$ARGUMENTS`. Only ask for what's genuinely missing.

- **Client name** (required) -- must exist in `campaigns/`. If not, suggest `/onboard-new-client` first.
- **Apollo URL** (required) -- full `https://app.apollo.io/#/people?...`. Must include `organizationLocations[]=<Country>` (country is auto-extracted from the URL, not asked separately).

Do NOT ask the user about:
- Sheet title -- orchestrator uses `Backup Apollo -- {country} {YYYY-MM-DD}` by default.
- Dedup CSV -- user can dedup the output themselves after the fact.
- Dual-sort mode -- orchestrator recommends based on pool size and auto-runs.
- Cost / subscription confirmation -- assume the user knows (the directive documents costs).

## Procedure

Read `directives/backup_apollo_pipeline.md` for the full SOP.

1. **Verify client exists** in `campaigns/{client}/client.json`. If missing, stop and suggest `/onboard-new-client`.
2. **Extract country** from the URL's `organizationLocations[]=` param (for user-facing messaging). If not present in URL, ask the user (don't invent).
3. **Create the work dir**: `campaigns/{client}/apollo_lists/{YYYYMMDD}/backup_run/` and mkdir it.
4. **Run the orchestrator** with `--assume-yes` to skip the >5K confirmation prompt:
   ```
   py execution/backup_apollo_orchestrator.py \
     --url "<URL>" \
     --work-dir "campaigns/{client}/apollo_lists/{YYYYMMDD}/backup_run/" \
     --assume-yes
   ```
5. **Monitor phases** and relay progress to the user briefly:
   - Phase 0 pool check: report total_entries and the dual-sort recommendation
   - Phase 1-5 milestones: just report at completion
6. **Report final counts by tier** and the Google Sheet URL.

## Common issues (fix, don't surface generic errors)

- **Apify out of credit mid-run**: tell user to top up Apify at https://console.apify.com/billing/subscription and rerun the same command -- checkpoints resume.
- **Usamamern 429 / 402**: tell user to check their usamamern RapidAPI subscription at https://rapidapi.com/usamamern/api/apollo-io-no-cookies-required
- **Page 101 400 Bad Request**: expected -- Apollo's pagination cap. Orchestrator auto-handles it.

## Related skills

- `/new-apollo-list` -- primary flow (use this first)
- `/build-apollo-url` -- construct Apollo URL from natural language
- `/research-client` -- generate ICP before building URL

# Backup Apollo Pipeline

A separate lead generation pipeline that runs when the primary Apollo scrapers (Olympus, CodeCrafter, PeakyDev) are unavailable or produce poor results. Isolated from the main flow — not in `scraper_registry.py`, not called by `fast_lead_orchestrator.py`. Sequential enrichment (not parallel), different cost profile, requires extra paid tools.

## Objective

Get fresh Apollo leads with verified emails when the main Apollo scrapers can't deliver (Olympus under maintenance, cookies expired, niche markets with thin backup-scraper coverage). Output a tiered list (A/B/C/D) of usable leads in Google Sheets.

## When to use

- **Olympus is down / cookies expired** and you need fresh Apollo data immediately.
- **Niche markets** (small countries, specific titles) where CodeCrafter/PeakyDev return too few leads.
- **Verified-email-only campaigns** where `contactEmailStatusV2[]=verified` filter is on the Apollo URL and you need every single verified lead.
- **Batches > 2,500** where Apollo's 100-page cap hurts single-scraper runs.

## When NOT to use

- Budget-sensitive runs on broad filters (>5K leads). The middle of the recommendation_score range is unreachable even with dual-sort.
- Runs where the primary scrapers are working fine. They're cheaper per lead.

## Required tools / external dependencies

| Service | Purpose | Cost model | Env var |
|---|---|---|---|
| [usamamern Apollo RapidAPI](https://rapidapi.com/usamamern/api/apollo-io-no-cookies-required) | Phase 1 scrape | Subscription (~$20/mo, 10K req/mo cap) | `x-rapidapi-key` |
| [snipercoder bulk LinkedIn email finder](https://console.apify.com/actors/ddgw2oGFaH645BFAq) | Phase 2 enrich | $0.8 per 1,000 URLs | `APIFY_API_KEY` |
| [clearpath email finder](https://console.apify.com/actors/eWT8czb4kT3gH1OWt) | Phase 3 enrich | Pay-per-event (~$0.003 × ~2 events/lead) | `APIFY_API_KEY` |
| [xmiso bulk email validator](https://console.apify.com/actors/QM5YJIYftbZQiNpgN) | Phase 4 verify | $1-1.7 per 1,000 emails | `APIFY_API_KEY` |

**Approximate cost per 1,000 Apollo leads: $6-10** (depending on clearpath hit rate and catch-all-domain density).

## Input

- Apollo search URL (`https://app.apollo.io/#/people?...`)
- Campaign country (e.g. `Germany`) — used for `company_country` label since usamamern doesn't return org-level location
- Google Sheet title for the final export
- Optional: CSV path to dedup against (typically the client's existing leads CSV)
- Optional: `--dual-sort yes|no|auto`
- Optional: working directory override (default: `.tmp/backup_apollo/{timestamp}/`)

## Process Flow

### Phase 0 — Pre-flight pool check (free)

Orchestrator hits usamamern with `page=1` only to read `total_entries` and `total_pages`. Based on pool size, recommends sort mode:

- **Pool ≤ 2,500**: **single DESC** sort. Dual would waste API calls.
- **Pool 2,501 – 5,000**: **dual sort** (DESC + ASC). Captures full set with minimal overlap.
- **Pool > 5,000**: **dual sort** with warning. Dual gets top 2,500 by recommendations_score + bottom 2,500, missing ~`(total_entries - 5,000)` in the middle. The 100-page cap applies per sort direction — there is no workaround within this scraper.

If in doubt, re-query Apollo with tighter filters (fewer titles, narrower industries) to keep the pool under 5,000.

### Phase 1 — `scraper_usamamern.py`

Paginates Apollo URL via usamamern's `POST /search_people_via_url` endpoint. Returns raw person records with LinkedIn URLs, titles, headlines, full 20+ org metadata fields — but **NO real emails** (usamamern returns `email_not_unlocked@domain.com` placeholders; that's Apollo's unlock gate, not fixable downstream of usamamern).

Dual-sort mode paginates both `sortAscending=true` and `sortAscending=false`, merges by person `id`.

**Output**: `phase1_usamamern_raw.json` (list of raw person dicts).

### Phase 2 — `email_finder_snipercoder.py`

Sends all LinkedIn URLs from Phase 1 through snipercoder's Apify actor. Scrapes LinkedIn profile data + tries to extract the email from the profile / Apollo caches. Returns full profile records (email, phone, title, company, position history) for ~30-40% of input URLs.

Higher-confidence hits: email came from real profile data, not guessed.

**Output**: `phase2_snipercoder.json`.

### Phase 3 — `email_finder_clearpath.py`

For leads where snipercoder didn't find an email, sends `{firstName, surname, domain}` through clearpath's Apify actor. Clearpath generates common email patterns (`firstname.lastname@`, `flastname@`, `f.lastname@`) and SMTP-verifies each. Hit rate ~70% on snipercoder-misses.

Uses `mode=optimized` (4 most common patterns, ~85% coverage) and `useNicknames=true` (retries with common nicknames like Maximilian for Max).

Input field names are STRICT: `firstName` (camelCase), `surname` (not `lastName`), `domain` (not `companyDomain`). Sends in chunks of 1,000 (actor's max).

**Output**: `phase3_clearpath.json`.

**Caveat**: clearpath output flags `isCatchAll=true` on domains that accept any address (these pattern guesses may not be the real person's email — verify with Phase 4). Many German B2B domains are catch-all.

### Phase 3b — Merge (no external calls)

Builds one unified record per usamamern lead:
- Email: snipercoder's first, then clearpath's as fallback.
- Phone: snipercoder's first, then org's `sanitized_phone` / `phone`.
- Keeps full usamamern + snipercoder + clearpath dicts for downstream reference.

**Output**: `phase3b_all_emails.json`.

### Phase 4 — `email_verifier_xmiso.py`

Runs every found email through xmiso's bulk validator (MillionVerifier engine). Chunks of 1,000. Returns `email_quality` (good/risky/bad) + `email_result` (ok/catch_all/unknown/invalid).

**Output**: `phase4_xmiso.json`.

### Phase 5 — Normalize + dedup + export

- Applies xmiso verdict to each merged record, assigns a tier (see below).
- Dedups against `--dedup-csv` if provided (email + LinkedIn URL).
- Normalizes to the standard lead schema.
- Hardcodes `company_country` from `--country` arg (usamamern doesn't return it).
- Uploads to Google Sheets via `google_sheets_exporter.py`.

**Output**: `phase5_final_normalized.json` + a Google Sheet URL.

## Outputs

### Tier meanings (assigned in Phase 5)

| Tier | xmiso `email_quality` | xmiso `email_result` | Recommendation |
|---|---|---|---|
| **A** | good | ok | **Safe to cold email** — verified deliverable, not catch-all |
| **B** | risky | catch_all | Domain accepts any address. Send cautiously (lower volume, monitor bounces) |
| **C** | risky | unknown | SMTP inconclusive. Individually verify before sending |
| **D** | bad | invalid | Invalid address — **drop** |

Typical split on a German logistics campaign: **60-70% A, 15-25% B, 3-7% C, 5-10% D**.

### Sheet columns

Matches the standard lead schema (same as main pipeline's exporter):
- first_name, last_name, full_name, title, email, email_status, email_tier, email_source
- linkedin_url, phone, city, country
- company_name, company_website, company_linkedin, company_phone, company_domain, company_country
- industry, source

## Quota management

### RapidAPI (usamamern)

- Typical plan: 10,000 requests / month.
- Each Apollo URL = up to 100 requests (200 with dual-sort).
- One campaign URL at dual-sort = ~2% of monthly quota.
- Free tier is 50 req/mo — useful only for testing, not real campaigns.

Monitor `x-ratelimit-requests-remaining` header (orchestrator doesn't auto-monitor this yet — check RapidAPI dashboard).

### Apify

- Pay-as-you-go.
- Runs are pre-flight-quota-checked: if remaining Apify balance < estimated cost, the actor rejects the call.
- Typical failure mode: xmiso or clearpath call in the middle of a pipeline fails with `"By launching this job you will exceed your remaining usage of $X"`. Top up Apify and rerun — checkpoints pick up where they left off.
- Budget ~$10 per 1,000 Apollo leads.

## Error handling / common issues

| Error | Cause | Fix |
|---|---|---|
| `400 Bad Request` on usamamern page 101 | Apollo's 100-page cap | Expected. Pipeline auto-stops and moves on. |
| `Input is not valid: Field input.surname is required` | Sent `lastName` to clearpath | Always use `surname`, not `lastName` |
| `Input is not valid: Field input.people must NOT have more than 1000 items` | Sent >1000 to clearpath or xmiso | Orchestrator chunks automatically, but standalone calls need `CHUNK_SIZE` respect |
| `By launching this job you will exceed your remaining usage` | Apify out of credit | Top up billing and rerun — checkpoints resume |
| Empty `organization.raw_address` / no country in output | usamamern doesn't return org country | Use `--country` arg to set it from filter context |
| Zero hits on snipercoder | LinkedIn URLs malformed or index stale | Normal — clearpath backfills the misses |

## Notes

- **Isolation**: this pipeline is NOT part of `scraper_registry.py` or `fast_lead_orchestrator.py`. It has its own orchestrator (`backup_apollo_orchestrator.py`). Don't try to integrate into the main parallel flow — the sequential enrichment model doesn't fit.
- **Why not just use this as primary?**: costs 5-10× more per lead than CodeCrafter/PeakyDev, and 100-page cap misses middle of large pools. Only use when primary scrapers fall short.
- **No Latvia CSV dedup**: if your client's existing CSV is German-only, `--dedup-csv` for a Latvia campaign will dedup against irrelevant data (no harm, just no-op).
- **Cross-run dedup**: if running multiple backup campaigns for the same client (e.g., first run + second run with different titles), run each independently then cross-dedup manually. The orchestrator's `--dedup-csv` only accepts a single CSV.

## Related

- `directives/lead_generation_v5_optimized.md` — main pipeline (use this first if primary scrapers work)
- `directives/apollo_url_crafter.md` — building good Apollo URLs
- `execution/google_sheets_exporter.py` — final export target

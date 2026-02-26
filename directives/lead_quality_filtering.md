# Lead Quality Filtering

**Status:** Active
**Created:** February 13, 2026
**Scripts:** `execution/lead_quality_analyzer.py`, `execution/lead_filter.py`

## Purpose

After scraping and deduplicating leads, the raw list often contains leads that don't match what we actually need — wrong titles, missing emails, phones from wrong countries, irrelevant industries. This directive defines the process for analyzing lead quality, presenting findings to the user, and applying their chosen filters.

## When to Use

Run this workflow **after** the scraping + deduplication steps from `lead_generation_v5_optimized.md` are complete, and **before** the final Google Sheets export.

Specifically, this is **Step 7** in the V8 pipeline:
- Step 5 (cross-campaign dedup) → Step 6 (country verification) → **Step 7: THIS WORKFLOW** → Step 8 (AI enrichment) → Step 9 (upload to Google Sheets)

## Workflow

### Step 1: Analyze Lead Quality

Run the quality analyzer for each list, passing the Apollo URL and the deduplicated leads file.

```bash
py execution/lead_quality_analyzer.py \
    --apollo-url "APOLLO_URL_HERE" \
    --leads path/to/new_leads_only_XXXXX.json \
    --output-dir path/to/campaign_dir
```

This produces a report covering:
- **Apollo filter description** — human-readable summary of what the URL was filtering for
- **Email coverage** — how many leads have/lack email
- **Phone coverage** — country code breakdown, whether phones match target country
- **Location breakdown** — countries and cities
- **Title seniority breakdown** — C-level, VP, Director, Manager, IC counts
- **Industry breakdown** — full list with counts
- **Organization concentration** — are leads spread across companies or clustered
- **Recommended filters** — numbered list of suggested actions

### Step 2: Present Report to User

Show the user the quality report and ask them to choose which filters to apply. Frame it as a menu:

```
Based on the quality analysis, here are the available filters:

1. REQUIRE EMAIL — removes X leads without email
2. REQUIRE +371 PHONE — removes X leads without Latvian phone
3. EXCLUDE IC TITLES — removes ~X individual contributors (engineers, analysts, etc.)
4. EXCLUDE INDUSTRIES — choose specific industries to remove

Which filters would you like to apply? (e.g. "1, 2, 3" or "all" or "1 and 2 only")
```

**Key principles:**
- Always present counts so the user knows the impact
- Never apply filters without user approval
- If the user wants custom title exclusions (beyond the built-in set), discuss which roles to keep/exclude before running

### Step 3: Apply Chosen Filters

Run the filter script with the user's chosen parameters:

```bash
py execution/lead_filter.py \
    --input path/to/new_leads_only_XXXXX.json \
    --output-dir path/to/campaign_dir \
    --require-email \
    --require-phone +371 \
    --exclude-titles-builtin \
    --exclude-industries "Farming|Gambling & Casinos"
```

#### Filter flags reference:

| Flag | What it does |
|------|-------------|
| `--require-email` | Removes leads with no email address |
| `--require-phone CODE` | Keeps only leads with a phone matching the country code (e.g. `+371`) |
| `--require-country NAME` | Keeps only leads matching this country (e.g. `Italy`). Case-insensitive. Checks both `country` and `company_country` fields. |
| `--remove-phone-discrepancies` | Removes leads where phone prefix doesn't match lead country. Leads without phone are kept. Uses built-in mapping of 45 countries. |
| `--include-industries LIST` | Pipe-separated (`|`) industry whitelist. Keeps only leads whose industry matches (case-insensitive, `and`/`&` normalized). Leads with no industry field are kept. Use pipe because industry names can contain commas (e.g. "Glass, Ceramics & Concrete"). |
| `--exclude-titles-builtin` | Excludes individual contributors using the built-in pattern set (engineers, analysts, coordinators, etc.). Keeps all managers, directors, heads, VPs, C-level, owners. |
| `--exclude-titles FILE` | Custom regex patterns from a JSON file (list of regex strings). Use when the built-in set needs augmenting for a specific campaign. |
| `--exclude-industries LIST` | Pipe-separated (`|`) industry names to exclude. Case-insensitive. |
| `--output-prefix PREFIX` | Change output filename prefix (default: `filtered`) |

### Step 4: Review Filter Results

The filter script prints a stage-by-stage breakdown showing how many leads were removed at each step and what was removed (specific titles, industries). Present this to the user.

If the results look wrong (too aggressive or too lenient), adjust and re-run. Common adjustments:
- **Too many removed by title filter** → User may want to keep certain roles. Create a custom patterns file that excludes fewer roles.
- **Too few removed** → Add more patterns or add industry exclusions.

### Step 5: Export & Update

Once the user approves the filtered results:
1. Export to Google Sheets: `py execution/google_sheets_exporter.py --input filtered_XXXXX.json --sheet-title "..."`
2. Update `client.json` with the final filtered count and sheet URL

## Built-in Title Exclusion Patterns

The `--exclude-titles-builtin` flag uses an exclude-only approach:
- **Everything passes UNLESS it matches an exclusion pattern**
- Leads with no title are kept (can't determine relevance, so err on inclusion)

### What gets EXCLUDED (individual contributors + irrelevant roles):

**Technical ICs:** software, engineer, developer, programmer, devops, data scientist, data engineer, QA, tester, designer (unless Director), architect (unless Chief), frontend, backend, full-stack, sysadmin, DBA

**Business ICs:** consultant (unless managing/principal), analyst (unless lead/head), specialist (unless lead/head), coordinator, expert (unless chief/lead), researcher, junior, intern, trainee, assistant (unless director/manager)

**Admin/Clerical:** administrator (unless director/manager), secretary, receptionist, clerk

**Finance ICs:** accountant (unless chief/head), auditor (unless chief/head), bookkeeper

**Legal ICs:** lawyer (unless managing partner), legal advisor, legal counsel (unless general/chief)

**Irrelevant Managers:** IT manager, system manager, network manager, database manager, warehouse manager

**Recruitment ICs:** recruitment specialist, recruiter (unless head/director/manager)

### What gets KEPT:

All manager-level people, project managers, sales managers, office managers, HR managers, general managers, department heads, directors, VPs, C-level, owners, founders, board members, partners, principals, managing directors — basically anyone with decision-making authority.

## Custom Title Patterns

For campaigns where the built-in set doesn't fit, create a JSON file with custom patterns:

```json
[
    "\\bteacher\\b",
    "\\bprofessor\\b",
    "^(?!.*\\b(?:manager)\\b).*\\bnurse\\b",
    "\\bdriver\\b"
]
```

Then pass it: `--exclude-titles custom_patterns.json`

These are **added to** (not replacing) the built-in set if `--exclude-titles-builtin` is also used.

## Common Phone Country Codes

| Country | Code |
|---------|------|
| Latvia | +371 |
| Lithuania | +370 |
| Estonia | +372 |
| Finland | +358 |
| Germany | +49 |
| Austria | +43 |
| New Zealand | +64 |
| United States | +1 |
| United Kingdom | +44 |

## Industry Relevance Filtering (V6)

For campaigns with many scrapers, the merged lead list often contains leads from industries that don't match the Apollo search intent. Two approaches are available:

### Approach 1: AI-Powered Scoring (Recommended for large lists)

Use `execution/industry_relevance_filter.py` for semantic matching. This uses gpt-4o-mini to score each unique industry name as relevant/maybe/irrelevant in a single API call (~$0.005 per run).

```bash
py execution/industry_relevance_filter.py \
    --input .tmp/merged/merged_leads_XXXXX.json \
    --apollo-url "APOLLO_URL_HERE" \
    --olympus-file .tmp/b2b_finder/olympus_leads_XXXXX.json \
    --output-dir .tmp/filtered/ \
    --output-prefix "campaign_relevant"
```

Key flags:
- `--intent-cache .tmp/campaign_industry_cache.json` — Reuse cached industry intent from M1
- `--exclude-maybe` — Strict mode: only keep "relevant" industries (lower recall, higher precision)
- `--dry-run` — Score and report without writing files

The filter outputs:
- Filtered leads JSON (relevant + maybe by default)
- Removed leads JSON (for review)
- Scores sidecar JSON (for auditability)

### Approach 2: Whitelist (Fast, no AI)

If you know the exact industries to keep, use the `--include-industries` flag in `lead_filter.py`:

```bash
py execution/lead_filter.py \
    --input .tmp/merged/merged_leads_XXXXX.json \
    --output-dir .tmp/filtered/ \
    --include-industries "Retail|Construction|Building Materials|Plastics|Wholesale"
```

### When to use which:
- **AI scoring**: Large merged lists (10K+ leads), 50+ unique industries, uncertain which industries are relevant
- **Whitelist**: Small lists, known industries, re-running a previous campaign with same intent

## Edge Cases & Learnings

- **PeakyDev scraper** often returns leads without email for contacts beyond its verified set. Filter with `--require-email` to clean these out.
- **CodeCrafter with broad org keywords** (e.g. top500 searches) may have low match rates (3-5%). This is expected — the org keyword filter is loose by design.
- **Industry data** comes from the scrapers, not from Apollo filters. Coverage is usually 95-99%. Leads with empty industry are kept by default (could be relevant companies without classification).
- **Phone codes** — the script checks `company_phone` (primary, set by normalizer), with fallbacks to `phone` and `organization_phone` for un-normalized leads. A match on any of these passes the filter.
- **Title patterns use full-title negative lookahead** — e.g. `^(?!.*\b(?:director)\b).*\bdesigner\b` excludes "Designer" but keeps "Design Director". The `^` anchor ensures the qualifier check scans the entire title. Be careful when adding patterns to preserve this structure.

## Decision: Filter Order

Filters are applied in this fixed order for consistency:
1. Email (cheapest check, biggest reduction usually)
2. Phone country code
3. Title exclusion
4. Industry inclusion whitelist (if specified)
5. Industry exclusion
6. Country requirement
7. Website requirement (`--require-website`)
8. Foreign TLD removal (`--remove-foreign-tld`)
9. Phone/country discrepancy removal

This order ensures that expensive regex matching (titles) runs on a smaller set, and country/phone checks run last since they depend on enrichment data that may be added in earlier pipeline steps.

**Note**: AI-powered industry relevance filtering (`industry_relevance_filter.py`) runs as a **separate step before** `lead_filter.py`. It produces a pre-filtered file that you then feed into `lead_filter.py` for further quality filtering.

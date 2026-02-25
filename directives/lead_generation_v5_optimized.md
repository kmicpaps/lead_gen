# Lead Generation Workflow V5 (Optimized for Speed)

**Status:** Active workflow - Optimized for speed
**Created:** December 5, 2025
**Supersedes:** lead_generation_v4_final.md

## Key Optimizations

This version reduces workflow time by **60-80%** through:
1. **Smart scraper routing** - Skip redundant scrapers when Olympus succeeds
2. **Optional enrichment** - Make AI enrichment opt-in, not mandatory
3. **Parallel execution** - Run independent operations concurrently
4. **Reduced validation** - Skip validation tests when using Olympus directly

## Fast-Track Workflow (3-Step Minimum)

For campaigns where Olympus works and enrichment isn't needed:

```
1. Scrape with olympus/b2b-leads-finder (5-6 min for 1000 leads)
2. Cross-campaign deduplication (if client has existing campaigns) (30 sec)
3. Upload to Google Sheets (30 sec)

Total: ~6-7 minutes for 1000 leads ✅
```

## Standard Workflow (When Olympus Gets Enough Leads)

```
1. ⚠️ ALWAYS TRY FIRST: olympus/b2b-leads-finder
   - If gets ≥ target leads → Skip to step 5
   - If gets < target leads → Continue to step 2

2. [SKIP if olympus successful] Pre-scrape filter gap analysis
   - Run: py execution/filter_gap_analyzer.py --apollo-url "URL"
   - Show user which filters each backup scraper handles vs drops
   - If non-enforceable filters exist (revenue, funding, functions),
     ask user: proceed anyway or wait for Olympus cookies?
   - Calculate oversample multiplier per scraper

3. [SKIP if olympus successful] Calculate remaining leads needed
   - Parse Apollo URL → resolve industry hex IDs to text names
   - Apply oversample multiplier if backup scrapers drop filters (see filter_gap_analyzer.py)
   - Pass resolved industries to CodeCrafter/PeakyDev mappers

4. [SKIP if olympus successful] Run code_crafter + peakydev in PARALLEL
   - code_crafter for remaining count (with industry filter)
   - peakydev for backup (only if remaining ≥ 1000, with industry filter)
   - Use oversample counts, not raw target counts

4.5 [SKIP if olympus successful] Post-scrape filter enforcement (if needed)
   - PeakyDev now supports most filters natively (titles, seniority, location,
     revenue, funding, functions, email_status) — post-filter rarely needed
   - CodeCrafter: only drops email_status (minor — hardcoded to validated)
   - If any scraper still drops enforceable filters:
     py execution/post_scrape_filter.py --input LEADS --apollo-url "URL" --scraper SCRAPER
   - Enforces: titles (substring match), seniority (inferred from title), location
   - Use filtered output for merge step

5. Merge & deduplicate (if multiple sources)

6. Cross-campaign deduplication (if client has multiple campaigns)

7. Industry relevance filter (if multiple scrapers used)
   - Run AI-powered industry scoring against Apollo intent
   - Removes leads from irrelevant industries (~20-65% reduction)
   - See directives/lead_quality_filtering.md for details

8. Lead quality filtering (see directives/lead_quality_filtering.md)
   - Apply user's chosen filters (email, phone, title, industry, country)
   - New flags: --require-country, --remove-phone-discrepancies

9. [OPTIONAL] Email validation + enrichment
   - Only if user requests it
   - Scrapers already provide validated emails

10. [OPTIONAL] AI enrichment (casual names + icebreakers)
    - Only if user requests it
    - Can be done later as separate step

11. Upload to Google Sheets + update client.json

Total time with Olympus success: ~6-7 minutes
Total time with all scrapers + post-filter: ~16-22 minutes
Total time with AI enrichment: ~30-45 minutes
```

## Fallback Workflow (When Olympus Fails)

```
1. Olympus fails (cookie/authentication issue or offline)

2. Extract filters from Apollo URL + run filter gap analysis
   - Resolve industry hex IDs to text names (apollo_industry_resolver.py)
   - Run: py execution/filter_gap_analyzer.py --apollo-url "URL"
   - Show user which filters are dropped per scraper
   - Calculate oversample multiplier per scraper
   - If non-enforceable filters exist, warn user before spending money

3. Test with code_crafter (25 leads) - validate 80% match

4. Run code_crafter + peakydev in PARALLEL:
   - Launch code_crafter scraper (target count, with industry filter)
   - Launch peakydev scraper (oversample count ≥ 1000, with industry filter)
   - Wait for both to complete

5. Post-scrape filter enforcement (if needed)
   - PeakyDev now handles most filters natively — post-filter rarely needed
   - For any scraper with dropped enforceable filters:
     py execution/post_scrape_filter.py --input LEADS --apollo-url "URL" --scraper SCRAPER
   - Enforces titles, seniority, location on backup scraper output
   - Use filtered output for merge step

6. Merge & deduplicate all sources

7. Cross-campaign deduplication (if needed)

8. Industry relevance filter
   - Run industry_relevance_filter.py (no Olympus data available in fallback)
   - Uses resolved industries from Apollo URL as sole intent source

9. Lead quality filtering (--require-country, --remove-phone-discrepancies, etc.)

10. [OPTIONAL] Email validation + enrichment

11. [OPTIONAL] AI enrichment

12. Upload to Google Sheets

Total time: ~16-22 minutes (without enrichment)
```

## Cookie Validation Failure Protocol ⚠️

**CRITICAL**: When Olympus scraper fails due to cookie validation:

**Detection**:
- Exit code 2 from Olympus scraper
- Error message contains "Session Validation Failed", "Resurrect the run", or "cookie expired"
- Very low lead count (< 1% of target, e.g., 3 leads when 2000 requested)

**AI Agent Actions** (MANDATORY):
1. **STOP the workflow immediately**
2. **ALERT the user** with clear message:
   ```
   ⚠️  COOKIE VALIDATION FAILED

   The Apollo session cookie has expired.

   Please:
   1. Log into Apollo: https://app.apollo.io
   2. Export cookies using EditThisCookie extension
   3. Update APOLLO_COOKIE in .env file
   4. Confirm when ready to continue
   ```
3. **ASK user for decision**:
   - A) Wait while they refresh cookies (recommended)
   - B) Continue with backup scrapers (lower quality)
4. **WAIT for user confirmation** before proceeding
5. **DO NOT** silently fall back to other scrapers
6. **DO NOT** continue workflow without explicit user choice

**Why this matters**:
- Olympus provides the highest quality Apollo leads
- Backup scrapers may have different data quality/coverage
- User should explicitly choose degraded mode vs. waiting for cookies

**Fast orchestrator now handles this automatically** (as of 2025-12-11)

## Industry Hex ID Resolution Protocol ⚠️

**CRITICAL**: Apollo URLs use hex IDs for industry filters (`organizationIndustryTagIds[]`).
CodeCrafter/PeakyDev need text names, not hex IDs. If the resolver can't map them,
the scrapers will REFUSE to run (exit code 3) instead of scraping unfiltered.

**Detection**:
- `apollo_url_parser.py` prints WARNING about unresolved IDs to stderr
- CodeCrafter/PeakyDev print `INDUSTRY RESOLUTION FAILED` and exit with code 3

**AI Agent Actions**:
1. ALERT the user:
   ```
   INDUSTRY IDs NOT MAPPED

   The Apollo URL has X industry filter(s) that aren't in our mapping yet.
   CodeCrafter/PeakyDev can't scrape without the text names.

   Please open your Apollo search in the browser and tell me the industry
   names from the sidebar filter. I'll save them permanently.
   ```
2. For each industry name the user provides, run:
   `py execution/apollo_industry_resolver.py --add HEX_ID "Industry Name"`
3. Verify all resolved: `py execution/apollo_url_parser.py --apollo-url "URL"`
4. Re-run the scraper

**Olympus doesn't need this**: It passes the raw Apollo URL directly, so hex IDs work natively.

**Auto-learning**: When Olympus runs first and succeeds, its output can teach us new mappings
via `learn_from_olympus()`. The pipeline should call this when unresolved IDs exist.

**Persistent storage**: Learned mappings are saved in `execution/apollo_industry_learned_mappings.json`
and loaded automatically on every run. Each ID only needs to be mapped once, ever.

## Decision Tree: When to Use Which Scrapers

```
START: Run Olympus
│
├─ Cookie validation failed (exit code 2)
│  └─ STOP → Alert user → Wait for cookie refresh OR user approval to continue
│
├─ Olympus succeeds with ≥ target leads
│  └─ DONE - Skip other scrapers ✅ (Save 10-15 min)
│
├─ Olympus succeeds with < target leads
│  └─ Calculate gap → Run code_crafter + peakydev in parallel
│
└─ Olympus fails (other reasons)
   └─ Run code_crafter + peakydev in parallel (after validation)
```

## Parallel Execution Pattern

When multiple scrapers are needed, run them in parallel:

```python
# OLD WAY (Sequential - SLOW)
olympus_leads = scrape_olympus()     # 6 min
codecrafter_leads = scrape_codecrafter()  # 5 min
peakydev_leads = scrape_peakydev()   # 4 min
Total: 15 minutes

# NEW WAY (Parallel - FAST)
with ThreadPoolExecutor(max_workers=3):
    future_olympus = executor.submit(scrape_olympus)
    future_codecrafter = executor.submit(scrape_codecrafter)
    future_peakydev = executor.submit(scrape_peakydev)
    # All run simultaneously
Total: 6 minutes (duration of slowest scraper)
```

## Optional Enrichment Strategy

AI enrichment is **expensive and slow**. Make it opt-in:

### When to Skip Enrichment:
- User wants leads ASAP
- Basic outreach campaign (manual personalization)
- High volume campaigns (>5000 leads)
- Testing/validation runs

### When to Use Enrichment:
- High-value target accounts
- User explicitly requests it
- Small, focused campaigns (<500 leads)
- Premium outreach sequences

### Enrichment Timing:
- **Batch enrichment** (recommended): Enrich all leads at once
- **Lazy enrichment**: Enrich only leads that get positive responses
- **Selective enrichment**: Enrich only high-priority segments

## Email Validation Decision

**Key insight**: Scrapers already provide validated emails!

- **Olympus**: Returns validated emails from Apollo
- **Code_crafter**: `email_status: ["validated"]` filter
- **Peakydev**: `includeEmails: true` - verified emails only

**Recommendation**: Skip email validation unless:
1. Leads are older than 3 months
2. User specifically requests re-validation
3. High bounce rate detected in prior campaigns

## Performance Benchmarks

### Scraper Pricing (per 1k leads)

| Scraper | Cost/1k | Source | Notes |
|---------|---------|--------|-------|
| Olympus | $1.82 | Apify | Best quality, needs cookies |
| PeakyDev | $1.76 | Apify | Cheapest, min 1000 leads |
| CodeCrafter | $2.00 | RapidAPI | Most expensive per lead |

### Workflow Cost Estimates

| Workflow Variant | Lead Count | Time | Est. Cost |
|-----------------|-----------|------|-----------|
| Fast-track (Olympus only) | 1,000 | 6-7 min | ~$1.82 |
| Standard (3 scrapers) | 1,500 | 15-20 min | ~$8-9 |
| With email validation | 1,500 | 18-23 min | ~$9-10 |
| With AI enrichment | 1,000 | 35-45 min | ~$6-8 |
| Full pipeline | 1,500 | 50-60 min | ~$12-15 |

## Apollo URL Construction

If the user doesn't have an Apollo URL yet, use the URL crafter workflow:
- See `directives/apollo_url_crafter.md` for the full SOP
- Quick build: `py execution/apollo_url_builder.py --titles "CEO,Owner" --industries "Construction" --org-locations "Latvia"`
- From JSON: `py execution/apollo_url_builder.py --from-json .tmp/url_draft.json --validate`
- List all industries: `py execution/apollo_url_builder.py --list-industries`

## Execution Scripts (Optimized Usage)

### 0. Pre-Scrape Analysis

```bash
# Filter gap analysis — run BEFORE scraping with backup scrapers
py execution/filter_gap_analyzer.py --apollo-url "..."

# Post-scrape filter enforcement — run AFTER backup scrapers finish
py execution/post_scrape_filter.py \
  --input .tmp/peakydev/peakydev_leads_*.json \
  --apollo-url "..." \
  --scraper peakydev
```

### 1. Fast Campaign (Olympus Only)

```bash
# Single command - done in 6 minutes
py execution/scraper_olympus_b2b_finder.py \
  --apollo-url "..." \
  --max-leads 1000 \
  --country NZ

# Then upload
py execution/google_sheets_exporter.py \
  --input .tmp/b2b_finder/b2b_leads_*.json \
  --sheet-title "Campaign Name"
```

### 2. Multi-Source Campaign (Parallel Scrapers)

```bash
# Run in parallel (3 separate terminal windows)
# Terminal 1:
py execution/scraper_olympus_b2b_finder.py --apollo-url "..." --max-leads 1000

# Terminal 2:
py execution/scraper_codecrafter.py --apollo-url "..." --max-leads 500

# Terminal 3:
py execution/scraper_peakydev.py --apollo-url "..." --max-leads 1000

# Then merge
py execution/leads_deduplicator.py \
  --source-file .tmp/b2b_finder/b2b_leads_*.json \
  --source-file .tmp/codecrafter/codecrafter_leads_*.json \
  --source-file .tmp/peakydev/peakydev_leads_*.json
```

### 3. With Cross-Campaign Deduplication

```bash
# After getting leads, deduplicate across campaigns
py execution/cross_campaign_deduplicator.py --client-id acme_corp
```

### 4. Optional AI Enrichment (Run Separately)

```bash
# Run only if requested - can be done hours/days later
py execution/ai_casual_name_generator.py --input leads.json
py execution/ai_icebreaker_generator.py --input casual_enriched_leads.json
```

## Updated Workflow Checklist

**Pre-Flight**:
- [ ] Get Apollo URL from user (or craft one — see `directives/apollo_url_crafter.md`)
- [ ] Get target lead count
- [ ] Ask: "Do you need AI enrichment?" (Default: No)
- [ ] Check if client has existing campaigns (for cross-campaign dedup)
- [ ] Parse Apollo URL → resolve industry hex IDs (`apollo_industry_resolver.py`)
- [ ] Run filter gap analysis → show user what each scraper drops (`filter_gap_analyzer.py`)
- [ ] If non-enforceable filters exist, ask: proceed or wait for Olympus?
- [ ] Calculate oversample multipliers for backup scrapers

**Execution**:
- [ ] Run Olympus scraper (always first)
- [ ] Check if Olympus got enough leads (≥ target)
  - If YES: Skip to deduplication
  - If NO: Calculate gap and run additional scrapers in parallel (with resolved industries)
- [ ] Merge & deduplicate (if multiple sources)
- [ ] Cross-campaign deduplication (if client has multiple campaigns)
- [ ] **Industry relevance filter** (if multi-scraper campaign):
  - [ ] Run `industry_relevance_filter.py` with Apollo intent + Olympus data
  - [ ] Review AI scores (relevant/maybe/irrelevant)
  - [ ] Apply filter (default: keep relevant + maybe)
- [ ] **Lead quality filtering** (see `directives/lead_quality_filtering.md`):
  - [ ] Run quality analyzer to assess data
  - [ ] Present filter options to user (email, phone, title, industry, country)
  - [ ] Apply user's chosen filters (including `--require-country`, `--remove-phone-discrepancies`)
- [ ] Skip email validation (scrapers provide validated emails)
- [ ] Skip AI enrichment (unless user requested)
- [ ] Upload to Google Sheets
- [ ] Update client.json

**Total Time**: 6-22 minutes (depending on scraper success)

## Data Quality Validation (Critical)

**Always verify scraper field mappings before running full campaigns!**

### The Problem:
Scraper APIs can have inconsistent field names across different versions or updates. If normalization functions don't extract all available fields, you'll lose valuable data (company LinkedIn URLs, domains, etc.).

### Prevention Protocol:

1. **Small Batch Testing** (MANDATORY for new campaigns or scrapers):
   ```bash
   # Test with 25 leads first (fast & cheap)
   py execution/scraper_codecrafter.py --apollo-url "..." --max-leads 25 --output-dir ".tmp/test"

   # Inspect the output JSON to verify all fields are populated:
   # - company_linkedin (must be present)
   # - company_domain (extracted from website_url)
   # - linkedin_url (personal LinkedIn)
   # - All contact and company fields
   ```

2. **Field Verification Checklist**:
   - [ ] Personal LinkedIn URL (`linkedin_url`)
   - [ ] Company LinkedIn URL (`company_linkedin`)
   - [ ] Company domain (`company_domain` - extract from `website_url`)
   - [ ] Company phone (`organization_phone`)
   - [ ] Job title (`title`)
   - [ ] Email (`email`)
   - [ ] City/Country (`city`, `country`)
   - [ ] Company name (`company_name` or legacy `org_name`)
   - [ ] Company country (`company_country` — empty until Lead Magic enrichment)
   - [ ] Website URL (`website_url`)

3. **Scraper-Specific Field Mappings**:

   **IMPORTANT**: All normalization is now handled by `execution/lead_normalizer.py`
   This library automatically detects scraper format and maps fields correctly.

   **Code_crafter** (code_crafter/leads-finder):
   ```python
   # Raw API fields → Normalized schema
   'linkedin' → linkedin_url              # KEY: 'linkedin' NOT 'linkedin_url'
   'full_name' → name                     # KEY: 'full_name' NOT 'name'
   'job_title' → title                    # KEY: 'job_title' NOT 'title'
   'company_linkedin' → company_linkedin
   'company_website' → company_website
   'company_name' → company_name
   'company_phone' → company_phone
   'company_domain' → company_domain
   'industry' → industry
   ```

   **Peakydev** (peakydev/leads-scraper-ppe):
   ```python
   # ALL fields use camelCase (not snake_case)
   'firstName' → first_name               # KEY: camelCase
   'lastName' → last_name
   'fullName' → name                      # KEY: 'fullName' NOT 'full_name'
   'position' → title                     # KEY: 'position' NOT 'job_title'
   'linkedinUrl' → linkedin_url           # KEY: 'linkedinUrl' NOT 'linkedin_url'
   'organizationName' → company_name
   'organizationWebsite' → company_website
   'organizationLinkedinUrl' → company_linkedin
   'organizationIndustry' → industry
   'country' → country                    # City NOT available
   ```

   **Olympus** (olympus/b2b-leads-finder):
   ```python
   # TWO POSSIBLE FORMATS depending on scraper run:

   # Format 1: Nested organization object (most common in Campaign 1)
   'organization' (dict):
     .name → company_name
     .website_url → company_website
     .linkedin_url → company_linkedin
     .phone OR .primary_phone.number → company_phone
     .primary_domain → company_domain
     .naics_codes / .sic_codes → industry

   # Format 2: org_name as dict (seen in Campaign 2)
   'org_name' (dict):
     .name → company_name
     .website_url → company_website
     .linkedin_url → company_linkedin
     .phone OR .primary_phone.number → company_phone
     .primary_domain → company_domain

   # Personal fields (consistent across both formats):
   'first_name', 'last_name', 'name', 'title', 'email',
   'email_status', 'linkedin_url', 'city', 'country'
   ```

4. **Centralized Normalization Library**:

   **USE THIS**: `execution/lead_normalizer.py`

   This library provides:
   - `normalize_lead(lead, source)` - Normalizes single lead
   - `normalize_leads_batch(leads, source)` - Normalizes list of leads
   - Automatic format detection (raw vs pre-normalized)
   - Handles all scraper field variations

   **Usage Example**:
   ```python
   from execution.lead_normalizer import normalize_leads_batch

   # Load raw scraper output
   with open('olympus_leads.json', 'r') as f:
       olympus_raw = json.load(f)

   # Normalize automatically
   olympus_normalized = normalize_leads_batch(olympus_raw, 'olympus')
   # Returns leads with unified field names regardless of input format
   ```

5. **When to Update lead_normalizer.py**:
   - After Apify actor updates (check release notes)
   - When output fields are missing or empty in Google Sheets
   - When starting a new campaign type (verify with 25-lead test)
   - After scraper API errors or changes
   - When scrapers change their output format

6. **Cost-Effective Testing Strategy**:
   - **Code_crafter**: Test with 25 leads ($0.05)
   - **Peakydev**: Minimum 1000 leads required ($1-2) - trust code if code_crafter test passes
   - **Olympus**: Direct Apollo passthrough - no testing needed (always has all fields)

### Self-Annealing Process:

When field mappings break (e.g., Google Sheets shows missing company_name, company_linkedin):
1. Run small test batch (25 leads) if not done already
2. Inspect raw scraper JSON output to identify actual field names
3. Update `execution/lead_normalizer.py` normalize functions with correct mappings
4. Re-normalize the campaign using updated library
5. Re-export to Google Sheets and verify all fields populated
6. Update this documentation with learnings
7. Future campaigns automatically benefit from the fix

**Cost of skipping this step**: Re-running full campaigns wastes time and money!
**Cost of fixing properly**: Update normalize function once, benefits all future campaigns ✅

## Common Mistakes to Avoid

1. ❌ **Running all scrapers when Olympus succeeds**
   - Wastes 10-15 minutes and $2-4
   - Olympus alone is often sufficient

2. ❌ **Running scrapers sequentially**
   - Use parallel execution when multiple scrapers needed
   - Save 50% of scraping time

3. ❌ **Always doing AI enrichment**
   - Make it opt-in based on user needs
   - Save 30-40 minutes per campaign

4. ❌ **Re-validating already validated emails**
   - Scrapers provide validated emails
   - Skip unless specifically needed

5. ❌ **Not using cross-campaign deduplication**
   - Always run for clients with multiple campaigns
   - Prevents duplicate outreach

6. ❌ **Skipping field validation before full runs**
   - Always test with 25 leads first
   - Verify all fields are populated correctly
   - Prevents data loss and re-scraping costs

7. ❌ **Skipping industry relevance filter on multi-scraper campaigns**
   - CodeCrafter/PeakyDev may return leads from 200+ industries
   - Without filtering, 20-65% of merged leads may be irrelevant
   - AI scoring costs <$0.01 and saves manual cleanup time

## Migration from V4

If following the old V4 workflow:

**OLD**: 14 steps, ~45-60 min
**NEW**: 3-8 steps, ~6-20 min

**Changes**:
- Steps 2-7: Now conditional (only if Olympus insufficient)
- Steps 9-13: Now optional (only if user requests)
- Step 15: New - Cross-campaign deduplication
- Parallel execution for scrapers when needed

## From Lead Gen to Outreach

After leads are scraped, filtered, and exported, the next step is cold email outreach. The pipeline feeds directly into the copywriting workflow:

```
Lead Gen Pipeline (this directive)
  → Quality Filtering (lead_quality_filtering.md)
    → Cold Email Copywriting (cold_email_copywriting.md)
      → Export to Instantly/Lemlist
        → Monitor & Optimize
```

**Key insight from research:** #1 predictor of cold email success is **list quality, not copy quality**. This pipeline's filtering and micro-segmentation directly determines outreach reply rates.

**Micro-segmentation pattern:** Instead of exporting 5,000 leads to one campaign, segment into 10 lists of 200-500 leads by niche/industry/pain point and tailor each email per segment. Result: 8-15% reply rate vs 3-5% for unsegmented.

See `docs/2026-02_cold_email_deep_dive.md` and `docs/cold_email_best_practices.md` for full outreach research.

## Future Optimizations

Potential improvements:
1. **Batch AI enrichment**: Call AI API with 10 leads per request instead of 1
2. **Cached enrichment**: Store enrichment results to reuse across campaigns
3. **Smart scraper selection**: Use ML to predict which scraper will succeed
4. **Progressive enrichment**: Enrich leads as they show engagement
5. **Incremental uploads**: Upload leads as they're scraped (real-time sheets)
6. **Auto micro-segmentation**: Segment leads by industry/title for targeted outreach

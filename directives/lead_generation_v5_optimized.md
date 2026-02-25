# Lead Generation Workflow V8 (Parallel-First)

**Status:** Active workflow
**Created:** December 5, 2025
**Updated:** February 25, 2026 — V8: User picks scrapers upfront, all run in parallel
**Supersedes:** V5/V7 (Olympus-first sequential flow)

## Design Philosophy

User picks which scrapers to run **before** scraping starts. All selected scrapers run **in parallel**. No more "try Olympus first, then decide" — the user sees costs, time estimates, and filter support upfront and makes the call.

## Scraper Reference

| Scraper | Cost/1k | Speed | Min Leads | Notes |
|---------|---------|-------|-----------|-------|
| Olympus | $1.82 | ~26 leads/min | None | Needs Apollo cookies |
| CodeCrafter | $2.00 | ~345 leads/min | 25 | Fastest scraper |
| PeakyDev | $1.76 | ~286 leads/min | 1,000 | Cheapest per lead |

**Time estimates for 1,000 leads:**
- Olympus: ~38 min
- CodeCrafter: ~3 min
- PeakyDev: ~4 min
- All 3 in parallel: ~38 min (Olympus is bottleneck)

## Unified Workflow

```
1. PRE-FLIGHT: Parse Apollo URL, show detailed per-scraper breakdown:
   - Actual lead count that will be requested (after min/max clamping)
   - Specific filter values sent to each scraper (with transforms noted)
   - Which filters are dropped or post-filtered
   - Cost and time estimates
   - Notes (cookies needed, min leads, etc.)

2. USER PICKS SCRAPERS (default: all)
   - Agent presents one section per scraper with full detail, NOT a summary table
   - User sees exactly what each scraper will do before choosing

3. RUN ALL SELECTED SCRAPERS IN PARALLEL
   - Orchestrator: py execution/fast_lead_orchestrator.py --scrapers <choice>
   - If Olympus cookie fails mid-run, other scrapers continue unaffected
   - Cookie failure is logged as warning, not a blocker

4. Merge & deduplicate (if multiple sources)

5. Cross-campaign deduplication (if client has existing campaigns)

6. Industry relevance filter (if multi-scraper)
   - AI-powered industry scoring against Apollo intent
   - ~20-65% irrelevant lead reduction

7. Quality filtering (present report to user, get approval)
   - --require-email, --require-website, --require-country
   - --remove-phone-discrepancies, --remove-foreign-tld

8. [OPTIONAL] AI enrichment (only if user requests)

9. Upload to Google Sheets + update client.json

Total time: parallel time of slowest selected scraper + ~2 min post-processing
```

## Cookie Validation Failure Protocol ⚠️

**CRITICAL**: When Olympus scraper fails due to cookie validation:

**Detection**:
- Exit code 2 from Olympus scraper
- Error message contains "Session Validation Failed", "Resurrect the run", or "cookie expired"
- Very low lead count (< 1% of target, e.g., 3 leads when 2000 requested)

**Behavior in parallel mode**:
Since all scrapers run in parallel, Olympus cookie failure does NOT block other scrapers.
The orchestrator logs a warning and continues collecting results from other scrapers.

**AI Agent Actions**:
1. After parallel run completes, check if Olympus failed with cookie error
2. **ALERT the user**: "Olympus failed (cookie expired) — other scrapers succeeded normally"
3. If user selected ONLY Olympus, the run fails entirely — alert user to refresh cookies
4. If user selected multiple scrapers, the run completes with remaining scrapers' output

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

## Scraper Selection Guide

User always picks scrapers before scraping starts. Here are common selection patterns:

| Scenario | Recommended Scrapers | Why |
|----------|---------------------|-----|
| Speed matters, < 1000 leads | codecrafter | Fastest, cheapest for small runs |
| Maximum coverage | all three | Different data sources, best dedup |
| Budget-conscious | peakydev | Cheapest per lead ($1.76/1k) |
| Highest quality | olympus | Direct Apollo data, all fields |
| Olympus cookies expired | codecrafter + peakydev | Skip Olympus entirely |
| Need > 5000 leads | codecrafter + peakydev | Olympus has no cap but is slow; CC+PD faster |

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

### Scraper Pricing & Speed

| Scraper | Cost/1k | Speed | Source | Notes |
|---------|---------|-------|--------|-------|
| Olympus | $1.82 | ~26 leads/min | Apify | Needs cookies, slowest |
| PeakyDev | $1.76 | ~286 leads/min | Apify | Cheapest, min 1000 leads |
| CodeCrafter | $2.00 | ~345 leads/min | RapidAPI | Fastest |

### Time estimates (from `scraper_registry.py`)

| Scraper | 500 leads | 1,000 leads | 2,000 leads | 5,000 leads |
|---------|-----------|-------------|-------------|-------------|
| Olympus | ~19 min | ~38 min | ~77 min | ~192 min |
| CodeCrafter | ~1 min | ~3 min | ~6 min | ~14 min |
| PeakyDev | ~2 min | ~4 min | ~7 min | ~17 min |

**Parallel time = slowest selected scraper.** If running all 3 for 1,000 leads, total is ~38 min (Olympus bottleneck).

### Workflow Cost Estimates

| Scrapers Selected | Lead Count | Parallel Time | Est. Cost |
|------------------|-----------|---------------|-----------|
| CodeCrafter only | 1,000 | ~3 min | ~$2.00 |
| PeakyDev only | 1,000 | ~4 min | ~$1.76 |
| Olympus only | 1,000 | ~38 min | ~$1.82 |
| CC + PeakyDev | 1,000 | ~4 min | ~$3.76 |
| All 3 | 1,000 | ~38 min | ~$5.58 |
| All 3 + AI enrichment | 1,000 | ~70 min | ~$8-10 |

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

## Workflow Checklist

**Pre-Flight**:
- [ ] Get Apollo URL from user (or craft one — see `directives/apollo_url_crafter.md`)
- [ ] Get target lead count
- [ ] Check if client has existing campaigns (for cross-campaign dedup)
- [ ] Parse Apollo URL → resolve industry hex IDs
- [ ] Run pre-flight: show detailed per-scraper breakdown (filters, lead count, cost, time)
- [ ] Present per-scraper sections to user (actual filter values, transforms, lead counts)
- [ ] User picks which scrapers to run

**Execution**:
- [ ] Run ALL selected scrapers in parallel (`--scrapers <choice>`)
- [ ] Check for cookie failures (Olympus) — warn user, don't block
- [ ] Merge & deduplicate (if multiple sources)
- [ ] Cross-campaign deduplication (if client has multiple campaigns)
- [ ] Industry relevance filter (if multi-scraper)
- [ ] Quality filtering (present report, get user approval)
- [ ] Skip AI enrichment (unless user requested)
- [ ] Upload to Google Sheets
- [ ] Update client.json

**Total Time**: parallel time of slowest scraper + ~2 min post-processing

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

1. ❌ **Not showing scraper options before running**
   - Always present detailed per-scraper breakdown (specific filters, lead counts, cost, time)
   - Never use a generic "All OK" summary — show actual filter values and transforms
   - User must explicitly choose scrapers

2. ❌ **Running scrapers sequentially**
   - All selected scrapers run in parallel
   - Total time = slowest scraper, not sum of all

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

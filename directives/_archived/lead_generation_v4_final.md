# Lead Generation Workflow V4 (Final)

**Status:** Active workflow as of December 3, 2025
**Last Updated:** December 5, 2025 - Reinforced mandatory olympus-first workflow to prevent skipping Step 1
**Supersedes:** lead_generation_v3_corrected.md

## Critical Understanding

### Scraper Architecture

**IMPORTANT**: Only `olympus/b2b-leads-finder` accepts Apollo URL directly!

- **olympus/b2b-leads-finder**: Uses Apollo URL + cookies → scrapes from Apollo directly
- **code_crafter/leads-finder**: Requires extracted filters (NOT Apollo URL)
- **peakydev/leads-scraper-ppe**: Requires extracted filters (NOT Apollo URL)

### Why This Matters

When you pass Apollo URL to Peakydev/Code_Crafter WITHOUT extracting filters, they return **random contacts** that don't match your ICP!

## Complete Workflow (14 Steps)

⚠️ **CRITICAL: ALWAYS START WITH STEP 1 - OLYMPUS SCRAPER!** ⚠️
**DO NOT skip to Step 2 (filter extraction) without attempting olympus first!**
**Olympus provides the highest quality leads and must be attempted before other scrapers.**

```
1. ⚠️ ALWAYS TRY FIRST ⚠️ Scrape leads with olympus/b2b-leads-finder (Apify, accepts Apollo URL)
   - If fails due to cookies/authentication: Ask user to renew Apollo cookies
   - If still fails with fresh cookies: Skip olympus and continue with other scrapers
   - If olympus is offline/broken: Skip and continue
2. Extract filters from Apollo URL for other scrapers
3. Test filters with code_crafter/leads-finder (25-lead test batch)
4. Validate 80% match with Apollo ICP → if not, adjust filters and retry step 3
5. Full scrape with code_crafter/leads-finder (target lead count)
6. Scrape with peakydev/leads-scraper-ppe (target lead count, min 1000)
7. If no leads from peakydev, try again with broader filters
8. Merge & deduplicate all lead sources (olympus + code_crafter + peakydev)
9. Email validation (Lead Magic API)
10. Email enrichment for missing/invalid (Lead Magic API)
11. AI enrichment - Casual company names (OpenAI/Anthropic)
12. AI enrichment - Icebreakers with website scraping (OpenAI/Anthropic)
13. AI fallback enrichment - Generic icebreakers for missing data
14. Upload to Google Sheets (with all enriched fields) + report
```

## 🚨 MANDATORY FIRST STEP - READ THIS BEFORE STARTING ANY CAMPAIGN 🚨

**When starting a NEW campaign, you MUST:**

1. ✅ **ALWAYS attempt olympus/b2b-leads-finder FIRST** (Step 1)
   - Run: `py execution/scraper_olympus_b2b_finder.py --apollo-url "..." --max-leads 1000`
   - This is NOT optional - you must try it before other scrapers

2. ✅ **Only proceed to Step 2 (filter extraction) if:**
   - Olympus failed due to authentication (after asking user to update cookies)
   - Olympus failed even with fresh cookies
   - Olympus actor is offline/broken

3. ❌ **NEVER skip directly to filter extraction without attempting olympus**

**Why olympus must be tried first:**
- Uses your Apollo account directly (highest quality matches)
- No filter translation errors
- Often finds leads other scrapers miss
- Required by the workflow - skipping it is a mistake

**If you catch yourself about to run `apollo_url_parser.py` or `scraper_codecrafter.py` as your FIRST action:**
- STOP ✋
- Go back and run olympus scraper first
- Only extract filters if olympus fails

## Critical Workflow Details

### Step 1: Olympus Scraper Cookie Management

**IMPORTANT**: When olympus/b2b-leads-finder fails, follow this decision tree:

1. **Check the error message**:
   - "Something went wrong. Resurrect the run" → Cookie/authentication issue
   - "Authentication failed" → Cookie/authentication issue
   - Actor timeout or network error → May be temporary, can retry once

2. **If cookie/authentication issue**:
   - **STOP and ask user**: "The olympus scraper failed due to authentication. Please update your Apollo cookies in the .env file."
   - Wait for user to update cookies
   - Retry olympus scraper
   - If still fails after cookie update → Skip olympus and continue to step 2

3. **If actor is offline or broken**:
   - Skip olympus and continue to step 2
   - Note in final report that olympus was skipped

**How to update cookies**:
- Go to Apollo.io in browser (logged in)
- Export cookies using EditThisCookie extension
- Update `APOLLO_COOKIE=[...]` in .env file
- Re-run the scraper

### Steps 3-6: Scraping Order (CRITICAL)

**After 25-lead test passes validation, scrape in this order**:

1. **Step 5: Full scrape with code_crafter** (accepts any lead count, 25-5000+)
   - Use same filters that passed the 25-lead test
   - Target the full lead count requested by user
   - Fast, reliable, no cookies needed
   - Example: `--max-leads 1400`

2. **Step 6: Scrape with peakydev** (minimum 1000 leads)
   - Use same filters from step 2
   - Request same target count
   - This provides redundancy and additional leads
   - May find leads that code_crafter missed

**Why this order?**
- Code_crafter is more flexible (no minimum) and reliable
- Get leads faster with code_crafter while peakydev runs
- If peakydev fails, we already have code_crafter leads
- Merge & deduplicate combines all sources for maximum coverage

## Execution Scripts (Active)

### Scrapers

#### 1. olympus/b2b-leads-finder
**File**: [scraper_olympus_b2b_finder.py](../execution/scraper_olympus_b2b_finder.py)
**Input**: Apollo URL (direct), cookies, country code
**Min leads**: 1000
**Method**: Scrapes Apollo directly using your account
**Cost**: $1/1k leads (Apify paid users)

**Usage:**
```bash
py execution/scraper_olympus_b2b_finder.py \
  --apollo-url "https://app.apollo.io/#/people?..." \
  --max-leads 1000 \
  --country AT
```

#### 2. code_crafter/leads-finder
**File**: [scraper_codecrafter.py](../execution/scraper_codecrafter.py)
**Input**: Apollo URL → parses filters internally → calls actor
**Min leads**: 25 (perfect for testing)
**Method**: Uses extracted filters (job_title, location, seniority, company_size, etc.)

**Usage:**
```bash
py execution/scraper_codecrafter.py \
  --apollo-url "https://app.apollo.io/#/people?..." \
  --max-leads 25 \
  --test-only
```

#### 3. peakydev/leads-scraper-ppe
**File**: [scraper_peakydev.py](../execution/scraper_peakydev.py)
**Input**: Apollo URL → parses filters → calls actor
**Min leads**: 1000 (actor limitation)
**Method**: Uses extracted filters (personCountry, industryKeywords, companyEmployeeSize, etc.)

**Usage:**
```bash
py execution/scraper_peakydev.py \
  --apollo-url "https://app.apollo.io/#/people?..." \
  --max-leads 1000 \
  --test-only
```

### Filter Extraction & Helpers

**File**: [apollo_url_parser.py](../execution/apollo_url_parser.py)
Extracts structured filters from Apollo URL

**File**: [apollo_to_apify_mapper.py](../execution/apollo_to_apify_mapper.py)
Maps Apollo filters to Apify actor input formats

### Data Processing

**File**: [leads_deduplicator.py](../execution/leads_deduplicator.py)
**Purpose**: Merge multiple lead sources and remove duplicates by email/LinkedIn URL

### Email Operations

**File**: [email_verifier.py](../execution/email_verifier.py)
**Purpose**: Validate email addresses using Lead Magic API
**API**: Lead Magic
**Cost**: $0.0003 per verification

**File**: [email_enricher.py](../execution/email_enricher.py)
**Purpose**: Find missing/invalid emails using Lead Magic API
**API**: Lead Magic
**Cost**: $0.001 per enrichment

### AI Enrichment

**File**: [ai_casual_name_generator.py](../execution/ai_casual_name_generator.py)
**Purpose**: Transform formal company names into casual, human-friendly versions
**API**: OpenAI (default) or Anthropic
**Cost**: ~$0.10-0.20 per 1000 leads

**Example transformation:**
- "HABA-Beton Sp. Z O.o." → "HABA-Beton"
- "Smith Construction Services LLC" → "Smith Construction"

**Usage:**
```bash
py execution/ai_casual_name_generator.py \
  --input leads.json \
  --ai-provider openai
```

**File**: [ai_icebreaker_generator.py](../execution/ai_icebreaker_generator.py)
**Purpose**: Generate personalized icebreaker messages using website content
**Features**:
- Concurrent website scraping (10 workers, 30s timeout)
- AI generation referencing specific website content
- Fallback to generic icebreakers if website unavailable

**API**: OpenAI (default) or Anthropic
**Cost**: ~$0.30-0.50 per 1000 leads
**Dependency**: [website_scraper.py](../execution/website_scraper.py)

**Usage:**
```bash
py execution/ai_icebreaker_generator.py \
  --input casual_enriched_leads.json \
  --ai-provider openai
```

**Optional parameters:**
- `--template my_template.txt`: Use custom icebreaker style
- `--skip-scraping`: Use existing website_content
- `--force-regenerate`: Regenerate existing icebreakers

**File**: [ai_fallback_enricher.py](../execution/ai_fallback_enricher.py)
**Purpose**: Add missing icebreakers and company summaries
**Features**:
- Generic icebreakers when website unavailable (ensures 100% coverage)
- Company summaries extracted from website content

**Usage:**
```bash
py execution/ai_fallback_enricher.py \
  --input icebreaker_enriched_leads.json
```

### Export

**File**: [google_sheets_exporter.py](../execution/google_sheets_exporter.py)
**Purpose**: Export leads with all enrichments to Google Sheets

**Exported columns:**
- Basic info: Name, Title, Email, Email Status
- Contact: LinkedIn URL, City, Country, Phone
- Company: Organization Name, Casual Name, Website
- AI-generated: Company Summary, Icebreaker
- Metadata: Source, Generated timestamps

**Usage:**
```bash
py execution/google_sheets_exporter.py \
  --input icebreaker_enriched_leads.json \
  --sheet-title "My Leads"
```

### Orchestration

**Note**: Python orchestrator scripts have been archived. The AI agent now orchestrates the workflow by reading this directive and calling execution tools as needed. This follows the 3-layer architecture:
- **Layer 1**: This directive defines the 12-step process
- **Layer 2**: AI agent reads directive and makes decisions
- **Layer 3**: Execution scripts perform deterministic work

To run the complete workflow, ask the AI agent to execute the 12 steps using the scripts above.

## Filter Extraction & Mapping

### Apollo → Code_Crafter Mapping

```python
{
    "fetch_count": 25,
    "email_status": ["validated"],
    "contact_job_title": apollo_filters['titles'],           # Direct
    "contact_location": apollo_filters['locations'],         # Direct
    "seniority_level": map_seniority(apollo_filters['seniority']),  # Mapped
    "company_keywords": apollo_filters['keywords'],          # Direct
    "size": map_company_size(apollo_filters['company_size']),  # Mapped
    "min_revenue": apollo_filters['revenue']['min'],        # Direct
    "funding": apollo_filters['funding']                     # Direct
}
```

### Apollo → Peakydev Mapping

```python
{
    "includeEmails": True,
    "totalResults": 1000,
    "personCountry": apollo_filters['locations'],           # Country names
    "industryKeywords": apollo_filters['keywords'],         # Keywords
    "companyEmployeeSize": map_size(apollo_filters['company_size'])  # Mapped format
}
```

## Validation Logic

### What 80% Match Means

After scraping 25 test leads:
1. Extract validation keywords from Apollo filters (titles, seniority, keywords, locations)
2. For each lead, check if ANY of these match:
   - Title contains any title keyword
   - Location contains any location keyword
   - Company/lead text contains any general keyword
3. Count matches / total leads
4. If ≥80% → PASS
5. If <80% → FAIL → Broaden filters → Test again

### Filter Broadening Strategy (If validation fails)

**Attempt 1**: Use exact Apollo filters
**Attempt 2**: Remove city filter (keep country/state)
**Attempt 3**: Remove specific job titles (keep seniority)
**Attempt 4**: Remove company size filter
**Attempt 5**: Keep only essentials (seniority, country, industry)

## Known Constraints

### Peakydev Limitations
- **Minimum 1000 leads** - cannot do 25-lead test
- For test mode: Must scrape 1000 leads even for validation
- More expensive for testing phase

### B2B_Finder Limitations
- **Minimum 1000 leads** - cannot do small batches
- Requires valid Apollo cookies
- Country code must match Apollo account region

### Code_Crafter Advantages
- Can scrape as few as 25 leads
- Perfect for validation testing
- No cookies required
- Flexible filter combinations

## Tools/Dependencies

- **apollo_url_parser.py**: Parses Apollo URL → extracts filter dict
- **apollo_to_apify_mapper.py**: Maps filters to Apify actor formats
- **Apify actors**: olympus/b2b-leads-finder, code_crafter/leads-finder, peakydev/leads-scraper-ppe
- **LeadMagic API**: Email validation + enrichment
- **OpenAI / Anthropic APIs**: AI enrichment (casual names + icebreakers)
- **Google Sheets API**: Final export
- **website_scraper.py**: Website content extraction for icebreakers
- **error_handler.py**: Error handling utilities

## Archived Scripts

The following scripts have been moved to [execution/_archived/](../execution/_archived/) and are no longer part of the active workflow:

**Deprecated Scrapers:**
- `run_apollo_scraper.py` - Old RapidAPI version
- `run_apollo_scraper_fast.py` - RapidAPI (NOT Apify), wrong approach
- `run_apify_apollo_scraper.py` - Fallback using x_guru, redundant
- `run_apify_scraper_v2.py` - Deprecated
- `run_hiworld_scraper.py` - Alternative scraper, not in defined process
- `run_xguru_scraper.py` - Alternative scraper, not in defined process

**Deprecated Orchestrators (Anti-pattern):**
- `enhanced_lead_workflow.py` - Old version, superseded by v2
- `enhanced_lead_workflow_fast.py` - Fast variant, superseded by v2
- `main_lead_orchestrator.py` - Python orchestrator (AI agent should orchestrate, not Python)
- `complete_poland_workflow.py` - Country-specific, not general

**Utilities:**
- `cleanup_enrichment_fields.py` - Unused utility

See [execution/_archived/README.md](../execution/_archived/README.md) for details.

## Common Mistakes to Avoid

1. **Skipping cookie renewal when olympus fails** - Always ask user to update cookies before giving up on olympus scraper
2. **Jumping to peakydev after test passes** - Must do full scrape with code_crafter (step 5) BEFORE peakydev (step 6)
3. **Using RapidAPI scrapers instead of Apify** - Always use `scraper_olympus_b2b_finder.py`, never `run_apollo_scraper_fast.py`
4. **Passing Apollo URL to code_crafter/peakydev without filter extraction** - These actors require extracted filters
5. **Skipping 80% validation test** - Always test with 25 leads before full scrape
6. **Not using generic icebreakers** - Ensure 100% icebreaker coverage with fallbacks (step 13)
7. **Missing company summaries** - Always run `ai_fallback_enricher.py` after icebreaker enrichment
8. **Using Python orchestrators** - Let AI agent orchestrate based on this directive, don't hard-code workflow in Python

## Next Steps

If you need to generate new leads:

1. **Get Apollo URL** from your Apollo search
2. **Ask the AI agent to execute the 12-step workflow** by providing:
   - Apollo URL
   - Target lead count (minimum 1000)
   - Desired Google Sheets title
3. **AI agent will orchestrate** - Reads this directive and calls execution scripts in correct order
4. **Access results** - Google Sheets link will be provided at the end

For manual step-by-step execution, follow the 12-step workflow above, running each script individually with the commands shown in each section.

# Lead Generation Workflow V3 (Corrected)

## Critical Understanding

### Scraper Architecture

**IMPORTANT**: Only `olympus/b2b-leads-finder` accepts Apollo URL directly!

- **olympus/b2b-leads-finder**: Uses Apollo URL + cookies → scrapes from Apollo directly
- **code_crafter/leads-finder**: Requires extracted filters (NOT Apollo URL)
- **peakydev/leads-scraper-ppe**: Requires extracted filters (NOT Apollo URL)

### Why This Matters

When you pass Apollo URL to Peakydev/Code_Crafter WITHOUT extracting filters, they return **random contacts** that don't match your ICP!

## Complete Workflow (12 Steps)

```
1. Parse Apollo URL → Extract Filters
2. Run 3 Parallel Test Scrapers (25 leads each):
   - olympus/b2b-leads-finder (with Apollo URL)
   - code_crafter/leads-finder (with EXTRACTED filters)
   - peakydev/leads-scraper-ppe (with EXTRACTED filters) [NOTE: min 1000 leads]
3. Validate Each Against Apollo ICP (80% threshold)
4. If <80% match → Adjust filters → Test again (iterative)
5. If ≥80% match → Proceed to full scrape
6. Full scrape (all passing scrapers in parallel)
7. Merge & deduplicate lead lists
8. Email validation (Lead Magic)
9. Email enrichment for missing/invalid (Lead Magic)
10. AI Enrichment - Casual company names (NEW)
11. AI Enrichment - Icebreakers with website scraping (NEW)
12. Export to Google Sheets (with AI fields) + Report
```

## Execution Scripts

### 1. olympus/b2b-leads-finder
**File**: `execution/run_apify_b2b_leads_finder.py`
**Input**: Apollo URL (direct), cookies, country code
**Min leads**: 1000
**Method**: Scrapes Apollo directly using your account

### 2. code_crafter/leads-finder
**File**: `execution/run_codecrafter_scraper.py` (NEW - accepts Apollo URL, extracts filters internally)
**Input**: Apollo URL → parses filters → calls actor with extracted params
**Min leads**: 25 (for testing)
**Method**: Uses extracted filters (job_title, location, seniority, company_size, etc.)

### 3. peakydev/leads-scraper-ppe
**File**: `execution/run_peakydev_scraper.py`
**Input**: Apollo URL → parses filters → calls actor with extracted params
**Min leads**: 1000 (actor limitation)
**Method**: Uses extracted filters (personCountry, industryKeywords, companyEmployeeSize, etc.)

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

## Example Command Usage

### Test Code_Crafter (25 leads)
```bash
python execution/run_codecrafter_scraper.py \
  --apollo-url "https://app.apollo.io/#/people?..." \
  --max-leads 25 \
  --test-only
```

### Test B2B_Finder (1000 min)
```bash
python execution/run_apify_b2b_leads_finder.py \
  --apollo-url "https://app.apollo.io/#/people?..." \
  --max-leads 1000
```

### Test Peakydev (1000 min)
```bash
python execution/run_peakydev_scraper.py \
  --apollo-url "https://app.apollo.io/#/people?..." \
  --max-leads 1000 \
  --test-only
```

## Orchestration Script

**File**: `execution/enhanced_lead_workflow_v2.py`

This script:
1. Accepts Apollo URL + target lead count
2. Parses URL to extract filters
3. Tests all 3 scrapers in parallel (with filter extraction)
4. Validates results against Apollo ICP
5. Iteratively adjusts filters if needed
6. Runs full scrape with passing scrapers
7. Merges, validates, enriches, exports

## AI Enrichment (Steps 10-11)

### Step 10: Casual Company Names

**Script**: `execution/enrich_casual_org_names.py`

Transform formal company names into casual, human-friendly versions:
- Removes legal suffixes (LLC, Ltd, Sp. Z O.o., GmbH, AB, AS, etc.)
- Extracts core brand name (1-2 words max)
- Handles nested `org_name` format from B2B Finder

**Usage:**
```bash
py execution/enrich_casual_org_names.py --input leads.json --ai-provider openai
```

**AI Providers:** OpenAI (default) or Anthropic
**Cost:** ~$0.10-0.20 per 1000 leads
**Output Fields:** `casual_org_name`, `casual_org_name_generated_by`, `casual_org_name_generated_at`

### Step 11: Icebreaker Generation

**Script**: `execution/enrich_icebreakers.py`

Generate personalized icebreaker messages using:
1. Website scraping (10 concurrent, 30s timeout)
2. AI generation referencing specific website content

**Usage:**
```bash
py execution/enrich_icebreakers.py --input casual_enriched_leads.json --ai-provider openai
```

**AI Providers:** OpenAI (default) or Anthropic
**Cost:** ~$0.30-0.50 per 1000 leads
**Output Fields:** `icebreaker`, `website_content`, `icebreaker_generated_by`, `icebreaker_generated_at`

**Optional Parameters:**
- `--template my_template.txt`: Use custom icebreaker style
- `--skip-scraping`: Use existing website_content (for re-generation)
- `--force-regenerate`: Regenerate existing icebreakers

### Step 12: Google Sheets Export (Updated)

**Script**: `execution/upload_to_google_sheet.py`

Exports leads with AI-enriched fields to Google Sheets:

**New Columns:**
- Casual Company Name (`casual_org_name`)
- Company Summary (`company_summary`)
- Icebreaker (`icebreaker`)

**Usage:**
```bash
py execution/upload_to_google_sheet.py --input icebreaker_enriched_leads.json --sheet-title "My Leads"
```

## Tools/Dependencies

- **parse_apollo_filters.py**: Parses Apollo URL → extracts filter dict
- **Apify actors**: olympus/b2b-leads-finder, code_crafter/leads-finder, peakydev/leads-scraper-ppe
- **LeadMagic API**: Email validation + enrichment
- **OpenAI / Anthropic APIs**: AI enrichment (casual names + icebreakers)
- **Google Sheets API**: Final export

## Critical Fixes Applied

1. ✓ Created `run_codecrafter_scraper.py` that accepts Apollo URL and extracts filters
2. ✓ Updated Peakydev to extract filters (not use URL directly)
3. ✓ Removed emoji characters causing Windows encoding errors
4. ✓ Fixed B2B_Finder org_name normalization issue
5. ✓ Filter out garbage log records from B2B_Finder output

## Next Steps

1. Test Code_Crafter with Poland URL (25 leads)
2. Verify extracted filters produce relevant results
3. Update enhanced_lead_workflow_v2.py to use new Code_Crafter script
4. Remove old run_apify_scraper_v2.py (deprecated)

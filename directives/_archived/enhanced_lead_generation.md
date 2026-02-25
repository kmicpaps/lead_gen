# Enhanced Multi-Source Lead Generation

## Goal
Generate high-quality B2B leads from multiple sources (RapidAPI + Apify), deduplicate, verify emails, enrich missing emails, and deliver via Google Sheets.

## Workflow Overview

```
1. Test Run (25 leads) → Validation (80% threshold)
2. RapidAPI Scraper (Apollo Data) → Target leads (User specified)
3. Apify Scraper → Target leads (User specified)
4. Merge & Deduplicate → Remove duplicates by email/name
5. Email Verification (Lead Magic) → Verify all emails
6. Email Enrichment (Lead Magic) → Find missing emails
7. Export to Google Sheets → Final deliverable
8. Quality Report → Statistics and metrics
```

## Inputs

### RapidAPI Scraper (Apollo Data Source)
- **RapidAPI Search URL** (required): Full Apollo.io search URL with filters
  - Example: `https://app.apollo.io/#/people?page=1&contactEmailStatusV2[]=verified&personTitles[]=ceo...`
- **Max Leads**: Target count (Required, no default)
  - Note: Actual count may be less if filters are restrictive
  - **Priority: Filter compliance over quantity**

### Apify Scraper (code_crafter/leads-finder)
- **Max Leads**: Target count (Required, no default)
- **People Targeting**:
  - `Job Titles`: Include/Exclude (e.g., "CEO,Founder")
  - `Seniority`: Owner, C-Level, VP, Director, etc.
  - `Functional Level`: Marketing, Sales, Engineering, etc.
- **Location Targeting**:
  - `Location`: Region/Country/State (e.g., "United States", "California")
  - `City`: Specific cities (e.g., "San Francisco")
  - `Exclude Location/City`: Areas to exclude
- **Company Targeting**:
  - `Industry`: Include/Exclude industries
  - `Keywords`: Include/Exclude company keywords
  - `Size`: Company size range (e.g., "11-50")
  - `Revenue`: Min/Max revenue
  - `Funding`: Funding type (e.g., "Series A")
  - `Domain`: Specific company domains
- **Email Quality**:
  - `Status`: validated (default), not_validated, unknown

### Validation Settings
- **Validation Keywords**: Comma-separated keywords to check against Company, Industry, and Job Title.
- **Validation Threshold**: Minimum match percentage (default: 0.8 / 80%)

### General Options
- `--skip-rapidapi`: Skip RapidAPI scraping
- `--skip-apify`: Skip Apify scraping
- `--skip-enrichment`: Skip email enrichment to save credits
- `--sheet-title`: Custom Google Sheet title

## Standardized Output Schema

All leads are normalized to this schema:

```
first_name, last_name, name, organization_phone, linkedin_url,
title, email_status, email, city, country, org_name, website_url
```

### Field Descriptions
- **first_name**: Contact's first name
- **last_name**: Contact's last name
- **name**: Full name (auto-generated if missing)
- **organization_phone**: Company phone number
- **linkedin_url**: LinkedIn profile URL
- **title**: Job title
- **email_status**: Verification status (valid, invalid, risky, unknown, missing)
- **email**: Email address
- **city**: City
- **country**: Country
- **org_name**: Organization/company name
- **website_url**: Company website URL

## Execution Tools

### Core Scripts
1. **`execution/run_apollo_scraper.py`**
   - Scrapes leads from RapidAPI (Apollo data source)
   - Requires: RapidAPI URL, APOLLO_COOKIE, RapidAPI credentials
   - Output: `.tmp/apollo_run/apollo_leads_*.json`

2. **`execution/run_apify_scraper_v2.py`**
   - Scrapes leads from Apify leads-finder
   - Requires: APIFY_API_KEY
   - Output: `.tmp/apify_run/apify_leads_*.json`

3. **`execution/merge_deduplicate_leads.py`**
   - Merges leads from multiple sources
   - Deduplicates by email (primary) or name+company (fallback)
   - Enriches data by combining fields from both sources
   - Output: `.tmp/merged/merged_leads_*.json`

4. **`execution/verify_emails_leadmagic_fast.py`**
   - Verifies all emails using Lead Magic API
   - Rate limit: 1000 req/min
   - Cost: Cheap (token-based)
   - Output: `.tmp/verified/verified_leads_*.json`

5. **`execution/enrich_emails_leadmagic_fast.py`**
   - Finds missing/invalid emails using Lead Magic
   - Rate limit: 400 req/min (conservative)
   - Cost: Expensive (1 credit per lookup)
   - Output: `.tmp/enriched/enriched_leads_*.json`

6. **`execution/upload_to_google_sheet.py`**
   - Exports leads to Google Sheets
   - Requires: credentials.json, token.json
   - Output: Google Sheets URL

### Master Orchestrator
**`execution/enhanced_lead_workflow_fast.py`** (Recommended)
- Runs entire workflow end-to-end with parallel scraping
- Performs pre-validation check
- Handles errors at each stage
- Generates quality report
- Example usage:
  ```bash
  python execution/enhanced_lead_workflow_fast.py \
    --rapidapi-url "https://app.apollo.io/#/people?..." \
    --rapidapi-max 5000 \
    --apify-industry "marketing & advertising" \
    --apify-job-titles "CEO,Founder,Owner" \
    --apify-max 2000 \
    --validation-keywords "Marketing,Advertising,CEO" \
    --sheet-title "PPC Agency Leads - DC Metro"
  ```

## API Requirements

### Environment Variables (.env)
```
# Apify
APIFY_API_KEY=apify_api_...

# RapidAPI (Apollo Data Source)
x-rapidapi-key=...
x-rapidapi-host=apollo-scraper-up-to-50k-leads.p.rapidapi.com

# Lead Magic
LeadMagic-X-API-Key=...

# Apollo Cookie (JSON array format)
APOLLO_COOKIE=[{...}]
```

### API Rate Limits & Costs

#### Lead Magic
- **Rate Limit**: 1000 requests/minute (some docs say 400, use conservative 400 for enrichment)
- **Email Verification**: Cheap (~0.1 credits per verification)
- **Email Finder**: Expensive (1 credit per lookup)
- **Recommendation**: Always verify all emails, be selective with enrichment

#### RapidAPI (Apollo Data)
- **Rate Limit**: Unknown (monitor for 429 errors)
- **Cost**: Per RapidAPI subscription tier

#### Apify
- **Rate Limit**: Based on Apify account
- **Cost**: Based on compute units

## Output Files

### Temporary Files (.tmp/)
```
.tmp/
├── apollo_run/
│   └── apollo_leads_YYYYMMDD_HHMMSS_XXXXleads.json
├── apify_run/
│   └── apify_leads_YYYYMMDD_HHMMSS_XXXXleads.json
├── merged/
│   └── merged_leads_YYYYMMDD_HHMMSS_XXXXleads.json
├── verified/
│   └── verified_leads_YYYYMMDD_HHMMSS_XXXXleads.json
├── enriched/
│   └── enriched_leads_YYYYMMDD_HHMMSS_XXXXleads.json
└── quality_report_YYYYMMDD_HHMMSS.txt
```

### Deliverable
- **Google Sheet**: Cloud-based, shareable spreadsheet with all leads
- Contains columns matching standardized schema
- Automatically formatted with headers

## Quality Metrics

The workflow generates a quality report with:
- Lead acquisition counts (RapidAPI, Apify)
- Validation pass rate
- Deduplication statistics
- Email verification breakdown (valid, invalid, risky, missing)
- Email enrichment success rate
- Final deliverable count
- Source attribution (RapidAPI only, Apify only, both)

## Edge Cases & Learnings

### Filter Compliance
**Issue**: Previous runs prioritized hitting lead count over filter compliance.
- Example: Requested "Washington DC" leads but got leads from all over US to hit 5k target

**Solution**:
- Always prioritize filter accuracy over quantity
- Accept lower lead counts if filters are restrictive
- Log warnings when requested count isn't met
- Document actual vs. requested counts in output

### Apollo Cookie Expiration
**Symptom**: RapidAPI scraper returns 0 leads or authentication errors
**Solution**:
1. Log into Apollo.io in browser
2. Export cookies using browser extension (e.g., EditThisCookie)
3. Update APOLLO_COOKIE in .env
4. Rerun workflow

### Lead Magic Rate Limits
**Symptom**: HTTP 429 errors during verification/enrichment
**Solution**:
- Scripts automatically wait 60s and retry
- Use conservative rate limiting (0.15s between requests for enrichment)
- Monitor API credits using Lead Magic dashboard

### Deduplication Strategy
**Primary Key**: Email (case-insensitive)
- Most reliable, handles ~90% of duplicates

**Fallback Key**: Name + Company
- For leads without emails
- Case-insensitive matching
- Handles ~9% of duplicates

**Edge Case**: Leads with no email AND insufficient name/company data
- Kept in output with warning
- Assigned unique temporary key

### Email Verification vs. Enrichment
**When to skip enrichment**:
- Budget constraints (enrichment is expensive)
- High existing email coverage (>85% valid emails)
- Testing/development runs

**When to run enrichment**:
- Low email coverage (<70%)
- High-value lead lists (C-suite targets)
- Production runs where completeness matters

## Example Commands

### Full Workflow (RapidAPI + Apify)
```bash
  python execution/enhanced_lead_workflow_fast.py \
    --rapidapi-url "https://app.apollo.io/#/people?page=1&contactEmailStatusV2[]=verified&personTitles[]=ceo" \
    --rapidapi-max 5000 \
    --apify-industry "marketing & advertising" \
    --apify-job-titles "CEO,Founder,Owner" \
    --apify-seniority "C-Level,Owner" \
    --apify-location "United States" \
    --apify-city "Washington" \
    --apify-max 2000 \
    --validation-keywords "Marketing,CEO,Founder" \
    --sheet-title "Marketing Decision Makers - DC Metro"
```

### RapidAPI Only (Skip Apify)
```bash
python execution/enhanced_lead_workflow_fast.py \
  --rapidapi-url "https://app.apollo.io/#/people?..." \
  --rapidapi-max 5000 \
  --skip-apify \
  --sheet-title "RapidAPI Leads Only"
```

### Skip Enrichment (Save Credits)
```bash
python execution/enhanced_lead_workflow_fast.py \
  --rapidapi-url "https://app.apollo.io/#/people?..." \
  --rapidapi-max 5000 \
  --apify-industry "technology" \
  --apify-max 2000 \
  --skip-enrichment
```

## Troubleshooting

### "No leads returned from RapidAPI"
1. Check RapidAPI URL is valid
2. Verify APOLLO_COOKIE hasn't expired
3. Check filters aren't too restrictive
4. Try the URL directly in browser

### "No leads returned from Apify"
1. Check APIFY_API_KEY is valid
2. Verify Apify account has credits
3. Check filters aren't too restrictive

### "Validation Failed"
1. Check your validation keywords
2. Verify the scraped leads actually match your criteria
3. Adjust threshold if needed (`--validation-threshold 0.7`)

### "Merge failed"
1. Ensure at least one scraper succeeded
2. Check JSON files aren't corrupted
3. Verify file paths are accessible

### "Email verification taking too long"
- Normal for large datasets (5000 leads ≈ 5 minutes)
- Script shows progress every 100 emails
- Can interrupt and resume if needed

### "Email enrichment very expensive"
- Expected: 1 credit per email lookup
- Use `--skip-enrichment` flag for testing
- Monitor Lead Magic credits dashboard

## Self-Annealing Notes

### Lessons Learned
1. **Filter Priority**: Users want accurate targeting over high volume
2. **Cookie Management**: Apollo cookies expire, need refresh workflow
3. **Rate Limiting**: Conservative delays prevent API errors
4. **Cost Management**: Email enrichment costs add up quickly
5. **Schema Standardization**: Consistent output enables downstream processing
6. **Validation**: Early validation prevents wasting credits on bad leads

### Future Improvements
- [ ] Add resume capability for interrupted workflows
- [ ] Implement batch email verification (if API supports)
- [ ] Add CRM export options (HubSpot, Salesforce)
- [ ] Create filter validation before scraping
- [ ] Add cost estimation before enrichment
- [ ] Implement cookie auto-refresh mechanism

## Summary

This workflow combines RapidAPI (Apollo data) and Apify lead sources, validates quality early, deduplicates intelligently, verifies all emails, enriches missing emails, and delivers clean data via Google Sheets. Filter accuracy is prioritized over lead quantity to ensure targeting precision.

**Key Principle**: Quality over quantity. A smaller list of accurate, verified leads is more valuable than a large list of mismatched contacts.

# Enhanced Multi-Source Lead Generation V2

## Goal
Generate high-quality B2B leads from multiple sources (RapidAPI + Apify) with **simplified user inputs**, intelligent auto-optimization, and cost-aware enrichment.

## Major Changes in V2

### Simplified User Inputs
**User provides only 2 inputs:**
1. **Apollo URL** - Contains all filters (titles, locations, industries, etc.)
2. **Target Lead Count** - Number of leads desired (e.g., 2000)

**System automatically:**
- Parses Apollo URL to extract filters
- Derives Apify filters with intelligent broadening
- Validates both scrapers before full run
- Optimizes Apify filters if validation fails
- Manages enrichment costs

### Intelligent Pre-Validation
- **RapidAPI Test**: 25 leads → validate → auto-troubleshoot (3 attempts)
- **Apify Test**: 25 leads → validate → auto-optimize filters (up to 5 attempts)
- **Gate**: Both scrapers must succeed before full run

### Smart Lead Count Strategy
- Each scraper targets the **full lead count** specified by user
- Example: User wants 2000 leads → RapidAPI scrapes 2000 + Apify scrapes 2000
- After deduplication, final count may be >2000 → **This is good!**
- More leads after dedup = better outcome

### Cost-Aware Enrichment
- **<500 leads** needing enrichment → Auto-run (no prompt)
- **≥500 leads** needing enrichment → Ask user first (show cost estimate)

---

## Workflow Overview

```
1. Parse Apollo URL → Extract filters → Derive Apify filters
2. Pre-Validation (25 leads from each source)
   2.1. RapidAPI: Test + validate → auto-troubleshoot if fails
   2.2. Apify: Test + validate → auto-optimize if <80% match
   2.3. Gate: Both must succeed (or offer single-source option)
3. Full Scrape (both target user's lead count in parallel)
4. Merge & Deduplicate
5. Email Verification (all emails)
6. Email Enrichment (cost gate: <500 auto, ≥500 ask)
7. Export to Google Sheets
8. Quality Report
```

---

## Inputs

### Required
- **`--apollo-url`**: Full Apollo.io search URL with filters
  - Example: `https://app.apollo.io/#/people?page=1&contactEmailStatusV2[]=verified&personTitles[]=ceo&personLocations[]=United%20States`
  - Filters baked into URL: titles, locations, seniority, industries, company size, etc.
- **`--target-leads`**: Target lead count (e.g., 2000)
  - Both scrapers will target this count
  - Final count after deduplication may be higher

### Optional
- **`--skip-enrichment`**: Skip email enrichment entirely
- **`--force-enrichment`**: Force enrichment even for >500 leads (no prompt)
- **`--sheet-title`**: Custom Google Sheet title
- **`--validation-threshold`**: Validation threshold (default: 0.8 / 80%)

---

## Filter Derivation Logic

### How Apollo Filters Map to Apify

**Principle**: Apify filters should be **broader** than Apollo to capture similar leads.

| Apollo Filter | Apify Mapping | Broadening Strategy |
|--------------|---------------|---------------------|
| **Job Titles** | `job_titles` + `seniority` | Keep titles, add derived seniority levels |
| **"CEO"** | `job_titles: "CEO"` + `seniority: "C-Level,Owner"` | Add related seniority |
| **Locations** | `location` (country/state) + `city` | Extract country/state, separate city |
| **"Washington DC"** | `location: "United States"` + `city: "Washington"` | Broaden to state level |
| **Seniority** | `seniority` (broadened) | Add adjacent levels |
| **"C-Level"** | `seniority: "C-Level,Owner"` | Include Owner |
| **Industries** | `industry` | Keep text, remove numeric IDs |
| **Company Size** | `company_size` | Keep as-is |
| **Revenue** | `min_revenue`, `max_revenue` | Keep as-is |
| **Funding** | `funding` | Keep as-is |

### Auto-Optimization Strategy

If Apify validation fails (<80% match), system automatically:
1. **Attempt 1**: Use derived filters
2. **Attempt 2**: Remove city filter (keep state/country)
3. **Attempt 3**: Remove specific job titles (keep seniority)
4. **Attempt 4**: Remove company size filter
5. **Attempt 5**: Keep only essential (seniority, location, industry)

System logs each adjustment and retests until ≥80% match achieved.

---

## Standardized Output Schema

All leads normalized to:
```
first_name, last_name, name, organization_phone, linkedin_url,
title, email_status, email, city, country, org_name, website_url, source
```

---

## Execution Tools

### New Tools (V2)
1. **`execution/parse_apollo_filters.py`**
   - Parses Apollo URL query parameters
   - Extracts: titles, locations, seniority, industries, company size, etc.
   - Generates validation keywords

2. **`execution/map_apollo_to_apify_filters.py`**
   - Maps Apollo filters to Apify payload
   - Applies intelligent broadening logic
   - Supports broadening levels (1=default, 2=more broad, 3=very broad)

3. **`execution/error_handler.py`**
   - Parses RapidAPI and Apify errors
   - Returns user-friendly troubleshooting steps
   - Maps error codes to actionable instructions

### Master Orchestrator (V2)
**`execution/enhanced_lead_workflow_v2.py`** (Recommended)
- Simplified inputs: Apollo URL + target lead count
- Auto-derives Apify filters
- Intelligent pre-validation with auto-troubleshooting
- Smart enrichment cost gate
- Example usage:
  ```bash
  python execution/enhanced_lead_workflow_v2.py \
    --apollo-url "https://app.apollo.io/#/people?page=1&contactEmailStatusV2[]=verified&personTitles[]=ceo&personLocations[]=United%20States" \
    --target-leads 2000 \
    --sheet-title "CEO Leads - USA"
  ```

### Legacy Tools (Still Available)
- `execution/run_apollo_scraper_fast.py` - Direct RapidAPI scraping
- `execution/run_apify_scraper_v2.py` - Direct Apify scraping
- `execution/merge_deduplicate_leads.py` - Merge and deduplicate
- `execution/verify_emails_leadmagic_fast.py` - Email verification
- `execution/enrich_emails_leadmagic_fast.py` - Email enrichment
- `execution/upload_to_google_sheet.py` - Google Sheets export

---

## API Requirements

### Environment Variables (.env)
```bash
# Apify (Paid Plan - No cost concerns)
APIFY_API_KEY=apify_api_...

# RapidAPI (Monthly 50k leads - Won't exceed)
x-rapidapi-key=...
x-rapidapi-host=apollo-scraper-up-to-50k-leads.p.rapidapi.com

# Lead Magic (Cost concern: enrichment only)
LeadMagic-X-API-Key=...

# Apollo Cookie (JSON array)
APOLLO_COOKIE=[{...}]
```

### API Costs
- **Apify**: Paid plan (no concerns)
- **RapidAPI**: Monthly fee for 50k leads (won't exceed)
- **Lead Magic Verification**: ~$0.001/email (cheap - always run)
- **Lead Magic Enrichment**: ~$0.10/email (expensive - cost gate at 500 leads)

---

## Pre-Validation Logic

### RapidAPI Test (25 leads)
1. Scrape 25 leads using Apollo URL
2. **On success:**
   - Validate against Apollo filters
   - **If <80% match:**
     - Auto-troubleshoot (check API call parameters)
     - Retry up to 3 times
     - After 3 failures → Notify user: "RapidAPI scraper not functional"
3. **On failure:**
   - Parse error response
   - Display user-friendly troubleshooting steps:
     - Cookie expired → "Update APOLLO_COOKIE in .env"
     - Auth error → "Check x-rapidapi-key in .env"
     - Rate limit → "Wait 60s and retry"

### Apify Test (25 leads)
1. Derive Apify payload from Apollo filters
2. Scrape 25 leads
3. Validate against Apollo filters
4. **If <80% match:**
   - Auto-optimize filters (up to 5 attempts)
   - Remove restrictive filters progressively
   - Log each adjustment
   - **DO NOT notify user** - system handles autonomously
5. **If 5 attempts fail:**
   - Proceed with RapidAPI only
   - Log warning: "Could not optimize Apify filters"

### Dual-Scraper Gate
- **Both succeed** → Proceed to full run
- **RapidAPI fails** → Notify user, offer Apify-only option
- **Apify fails** → Proceed with RapidAPI-only (log warning)
- **Both fail** → Abort, display troubleshooting summary

---

## Full Run Execution

### Lead Count Strategy
- User specifies target (e.g., 2000 leads)
- **RapidAPI**: Scrapes 2000 leads
- **Apify**: Scrapes 2000 leads
- **Merge/Dedupe**: Final count determined by uniqueness
  - Example: 2000 + 2000 = 4000 raw → 3247 unique after dedup
  - **More unique leads = better outcome**

### Parallel Scraping
- Both scrapers run simultaneously
- ~2x speed improvement over sequential

---

## Email Enrichment Cost Gate

### Decision Logic
```
leads_needing_enrichment = count(missing or invalid emails)

if leads_needing_enrichment < 500:
    ✅ Auto-run enrichment (no prompt)
elif --force-enrichment flag set:
    ✅ Run enrichment (override)
elif --skip-enrichment flag set:
    ⏭️ Skip enrichment
else:
    💰 Show estimated cost: leads_needing_enrichment × $0.10
    ❓ Prompt user: "Proceed with enrichment? (y/n)"
```

### Examples
- **300 leads** need enrichment → Auto-runs (cost: ~$30)
- **700 leads** need enrichment → Asks user first (cost: ~$70)
- **User sets `--skip-enrichment`** → Skips regardless of count

---

## Output Files

### Temporary Files (.tmp/)
```
.tmp/
├── apollo_run/
│   ├── apollo_leads_YYYYMMDD_HHMMSS_25leads.json (test)
│   └── apollo_leads_YYYYMMDD_HHMMSS_2000leads.json (full)
├── apify_run/
│   ├── apify_leads_YYYYMMDD_HHMMSS_25leads.json (test)
│   └── apify_leads_YYYYMMDD_HHMMSS_2000leads.json (full)
├── merged/
│   └── merged_leads_YYYYMMDD_HHMMSS_3247leads.json
├── verified/
│   └── verified_leads_YYYYMMDD_HHMMSS_3247leads.json
├── enriched/
│   └── enriched_leads_YYYYMMDD_HHMMSS_3247leads.json
└── quality_report_YYYYMMDD_HHMMSS.txt
```

### Deliverable
- **Google Sheet**: Cloud-based, shareable spreadsheet
- Contains all enriched leads in standardized schema

---

## Quality Metrics

Report includes:
- Lead acquisition (RapidAPI, Apify, Total)
- Deduplication (raw → final count, % duplicates)
- Email verification breakdown (valid%, invalid%, risky%, missing%)
- Email enrichment success rate (if run)
- Final deliverable count

---

## Error Handling

### User-Friendly Error Messages

All errors parsed and displayed with:
- **Error type**: authentication, rate_limit, cookie_expired, etc.
- **Clear message**: What went wrong
- **Actionable steps**: Exactly what to do to fix

### Example: Cookie Expired
```
=====================================
ERROR: COOKIE EXPIRED
=====================================

Apollo cookie has expired or is invalid.

TROUBLESHOOTING STEPS:
1. Log into https://app.apollo.io/ in your browser
2. Open browser DevTools (F12)
3. Go to Application > Cookies > apollo.io
4. Export cookies as JSON using EditThisCookie extension
5. Update APOLLO_COOKIE in .env file
6. Re-run the workflow

Note: Apollo cookies expire after ~30 days.
=====================================
```

---

## Example Commands

### Standard Production Run
```bash
python execution/enhanced_lead_workflow_v2.py \
  --apollo-url "https://app.apollo.io/#/people?page=1&contactEmailStatusV2[]=verified&personTitles[]=ceo&personLocations[]=United%20States&organizationNumEmployeesRanges[]=11-50" \
  --target-leads 2000 \
  --sheet-title "CEO Leads - Small Businesses - USA"
```

### Test Run (Skip Enrichment)
```bash
python execution/enhanced_lead_workflow_v2.py \
  --apollo-url "https://app.apollo.io/#/people?..." \
  --target-leads 100 \
  --skip-enrichment \
  --sheet-title "Test Run"
```

### Force Enrichment (Override 500 Threshold)
```bash
python execution/enhanced_lead_workflow_v2.py \
  --apollo-url "https://app.apollo.io/#/people?..." \
  --target-leads 5000 \
  --force-enrichment \
  --sheet-title "High-Value Leads"
```

---

## Troubleshooting

### "RapidAPI scraper not functional"
**After 3 auto-troubleshooting attempts failed**

**Likely causes:**
1. Apollo cookie expired → Update APOLLO_COOKIE in .env
2. RapidAPI key invalid → Check x-rapidapi-key in .env
3. Rate limit exceeded → Wait and retry
4. Service outage → Check RapidAPI status page

### "Apify filters could not be optimized"
**After 5 auto-optimization attempts**

**System response:**
- Proceeds with RapidAPI only
- Logs warning but doesn't abort workflow
- User can manually adjust filters if needed

### "Both scrapers failed"
**Workflow aborts**

**Next steps:**
1. Fix RapidAPI issue → Run with both scrapers
2. Fix Apify issue → Run with both scrapers
3. Fix one issue → Run with single scraper
4. Contact support

---

## Self-Annealing Notes

### Lessons Learned
1. **Simplified UX**: Users shouldn't manually map filters between systems
2. **Auto-Optimization**: System should handle filter tuning autonomously
3. **Cost Awareness**: Enrichment costs can surprise users - gate at 500 leads
4. **Intelligent Errors**: Generic errors frustrate users - provide exact steps
5. **Filter Broadening**: Apify needs broader filters than Apollo for similar results
6. **Lead Count Strategy**: Scraping full count from both sources yields more unique leads after dedup

### Future Improvements
- [ ] Add support for multiple Apollo URLs (batch mode)
- [ ] Implement caching for filter derivation
- [ ] Add webhook notifications for long-running jobs
- [ ] Create web UI for non-technical users
- [ ] Add resume capability for interrupted workflows
- [ ] Implement A/B testing for filter broadening strategies

---

## Summary

**V2 simplifies the workflow to 2 user inputs** (Apollo URL + lead count) while adding:
- Intelligent filter derivation
- Auto-troubleshooting (RapidAPI)
- Auto-optimization (Apify)
- Cost-aware enrichment
- User-friendly error handling

**Key Principle**: System handles complexity autonomously. User provides intent, system executes intelligently.

# Industry Enrichment

## Goal
Add human-readable industry categorization to leads using SIC/NAICS codes or AI website analysis. Provides structured industry data for lead segmentation and targeting.

## Input
- JSON file containing leads
- SIC/NAICS codes in `org_name` object (Olympus leads have ~100% coverage)
- Company websites (all leads)

## Tools
- `execution/ai_industry_enricher.py` - Main enrichment script
- OpenAI or Anthropic API - AI categorization
- `execution/scrape_website_content.py` - Website scraper (for leads without codes)

## Output
- JSON file with added industry fields
- Enrichment statistics (success rate, code vs website ratio, processing time)
- Error log for failed enrichments

## Process

### 1. Load Leads
Load the leads JSON file and validate required fields:
- Each lead should have either `org_name.sic_codes`/`org_name.naics_codes` OR `company_website`
- Skip leads with neither data source

### 2. Filter Leads for Enrichment
Determine which leads need industry categorization:
- Leads missing `industry` field
- Leads with `--force-regenerate` flag enabled
- Skip leads that already have `industry` (unless force regenerate)

### 3. Two-Path Enrichment

**Path A: SIC/NAICS Code Conversion (70% of leads)**

For leads with SIC/NAICS codes in `org_name` object:
1. Extract `sic_codes` and `naics_codes` arrays from `org_name`
2. Send codes to AI with conversion prompt
3. Receive human-readable industry name (2-5 words)
4. Add to lead as `industry` field with `industry_source: "sic_naics"`

**Path B: Website Categorization (30% of leads)**

For leads without codes:
1. Extract `company_website` from lead
2. Scrape website content (homepage, truncate to 2000 chars)
3. Send website content + company name to AI with categorization prompt
4. Receive industry category (2-5 words)
5. Add to lead as `industry` field with `industry_source: "website"`

**Processing:**
- 10 concurrent requests max (ThreadPoolExecutor)
- Rate limiting: 50 req/sec for OpenAI, 5 req/sec for Anthropic
- Retry logic: 3 attempts with exponential backoff (5s, 10s, 20s)
- Timeout: 30 seconds per request

**AI Prompt for SIC/NAICS Conversion:**
```
You are categorizing companies based on their industry classification codes.

SIC Codes: {sic_codes}
NAICS Codes: {naics_codes}

Based on these industry codes, provide a single, human-readable industry category name.
Use 2-5 words maximum. Be specific but concise.

Examples:
- SIC 8712, NAICS 54131 → "Architectural Services"
- SIC 5091, NAICS 42312 → "Furniture Wholesale"
- SIC 7372, NAICS 51121 → "Software Development"

Return ONLY the industry name, nothing else.
```

**AI Prompt for Website Categorization:**
```
You are categorizing a company's primary industry based on their website.

Company Name: {company_name}
Website Content: {website_content[:2000]}

Categorize this company's PRIMARY industry in 2-5 words.
Be specific and professional. Focus on their main business activity.

Examples:
- "Digital Marketing Agency"
- "SaaS Software"
- "Construction Services"
- "Financial Consulting"

Return ONLY the industry category, nothing else.
```

### 4. Add Fields to Leads
For each successfully enriched lead:
- Add `industry` field with categorized industry name
- Add `industry_source` field ("sic_naics" or "website")
- Add `industry_generated_by` field (openai/anthropic)
- Add `industry_generated_at` timestamp

For failed enrichments:
- Set `industry` to empty string
- Add `industry_error` field with error type:
  - `no_data`: No SIC/NAICS codes and no website
  - `no_content`: Website scraped but no meaningful content (< 100 chars)
  - `scrape_failed`: Website scraping failed
  - `ai_failed`: AI categorization failed after retries
- Log error details

### 5. Save Results
- Save enriched leads to output directory
- Filename format: `industry_enriched_YYYYMMDD_HHMMSS_Nleads.json`
- Print summary statistics:
  - Total leads processed
  - Successfully enriched count and percentage
  - Source breakdown (SIC/NAICS vs website)
  - Failed enrichment count by error type
  - Processing time and rate (leads/sec)

## Command Examples

**Basic usage (OpenAI, auto-detect codes/websites):**
```bash
py execution/ai_industry_enricher.py --input merged_leads.json
```

**Use Anthropic instead:**
```bash
py execution/ai_industry_enricher.py --input merged_leads.json --ai-provider anthropic
```

**Force regenerate existing industries:**
```bash
py execution/ai_industry_enricher.py --input merged_leads.json --force-regenerate
```

**Custom output directory:**
```bash
py execution/ai_industry_enricher.py --input merged_leads.json --output-dir campaigns/acme_corp/apollo_lists/latvia_20251222
```

## Error Handling

### Path A Errors (SIC/NAICS Conversion)
- **Invalid codes (empty arrays)**: Fallback to Path B (website scraping)
- **AI fails after retries**: Mark as `industry_error: "ai_failed"`
- **Rate limit exceeded**: Wait and retry with exponential backoff

### Path B Errors (Website Categorization)
- **No website URL**: Mark as `industry_error: "no_data"`
- **Website timeout**: Retry with shorter timeout (15s), then fail
- **Connection refused/404/403**: Mark as `industry_error: "scrape_failed"`
- **No meaningful content (< 100 chars)**: Mark as `industry_error: "no_content"`
- **AI categorization fails**: Mark as `industry_error: "ai_failed"`

### Recovery
- Script never crashes due to single lead failure
- Continue processing remaining leads after errors
- Save partial results even if some leads fail
- All errors logged with details

## Cost Estimation

**Path A (SIC/NAICS conversion):**
- OpenAI GPT-4o-mini: ~$0.0001 per lead
- Anthropic Claude Haiku: ~$0.0002 per lead
- 1000 leads @ 70% with codes = $0.07-0.14

**Path B (Website categorization):**
- Website scraping: Free (self-hosted)
- OpenAI GPT-4o-mini: ~$0.0003 per lead (includes website content)
- Anthropic Claude Haiku: ~$0.0005 per lead
- 1000 leads @ 30% without codes = $0.09-0.15

**Total: ~$0.16-0.29 per 1,000 leads**

Actual costs depend on:
- Ratio of Olympus vs CodeCrafter/Peakydev leads
- AI provider chosen
- Retry rate (failed API calls)

## Integration Notes
- Run AFTER merging/deduplication (to work with unified lead list)
- Run BEFORE icebreaker enrichment (industry can inform icebreaker context)
- Run BEFORE Google Sheets export (to include Industry column)
- Compatible with all scraper outputs (Olympus, CodeCrafter, Peakydev)
- Preserves all existing lead fields (only adds new ones)
- SIC/NAICS codes preserved in `org_name` object for Olympus leads

## Workflow Integration

Full workflow with industry enrichment:

```bash
# Step 1: Scrape leads (existing)
py execution/fast_lead_orchestrator.py --client-id acme_corp --campaign-name "Latvia Campaign" --apollo-url "..." --target-leads 1000

# Step 2: Industry enrichment (MANUAL STEP - NEW)
py execution/ai_industry_enricher.py --input .tmp/merged_latvia_leads_20251222.json --output-dir campaigns/acme_corp/apollo_lists/latvia_20251222

# Step 3: Optional AI enrichments (existing)
py execution/enrich_casual_org_names.py --input campaigns/acme_corp/.../industry_enriched_*.json
py execution/ai_icebreaker_generator.py --input .tmp/casual_enriched_*.json

# Step 4: Export to Google Sheets (existing, now includes Industry column)
py execution/google_sheets_exporter.py --input .tmp/icebreaker_enriched_*.json --sheet-title "Acme Corp - Latvia with Industries"
```

**Note:** Industry enrichment is a manual step. It is NOT automatically integrated into the orchestrator. Run it manually between merge and other enrichments.

## Quality Checks

The script validates AI outputs:
- Industry name is not empty
- Industry length is reasonable (2-5 words, 5-50 characters)
- Industry doesn't contain placeholder text (e.g., "[Industry]", "N/A", "Unknown")
- Industry is not overly generic (reject "Business", "Company", "Services" alone)
- Source field correctly indicates "sic_naics" or "website"

If validation fails:
- Log warning
- Accept result anyway (AI may have good reason for edge cases)
- User can filter/clean in post-processing

Expected quality distribution:
- ~70% should use SIC/NAICS codes (Olympus leads)
- ~30% should use website categorization (CodeCrafter/Peakydev leads)
- ~85-90% success rate overall
- ~10-15% failure rate (no data, scrape failures, AI failures)

## Testing

### Unit Test (10 leads)
Before running on full dataset, test with small sample:

```bash
# Create test file with 10 leads (5 with codes, 5 without)
# Use Python to extract first 10 leads from merged file

py execution/ai_industry_enricher.py --input test_10leads.json --output-dir .tmp/test
```

**Validate output:**
- All 10 leads processed
- Leads with SIC/NAICS codes have `industry_source: "sic_naics"`
- Leads without codes have `industry_source: "website"` (or error)
- Industry names are human-readable (not codes)
- No empty industry names (except for leads with errors)
- Reasonable categorizations (spot check 3-5 manually)
- Processing time < 30 seconds for 10 leads

### Integration Test (100 leads)
After unit test passes:

```bash
# Extract 100-lead subset
py execution/ai_industry_enricher.py --input test_100leads.json --output-dir .tmp/test
```

**Validate:**
- Both paths work correctly (codes and website)
- Success rate ~85-90%
- Cost ~$0.02 (verify against budget)
- Export to Google Sheets includes Industry column
- Industry column has meaningful data

### Full Campaign Test
After integration test passes:

```bash
# Run on full Latvia campaign (8,741 leads)
py execution/ai_industry_enricher.py --input .tmp/merged_latvia_leads_20251222.json --output-dir campaigns/acme_corp/apollo_lists/latvia_medium-large_companies_20251222
```

**Expected results:**
- Total cost: ~$1.40-2.50
- Total time: ~10-15 minutes
- Success rate: ~85-90%
- ~70% from SIC/NAICS codes
- ~15-20% from website categorization
- ~10-15% failures (acceptable)

## Edge Cases

### Missing SIC/NAICS in Olympus Leads
Some Olympus leads may have empty `sic_codes` and `naics_codes` arrays:
- Fallback to Path B (website scraping)
- Log as warning (unexpected for Olympus)
- Should be rare (< 5% of Olympus leads)

### Website Redirects
If website redirects to different domain:
- Scraper follows redirects (up to 3 hops)
- Scrape final destination
- Log redirect chain for reference (if needed)

### Dynamic Websites (JavaScript-heavy)
If website requires JavaScript to load content:
- Basic scraper may fail to extract content
- Mark as `no_content` or `scrape_failed`
- Consider adding Playwright/Selenium for future enhancement
- Expected failure rate: ~5-10% of website scrapes

### Non-English Websites
If website is in non-English language:
- Scraper extracts content as-is
- AI attempts categorization (works reasonably well for major languages)
- May result in less specific categorizations
- Consider adding translation step in future for better accuracy

### Ambiguous Industries
Some companies operate in multiple industries:
- AI prompt instructs to choose PRIMARY industry
- AI makes best judgment based on available data
- User can manually adjust post-export if needed
- This is acceptable - perfect accuracy not critical for lead gen

### Very Generic Categorizations
AI may return generic categories like "Consulting" or "Technology":
- Accept these results (they may be accurate)
- Quality checks warn but don't reject
- User can apply filters in Google Sheets to review generic categories
- Future enhancement: Add industry hierarchy/taxonomy for more specific categories

## Performance Optimization

### Parallel Processing
- Scraping: Up to 10 concurrent requests (ThreadPoolExecutor)
- AI generation: Rate-limited concurrent requests (50/sec OpenAI, 5/sec Anthropic)
- Total time for 1,000 leads: ~2-3 minutes (mostly API wait time)
- Total time for 10,000 leads: ~15-20 minutes

### Caching (Not Implemented Yet)
Future enhancement ideas:
- Cache SIC/NAICS code → industry mappings (reduce API calls)
- Cache domain → industry mappings (for duplicate companies)
- Save cache to JSON file for reuse across campaigns

### Batch Processing
For very large lead lists (10,000+):
- Script handles automatically with concurrent processing
- No need to split manually
- Monitor memory usage (JSON loading may be slow for 50k+ leads)

## Limitations

1. **SIC/NAICS codes only in Olympus leads**: CodeCrafter and Peakydev don't provide codes
2. **Website scraping may fail**: ~10-15% failure rate expected for dynamic sites, blocked scrapers, etc.
3. **AI categorization is probabilistic**: May occasionally mis-categorize or be overly generic
4. **No human review**: Categorizations are automatic, user reviews post-export
5. **Manual execution**: Not integrated into orchestrator, must run separately

## Future Enhancements

1. **Add to orchestrator**: Support `--enrich-industry` flag for automatic integration
2. **Industry taxonomy**: Support custom industry hierarchies (ICB, GICS, etc.)
3. **Caching**: Cache code/domain mappings to reduce API costs
4. **Batch API support**: Use batch endpoints for cheaper processing
5. **Translation**: Translate non-English websites before categorization
6. **JavaScript rendering**: Use Playwright for dynamic website scraping
7. **Confidence scores**: Have AI return confidence level with categorization
8. **Multi-industry support**: Allow tagging with secondary industries

## Summary

Industry enrichment adds valuable categorization data to leads with minimal cost and high automation. Two-path approach maximizes coverage: SIC/NAICS codes for Olympus leads (~70%), website scraping for others (~20-25%), acceptable failure rate (~10-15%).

**Key Stats:**
- Cost: ~$0.16-0.29 per 1,000 leads
- Time: ~2-3 minutes per 1,000 leads
- Success rate: ~85-90%
- Google Sheets: Industry column automatically added to exports

**Usage Pattern:**
1. Run after merge/deduplicate
2. Run before other enrichments and export
3. Manual execution (separate script, not in orchestrator)
4. Test with small sample before full run

# LinkedIn Profile Enrichment

## Goal
Enrich leads with detailed LinkedIn profile data using Lead Magic's Profile Search API. Adds work history, education, bio, tenure, and follower data to improve personalization and lead scoring.

## Input
- JSON file containing leads with `linkedin_url` field
- Optional: `--force-regenerate` flag to re-enrich existing profiles

## Tools
- `execution/linkedin_enricher.py` - Lead Magic Profile Search integration

## Output
- JSON file with added LinkedIn profile fields
- Enrichment statistics (success rate, credits consumed, processing time)
- Error log for failed enrichments

## API Reference

### Lead Magic Profile Search
**Endpoint:** `POST https://api.leadmagic.io/v1/people/profile-search`
**Cost:** 1 credit per profile (0 if not found)
**Rate Limit:** 500 requests/minute

**Request:**
```json
{
  "profile_url": "linkedin.com/in/username",
  "extended_response": true
}
```

**Response:**
```json
{
  "profile_url": "linkedin.com/in/johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "professional_title": "VP of Sales at TechCorp",
  "bio": "Experienced sales leader...",
  "company_name": "TechCorp Inc",
  "company_industry": "Technology",
  "company_website": "techcorp.com",
  "location": "San Francisco, CA",
  "country": "United States",
  "total_tenure_years": "12",
  "total_tenure_months": "144",
  "followers_range": "10K-15K",
  "work_experience": [
    {
      "position_title": "VP of Sales",
      "company_name": "TechCorp Inc",
      "employment_period": "Jan 2022 - Present",
      "company_website": "techcorp.com"
    }
  ],
  "education": [
    {
      "institution_name": "Stanford University",
      "degree": "MBA",
      "attendance_period": "2010 - 2012"
    }
  ],
  "certifications": [...],
  "honors": [...],
  "credits_consumed": 1,
  "message": "Profile found."
}
```

## Process

### 1. Load Leads
Load the leads JSON file and validate required fields:
- Each lead must have `linkedin_url` field
- Skip leads with missing or invalid `linkedin_url`

### 2. Filter Leads for Enrichment
Determine which leads need LinkedIn enrichment:
- Leads missing `linkedin_bio` field (indicates not yet enriched)
- Leads with `--force-regenerate` flag enabled
- Skip leads that already have LinkedIn data (unless force regenerate)

### 3. API Enrichment
Process leads through Lead Magic Profile Search API:

**Processing:**
- Concurrent requests (ThreadPoolExecutor, 10 workers)
- Rate limiting: 8 req/second (conservative, limit is 500/min)
- Retry logic: 3 attempts with exponential backoff (5s, 10s, 20s)
- Timeout: 30 seconds per request

**URL Normalization:**
- Strip protocol and www: `http://www.linkedin.com/in/user` → `linkedin.com/in/user`
- Handle both formats: `/in/username` and full URLs

### 4. Add Fields to Leads
For each successfully enriched lead:
```json
{
  "linkedin_bio": "Profile summary/bio text",
  "linkedin_headline": "Professional title from profile",
  "linkedin_company": "Current company from profile",
  "linkedin_industry": "Company industry",
  "linkedin_location": "Location from profile",
  "linkedin_tenure_years": "12",
  "linkedin_followers": "10K-15K",
  "linkedin_experience": [
    {"title": "...", "company": "...", "period": "..."}
  ],
  "linkedin_education": [
    {"school": "...", "degree": "...", "period": "..."}
  ],
  "linkedin_enriched_at": "2026-02-03T10:30:00Z",
  "linkedin_enrichment_credits": 1
}
```

For failed enrichments:
- Set `linkedin_enrichment_error` field with error type:
  - `missing_url`: No linkedin_url field
  - `invalid_url`: URL doesn't contain linkedin.com
  - `not_found`: Profile not found (0 credits charged)
  - `api_error`: API returned error
  - `rate_limited`: Rate limit exceeded after retries
- Log error details

### 5. Save Results
- Save enriched leads to output directory
- Filename format: `linkedin_enriched_YYYYMMDD_HHMMSS_Nleads.json`
- Print summary statistics:
  - Total leads processed
  - Successfully enriched count and percentage
  - Not found count (profiles that don't exist)
  - Failed count by error type
  - Total credits consumed
  - Processing time and rate (leads/sec)

## Command Examples

**Basic usage:**
```bash
py execution/linkedin_enricher.py --input leads.json
```

**Custom output directory:**
```bash
py execution/linkedin_enricher.py --input leads.json --output-dir campaigns/client/apollo_lists/campaign_name
```

**Force regenerate existing LinkedIn data:**
```bash
py execution/linkedin_enricher.py --input leads.json --force-regenerate
```

**Test with small batch:**
```bash
py execution/linkedin_enricher.py --input leads.json --limit 10
```

## Error Handling

### API Errors
- **Rate limit exceeded (429)**: Wait 60 seconds and retry
- **Invalid API key**: Fail immediately with clear error message
- **Timeout**: Retry up to 3 times, then mark as failed
- **Profile not found**: Mark as `not_found`, no retry needed (0 credits)

### Data Errors
- **Missing linkedin_url**: Skip lead, log warning
- **Invalid URL format**: Skip lead, log warning
- **Non-LinkedIn URL**: Skip lead, log warning

### Recovery
- Script never crashes due to single lead failure
- Continue processing remaining leads after errors
- Save partial results even if some leads fail
- Progress saved every 100 leads

## Cost Estimation
- 1 credit per successfully found profile
- 0 credits for profiles not found
- Expected hit rate: ~80-90% (some profiles may be private/deleted)
- 1000 leads ≈ 800-900 credits

## Integration Notes

### Workflow Position
Run LinkedIn enrichment:
1. **After** email verification (have clean lead list)
2. **Before** icebreaker generation (bio improves personalization)
3. **Before** Google Sheets export (include LinkedIn data)

### Enhanced Icebreaker Generation
When `linkedin_bio` is available, icebreaker prompts can use:
- Professional background from bio
- Career trajectory from work_experience
- Education for rapport building
- Industry expertise signals

### Lead Scoring
LinkedIn data enables scoring:
- `linkedin_tenure_years` > 10 = senior leader
- `linkedin_followers` > 5K = thought leader/influencer
- Recent job change (from work_experience dates) = buying signal

## Workflow Integration

Full workflow with LinkedIn enrichment:

```bash
# Step 1: Scrape leads (existing)
py execution/fast_lead_orchestrator.py --client-id acme_corp --campaign-name "Latvia Campaign" --apollo-url "..." --target-leads 1000

# Step 2: Email verification (existing)
py execution/email_verifier.py --input .tmp/merged_leads.json

# Step 3: LinkedIn enrichment (NEW)
# Output: .tmp/linkedin_enriched/linkedin_enriched_{timestamp}_{N}leads.json
py execution/linkedin_enricher.py --input .tmp/verified_leads.json

# Step 4: Industry enrichment (use latest output from step 3)
py execution/ai_industry_enricher.py --input .tmp/linkedin_enriched/linkedin_enriched_*.json

# Step 5: Icebreaker generation (existing, now with LinkedIn data)
py execution/ai_icebreaker_generator.py --input .tmp/industry_enriched_leads.json

# Step 6: Export to Google Sheets
py execution/google_sheets_exporter.py --input .tmp/icebreaker_enriched_leads.json
```

## Edge Cases

### Private Profiles
- Lead Magic may return partial data or `not_found`
- Mark as `not_found`, move on
- No credits charged for private profiles

### Duplicate LinkedIn URLs
- Deduplicate before enrichment to save credits
- Same person at multiple companies → same LinkedIn URL

### Non-English Profiles
- Lead Magic returns data as-is (original language)
- Bio may be in local language
- Consider translation step if needed for icebreakers

### Very Long Work History
- Some profiles have 20+ positions
- Store all experience, but truncate for display/prompts
- Use most recent 3-5 positions for icebreaker context

### URL Variations
Handle all formats:
- `https://www.linkedin.com/in/username`
- `http://linkedin.com/in/username`
- `linkedin.com/in/username`
- `www.linkedin.com/in/username`

## Testing

### Unit Test (10 leads)
```bash
# Extract 10 leads with LinkedIn URLs
py execution/linkedin_enricher.py --input test_10leads.json --output-dir .tmp/test
```

**Validate:**
- All 10 leads processed
- ~8-9 successfully enriched (80-90% hit rate)
- linkedin_bio and linkedin_experience populated
- Credits tracked correctly
- Processing time < 30 seconds

### Integration Test
After unit test passes, test with 100 leads and verify:
- Rate limiting works correctly
- No API errors
- Cost matches expected (~80-90 credits)
- Data integrates with icebreaker generator

## Performance Optimization

### Concurrent Processing
- 10 concurrent workers (ThreadPoolExecutor)
- Rate limiting at 8 req/sec (conservative)
- Total time for 1000 leads: ~2-3 minutes

### Caching
- Script tracks enriched leads by `linkedin_url`
- Re-running skips already enriched (unless --force-regenerate)
- Saves credits on incremental runs

### Batch Processing
- Large lists handled automatically
- Progress saved every 100 leads
- Resumable if interrupted

## Limitations

1. **Credit cost**: 1 credit per profile adds up for large campaigns
2. **Private profiles**: ~10-20% may not return data
3. **Data freshness**: Lead Magic caches profiles; use `skip_cache: true` for real-time (more expensive)
4. **Manual execution**: Not integrated into orchestrator; run separately

## Future Enhancements

1. **Add to orchestrator**: Support `--enrich-linkedin` flag
2. **Smart enrichment**: Only enrich high-value leads (by title, company size)
3. **Job change alerts**: Use Lead Magic Job Change Detector for trigger-based outreach
4. **Company enrichment**: Cross-reference with Company Search for firmographic data

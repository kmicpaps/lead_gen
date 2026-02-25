# Icebreaker Enrichment

## Goal
Generate personalized icebreaker messages for cold outreach by scraping company websites and using AI to create casual, engaging intros that reference specific details about the prospect's business.

## Input
- JSON file containing leads with `company_website` field
- Optional: User-provided template file for icebreaker style

## Tools
- `execution/scrape_website_content.py` - Website scraper utility
- `execution/ai_icebreaker_generator.py` - AI-powered icebreaker generator

## Output
- JSON file with added `icebreaker` field
- Enrichment statistics (success rate, scraping errors, processing time)
- Error log for failed enrichments

## Process

### 1. Load Leads
Load the leads JSON file and validate required fields:
- Each lead must have `company_website` field
- Skip leads with missing `company_website`

### 2. Filter Leads for Enrichment
Determine which leads need icebreaker generation:
- Leads with valid `company_website`
- Leads missing `icebreaker` field
- Leads with `--force-regenerate` flag enabled
- Skip leads that already have `icebreaker` (unless force regenerate)

### 3. Website Scraping (Step A)
Scrape company websites concurrently to extract relevant content:

**Scraping Strategy:**
- 10 concurrent requests max
- 30-second timeout per website
- Extract main page content (homepage)
- Optionally scrape /about page if available
- Store raw content in lead as `website_content` field

**Content Extraction:**
- Main headline/hero text
- About section
- Services/products listed
- Key value propositions
- Team information (if prominent)
- Max 2000 characters (truncate if longer)

**Error Handling:**
- If scrape fails after 3 attempts: set `icebreaker_error: "scrape_failed"`
- If website times out: try with shorter timeout (15s)
- If website blocks: log and skip (don't retry)
- If no meaningful content extracted: skip icebreaker generation

### 4. AI Icebreaker Generation (Step B)
Generate personalized icebreakers using scraped content:

**Processing:**
- Batch process leads through AI API (10 leads per batch)
- Rate limiting: 50 req/sec for OpenAI, 5 req/sec for Anthropic
- Retry logic: 3 attempts with exponential backoff
- Timeout: 30 seconds per request

**AI Prompt (No Template):**
```
You are writing a personalized cold outreach icebreaker for a B2B prospect.

Lead information:
- Name: {full_name}
- Company: {company_name or casual_org_name}
- Job title: {job_title}
- Website content: {website_content}

Write a 1-2 sentence personalized icebreaker that:
1. References something SPECIFIC from their website (not generic)
2. Shows genuine interest in their business
3. Feels casual and human (not salesy or robotic)
4. Connects to a potential business need or mutual interest
5. Uses natural, conversational language

Examples:
- "Read your LinkedIn about driving digital strategy and noticed Pierce Media's focus on custom results. That blend caught my eye, so I decided to reach out."
- "Hi Thomas! Roman Media Group's focus on local service growth stood out—systems thinking plus digital marketing is a rare combo. Caught my eye, decided to reach out."

Return ONLY the icebreaker text, nothing else. No greetings, no signatures, just the icebreaker.
```

**AI Prompt (With User Template):**
```
You are writing a personalized cold outreach icebreaker for a B2B prospect.

Lead information:
- Name: {full_name}
- Company: {company_name or casual_org_name}
- Job title: {job_title}
- Website content: {website_content}

User template for tone and structure:
{user_template}

Instructions:
1. Use the user template as a guide for tone and structure
2. Fill in personalized details from the website content
3. Reference something SPECIFIC from their website (not generic)
4. Keep it 1-2 sentences
5. Feel casual and human (not salesy or robotic)
6. Match the style of the template while personalizing with their website info

Return ONLY the icebreaker text, nothing else. No greetings, no signatures, just the icebreaker.
```

### 5. Add Fields to Leads
For each successfully enriched lead:
- Add `icebreaker` field with generated text
- Add `icebreaker_generated_by` field (openai/anthropic)
- Add `icebreaker_generated_at` timestamp
- Keep `website_content` field (for reference)

For failed enrichments:
- Set `icebreaker` to empty string
- Add `icebreaker_error` field with error type:
  - `scrape_failed`: Website scraping failed
  - `no_content`: Website scraped but no meaningful content
  - `ai_failed`: AI generation failed
  - `missing_website`: No company_website field
- Log error details to error log file

### 6. Save Results
- Save enriched leads to output directory
- Filename format: `icebreaker_enriched_YYYYMMDD_HHMMSS_Nleads.json`
- Print summary statistics:
  - Total leads processed
  - Successfully scraped count
  - Scraping failures
  - Successfully enriched count and percentage
  - Failed enrichment count
  - Processing time and rate (leads/sec)

## Command Examples

**Basic usage (OpenAI, no template):**
```bash
py execution/ai_icebreaker_generator.py --input leads.json
```

**Use Anthropic instead:**
```bash
py execution/ai_icebreaker_generator.py --input leads.json --ai-provider anthropic
```

**With user template:**
```bash
py execution/ai_icebreaker_generator.py --input leads.json --template my_template.txt
```

**Skip scraping (use existing website_content):**
```bash
py execution/ai_icebreaker_generator.py --input leads.json --skip-scraping
```

**Force regenerate existing icebreakers:**
```bash
py execution/ai_icebreaker_generator.py --input leads.json --force-regenerate
```

**Custom output directory:**
```bash
py execution/ai_icebreaker_generator.py --input leads.json --output-dir .tmp/icebreakers
```

## Error Handling

### Scraping Errors
- **Timeout**: Retry with shorter timeout (15s), then fail
- **Connection refused**: Skip, mark as scrape_failed
- **404/403**: Skip, mark as scrape_failed
- **Redirect loop**: Skip after 3 redirects
- **No content extracted**: Skip, mark as no_content

### AI Errors
- **Rate limit exceeded**: Wait and retry with exponential backoff (5s, 10s, 20s)
- **Invalid API key**: Fail immediately with clear error message
- **Timeout**: Retry up to 3 times, then mark as failed
- **Invalid response**: Log error, set icebreaker to empty string

### Recovery
- Script should never crash due to single lead failure
- Continue processing remaining leads after errors
- Save partial results even if some leads fail
- Generate scraping errors report in `.tmp/scraping_errors.log`

## Cost Estimation
- Website scraping: Free (self-hosted)
- OpenAI GPT-4o-mini: ~$0.0003 per lead (with website content)
- Anthropic Claude Haiku: ~$0.0005 per lead
- 1000 leads ≈ $0.30-0.50

## Integration Notes
- Run after casual name enrichment (to use casual_org_name in prompts)
- Run before Google Sheets export
- Compatible with existing workflow scripts
- Does not modify existing fields (only adds new ones)
- Website content is cached in lead for future reference

## Edge Cases

### Missing Website
If `company_website` is empty or invalid:
- Skip lead
- Set `icebreaker_error: "missing_website"`
- Log warning

### Website Redirects
If website redirects to different domain:
- Follow redirect (up to 3 hops)
- Scrape final destination
- Log redirect chain for reference

### Dynamic Websites (JavaScript-heavy)
If website requires JavaScript:
- Scraper uses `requests-html` to handle basic JS
- If content still not available, mark as no_content
- Consider adding Playwright/Selenium for future enhancement

### Non-English Websites
If website is in non-English language:
- Scraper extracts content as-is
- AI will attempt to generate icebreaker based on content
- May result in less personalized icebreakers
- Consider adding translation step in future

### Very Short Website Content
If website content < 100 characters:
- Mark as no_content
- Skip icebreaker generation
- Log warning

### User Template Conflicts
If user template conflicts with AI instructions:
- AI instructions take precedence
- Template is used as style guide only
- AI may deviate from template if needed for personalization

## Quality Checks
The script should validate AI outputs:
- Icebreaker is not empty
- Icebreaker length between 50-300 characters
- Icebreaker doesn't contain placeholder text (e.g., "[Company Name]")
- Icebreaker mentions company name or specific detail
- Icebreaker feels personalized (not generic)

If validation fails:
- Set icebreaker to empty string with fallback template
- Log validation failure
- Mark as ai_failed

## Testing
Before full run, test with sample data:
```bash
# Test with 5 leads
py execution/ai_icebreaker_generator.py --input sample_5leads.json --output-dir .tmp/test
```

Expected output:
- 5 websites scraped successfully (or errors logged)
- All successful scrapes should have icebreakers
- Icebreakers should reference specific website details
- Processing time < 30 seconds for 5 leads

## User Template Format

If user provides a template file, it should contain example icebreaker(s) showing desired tone and structure:

```
Example 1: Read your [specific detail from website] and noticed [company name]'s focus on [key offering]. That [specific aspect] caught my eye, so I decided to reach out.

Example 2: Hi [name]! [Company name]'s focus on [key value prop] stood out—[specific observation] is a rare combo. Caught my eye, decided to reach out.
```

Template should be plain text file, one or more examples showing desired style.

## Workflow Integration

Full workflow with AI enrichment:

```bash
# Step 1: Scrape leads (existing)
py execution/run_apify_b2b_leads_finder.py --apollo-url "..." --max-leads 1000

# Step 2: Merge & dedup (existing)
py execution/merge_deduplicate_leads.py --source-file b2b_leads.json

# Step 3: Email validation (existing)
py execution/verify_emails_leadmagic_fast.py --input merged_leads.json

# Step 4: Email enrichment (existing)
py execution/enrich_emails_leadmagic_fast.py --input verified_leads.json

# Step 5: Cleanup (existing)
# ... cleanup script ...

# Step 6: AI Enrichment - Casual names (NEW)
py execution/ai_casual_name_generator.py --input cleaned_leads.json

# Step 7: AI Enrichment - Icebreakers (NEW)
py execution/ai_icebreaker_generator.py --input casual_enriched_leads.json

# Step 8: Export to Google Sheets (existing, updated)
py execution/upload_to_google_sheet.py --input icebreaker_enriched_leads.json
```

## Performance Optimization

### Parallel Processing
- Scraping: 10 concurrent requests
- AI generation: 10 concurrent requests
- Total time for 100 leads: ~20-30 seconds (with good internet)

### Caching
- Once website_content is scraped, it's cached in lead
- Re-running with `--skip-scraping` skips scraping step
- Useful for testing different AI providers or templates

### Batch Processing
- Large lead lists (1000+) can be split into batches
- Run multiple enrichment processes in parallel
- Merge results after completion

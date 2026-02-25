# Casual Org Name Enrichment

## Goal
Generate human-friendly, casual versions of formal company names for use in personalized outreach. Transform corporate legal names into the casual names people actually use.

## Input
- JSON file containing leads with `company_name` field
- Optional: `--force-regenerate` flag to regenerate existing casual names

## Tools
- `execution/enrich_casual_org_names.py` - AI-powered casual name generator

## Output
- JSON file with added `casual_org_name` field
- Enrichment statistics (success rate, processing time)
- Error log for failed enrichments

## Process

### 1. Load Leads
Load the leads JSON file and validate required fields:
- Each lead must have `company_name` field
- Skip leads with missing `company_name`

### 2. Filter Leads for Enrichment
Determine which leads need casual name generation:
- Leads missing `casual_org_name` field
- Leads with `--force-regenerate` flag enabled
- Skip leads that already have `casual_org_name` (unless force regenerate)

### 3. AI Generation
Process leads through AI API to generate casual names:
- Use batch processing for efficiency (10 leads per batch)
- Rate limiting: 50 req/sec for OpenAI, 5 req/sec for Anthropic
- Retry logic: 3 attempts with exponential backoff
- Timeout: 30 seconds per request

**AI Prompt:**
```
Given this company name, generate a short, casual, human-friendly version:
Company name: "{company_name}"

Rules:
- Remove legal suffixes (Sp. Z O.o., LLC, Ltd, Inc, GmbH, AB, AS, etc.)
- Remove marketing taglines and slogans
- Extract core brand name
- Keep 1-2 words maximum
- Return ONLY the casual name, nothing else

Examples:
"Tatran Group 3r Reduce, Reuse, Recycle ... In Harmony With The Nature" → "Tatran"
"Pmtech Engineering" → "Pmtech"
"Prefasprzęt Sp. Z O.o." → "Prefasprzęt"
"ABC Marketing Solutions LLC" → "ABC Marketing"
"Digital Growth Agency Inc." → "Digital Growth"
```

### 4. Add Field to Leads
For each successfully enriched lead:
- Add `casual_org_name` field with generated name
- Add `casual_org_name_generated_by` field (openai/anthropic)
- Add `casual_org_name_generated_at` timestamp

For failed enrichments:
- Set `casual_org_name` to empty string
- Add `casual_org_name_error` field with error message
- Log error details to error log file

### 5. Save Results
- Save enriched leads to output directory
- Filename format: `casual_enriched_YYYYMMDD_HHMMSS_Nleads.json`
- Print summary statistics:
  - Total leads processed
  - Successfully enriched count and percentage
  - Failed enrichment count
  - Processing time and rate (leads/sec)

## Command Examples

**Basic usage (OpenAI):**
```bash
py execution/enrich_casual_org_names.py --input leads.json
```

**Use Anthropic instead:**
```bash
py execution/enrich_casual_org_names.py --input leads.json --ai-provider anthropic
```

**Force regenerate existing casual names:**
```bash
py execution/enrich_casual_org_names.py --input leads.json --force-regenerate
```

**Custom output directory:**
```bash
py execution/enrich_casual_org_names.py --input leads.json --output-dir .tmp/ai_enriched
```

## Error Handling

### API Errors
- **Rate limit exceeded**: Wait and retry with exponential backoff (5s, 10s, 20s)
- **Invalid API key**: Fail immediately with clear error message
- **Timeout**: Retry up to 3 times, then mark as failed
- **Invalid response**: Log error, set casual_org_name to empty string

### Data Errors
- **Missing company_name**: Skip lead, log warning
- **Empty company_name**: Skip lead, log warning
- **Non-string company_name**: Convert to string, then process

### Recovery
- Script should never crash due to single lead failure
- Continue processing remaining leads after errors
- Save partial results even if some leads fail

## Cost Estimation
- OpenAI GPT-4o-mini: ~$0.0001 per lead (cheap)
- Anthropic Claude Haiku: ~$0.0002 per lead (cheap)
- 1000 leads ≈ $0.10-0.20

## Integration Notes
- Run after email validation/enrichment
- Run before icebreaker generation
- Compatible with existing workflow scripts
- Does not modify existing fields (only adds new ones)

## Edge Cases

### Very Long Company Names
If `company_name` exceeds 500 characters:
- Truncate to first 200 characters
- Process truncated version
- Log warning

### Special Characters
- AI should handle Unicode characters correctly
- Non-ASCII characters are preserved if they're part of brand name
- Examples: "Müller GmbH" → "Müller", "Łódź Construction" → "Łódź"

### Ambiguous Names
For generic names like "ABC Company" or "Consulting Group LLC":
- AI should extract the distinctive part ("ABC", "Consulting Group")
- If name is too generic (e.g., "Company LLC"), return original minus legal suffix

### Multiple Entities
If company name contains "and" or "&":
- Keep both if they're part of brand (e.g., "Smith & Jones" → "Smith & Jones")
- Remove if it's descriptive (e.g., "Marketing and Consulting LLC" → "Marketing")

## Quality Checks
The script should validate AI outputs:
- Casual name is not empty
- Casual name is shorter than or equal to original
- Casual name doesn't contain legal suffixes
- Casual name is reasonable (not gibberish)

If validation fails:
- Set casual_org_name to company_name with legal suffix removed
- Log validation failure
- Mark as fallback generation

## Testing
Before full run, test with sample data:
```bash
# Test with 10 leads
py execution/enrich_casual_org_names.py --input sample_10leads.json --output-dir .tmp/test
```

Expected output:
- All 10 leads should have casual_org_name field
- Names should be shorter and more casual
- No legal suffixes in casual names
- Processing time < 5 seconds for 10 leads

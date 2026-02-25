# Google Maps Lead Generation Directive

## Overview

This directive provides a complete, self-contained lead generation pipeline that scrapes businesses from Google Maps, enriches them with deep website contact extraction, and saves to Google Sheets with deduplication.

**Use this when:** The user wants location-based lead generation without requiring an Apollo search URL. This is ideal for local businesses, service providers, or any geographic-based prospecting.

## Architecture

### Layer 1: Google Maps Scraping
- **Tool:** `execution/scrape_google_maps.py`
- **API:** Apify's `compass/crawler-google-places` actor
- **Input:** Search query (e.g., "plumbers in Austin TX"), limit
- **Output:** Structured business data (name, address, phone, website, rating, etc.)

### Layer 2: Website Contact Extraction
- **Tool:** `execution/extract_website_contacts.py`
- **Process:**
  1. HTTP fetch main page and convert to markdown
  2. Find and fetch up to 5 contact-related pages (/contact, /about, /team, etc.)
  3. Search DuckDuckGo for owner/contact information
  4. Send all content to Claude 3.5 Haiku for structured extraction
- **Output:** Emails, phones, social media, owner info, team members, business hours

### Layer 3: Pipeline Orchestration
- **Tool:** `execution/gmaps_lead_pipeline.py`
- **Process:**
  1. Scrape businesses from Google Maps
  2. Parallel enrichment with ThreadPoolExecutor (default 3 workers)
  3. Google Sheets authentication (OAuth)
  4. Save with MD5 deduplication (based on name|address)
- **Output:** Google Sheet with 34-column schema

## Output Schema (34 Columns)

```
scraped_at, search_query, business_name, category,
address, city, state, zip_code, country, phone, website,
google_maps_url, rating, review_count, price_level,
emails, additional_phones, business_hours, facebook, twitter,
linkedin, instagram, youtube, tiktok, owner_name, owner_title,
owner_email, owner_phone, owner_linkedin, team_contacts,
additional_contact_methods, pages_scraped, search_enriched,
enrichment_status
```

**Note:** `lead_id` and `place_id` are excluded from the export. Deduplication still works by regenerating lead_ids from business_name and address when reading existing sheets.

## Usage

### Basic Usage
```bash
# Scrape and enrich 10 businesses
python3 execution/gmaps_lead_pipeline.py --search "plumbers in Austin TX" --limit 10

# Append to existing sheet
python3 execution/gmaps_lead_pipeline.py --search "roofers in Austin TX" --limit 50 \
  --sheet-url "https://docs.google.com/spreadsheets/d/..."

# Skip enrichment for quick GMaps-only scraping
python3 execution/gmaps_lead_pipeline.py --search "coffee shops in Seattle" --limit 20 \
  --skip-enrichment

# Adjust parallel workers (default: 3)
python3 execution/gmaps_lead_pipeline.py --search "bakeries in Portland" --limit 30 \
  --workers 5
```

### Individual Tool Usage

```bash
# Just scrape Google Maps
python3 execution/scrape_google_maps.py --search "dentists in Chicago" --limit 10

# Just extract website contacts
python3 execution/extract_website_contacts.py \
  --url "https://example.com" \
  --name "Example Business"
```

## Learnings & Edge Cases

### 1. Google Maps Scraping
- **Country codes must be lowercase** (use "us" not "US") - Apify API requirement
- **Scraper may return different results each run** - Google Maps rankings change
- **Permanently closed businesses are automatically filtered**
- **Cost:** ~$0.01-0.02 per business via Apify

### 2. Website Enrichment
- **~10-15% of sites return 403/503** - These fail gracefully, lead still saved with GMaps data
- **Facebook URLs always return 400** - Automatically skipped in web search results
- **Some sites have broken DNS** - Caught and marked as error in enrichment_status
- **Content is truncated to 50K chars** - Prevents token overflow to Claude
- **DuckDuckGo HTML search is free** - Using html.duckduckgo.com/html/ to avoid API costs
- **Claude extraction cost:** ~$0.002 per lead (Haiku)

### 3. Error Handling
- **Claude sometimes returns dicts for string fields** - Using `stringify_value()` helper
- **Null values in extracted data** - All fields use `data.get(field) or {}` pattern
- **Parallel enrichment can fail individually** - Each lead fails independently, doesn't stop pipeline
- **Enrichment statuses:**
  - `success` - Full enrichment completed
  - `no_website` - Business has no website
  - `error: ...` - Specific error encountered
  - `skipped` - User used --skip-enrichment flag

### 4. Deduplication
- **lead_id = MD5(business_name|address)** - Case-insensitive, whitespace-trimmed (used internally, not exported)
- **Deduplication works across runs** - Existing sheets are scanned, lead_ids regenerated from business_name + address columns
- **Note:** Google Maps may return slightly different businesses or address formatting each run, leading to "false duplicates" being added

### 5. Performance
- **Parallel enrichment speeds up processing** - Default 3 workers, adjustable
- **Each enrichment takes ~10-20 seconds** - Website fetching + Claude extraction
- **Rate limiting:** Built-in 0.5s delay between contact page fetches
- **Total pipeline time:** ~2-5 minutes for 10 leads (depends on website complexity)

## Dependencies

Required packages (in [requirements.txt](../requirements.txt)):
```
httpx>=0.25.0          # Website fetching
html2text>=2020.1.16   # HTML to markdown
anthropic>=0.18.0      # Claude API
apify-client>=1.6.0    # Google Maps scraping
gspread>=5.11.0        # Google Sheets
```

## Environment Variables

Required in [.env](../.env):
```
APIFY_API_KEY=...           # From https://console.apify.com/
ANTHROPIC_API_KEY=...       # From https://console.anthropic.com/
```

Also required:
- `credentials.json` - Google OAuth credentials
- `token.json` - Auto-generated after first OAuth flow

## Cost Breakdown

Per lead:
- Apify (Google Maps): ~$0.01-0.02
- Claude Haiku (extraction): ~$0.002
- Everything else: Free (DuckDuckGo, website fetching)
- **Total: ~$0.015-0.025 per enriched lead**

## Success Criteria

The pipeline is working correctly when:
1. `python3 execution/gmaps_lead_pipeline.py --search "test query" --limit 10` runs without errors
2. 10 leads appear in Google Sheet with populated contact fields
3. All enrichment statuses are `success` or explainable errors (403/503/no_website)
4. Running same command with --sheet-url appends new leads and shows duplicate count

## Troubleshooting

### "APIFY_API_KEY not found"
- Ensure `.env` file exists with valid APIFY_API_KEY

### "credentials.json not found"
- Download Google OAuth credentials from Google Cloud Console
- Place in project root as `credentials.json`

### "Country code must be lowercase"
- This is fixed in the current version (default: "us")
- If manually specifying, use lowercase: --country us

### Enrichment errors
- Check enrichment_status column in sheet for specific errors
- 403/503 errors are normal for ~10-15% of sites
- Use --skip-enrichment flag to only get GMaps data

### High Apify costs
- Limit your --limit parameter appropriately
- Apify charges per request, not per result

## Future Improvements

Potential enhancements:
1. Add email verification integration (LeadMagic)
2. Support batch processing from CSV input
3. Add configurable contact page patterns
4. Implement retry logic for failed enrichments
5. Add progress bar for long-running jobs
6. Support multiple search queries in one run
7. Add filtering by rating/review count

## Niche-by-Niche Scraper (No-Website Filter)

For targeting businesses **without websites** across multiple niches, use the interactive niche scraper.

### Tool
- **Script:** `execution/gmaps_niche_scraper.py`
- **Use case:** Find local businesses that need a website (web design leads, digital marketing prospects)

### Features
- Interactive prompts for each niche
- Filters to only businesses WITHOUT a website
- Saves each niche to a separate tab in Google Sheets
- Deduplication within and across niches
- Simplified output schema (no enrichment columns)

### Usage

```bash
# Interactive mode - prompts for each niche
python execution/gmaps_niche_scraper.py --location "Riga Latvia" --limit 50 --no-website

# With existing sheet
python execution/gmaps_niche_scraper.py --location "Riga Latvia" --limit 50 --no-website \
  --sheet-url "https://docs.google.com/spreadsheets/d/..."
```

### Interactive Flow
1. Run the command
2. Script creates a new Google Sheet (or opens existing)
3. Prompt: `Enter niche to scrape (or 'done'):`
4. Enter a niche (e.g., "restaurants", "plumbers", "dentists")
5. Script scrapes, filters no-website, saves to niche-named tab
6. Repeat for more niches
7. Type `done` to finish

### Output Schema (10 Columns)
```
scraped_at, niche, business_name, category, address, city,
phone, google_maps_url, rating, review_count
```

### Arguments
| Argument | Default | Description |
|----------|---------|-------------|
| `--location` | (required) | Location to search (e.g., "Riga Latvia") |
| `--limit` | 50 | Max results per niche |
| `--country` | lv | Country code (lowercase) |
| `--no-website` | false | Only keep businesses without websites |
| `--sheet-url` | (none) | Append to existing sheet |

### Cost
- Apify: ~$0.02 per business scraped
- No Claude costs (no enrichment)
- Example: 4 niches × 50 limit = ~$4

### Tips
- Request higher `--limit` than needed since filtering removes businesses with websites
- Expect ~30-50% of businesses to have no website (varies by niche)
- "restaurants" and "retail" tend to have more websites
- "plumbers", "electricians", "cleaning services" often have fewer

---

## Integration with Existing System

This system is **completely separate** from the existing Apollo-based lead generation:
- Uses different scrapers (Apify Google Maps vs RapidAPI Apollo)
- Uses different enrichment (website scraping vs Apollo data)
- Can be used in parallel without conflicts
- Shared infrastructure: Google Sheets exporter, .env file

**When to use GMaps vs Apollo:**
- **Use GMaps:** Location-based prospecting, local businesses, service providers
- **Use Apollo:** B2B prospecting, specific job titles, company-based targeting

**When to use Niche Scraper vs Standard Pipeline:**
- **Use Niche Scraper:** Targeting businesses without websites, multiple niche categories
- **Use Standard Pipeline:** Full enrichment with website contact extraction

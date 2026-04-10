# Google Maps Lead Scraping

## Objective

Scrape local businesses from Google Maps, split into cold calling and cold email streams, optionally score websites with PageSpeed, and export to Google Sheets.

## When to Use

- Targeting **local service businesses** (plumbers, lawyers, salons, restaurants) that aren't on Apollo
- Building **cold calling lists** (GMaps has phone numbers Apollo often lacks)
- **Website-based offers** (web design, SEO, marketing) -- PageSpeed scoring identifies businesses with bad websites
- Finding businesses **without websites** -- for website creation offers

## What You Get

- **Business-level contacts**: company phone, generic emails (info@company.com), address, website, Google rating
- **NOT personal contacts**: no employee names, personal emails, or LinkedIn profiles (use Apollo pipeline for those)

## Execution Scripts

| Script | Purpose | Type |
|--------|---------|------|
| `execution/scrape_gmaps_contact.py` | Scrape businesses from Google Maps via Apify | CLI |
| `execution/gmaps_dedup.py` | Deduplicate by place_id + name\|address hash | CLI |
| `execution/gmaps_website_enricher.py` | Batch website contact extraction (finds extra emails) | CLI |
| `execution/lead_splitter.py` | Split into cold_calling / cold_email / no_contact | CLI |
| `execution/website_evaluator.py` | PageSpeed Insights scoring + CMS detection | CLI |
| `execution/extract_website_contacts.py` | Single-URL contact extraction (used by enricher) | CLI |
| `execution/gmaps_sheets_exporter.py` | Export to 3-tab Google Sheet (auto-creates if needed) | CLI |

## Process Flow

### Step 1: Keyword Discovery

Users describe businesses in plain language. The AI agent must find search terms that return results.

**Why this matters:** Google Maps categorizes businesses using the country's primary language. English terms often return 0 results in non-English countries.

**Auto-derive country code from location:** The user only provides a location (city/region/country). The AI must derive the 2-letter ISO country code itself. Examples: "Latvia"/"Riga" -> `lv`, "Auckland"/"NZ" -> `nz`, "Berlin"/"Germany" -> `de`, "Warsaw" -> `pl`. Do not ask the user for the country code.

**Process:**
1. Derive country code from location
2. For each business type, generate 3-5 candidate search terms:
   - Local language version (e.g. Latvian for Latvia)
   - English version
   - Common synonyms
3. Test each candidate:
   ```
   py execution/scrape_gmaps_contact.py --search "TERM" --limit 10 --country COUNTRY_CODE
   ```
   Cost: ~$0.09 per term. Check output count.
4. Pick the best term per niche (most results). Drop terms with 0 results.
5. Show user the results with counts, get confirmation before full scrape.

**Validated terms reference:**

| Country | Niche | Working term | Results | Bad terms |
|---------|-------|-------------|---------|-----------|
| Latvia | Lawyers | juristi | 300+ | advokats (0) |
| Latvia | Hairdressers | frizieris | 280+ | frizetavas (0) |
| Latvia | Beauty | skaistumkopsana | 387 | |
| Latvia | Construction | buvnieciba | 200+ | construction company (0) |
| Latvia | Hotels | viesnicas | 273 | |
| Latvia | Real estate | nekustamie | 286 | |
| Latvia | Shops/retail | veikali | 302 | |
| Latvia | Plumbers | santehnikis | 10+ | |
| Latvia | Plumbers (EN) | plumber | 10+ | Different businesses than santehnikis |
| Latvia | Auto repair | auto repair | 150+ | English works |
| Latvia | Dentists | zobārsts | 100+ | English also works |

**Update this table** after each successful campaign with new validated terms.

### Step 2: Scrape

Run the scraper for each confirmed niche:
```
py execution/scrape_gmaps_contact.py --search "TERM" --limit 500 --country lv --language en
```

Save each niche's output, then combine into one file. Tag each lead with its niche label.

**Key flags:**
- `--limit`: max results per niche (default 500, GMaps caps at ~120 per query)
- `--country`: 2-letter country code (default `lv`)
- `--language`: search language (default `en`)
- `--dump-raw`: save first raw Apify result for debugging

**Cost:** ~$9 per 1,000 leads via Apify.

### Step 3: Deduplicate

```
py execution/gmaps_dedup.py --input .tmp/gmaps/combined.json --output .tmp/gmaps/deduped.json
```

Dedup strategy:
1. Primary: by `place_id` (Apify's unique identifier)
2. Fallback: MD5 hash of `business_name|address` (case-insensitive)

### Step 4: Website Enrichment (Recommended)

GMaps often returns businesses with a website but no scraped email. Website enrichment scrapes each business's website + contact pages and uses Claude Haiku to extract additional emails, owner info, and phone numbers.

```
py execution/gmaps_website_enricher.py --input .tmp/gmaps/deduped.json --output .tmp/gmaps/enriched.json --workers 5
```

**Why run this BEFORE split:** Many phone-only leads have websites that yield emails. Running enrichment first means those leads get reclassified to cold_email instead of cold_calling.

**What it adds:**
- Additional emails (multiple per business when available)
- Owner names + titles
- Phone numbers (if missing)
- Social media links (if missing)

**Cost:** ~$0.002 per lead (Claude Haiku). For 500 leads: ~$1.
**Time:** ~5-15 sec per lead with website (5 parallel workers). For 500 leads: ~10-15 min.

### Step 5: Split

```
py execution/lead_splitter.py --input .tmp/gmaps/enriched.json --output-dir .tmp/gmaps/
```

| Stream | Criteria | Use |
|--------|----------|-----|
| cold_calling | Has phone, no email | Phone outreach |
| cold_email | Has email | Email outreach (evaluate websites) |
| no_contact | No phone, no email | Discard |

### Step 6: Score Websites (Optional)

Only run if user wants website scoring (e.g. for web design/SEO offers).

```
py execution/website_evaluator.py --input .tmp/gmaps/cold_email.json --output .tmp/gmaps/cold_email_scored.json --workers 5
```

Scores (mobile strategy): Performance 35%, Mobile 20%, SSL 15%, SEO 15%, Best Practices 15%.

Generates 3 template-based insight bullets per site (no AI cost):
- Slow loading: "Your site loads in {X}s on mobile"
- No SSL: "No HTTPS -- Google penalizes this"
- Not mobile-friendly: "Not optimized for mobile"
- Poor SEO: "Basic SEO fixes could help"

**Cost:** Free (Google PageSpeed API). **Time:** ~30-40 min for 150 sites with 5 workers.

### Step 7: Export to Google Sheets

```
py execution/gmaps_sheets_exporter.py \
    --cold-calling .tmp/gmaps/cold_calling.json \
    --cold-email .tmp/gmaps/cold_email.json \
    --all-leads .tmp/gmaps/deduped.json \
    --niches juristi frizieris \
    --total-scraped 500
```

Auto-creates a new Google Sheet if no `--sheet-url` is provided.

**Output tabs:**
- **cold_calling**: niche, business_name, category, address, city, phone, google_maps_url, rating, review_count
- **cold_email_scored**: above + website, emails, socials, scores, insights
- **summary**: totals, avg scores, CMS breakdown, per-niche counts
- **email_{niche}**: per-niche email tabs

## Cost Summary

| Component | Cost | Notes |
|-----------|------|-------|
| Keyword testing | ~$0.09/term | 10 leads per term |
| Scraping | ~$9/1K leads | Apify |
| Website enrichment | ~$2/1K leads | Claude Haiku (recommended) |
| PageSpeed | Free | Google API |
| **Typical run** | **~$6-12** | 2-3 niches x 500 leads + enrichment |

## Critical Rules

1. **NEVER substitute the user's requested business types** -- discover the right terms, but the user decides what businesses they want
2. **Always test terms before production runs** -- $0.09 to test vs $4.50 wasted on a bad term
3. **Local language terms usually outperform English** for non-English countries
4. **Update the validated terms table** after each successful campaign

## Error Handling

- **0 results on term test**: Try local language version, broader category, singular/plural variants
- **Apify timeout**: Actor has 600s timeout. If hit, reduce --limit
- **PageSpeed 429 (quota)**: Reduce --workers to 1. OAuth token has higher limits than unauthenticated
- **PageSpeed 403**: Delete token.json and re-auth (will prompt browser)

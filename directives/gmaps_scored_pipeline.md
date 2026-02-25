# techstart Latvia GMaps Pipeline

## Objective

Scrape local businesses from Google Maps (Latvia-wide), split into cold calling vs cold email streams, evaluate websites with PageSpeed Insights, and export scored leads to Google Sheets.

**Client:** techstart — website build offer targeting small Latvia businesses without websites or with poor-performing sites.

## Critical Rules

### 1. Niches come from the user — NEVER substitute or invent search terms
The `--niches` flag is **required**. There are no defaults. The AI agent must use exactly the niches the user requested. If the user says "juristi, frizieris, būvnieki" then those are the niches — do not swap in "auto repair" or "construction company" or any other term.

### 2. Always pre-test search terms before production runs
The pipeline runs an automatic pre-test (10 leads per term) before committing budget. If any term returns 0 results, the pipeline **aborts** with an error message suggesting alternative terms. This prevents wasting Apify credits on bad search terms.

To skip pre-testing (only if terms were already manually verified):
```
--no-pre-test
```

### 3. Search terms must match Google Maps categories for the target country
Not every word works as a Google Maps search term. Some terms return 0 results because they don't match how Google categorizes businesses.

**Validated Latvia search terms:**
| Niche | Working term | Category matches | Notes |
|-------|-------------|-----------------|-------|
| Lawyers | `juristi` | Attorney, Law firm, Legal services | Latvian term |
| Hairdressers | `frizieris` | Hairdresser, Beauty salon, Hair salon | Latvian term; `frizētavas` does NOT work |
| Construction | `būvniecība` | Construction company, Custom home builder | Latvian term; English `construction company` returns 0 |
| Auto repair | `auto repair` | Auto repair shop, Car repair | English works |
| Beauty salons | `beauty salon` | Beauty salon | English works |

**When adding new terms:** Always test with `--limit 10` first. If 0 results, try the Latvian-language equivalent.

## Inputs

- **Niches** as `label:search_term` pairs (REQUIRED, e.g., `juristi:juristi`, `būvnieki:būvniecība`)
- **Limit** per niche (default 500)
- **Google Sheet URL** for export
- Country code (default `lv`), language (default `en`)

## Execution Tools

| Script | Purpose |
|--------|---------|
| `execution/scrape_gmaps_contact.py` | Apify scraper (`lukaskrivka/google-maps-with-contact-details`, ~$9/1K leads) |
| `execution/lead_splitter.py` | Route leads into cold_calling / cold_email / no_contact |
| `execution/website_evaluator.py` | PageSpeed Insights + tech stack detection |
| `execution/gmaps_scored_pipeline.py` | **Orchestrator** — runs all steps end-to-end |

## Process Flow

### Step 0: Pre-test (automatic)
Pipeline scrapes 10 leads per term to validate they return results. Aborts if any term returns 0. Cost: ~$0.09 per term.

### Step 1: Scrape (Apify)
```
python execution/gmaps_scored_pipeline.py \
  --niches "juristi:juristi" "frizieris:frizieris" "būvnieki:būvniecība" \
  --limit 500 --evaluate-websites --workers 3 \
  --sheet-url "SHEET_URL"
```
Each niche runs as a separate Apify actor call (~5 min each). Raw results saved to `.tmp/techstart_pipeline/scraped_YYYYMMDD_HHMMSS.json`.

### Step 2: Dedup
Deduplicate by `place_id`, then by `business_name|address` hash.

### Step 3: Split
| Stream | Criteria | Use |
|--------|----------|-----|
| cold_calling | Has phone, no email | Phone outreach |
| cold_email | Has email (+ website) | Email outreach with website insights |
| no_contact | No phone, no email | Discarded |

### Step 4: Website Evaluation
For cold_email leads only. Uses Google PageSpeed Insights API (mobile strategy) + local tech stack detection.

**Scores:** Performance (35%), Mobile friendliness (20%), SSL (15%), SEO (15%), Best practices (15%).

**Insight bullets** (template-based, no AI cost):
- Slow loading: "Your site loads in {X}s on mobile — {Y}x slower than the 2.5s average"
- No SSL: "No HTTPS — Google penalizes this"
- Not mobile-friendly: "Not optimized for mobile — 70%+ of local searches are on phones"
- Poor SEO: "Basic SEO fixes could help more customers find you"

**Auth:** Uses OAuth token (same as Sheets auth, requires `openid` scope). Falls back to API key env var `GOOGLE_PAGESPEED_API_KEY`.

### Step 5: Export to Google Sheets
Three tabs:
- **cold_calling:** niche, business_name, category, address, city, phone, google_maps_url, rating, review_count
- **cold_email_scored:** niche, business_name, category, address, city, phone, website, email_1, email_2, facebook, instagram, linkedin, google_maps_url, rating, review_count, overall_score, performance_score, seo_score, mobile_friendly, has_ssl, cms, insight_1, insight_2, insight_3
- **summary:** totals, avg scores, CMS breakdown, per-niche counts

## Outputs

- Google Sheet with 3 tabs (deliverable)
- `.tmp/techstart_pipeline/` intermediate files (disposable)

## Error Handling

- **Pre-test catches bad terms:** Pipeline aborts before spending budget if any term returns 0 results
- **Apify rate limits:** Actor runs sequentially per niche — no parallel API stress
- **PSI 429 (quota):** OAuth token has higher limits than unauthenticated. If still hit, reduce `--workers` from 3 to 1
- **PSI 403:** Re-auth with expanded scopes: delete `token.json`, re-run pipeline (will prompt browser auth)
- **0 results mid-run:** Warning printed, but pipeline continues with remaining niches

## Notes

### Cost
- Apify: ~$9 per 1,000 leads (Starter plan)
- Pre-test: ~$0.09 per term (10 leads)
- PageSpeed API: Free with OAuth or API key
- Budget per run: ~$4.50 per 500-lead niche + pre-test

### Production Run Timing
- Pre-test: ~1 min per term
- Scraping: ~5 min per niche
- Website evaluation: ~30-40 min for 150 websites (3 workers)
- Sheets export: ~2 min
- **Total: ~55 min for 3 niches + eval**

### Email Quality Filtering
The scraper applies domain-based email filtering:
- Keeps emails matching business's own domain
- Keeps free provider emails (gmail.com, inbox.lv, etc.)
- Blocks emails from news/directory sites (db.lv, firmas.lv, 1188.lv, etc.)
- Treats Instagram/Facebook "websites" as no-website

### Skip-Scrape Mode
To re-run evaluation + export on existing data:
```
python execution/gmaps_scored_pipeline.py \
  --niches "juristi:juristi" \
  --skip-scrape .tmp/techstart_pipeline/scraped_YYYYMMDD_HHMMSS.json \
  --evaluate-websites --workers 3 \
  --sheet-url "SHEET_URL"
```

### Cold Email Copy Export (Post-Pipeline)

After the main pipeline completes, segment leads and generate Instantly-ready CSV:

```bash
# Step 1: Segment leads + translate insights to Latvian
python execution/lead_segmenter.py \
  --input .tmp/techstart_pipeline/cold_email_evaluated.json \
  --output .tmp/techstart_pipeline/cold_email_segmented.json

# Step 2: Export to Instantly CSV (with QA check)
python execution/cold_email_exporter.py \
  --input .tmp/techstart_pipeline/cold_email_segmented.json \
  --templates campaigns/techstart/copy/website_build/ \
  --output campaigns/techstart/instantly/website_build_YYYYMMDD.csv \
  --qa
```

**Key rules:**
- All email copy follows anti-AI writing rules (see `docs/anti_ai_writing_rules.md`)
- QA check must pass (zero em-dashes, zero Compliment-But patterns, insights max 15 words)
- Templates live in `campaigns/techstart/copy/website_build/` (10 Latvian templates)
- Export format: Instantly CSV with 3-email sequence per lead

### Campaign History
| Campaign | Date | Niches | Leads | Notes |
|----------|------|--------|-------|-------|
| latvia_website_leads_20260218 | 2026-02-18 | juristi, frizētavas, būvnieki | 29 | V1: frizētavas wrong term, superseded |
| latvia_gmaps_v2_20260220 | 2026-02-20 | frizieris, auto repair | 1000 | V2: auto repair was wrong niche (should have been juristi) |
| latvia_gmaps_v3_20260220 | 2026-02-20 | juristi, frizieris, būvniecība | 1,209 | V3: correct 3-niche run. 800 cold calling, 349 cold email (avg score 70/100), 60 no contact |

# Apollo URL Crafter

**Status:** Active directive
**Created:** 2026-02-24
**Scripts:** `execution/apollo_url_builder.py`, `execution/apollo_industry_resolver.py`

## Purpose

Help users go from a vague lead description ("I need construction company owners in Latvia") to a working Apollo search URL. The AI agent handles filter translation; the user refines in Apollo's browser UI.

## Workflow

```
1. User describes desired leads (natural language)
2. Agent extracts structured filters
3. Agent runs: py execution/apollo_url_builder.py --from-json .tmp/url_draft.json
4. Agent presents URL + filter summary to user
5. User opens URL in Apollo, refines filters visually
6. User pastes refined URL back
7. Agent runs gap analysis + scrapers as normal (see lead_generation_v5_optimized.md)
```

## IMPORTANT: English-Only Titles

**Always use English titles only.** Never include localized/translated job titles (e.g., "Amministratore Delegato", "Geschaeftsfuehrer", "Directeur Général"). Backup scrapers (CodeCrafter, PeakyDev) pass titles to their APIs as filter strings — non-English titles may not be understood, resulting in missed leads. Apollo's own search handles English titles fine even for non-English-speaking countries, since most LinkedIn profiles use English job titles. For niche local-language terms, use the `keywords` field instead (keywords filter on company descriptions and work across all scrapers).

## Step 1: Extract Filters from Description

When the user describes what they want, extract these parameters:

| Parameter | Apollo Field | Example User Input | Extracted Value |
|-----------|-------------|-------------------|-----------------|
| **Who** (roles) | titles | "owners and CEOs" | `["CEO", "Owner"]` |
| **Seniority** | seniority | "decision makers" | `["c_suite", "owner", "director"]` |
| **What industry** | industries | "construction companies" | `["Construction"]` |
| **Where** | org_locations | "in Latvia" | `["Latvia"]` |
| **How big** | company_size | "10-200 employees" | `["11,50", "51,200"]` |
| **Niche keywords** | keywords | "HVAC companies" | `["HVAC"]` |
| **Revenue** | revenue | "over 1M revenue" | `{"min": "1000000"}` |

### Seniority mapping reference

| User Says | Apollo Value |
|-----------|-------------|
| C-level, executives | `c_suite` |
| VPs | `vp` |
| Directors | `director` |
| Managers | `manager` |
| Owners | `owner` |
| Founders | `founder` |
| Department heads | `head` |
| Partners | `partner` |
| Senior staff | `senior` |
| Decision makers | `c_suite, owner, founder, vp, director` |

### Company size mapping reference

| User Says | Apollo Value(s) |
|-----------|----------------|
| Solo/micro | `1,10` |
| Small (10-50) | `11,50` |
| Small-medium (10-200) | `11,50`, `51,200` |
| Medium (50-500) | `51,200`, `201,500` |
| Large (500+) | `501,1000`, `1001,5000`, `5001,10000` |
| Enterprise (10k+) | `10001+` |

**Important — Apollo uses broad ranges** (e.g., `11,50` and `51,200`) that don't map 1:1 to scraper APIs. Each scraper has its own granularity:
- **CodeCrafter** accepts: `1-10`, `11-20`, `21-50`, `51-100`, `101-200`, `201-500`, `501-1000`, `1001-2000`, `2001-5000`, `5001-10000`, `10001-20000`, `20001-50000`, `50000+`. Apollo broad ranges must be **expanded** (e.g., `51,200` → `51-100` + `101-200`).
- **PeakyDev** accepts: `0 - 1`, `2 - 10`, `11 - 50`, `51 - 200`, `201 - 500`, `501 - 1000`, `1001 - 5000`, `5001 - 10000`, `10000+`. Apollo granular ranges must be **collapsed** (e.g., `51,100` + `101,200` both → `51 - 200`).
- **Olympus** passes the Apollo URL directly — no mapping needed.

Scraper scripts handle this mapping internally. If you add a new scraper, ensure its size map covers ALL Apollo range variants (both granular and broad).

## Step 2: Industry Selection

Use the LinkedIn V1 taxonomy (147 industries). List with: `py execution/apollo_url_builder.py --list-industries`

### Selection principles

1. **Be specific**: Use "Civil Engineering" instead of just "Construction" if the niche is specific
2. **Include adjacent industries**: Construction campaigns often need "Building Materials" and "Civil Engineering" too
3. **Use keywords for niches**: Industries are broad. For specific niches (HVAC, prefab, SaaS), add keywords instead of relying solely on industry filters
4. **Check with user**: Always present selected industries and ask if they want to add/remove any

### Common industry groupings

**Construction & Real Estate:**
Construction, Building Materials, Civil Engineering, Architecture & Planning, Real Estate, Commercial Real Estate, Glass Ceramics & Concrete

**Technology:**
Information Technology & Services, Computer Software, Internet, Computer & Network Security, Computer Hardware, Computer Networking, Telecommunications

**Marketing & Media:**
Marketing & Advertising, Online Media, Public Relations & Communications, Graphic Design, Design, Broadcast Media, Media Production

**Finance:**
Financial Services, Banking, Insurance, Accounting, Capital Markets, Investment Banking, Investment Management, Venture Capital & Private Equity

**Healthcare:**
Hospital & Health Care, Medical Practice, Medical Devices, Pharmaceuticals, Health Wellness & Fitness, Mental Health Care, Biotechnology

**Manufacturing:**
Machinery, Industrial Automation, Electrical/Electronic Manufacturing, Mechanical or Industrial Engineering, Plastics, Chemicals, Packaging & Containers

**HR & Training:**
Human Resources, Staffing & Recruiting, Professional Training & Coaching, Education Management, E-Learning, Higher Education

**Logistics:**
Logistics & Supply Chain, Transportation/Trucking/Railroad, Warehousing, Package/Freight Delivery, Maritime, Import & Export

## Step 3: Build and Present URL

Save filters to `.tmp/url_draft.json` and run:

```bash
py execution/apollo_url_builder.py --from-json .tmp/url_draft.json --validate

# Or build directly from CLI flags:
py execution/apollo_url_builder.py \
  --titles "CEO,Owner,Managing Director" \
  --industries "Construction,Building Materials" \
  --org-locations "Latvia" \
  --company-size "11,50" "51,200" \
  --validate
```

Present to user:
```
Here's the Apollo search URL based on your description:

Filters:
  Titles: CEO, Owner, Managing Director
  Seniority: c_suite, owner, director
  Industries: Construction, Building Materials
  Org Location: Latvia
  Company Size: 11-50, 51-200

URL: https://app.apollo.io/#/people?personTitles[]=CEO&...

Open this in Apollo to preview the results. Adjust any filters in the UI,
then paste the updated URL back here when you're ready to scrape.
```

## Step 4: After User Refines

When the user pastes back a refined URL:

1. Parse it: `py execution/apollo_url_parser.py --apollo-url "URL" --output-format text`
2. Run gap analysis: `py execution/filter_gap_analyzer.py --apollo-url "URL"`
3. Show the user what each scraper will handle vs drop
4. Proceed to scraping per `lead_generation_v5_optimized.md`

## Common Patterns (Copy-Paste Templates)

### Construction decision-makers in Latvia
```json
{
  "titles": ["CEO", "Owner", "Director", "Managing Director", "Founder", "Co-Founder"],
  "seniority": ["owner", "founder", "c_suite", "director"],
  "industries": ["Construction", "Building Materials", "Civil Engineering"],
  "org_locations": ["Latvia"],
  "company_size": ["11,50", "51,200", "201,500"]
}
```

### Marketing agency owners in DACH
```json
{
  "titles": ["CEO", "Founder", "Owner", "Managing Director"],
  "seniority": ["owner", "founder", "c_suite"],
  "industries": ["Marketing & Advertising", "Online Media"],
  "org_locations": ["Germany", "Austria", "Switzerland"],
  "company_size": ["1,10", "11,50"]
}
```

### IT services decision-makers in Nordics
```json
{
  "titles": ["CEO", "CTO", "VP Engineering", "IT Director", "Managing Director"],
  "seniority": ["c_suite", "vp", "director"],
  "industries": ["Information Technology & Services", "Computer Software", "Internet"],
  "org_locations": ["Sweden", "Norway", "Denmark", "Finland"],
  "company_size": ["11,50", "51,200", "201,500"]
}
```

### HR/Training leads in Baltics
```json
{
  "titles": ["CEO", "Owner", "HR Director", "Head of HR", "Training Director"],
  "seniority": ["c_suite", "owner", "director", "head"],
  "industries": ["Human Resources", "Professional Training & Coaching", "Education Management"],
  "org_locations": ["Latvia", "Lithuania", "Estonia"],
  "company_size": ["11,50", "51,200"]
}
```

## Edge Cases

- **User wants a niche not covered by industries**: Use `keywords` field. Example: "prefab housing" → `keywords: ["prefab", "prefabricated"]` + `industries: ["Construction", "Building Materials"]`
- **User wants multiple countries**: Just add all to `org_locations`. Apollo treats them as OR.
- **User wants to exclude industries**: Apollo URL doesn't support exclusion — handle this post-scrape with `lead_filter.py --exclude-industries`
- **Industry name not found**: Check exact spelling with `--list-industries`. Apollo uses "&" not "and" (e.g., "Marketing & Advertising", not "Marketing and Advertising"). The resolver handles this normalization.

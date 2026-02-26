# Client Discovery & Market Research

## Goal
When onboarding a new client, analyze their website to understand their business and generate a recommended ICP (Ideal Customer Profile) with Apollo filter suggestions. This replaces manual ICP entry with AI-assisted discovery.

## Input
- Client website URL (required)
- Optional: Client contact email
- Optional: Notes about the client's business

## Tools
- `execution/client_discovery.py` - Multi-page website scraper + AI analyzer

## Output
- Draft `client.json` with populated ICP
- Apollo filter recommendations (titles, industries, company sizes, locations)
- Summary report of findings

## Process

### 1. Collect Input
Gather basic information:
```
Required:
- Website URL (e.g., https://example.com)

Optional:
- Contact email
- Industry hint (if known)
- Notes from initial conversation
```

### 2. Multi-Page Website Scraping
Scrape key pages from the client's website:

**Pages to scrape (in order):**
1. Homepage (`/`)
2. About page (`/about`, `/about-us`, `/o-nas`, `/par-mums`, `/company`)
3. Services page (`/services`, `/solutions`, `/what-we-do`, `/pakalpojumi`)
4. Case studies (`/case-studies`, `/work`, `/portfolio`, `/clients`)
5. Team page (`/team`, `/about#team`, `/leadership`)

**Scraping approach:**
- Try each URL pattern until one succeeds
- Extract text content (hero, headlines, paragraphs)
- Limit to 3000 chars per page
- Total content cap: 10,000 chars for AI analysis

**Content extraction priorities:**
- Headline/hero text (what they do)
- About section (company description)
- Services list (offerings)
- Client logos/industries served
- Geographic mentions
- Team titles (indicates company maturity)

### 3. AI Analysis
Send scraped content to AI (Claude or GPT-4) for structured extraction:

**AI Prompt:**
```
You are analyzing a company's website to help create a lead generation strategy.

Website Content:
{scraped_content}

Additional Notes: {user_notes}

Analyze this company and provide a structured JSON response:

{
  "company_analysis": {
    "company_name": "Extracted or inferred company name",
    "industry": "Primary industry (e.g., 'Digital Marketing', 'SaaS', 'Consulting')",
    "business_model": "B2B / B2C / Both",
    "product_service": "Brief description of what they sell/offer (1-2 sentences)",
    "value_proposition": "Their main differentiator or promise to customers",
    "company_size_estimate": "Startup / Small (1-50) / Medium (51-200) / Large (200+)",
    "geographic_focus": ["Country 1", "Country 2"],
    "verticals_served": ["Industry 1", "Industry 2", "Industry 3"]
  },
  "ideal_customer_profile": {
    "description": "2-3 sentence description of ideal customer",
    "target_company_size": "e.g., '51-200 employees' or '11-50 employees'",
    "target_industries": ["Industry 1", "Industry 2", "Industry 3"],
    "target_job_titles": ["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"],
    "target_locations": ["Country/Region 1", "Country/Region 2"],
    "pain_points": ["Pain point 1", "Pain point 2", "Pain point 3"],
    "buying_signals": ["Signal 1", "Signal 2"]
  },
  "apollo_filter_suggestions": {
    "person_titles": ["CEO", "Founder", "Marketing Director", ...],
    "person_seniorities": ["owner", "c_suite", "vp", "director", "manager"],
    "organization_num_employees_ranges": ["1,10", "11,50", "51,200", "201,500"],
    "organization_locations": ["Latvia", "Lithuania", "Estonia"],
    "organization_industry_tag_ids": ["Marketing & Advertising", "Information Technology & Services"],
    "keywords": ["digital marketing", "lead generation", ...]
  },
  "confidence_score": 0.85,
  "notes": "Any caveats or areas of uncertainty"
}

Return ONLY the JSON, no other text.
```

### 4. Generate Draft Client JSON
Transform AI output into `client.json` format:

```json
{
  "client_id": "acme_corp",
  "company_name": "Acme Corp",
  "contact_email": "contact@example.com",
  "industry": "Digital Marketing",
  "product": "Google Ads campaign creation and management",
  "icp": {
    "description": "Mid to large businesses in the Baltics looking to scale their online advertising",
    "job_titles": ["Marketing Director", "CMO", "Head of Marketing", "Digital Marketing Manager", "Founder"],
    "company_size": "51-200",
    "industries": ["E-commerce", "SaaS", "Professional Services", "Finance"],
    "locations": ["Latvia", "Lithuania", "Estonia"]
  },
  "apollo_filters": {
    "person_titles": ["Marketing Director", "CMO", "Head of Marketing"],
    "person_seniorities": ["director", "vp", "c_suite", "owner"],
    "organization_num_employees_ranges": ["51,200", "201,500"],
    "organization_locations": ["Latvia", "Lithuania", "Estonia"]
  },
  "discovery": {
    "source": "ai_analysis",
    "analyzed_at": "2026-02-03T10:30:00Z",
    "confidence": 0.85,
    "pages_scraped": 4
  },
  "created_at": "2026-02-03T10:30:00Z",
  "updated_at": "2026-02-03T10:30:00Z",
  "campaigns": []
}
```

### 5. User Review & Approval
Present findings to user for review:
- Show extracted company analysis
- Show recommended ICP
- Show Apollo filter suggestions
- Allow user to modify before saving

### 6. Save Client
Save approved `client.json` to `campaigns/{client_id}/`

## Command Examples

**Interactive discovery:**
```bash
py execution/client_discovery.py --url https://example.com
```

**With additional context:**
```bash
py execution/client_discovery.py --url https://example.com --email contact@example.com --notes "They focus on PPC for e-commerce"
```

**Non-interactive (auto-save draft):**
```bash
py execution/client_discovery.py --url https://example.com --auto-save
```

**Use specific AI provider:**
```bash
py execution/client_discovery.py --url https://example.com --ai-provider anthropic
```

## Output Files

**Draft client file:**
`campaigns/{client_id}/client_draft.json`

**Discovery report:**
`campaigns/{client_id}/discovery_report.md`

**Report format:**
```markdown
# Client Discovery Report: Acme Corp

## Company Analysis
- **Industry:** Digital Marketing
- **Business Model:** B2B
- **Product/Service:** Google Ads campaign management
- **Value Proposition:** Data-driven PPC optimization for measurable ROI

## Recommended ICP
- **Target Companies:** Mid-size businesses (51-200 employees) in the Baltics
- **Industries:** E-commerce, SaaS, Professional Services
- **Decision Makers:** Marketing Directors, CMOs, Founders
- **Pain Points:** Wasted ad spend, lack of in-house PPC expertise

## Apollo Filter Suggestions
- **Titles:** Marketing Director, CMO, Head of Marketing, Digital Marketing Manager
- **Seniorities:** Director, VP, C-Suite, Owner
- **Company Size:** 51-100, 101-200, 201-500 employees
- **Locations:** Latvia, Lithuania, Estonia

## Confidence: 85%

## Notes
- Website is clear about services and target market
- May also target Poland based on language options

---
Generated: 2026-02-03 10:30:00
Pages analyzed: 4 (home, about, services, case-studies)
```

## Error Handling

### Scraping Errors
- **Website unreachable:** Retry 3 times with backoff, then fail
- **404 on subpages:** Continue with available pages, note in report
- **JavaScript-only site:** Use basic scraper, may have limited content
- **Blocked/Forbidden:** Note limitation, suggest manual review

### AI Errors
- **Rate limit:** Wait and retry with backoff
- **Invalid response:** Retry up to 3 times
- **Low confidence (<0.5):** Warn user, suggest manual review
- **Missing critical fields:** Prompt user for input

### Recovery
- Partial results are still useful
- Save whatever was extracted
- Mark confidence accordingly
- Log issues for manual follow-up

## Integration with Client Manager

After discovery, integrate with existing client workflow:

```bash
# Step 1: Run discovery
py execution/client_discovery.py --url https://newclient.com

# Step 2: Review draft in campaigns/newclient/client_draft.json
# Make any edits needed, then rename to client.json
# (or use: py execution/client_manager.py add — interactive prompt)

# Step 3: Run first campaign
py execution/fast_lead_orchestrator.py --client-id newclient --campaign-name "Initial Outreach" --apollo-url "..."
```

## Apollo Filter Mapping

### Company Size Mapping
| Discovery Output | Apollo Filter |
|------------------|---------------|
| "1-10 employees" | "1,10" |
| "11-50 employees" | "11,50" |
| "51-200 employees" | "51,200" |
| "201-500 employees" | "201,500" |
| "500+ employees" | "501,1000", "1001,5000" |

### Seniority Mapping
| Discovery Output | Apollo Seniority |
|------------------|------------------|
| "Founders/Owners" | "owner" |
| "C-Suite" | "c_suite" |
| "VP Level" | "vp" |
| "Directors" | "director" |
| "Managers" | "manager" |

### Industry Mapping
AI should output Apollo-compatible industry tags:
- "Marketing & Advertising"
- "Information Technology & Services"
- "Computer Software"
- "Financial Services"
- "Management Consulting"
- etc.

## Limitations

1. **Website-only analysis:** Doesn't include LinkedIn, reviews, or competitors
2. **Language limitations:** Works best with English sites; other languages may reduce accuracy
3. **Static content only:** Can't analyze JavaScript-rendered dynamic content well
4. **AI interpretation:** May misinterpret niche or technical businesses
5. **Manual review needed:** Always have user verify before using ICP

## Future Enhancements

1. **LinkedIn company page analysis:** Pull data from company LinkedIn
2. **Competitor analysis:** Identify and analyze 2-3 competitors
3. **Review site analysis:** Pull from G2, Capterra, Trustpilot
4. **Industry benchmarks:** Compare ICP to successful similar companies
5. **Apollo URL generator:** Auto-generate Apollo search URL from filters

## Best Practices

1. **Always review AI output:** Don't blindly trust discovery results
2. **Start with narrow ICP:** Better to start focused and expand
3. **Test with small campaign:** Run 100-lead test before scaling
4. **Update ICP based on results:** Refine after seeing campaign performance
5. **Document manual changes:** Note why you modified AI suggestions

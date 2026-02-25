# Sales Sample Generator

## Goal
Create a compelling demo deliverable for a prospective client that showcases the full lead generation capability. Used during sales to demonstrate value before signing.

## Input
- Prospect website URL (required)
- Apollo search URL (provided after Phase 1)
- Reference copies folder (optional)

## Tools
- `execution/generate_sales_sample.py` - Orchestrates the full workflow
- `execution/client_discovery.py` - Website analysis
- `execution/linkedin_enricher.py` - LinkedIn profile enrichment
- `execution/website_scraper.py` - Company website scraping
- Apollo scrapers (existing)

## Output
- Markdown report: `{output_dir}/sample_{prospect_name}_{date}.md`
- Contains: business analysis, ICP, sample leads, email templates, personalized emails

---

## Process

### Phase 1: Discovery (Automated)

**Input:** Prospect website URL

**Steps:**
1. Run `client_discovery.py` on prospect URL
2. Scrape: home, about, services, case studies pages
3. AI extracts: business model, value proposition, target audience
4. Output: ICP + Apollo filter suggestions

**Output for User Review:**
```
=== PHASE 1 COMPLETE ===

Business: [Company Name]
Industry: [Industry]
Product: [Description]

Recommended ICP:
- Titles: CMO, Marketing Director, Head of Growth
- Company Size: 51-200 employees
- Industries: SaaS, E-commerce
- Locations: United States, UK

Apollo Filter Suggestions:
- person_titles: ["CMO", "VP Marketing", "Head of Growth"]
- organization_num_employees_ranges: ["51-100", "101-200"]

ACTION REQUIRED:
1. Review ICP above
2. Build Apollo search in Apollo UI using these filters
3. Copy the Apollo URL and run Phase 2
```

### Phase 2: Lead Sampling (Automated)

**Input:** Apollo search URL from user

**Steps:**
1. Parse Apollo URL for filters
2. Scrape 2-3 sample leads
3. Extract: name, title, company, email, LinkedIn URL

**Limit:** 3 leads maximum (this is a sample, not a full campaign)

### Phase 3: Enrichment (Automated)

**Steps:**
1. Website scraping - each lead's company website
   - Company description
   - Products/services
   - Recent news/updates
   - Key differentiators

2. LinkedIn enrichment - each lead's profile
   - Bio/summary
   - Current role tenure
   - Career history
   - Education

**Credits Used:** ~1 Lead Magic credit per lead (3 total for sample)

### Phase 4: Email Generation (Automated)

**Steps:**
1. Load reference copies (if provided) or use defaults
2. Generate 3-email sequence template with `{{placeholders}}`
3. Generate personalized first email for EACH sample lead
4. Personalizations must be "super interesting" - see requirements below

**Output:** Final markdown report

---

## Personalization Requirements

The sample emails must demonstrate value. Generic personalizations waste the demo.

### Good Personalizations
- "I noticed TechCorp just launched your new analytics suite - the focus on real-time dashboards caught my eye"
- "With your expansion into the EU market (congrats on the Series B), scaling marketing ops is probably top of mind"
- "Your background at Google before joining DataFlow suggests you know the importance of data-driven decisions"

### Bad Personalizations (Avoid)
- "I saw your company is in the SaaS industry"
- "I noticed you're the Marketing Director"
- "Your company seems interesting"

### Sources for Personalization
| Source | What to Look For |
|--------|------------------|
| Company website | Recent product launches, news, blog posts, mission statement |
| LinkedIn bio | Career highlights, achievements, interests |
| LinkedIn experience | Previous companies, tenure, career trajectory |
| Company LinkedIn | Recent posts, company updates, hiring patterns |

---

## Command Examples

### Full Workflow (Interactive)
```bash
# Phase 1: Discovery
py execution/generate_sales_sample.py phase1 \
  --prospect-url https://prospect.com

# [User reviews ICP, creates Apollo URL]

# Phase 2-4: Complete sample
py execution/generate_sales_sample.py complete \
  --prospect-url https://prospect.com \
  --apollo-url "https://app.apollo.io/#/people?..."
```

### With Reference Copies
```bash
py execution/generate_sales_sample.py complete \
  --prospect-url https://prospect.com \
  --apollo-url "https://app.apollo.io/#/people?..." \
  --reference-copies campaigns/example_agency/reference_copies
```

### Custom Output Location
```bash
py execution/generate_sales_sample.py complete \
  --prospect-url https://prospect.com \
  --apollo-url "https://app.apollo.io/#/people?..." \
  --output-dir campaigns/example_agency/samples/
```

---

## Output Report Structure

```markdown
# Sales Sample: [Prospect Company]
Generated: [Date]

---

## 1. Business Analysis
[Deep analysis from discovery]

## 2. Recommended ICP
[Table of filters + Apollo suggestions]

## 3. Sample Leads (2-3)
[For each lead: basic info + enrichment data]

## 4. Email Sequence Template
[3 emails with {{placeholders}}]

## 5. Personalized Sample Emails
[First email customized for each lead]

## 6. Next Steps
[What happens if they want to proceed]
```

---

## Error Handling

### Phase 1 Errors
- **Website unreachable:** Retry 3x, then fail with clear message
- **Low content extracted:** Warn but continue, note in report

### Phase 2 Errors
- **Invalid Apollo URL:** Validate format, provide example
- **No leads found:** Suggest adjusting filters

### Phase 3 Errors
- **Website scraping fails:** Use available data, note limitation
- **LinkedIn enrichment fails:** Continue without, note limitation
- **Lead Magic rate limit:** Wait and retry

### Phase 4 Errors
- **AI generation fails:** Retry 3x with backoff
- **No reference copies:** Use built-in templates

---

## Best Practices

1. **Quality over quantity** - 2-3 leads is enough. Focus on personalization quality.

2. **Review before sending** - Always review the generated report before sharing with prospect.

3. **Update reference copies** - If you write a great personalization manually, add it to reference copies.

4. **Note limitations** - If enrichment failed for a lead, acknowledge it in the report rather than faking data.

5. **Timing expectations** - Full sample takes 30-60 minutes including the manual Apollo step.

---

## Integration with Sales Process

```
1. Initial call with prospect
   ↓
2. Run Phase 1 (discovery) - show them you understand their business
   ↓
3. Build Apollo search, run Phase 2-4
   ↓
4. Present sample report on follow-up call
   ↓
5. If interested → full campaign proposal
```

---

## Limitations

1. **Manual Apollo step required** - No way to auto-generate Apollo search URL
2. **Credits consumed** - ~3 Lead Magic credits per sample
3. **Time investment** - 30-60 min per sample
4. **AI variability** - Personalization quality varies, always review

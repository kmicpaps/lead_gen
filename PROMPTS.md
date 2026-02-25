# How to Use This System

Type a slash command. Claude reads the directive, runs the scripts, and handles the rest.

---

## Slash Commands

### Lead Generation

#### `/new-apollo-list`
Scrape leads from Apollo, deduplicate, filter, export to Google Sheets.

```
/new-apollo-list
Client: acme_corp
Apollo URL: https://app.apollo.io/#/people?...
Target: 2000
```

You provide: client name, Apollo URL, target lead count.
You'll choose: which scrapers to run, which quality filters to apply.
Output: Google Sheet with clean, deduplicated leads.

#### `/find-more-leads`
Rescrape an existing Apollo URL. Deduplicates against all previous campaigns — you only get new leads.

```
/find-more-leads
Client: acme_corp
Apollo URL: https://app.apollo.io/#/people?...
```

Expect 40-70% overlap with previous scrapes. That's normal.

#### `/gmaps-leads`
Scrape local businesses from Google Maps by location + niche.

```
/gmaps-leads
Client: acme_corp
Location: Riga
Niches: juristi, grāmatveži
```

Google Maps caps at ~120 results per search term. Use specific niches.

#### `/build-apollo-url`
Describe your target audience in plain English. Claude builds the Apollo URL.

```
/build-apollo-url construction company owners in Latvia, 10-50 employees
```

This is Step 0 — do this before `/new-apollo-list`. Open the URL in Apollo, refine visually, paste back the final version.

---

### Lead Processing

#### `/quality-filter`
Analyze a lead list and choose which filters to apply (email, phone codes, titles, industries).

```
/quality-filter .tmp/merged/leads.json
```

Claude shows you the report first. You pick the filters. Nothing gets removed without your approval.

#### `/deduplicate-leads`
Remove duplicates across all campaigns for a client.

```
/deduplicate-leads acme_corp
```

Runs dry-run first. You confirm before anything changes.

---

### Sales & Outreach

#### `/research-client`
Analyze a company's website to understand their business and suggest an ICP.

```
/research-client https://example.com
```

Free — no API credits used. Good for pre-call research or onboarding prep.

#### `/cold-email-planning`
Generate cold email sequences based on client ICP and best practices.

```
/cold-email-planning acme_corp
```

Plain text only, 50-100 words, no links in email 1. Claude warns you about risky countries (Germany, Italy, Poland).

#### `/create-sales-sample`
Create a demo deliverable to pitch a prospect: business analysis + sample leads + email templates.

```
/create-sales-sample https://prospect.com
```

#### `/onboard-new-client`
Set up a new client folder with metadata, ICP, and campaign structure.

```
/onboard-new-client "Acme Corp" https://acme.com
```

If you provide a website, Claude auto-runs discovery to suggest ICP details.

#### `/pipeline-overview`
Not sure what to do? This shows all available commands with a decision tree.

```
/pipeline-overview
```

---

## Enrichment (Copy-Paste Prompts)

These don't have slash commands. Copy the prompt, fill in the blanks.

### Industry Classification
```
Enrich industry data for:
- Lead file: [PATH]
- AI provider: openai
```

### Icebreaker Generation
```
Generate icebreakers for:
- Lead file: [PATH]
- AI provider: openai
```
Slowest enrichment — scrapes websites then generates copy. ~2-5 min per 100 leads.

### Casual Company Names
```
Generate casual company names for:
- Lead file: [PATH]
- AI provider: openai
```
Turns "SIA Latvijas Mobilais Telefons" into "LMT".

### LinkedIn Enrichment
```
Enrich LinkedIn profiles for:
- Lead file: [PATH]
- Max leads: [NUMBER]
```
Costs Lead Magic credits. Use for small, high-value lists only.

### Fix Name Diacritics
```
Fix name diacritics for:
- File: [PATH]
```
Restores Baltic/Slavic characters from LinkedIn URL slugs. Leads need `linkedin_url`.

---

## Admin (Copy-Paste Prompts)

### Import & Compare External CSV
```
Compare this CSV against existing leads:
- CSV file: [FILENAME in .tmp/imports/]
- Compare against: [CLIENT_NAME]
```

### Add a New Scraper
```
Add a new scraper to the pipeline:
- Apify actor: [NAME or URL]
- What it returns: [DESCRIPTION]

Follow the 3-step process: scraper script, registry entry, normalizer function.
Test with 25 leads first.
```

### Add a New Directive
```
Create a new directive for: [DESCRIBE WORKFLOW]
Steps: [LIST STEPS]
Scripts it uses: [LIST or "none yet"]
```

---

## Where Things Live

| What | Where |
|------|-------|
| This file | `PROMPTS.md` |
| Agent instructions | `CLAUDE.md` |
| SOPs / workflows | `directives/` |
| Python scripts | `execution/` |
| Client data | `campaigns/[client]/` |
| Temp files | `.tmp/` (safe to delete) |
| API keys | `.env` (never read directly) |

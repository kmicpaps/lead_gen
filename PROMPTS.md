# How to Use This System

Type a slash command. Claude asks you what it needs. You answer. It does the rest.

Not sure where to start? Type `/pipeline-overview`.

---

## Common Workflows

### New client, first campaign (full flow)

```
1. /onboard-new-client        → give company name + website
                                 Claude researches them, creates client folder
                                 you review the ICP

2. /build-apollo-url           → describe who you want (titles, industries, location, size)
                                 Claude builds the URL
                                 you open it in Apollo, tweak filters, paste back final URL

3. /new-apollo-list            → give client name, Apollo URL, target count
                                 Claude shows scraper options + costs — you pick which to run
                                 scrapers run in parallel (~5-15 min)
                                 Claude shows quality report — you pick which filters to apply
                                 output: Google Sheet link with clean leads

4. /quality-filter             → give path to leads file (or describe which campaign)
                                 Claude shows: email coverage, phone codes, title/industry breakdown
                                 you pick which filters to apply (email, country, titles, etc.)
                                 output: cleaned lead file
```

### Get more leads from the same list

```
1. /find-more-leads            → give client name + same Apollo URL
                                 runs scrapers again, deduplicates against ALL previous campaigns
                                 you only get truly new leads
                                 expect 40-70% overlap — that's normal
```

### Local business leads (Google Maps)

```
1. /gmaps-leads                → give client name, city, niches (e.g. "lawyers, accountants")
                                 Claude scrapes Google Maps + extracts business info
                                 output: Google Sheet with business name, address, phone, website, rating
                                 (~120 results per niche max)
```

Note: Google Maps gives you **business-level contacts** (company phone, website, address, generic emails like info@company.com) — not personal emails of employees. For personal emails (jake@company.com), use Apollo (`/new-apollo-list`).

### Pitch a prospect

```
1. /research-client            → give their website URL
                                 Claude analyzes their business, suggests ICP
                                 free — no API credits

2. /create-sales-sample        → give prospect website
                                 Claude generates: business analysis + sample leads + email templates
                                 you get a demo deliverable to show them
```

### Write cold emails

```
1. /cold-email-planning        → give client name
                                 Claude generates email sequences from their ICP
                                 plain text, 50-100 words, no links in email 1
```

---

## All Commands

| Command | What it does | Claude asks for |
|---------|-------------|-----------------|
| `/new-apollo-list` | Scrape + dedup + filter + export | client, Apollo URL, target count |
| `/find-more-leads` | Rescrape, only return new leads | client, Apollo URL |
| `/gmaps-leads` | Google Maps local business scraping | client, location, niches |
| `/build-apollo-url` | Build Apollo URL from description | who you want to target |
| `/quality-filter` | Analyze + filter a lead list | path to leads file |
| `/deduplicate-leads` | Remove dupes across campaigns | client name |
| `/research-client` | Analyze a company website | website URL |
| `/cold-email-planning` | Generate email sequences | client name |
| `/create-sales-sample` | Demo deliverable for prospects | prospect website |
| `/onboard-new-client` | Set up new client folder | company name, website |
| `/pipeline-overview` | Show all commands + decision tree | nothing |
| `/system-audit` | Run a structured codebase audit, log findings, fix issues | nothing |
| `/maintain` | Quick structural health check (registry, normalizer, directives, scripts) | nothing (or specific scope) |
| `/setup` | Workspace onboarding — check deps, API keys, credentials, health | nothing |

---

## Enrichment

Not slash commands — just tell Claude what you need:

| Task | Prompt | Note |
|------|--------|------|
| Add industries | `Enrich industry data for [PATH]` | Most leads already have this from Apollo |
| Add icebreakers | `Generate icebreakers for [PATH]` | Slow — scrapes websites first (~2-5 min/100 leads) |
| Casual company names | `Generate casual names for [PATH]` | "SIA Latvijas Mobilais Telefons" → "LMT" |
| LinkedIn profiles | `Enrich LinkedIn for [PATH], max [N]` | Costs Lead Magic credits — small lists only |
| Fix diacritics | `Fix name diacritics for [PATH]` | Baltic/Slavic names, needs linkedin_url |
| Import CSV | `Compare [FILE] against [CLIENT] leads` | Put CSV in .tmp/imports/ first |

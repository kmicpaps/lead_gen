---
name: pipeline-overview
description: Overview of all available lead generation workflows and slash commands. Use when the user asks what they can do, needs help choosing a workflow, or says something like "what commands are available".
allowed-tools: Read, Grep, Glob
---

## Available Slash Commands

| Command | What it does |
|---------|-------------|
| `/new-apollo-list` | Scrape leads from Apollo URL → dedup → filter → Google Sheets |
| `/find-more-leads` | Rescrape an existing Apollo list, get only new leads |
| `/gmaps-leads` | Scrape local businesses from Google Maps by location + niche |
| `/build-apollo-url` | Convert a lead description into a working Apollo search URL |
| `/quality-filter` | Analyze and filter a lead list for quality issues |
| `/deduplicate-leads` | Remove duplicates across campaigns for the same client |
| `/research-client` | Analyze a company's website to understand their business + suggest ICP |
| `/onboard-new-client` | Create a new client folder with metadata and campaign structure |
| `/create-sales-sample` | Create a demo deliverable to pitch a prospect |
| `/cold-email-planning` | Generate cold email sequences using client context and lead data |
| `/system-audit` | Run a structured codebase audit, log findings, fix issues, generate report |
| `/maintain` | Quick structural health check — registry, normalizer, directives, skills, scripts |

## Decision Tree

**"I want to scrape leads"**
→ Have an Apollo URL? → `/new-apollo-list`
→ Need to build one first? → `/build-apollo-url`
→ Want local businesses from Google Maps? → `/gmaps-leads`
→ Already scraped, want MORE from same list? → `/find-more-leads`

**"I have leads and want to clean them"**
→ Quality issues (bad emails, wrong titles)? → `/quality-filter`
→ Duplicates across campaigns? → `/deduplicate-leads`

**"I'm working with a new client"**
→ Need to understand their business? → `/research-client`
→ Ready to set up their folder? → `/onboard-new-client`
→ Want to show them a demo? → `/create-sales-sample`

**"I need email copy for outreach"**
→ `/cold-email-planning`

**"I want to audit or maintain the system"**
→ Quick check after changes? → `/maintain`
→ Deep bug-finding audit? → `/system-audit`

## Not a Slash Command (use PROMPTS.md templates)

These less common tasks are available as copy-paste templates in `PROMPTS.md`:
- Lead enrichment (industry, LinkedIn, icebreakers, casual names, diacritics)
- Import & compare external CSV
- Add new directive / scraper / task

## Reference

- Full directive index: `directives/README.md`
- All execution scripts: `execution/` (55+ scripts, each has `--help`)
- Client data: `campaigns/{client_name}/`

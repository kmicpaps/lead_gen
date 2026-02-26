# Directives

SOPs (Standard Operating Procedures) for the lead generation system.
These are "Layer 1" in the 3-layer architecture -- see `CLAUDE.md` for details.

Directives are living documents. Update them when you discover API constraints, better approaches, common errors, or timing expectations.

## Core Workflows

| Directive | Purpose |
|-----------|---------|
| `lead_generation_v5_optimized.md` | Main lead gen pipeline: Apollo scrapers -> merge -> dedup -> filter -> Sheets |
| `apollo_url_crafter.md` | AI-assisted Apollo URL construction from natural language descriptions |
| `lead_quality_filtering.md` | Analyze scraped leads and apply user-chosen filters (email, phone, title, industry) |
| `gmaps_lead_generation.md` | Google Maps scraping pipeline with website contact extraction |
| `gmaps_scored_pipeline.md` | Google Maps pipeline: Apify scrape → split → PageSpeed eval → Sheets |
| `cross_campaign_deduplication.md` | Deduplicate leads across multiple campaigns for same client |
| `client_management.md` | Client onboarding, campaign folder structure, metadata tracking |

## Enrichment

| Directive | Purpose |
|-----------|---------|
| `enrich_industry.md` | AI-based industry classification using SIC/NAICS codes or website analysis |
| `enrich_linkedin_profile.md` | LinkedIn profile data enrichment (bio, experience, education) |
| `enrich_icebreakers.md` | AI-generated personalized icebreaker lines from website scraping |
| `enrich_casual_org_names.md` | Convert formal corporate names to casual/friendly versions |
| `fix_name_diacritics.md` | Restore Baltic/Slavic diacritics from LinkedIn URL slugs |

## Sales & Outreach

| Directive | Purpose |
|-----------|---------|
| `client_discovery.md` | Research and profile potential clients using AI website analysis |
| `cold_email_copywriting.md` | Email sequence generation, copy frameworks, compliance, infrastructure, metrics |
| `generate_sales_sample.md` | Generate sample lead reports for client pitches |

## Reference Research (in `docs/`)

| Document | Contents |
|----------|----------|
| `docs/cold_outreach_strategy.md` | FixMyWorkflow cold outreach strategy: targeting coaches, channel strategies, lead sourcing, pipeline management |
| `docs/2026-02_cold_email_deep_dive.md` | Practitioner cold email playbooks: agency strategies, copy frameworks, targeting, case studies, infrastructure |
| `docs/cold_email_best_practices.md` | Legal compliance by country, copywriting best practices, deliverability, metrics, benchmarks |

## System Maintenance

| Directive | Purpose |
|-----------|---------|
| `system_maintenance.md` | Audit procedures, change logging protocol, severity/category definitions, MEMORY.md update rules |
| `coding_standards.md` | Script structure, lead schema, directive/skill templates, integration checklists for common operations |

## Archived

See `_archived/` for superseded versions and historical summaries:
- `lead_generation_v4_final.md` -- superseded by v5
- `FIXES_COOKIE_AND_SHARING_ISSUES.md` -- historical fix notes
- `IMPROVEMENTS_SUMMARY_20251211.md` -- historical improvements
- `WORKFLOW_OPTIMIZATION_SUMMARY.md` -- historical optimization notes

## Creating New Directives

Include: Objective, Inputs, Execution Tools (scripts in `execution/`), Process Flow (step-by-step), Outputs, Error Handling, Notes (API limits, timing).

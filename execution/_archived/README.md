# Archived Scripts

This folder contains deprecated or redundant execution scripts that are no longer part of the active lead generation workflow.

**Date Archived:** December 3, 2025

## Archived Scripts & Reasons

### Apollo Scrapers (Deprecated)
- **run_apollo_scraper.py** - Old RapidAPI version, replaced by Apify-based scrapers
- **run_apollo_scraper_fast.py** - RapidAPI (NOT Apify olympus/b2b-leads-finder), wrong approach per directive
- **run_apify_apollo_scraper.py** - Fallback using x_guru actor, redundant
- **run_apify_scraper_v2.py** - Explicitly deprecated in directive (line 244)

### Alternative Scrapers (Not in Defined Process)
- **run_hiworld_scraper.py** - Alternative scraper (hi_world/Leadscraper), not part of defined 3-scraper process
- **run_xguru_scraper.py** - Alternative scraper (x_guru/Leads-Scraper-apollo-zoominfo), not part of defined process

### Workflow Scripts (Deprecated - Anti-pattern)
- **enhanced_lead_workflow.py** - Old version, superseded by v2
- **enhanced_lead_workflow_fast.py** - Fast variant, superseded by v2
- **main_lead_orchestrator.py** - Python orchestrator (anti-pattern: AI agent should orchestrate, not Python)
- **complete_poland_workflow.py** - Country-specific workflow, not general-purpose

**Why orchestrators are archived:** In the 3-layer architecture, the AI agent (Layer 2) reads directives (Layer 1) and calls execution tools (Layer 3). Python orchestrators try to hard-code workflow logic, creating maintenance burden and getting out of sync with directives. The correct approach: AI agent reads directive and calls tools as needed.

### Utilities
- **cleanup_enrichment_fields.py** - Utility script, not imported or referenced by any active script

## Active Workflow (12 Steps)

The current lead generation process uses these scrapers:
1. **olympus/b2b-leads-finder** (Apify) - Primary Apollo scraper
2. **code_crafter/leads-finder** (Apify) - Secondary scraper with filter extraction
3. **peakydev/leads-scraper-ppe** (Apify) - Tertiary scraper with filter extraction

All other scrapers have been archived to reduce confusion and maintain a single source of truth.

## Recovery

If you need to recover any of these scripts, they remain in this folder and can be moved back to execution/ if needed. However, they may require updates to work with the current architecture.

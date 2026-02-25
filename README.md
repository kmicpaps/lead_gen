# Lead Generation System

3-layer architecture for reliable, maintainable lead generation workflows.

## Architecture

**Layer 1: Directives** (`directives/`) - SOPs in Markdown defining goals, inputs, tools, outputs, and edge cases.
**Layer 2: Orchestration** (AI agent) - Reads directives, calls execution tools in order, handles errors, updates directives.
**Layer 3: Execution** (`execution/`) - Deterministic Python scripts for API calls, data processing, file operations.

## Directory Structure

```
lead_gen/
├── CLAUDE.md, AGENTS.md, GEMINI.md    # AI agent instructions
├── .env                                # API keys (gitignored)
├── credentials.json, token.json        # Google OAuth (gitignored)
├── requirements.txt
├── docs/                               # Reference documentation
│   ├── IMPLEMENTATION_PLAN.md
│   ├── QUICK_START_OPTIMIZED.md
│   ├── SETUP.md
│   └── WORKFLOW_FIXES_DEC5.md
├── directives/                         # SOPs (see directives/README.md)
│   └── _archived/
├── execution/                          # Python scripts
│   └── _archived/
├── campaigns/                          # Client data (permanent)
│   ├── _template/
│   └── {client_id}/
│       ├── client.json
│       ├── apollo_lists/{campaign}/
│       └── google_maps_lists/{campaign}/
└── .tmp/                               # Intermediates (gitignored)
    ├── b2b_finder/                     # Olympus scraper output
    ├── codecrafter/                    # CodeCrafter scraper output
    ├── peakydev/                       # PeakyDev scraper output
    ├── merged/                         # Deduplication output
    ├── ai_enriched/                    # AI enrichment output
    ├── samples/                        # Sales sample output
    └── imports/                        # External CSV imports
```

## Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Configure API keys in `.env` (see `docs/SETUP.md`)
3. Set up Google OAuth: `credentials.json` + `token.json`

## Core Workflows

| Workflow | Directive | Key Scripts |
|----------|-----------|-------------|
| Apollo lead scraping | `lead_generation_v5_optimized.md` | `scraper_olympus_b2b_finder.py`, `scraper_codecrafter.py`, `scraper_peakydev.py` |
| Lead quality filtering | `lead_quality_filtering.md` | `lead_quality_analyzer.py`, `lead_filter.py` |
| Google Maps scraping | `gmaps_lead_generation.md` | `gmaps_niche_scraper.py`, `gmaps_lead_pipeline.py` |
| Cross-campaign dedup | `cross_campaign_deduplication.md` | `cross_campaign_deduplicator.py` |
| Industry enrichment | `enrich_industry.md` | `ai_industry_enricher.py` |
| Google Sheets export | (part of all workflows) | `google_sheets_exporter.py` |

## Key Principles

- Deliverables live in cloud (Google Sheets) -- local files are temporary
- Everything in `.tmp/` can be deleted and regenerated
- Self-annealing: when things break, fix the tool, update the directive, system gets stronger
- Push complexity into deterministic scripts; AI handles decision-making only

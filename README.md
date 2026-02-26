# Lead Generation Pipeline

AI-orchestrated B2B lead generation system using a 3-layer architecture for reliable, maintainable workflows.

Scrape leads from Apollo and Google Maps, enrich with AI, filter for quality, and export to Google Sheets — all orchestrated by an AI agent following structured SOPs.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: Directives (directives/)                  │
│  SOPs in Markdown — goals, inputs, tools, outputs   │
├─────────────────────────────────────────────────────┤
│  Layer 2: Orchestration (AI Agent)                  │
│  Reads directives, calls tools, handles errors      │
├─────────────────────────────────────────────────────┤
│  Layer 3: Execution (execution/)                    │
│  Deterministic Python scripts — APIs, data, files   │
└─────────────────────────────────────────────────────┘
```

**Why this works:** LLMs are probabilistic, but most business logic is deterministic. By pushing complexity into tested Python scripts, the AI agent only handles decision-making. 90% accuracy per step = 59% over 5 steps if the AI does everything; with deterministic execution, each step is ~100%.

## Prerequisites

You'll need accounts and API keys for:

| Service | Purpose | Get it from |
|---------|---------|-------------|
| [Apify](https://apify.com) | Apollo scrapers (Olympus, PeakyDev) | Console > Integrations |
| [RapidAPI](https://rapidapi.com) | Apollo scraper (CodeCrafter) | Dashboard > Security |
| [Apollo.io](https://apollo.io) | Lead database (cookies for Olympus) | Browser DevTools |
| [Google Cloud](https://console.cloud.google.com) | Sheets API for exports | OAuth credentials |
| [Anthropic](https://console.anthropic.com) | Primary AI (enrichment, classification) | API Keys |
| [OpenAI](https://platform.openai.com) | Fallback AI (industry filtering) | API Keys |
| [LeadMagic](https://leadmagic.io) | Email verification (optional) | API Keys |

## Setup

The fastest way: open this repo in Claude Code and run `/setup`. It checks everything and walks you through any missing pieces.

Or manually:

```bash
# 1. Clone
git clone https://github.com/kmicpaps/lead_gen.git
cd lead_gen

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API keys
cp .env.example .env
# Edit .env and fill in your actual API keys

# 4. Set up Google OAuth (for Sheets export)
# Place credentials.json in the root directory
# Run any script that uses Sheets — it will prompt for OAuth on first run

# 5. Verify everything works
py execution/setup_wizard.py
```

## Slash Commands

This workspace includes 14 Claude Code slash commands for common tasks:

| Command | What it does |
|---------|-------------|
| `/new-apollo-list` | Full Apollo scraping campaign (scrape → merge → dedup → filter → export) |
| `/find-more-leads` | Rescrape an existing Apollo list for new leads |
| `/gmaps-leads` | Google Maps local business scraping |
| `/build-apollo-url` | Convert natural language to Apollo search URL |
| `/quality-filter` | Analyze and filter a lead list for quality |
| `/deduplicate-leads` | Remove duplicates across campaigns |
| `/research-client` | AI website analysis for client onboarding |
| `/cold-email-planning` | Plan cold email sequences |
| `/create-sales-sample` | Generate demo deliverables for prospects |
| `/onboard-new-client` | Set up a new client folder structure |
| `/pipeline-overview` | See all available capabilities |
| `/system-audit` | Deep codebase audit — find and fix bugs |
| `/maintain` | Quick structural health check |
| `/setup` | Workspace onboarding — verify deps, API keys, credentials |

See [PROMPTS.md](PROMPTS.md) for copy-paste prompt templates and detailed usage.

## Core Workflows

| Workflow | Directive | Key Scripts |
|----------|-----------|-------------|
| Apollo lead scraping | `lead_generation_v5_optimized.md` | `scraper_olympus_b2b_finder.py`, `scraper_codecrafter.py`, `scraper_peakydev.py` |
| Lead quality filtering | `lead_quality_filtering.md` | `lead_quality_analyzer.py`, `lead_filter.py` |
| Google Maps scraping | `gmaps_lead_generation.md` | `gmaps_niche_scraper.py`, `gmaps_lead_pipeline.py` |
| Cross-campaign dedup | `cross_campaign_deduplication.md` | `cross_campaign_deduplicator.py` |
| Industry enrichment | `enrich_industry.md` | `ai_industry_enricher.py` |
| Cold email copywriting | `cold_email_copywriting.md` | `cold_email_exporter.py` |
| Google Sheets export | (part of all workflows) | `google_sheets_exporter.py` |

## Directory Structure

```
lead_gen/
├── CLAUDE.md, AGENTS.md, GEMINI.md    # AI agent instructions (identical)
├── PROMPTS.md                          # Prompt library & slash command docs
├── .env                                # API keys (gitignored)
├── .env.example                        # API key template
├── credentials.json, token.json        # Google OAuth (gitignored)
├── requirements.txt
├── docs/                               # Reference documentation
├── directives/                         # SOPs (see directives/README.md)
│   └── _archived/                      # Superseded versions
├── execution/                          # Python scripts (55+)
│   └── _archived/                      # Old script versions
├── campaigns/                          # Client data (gitignored except template)
│   ├── _template/                      # New client template
│   └── {client_id}/
│       ├── client.json
│       ├── apollo_lists/{campaign}/
│       └── google_maps_lists/{campaign}/
├── .claude/skills/                     # Claude Code slash commands (11)
└── .tmp/                               # Intermediates (gitignored)
```

## Key Principles

- **Deliverables live in cloud** — Google Sheets are the output; local files are temporary
- **Everything in `.tmp/` can be deleted** and regenerated from source data
- **Self-annealing** — when things break, fix the tool, update the directive, system gets stronger
- **Deterministic execution** — push complexity into Python scripts; AI handles decision-making only
- **Registry-driven** — adding a new scraper = 3 steps (script + registry entry + normalizer)

## Adding a New Scraper

1. Create `execution/scraper_newname.py` following existing scraper patterns
2. Add a registry entry in `execution/scraper_registry.py`
3. Add a `normalize_newname()` function in `execution/lead_normalizer.py`

No orchestrator changes needed — the pipeline picks up new scrapers automatically.

## License

Private repository. All rights reserved.

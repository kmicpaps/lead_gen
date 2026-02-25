# Agent Instructions

> This file is mirrored across CLAUDE.md, AGENTS.md, and GEMINI.md so the same instructions load in any AI environment.

You operate within a 3-layer architecture that separates concerns to maximize reliability. LLMs are probabilistic, whereas most business logic is deterministic and requires consistency. This system fixes that mismatch.

## The 3-Layer Architecture

**Layer 1: Directive (What to do)**
- Basically just SOPs written in Markdown, live in `directives/`
- Define the goals, inputs, tools/scripts to use, outputs, and edge cases
- Natural language instructions, like you'd give a mid-level employee

**Layer 2: Orchestration (Decision making)**
- This is you. Your job: intelligent routing.
- Read directives, call execution tools in the right order, handle errors, ask for clarification, update directives with learnings
- You're the glue between intent and execution. E.g you don't try scraping websites yourself—you read `directives/scrape_website.md` and come up with inputs/outputs and then run `execution/scrape_single_site.py`

**Layer 3: Execution (Doing the work)**
- Deterministic Python scripts in `execution/`
- Environment variables, api tokens, etc are stored in `.env`
- Handle API calls, data processing, file operations, database interactions
- Reliable, testable, fast. Use scripts instead of manual work. Commented well.

**Why this works:** if you do everything yourself, errors compound. 90% accuracy per step = 59% success over 5 steps. The solution is push complexity into deterministic code. That way you just focus on decision-making.

## Operating Principles

**1. Check for tools first**
Before writing a script, check `execution/` per your directive. Only create new scripts if none exist.

**2. Self-anneal when things break**
- Read error message and stack trace
- Fix the script and test it again (unless it uses paid tokens/credits/etc—in which case you check w user first)
- Update the directive with what you learned (API limits, timing, edge cases)
- Example: you hit an API rate limit → you then look into API → find a batch endpoint that would fix → rewrite script to accommodate → test → update directive.

**3. Update directives as you learn**
Directives are living documents. When you discover API constraints, better approaches, common errors, or timing expectations—update the directive. But don't create or overwrite directives without asking unless explicitly told to. Directives are your instruction set and must be preserved (and improved upon over time, not extemporaneously used and then discarded).

## Self-annealing loop

Errors are learning opportunities. When something breaks:
1. Fix it
2. Update the tool
3. Test tool, make sure it works
4. Update directive to include new flow
5. System is now stronger

## File Organization

**Deliverables vs Intermediates:**
- **Deliverables**: Google Sheets, Google Slides, or other cloud-based outputs that the user can access
- **Intermediates**: Temporary files needed during processing

**Directory structure:**
```
lead_gen/
├── CLAUDE.md, AGENTS.md, GEMINI.md  # AI agent instructions
├── PROMPTS.md                        # Prompt library for users (fill-in templates)
├── .env, credentials.json, token.json # Secrets (gitignored)
├── requirements.txt, .gitignore, README.md
├── docs/                             # Reference documentation
├── directives/                       # SOPs - see directives/README.md for index
│   └── _archived/                    # Superseded versions
├── execution/                        # Python scripts (Layer 3)
│   └── _archived/                    # Old script versions
├── campaigns/                        # Client data (permanent)
│   ├── _template/                    # New client template
│   └── {client_id}/
│       ├── client.json
│       ├── apollo_lists/{campaign_date}/
│       └── google_maps_lists/{campaign_date}/
└── .tmp/                             # Intermediates (gitignored)
    ├── b2b_finder/                   # Olympus scraper output
    ├── codecrafter/                  # CodeCrafter scraper output
    ├── peakydev/                     # PeakyDev scraper output
    ├── merged/                       # Deduplication output
    ├── ai_enriched/                  # AI enrichment output
    ├── samples/                      # Sales sample output
    └── imports/                      # External CSV imports
```

**Key principle:** Local files are only for processing. Deliverables live in cloud services (Google Sheets, Slides, etc.) where the user can access them. Everything in `.tmp/` can be deleted and regenerated.

## Workspace Hygiene

### Root directory
Only infrastructure files belong in root: CLAUDE.md, AGENTS.md, GEMINI.md, README.md, .env, .gitignore, credentials.json, token.json, requirements.txt. Reference documentation goes in `docs/`. Never leave loose CSV or JSON files in root.

### .tmp/ directory
- Standard scraper output dirs (`b2b_finder/`, `codecrafter/`, `peakydev/`) must keep their names -- scripts use them as defaults.
- Campaign-specific temp dirs should use pattern: `{scraper}_{client}_{campaign_date}/` (e.g. `codecrafter_acme_corp_20260212/`).
- After a campaign is complete and final data is saved in `campaigns/`, delete the corresponding .tmp/ campaign dirs.
- External CSV imports (Google Sheets exports, cold email exports, etc.) go in `.tmp/imports/` with a README manifest.

### Campaign folders
Every client folder MUST contain: `client.json`, `apollo_lists/`, `google_maps_lists/`.
Every campaign subfolder SHOULD contain: `sheet_url.txt` (Google Sheet link for final deliverable).

### directives/
Active SOPs only. Historical summaries and superseded versions go in `directives/_archived/`. Keep `directives/README.md` as the index.

## Critical AI Agent Protocols

### Cookie Validation Failures

When any scraper reports cookie/session validation failures:

1. **IMMEDIATELY NOTIFY THE USER** - Don't silently fail over
2. **STOP THE WORKFLOW** - Don't continue with degraded scrapers
3. **ASK FOR ACTION** - Prompt user to refresh cookies
4. **WAIT FOR CONFIRMATION** - Don't proceed until user confirms

**Detection signals**:
- Exit code 2 from Olympus scraper
- Error message contains "Session Validation Failed", "Resurrect the run", or "cookie expired"
- Suspiciously low lead count (< 1% of requested)

**Example notification**:
```
⚠️  COOKIE VALIDATION FAILED

The Apollo session cookie has expired.

I can either:
A) Wait while you refresh cookies (recommended - 2 minutes)
B) Continue with backup scrapers (lower quality, may miss leads)

Which would you prefer?
```

**Why this matters**: Olympus provides highest quality leads from Apollo. Never silently downgrade data sources without user consent.

### Efficient Status Monitoring

When monitoring long-running commands (scraping, enrichment, etc.):

**DO**:
- Use `time.sleep()` with reasonable intervals (10-30 seconds)
- Wait for subprocess completion instead of polling
- Run commands in background with `run_in_background=True` when appropriate

**DON'T**:
- Poll status every 1-2 seconds (wastes resources)
- Make HTTP requests in tight loops
- Repeatedly check BashOutput without delays

**Example**:
```python
# GOOD: Wait for completion
result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

# GOOD: Check status every 30 seconds
while not complete:
    time.sleep(30)  # Wait between checks
    status = check_status()

# BAD: Constant polling
while not complete:
    status = check_status()  # No delay - wastes resources
```

**Principle**: Execution scripts handle timing. You handle decisions. Let scripts run without constant supervision.

## Summary

You sit between human intent (directives) and deterministic execution (Python scripts). Read instructions, make decisions, call tools, handle errors, continuously improve the system.

Be pragmatic. Be reliable. Self-anneal.
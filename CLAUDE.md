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

**1. NEVER read .env or credential files**
Never use `cat`, `Read`, or any tool to view `.env`, `credentials.json`, or `token.json`. These contain API keys and secrets that must not enter conversation context. Scripts access them via `os.getenv()` / `load_dotenv()` at runtime — that's the only safe path.

**2. Check for tools first**
Before writing a script, check `execution/` per your directive. Only create new scripts if none exist.

**3. Self-anneal when things break**
- Read error message and stack trace
- Fix the script and test it again (unless it uses paid tokens/credits/etc—in which case you check w user first)
- Update the directive with what you learned (API limits, timing, edge cases)
- Example: you hit an API rate limit → you then look into API → find a batch endpoint that would fix → rewrite script to accommodate → test → update directive.

**4. Update directives as you learn**
Directives are living documents. When you discover API constraints, better approaches, common errors, or timing expectations—update the directive. But don't create or overwrite directives without asking unless explicitly told to. Directives are your instruction set and must be preserved (and improved upon over time, not extemporaneously used and then discarded).

## Self-annealing loop

Errors are learning opportunities. When something breaks:
1. Fix it
2. Update the tool
3. Test tool, make sure it works
4. Update directive to include new flow
5. Log the change (see Documentation Protocol below)
6. System is now stronger

## Change Protocol

Before modifying execution scripts, directives, or skills:
1. Read the relevant directive for the workflow you're modifying
2. Check `directives/coding_standards.md` for the applicable integration checklist
3. Identify all files that need coordinated updates (use the "When to Update What" table)

After making changes:
1. Verify against the coding standards checklist
2. Run `py execution/system_health_check.py` to catch structural drift
3. Log the change (see Documentation Protocol below)
4. Update the directive if behavior changed
5. Update MEMORY.md if significant (new capability, architecture change)

## Documentation Protocol

The self-annealing loop says "update the directive" — this section specifies what else to update. Full SOP: `directives/system_maintenance.md`.

**After fixing bugs** (any workflow):
- Run `py execution/changelog_manager.py add --type fix --severity LEVEL --summary "..." --files changed_file.py`
- If found during an audit, also close the finding: `py execution/audit_logger.py fix --finding ID --description "..."`

**After completing feature work:**
- Run `py execution/changelog_manager.py add --type feature --summary "..." --files file1.py file2.py`
- Update MEMORY.md with a compressed summary (2-5 lines)
- If 5+ files changed, create `docs/CONTEXT_{feature_name}.md`

**After completing audits:**
- Run `py execution/audit_logger.py report --audit AUDIT_ID`
- Update MEMORY.md with compressed audit results (3-5 lines)

**After updating directives:**
- Run `py execution/changelog_manager.py add --type directive --summary "..." --files directives/name.md`

**What NOT to log:** routine campaign runs, client data operations, conversations that don't change code/docs.

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

When Olympus scraper reports cookie/session validation failures during a pipeline run:

1. **IMMEDIATELY NOTIFY THE USER** - Don't silently fail over
2. **Other scrapers continue** - V8 pipeline runs scrapers in parallel, so Olympus failure does NOT block backup scrapers
3. **ASK FOR ACTION** - Prompt user to refresh cookies for future runs
4. **Report degraded results** - Make clear that Olympus leads are missing from this run

**Detection signals**:
- Exit code 2 from Olympus scraper
- Error message contains "Session Validation Failed", "Resurrect the run", or "cookie expired"
- Suspiciously low lead count (< 1% of requested)

**Example notification**:
```
⚠️  COOKIE VALIDATION FAILED

The Apollo session cookie has expired.
Olympus returned 0 leads — backup scrapers (CodeCrafter/PeakyDev) continued normally.

Results are available but may be lower quality without Olympus data.
Please refresh cookies before the next run: https://app.apollo.io → DevTools → Copy cookie
```

**Why this matters**: Olympus provides highest quality leads from Apollo. Notify the user so they can refresh cookies for future runs, but don't discard valid data from other scrapers that already completed.

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
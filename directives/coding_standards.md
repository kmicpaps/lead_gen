# Coding Standards Reference

**Status:** Active
**Created:** 2026-02-26
**Purpose:** Codified rules and integration checklists. The AI agent reads this before and after making changes to ensure consistency.

## Script Structure

Every Python script in `execution/` must follow this structure:

```python
# [CLI] | # [LIBRARY] | # [ORCHESTRATOR] | # [HYBRID]
"""
Module docstring with purpose and usage examples.

Usage:
    py execution/script_name.py --input file.json --output-dir .tmp/
"""

import os
import sys
import argparse  # CLI scripts only

# Sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_leads, save_leads, load_json, save_json
from utils import log_ok, log_error, log_warn, log_info


def main():
    parser = argparse.ArgumentParser(description='...')
    # Use --kebab-case for all flags
    args = parser.parse_args()
    # ... logic ...
    return 0  # Exit code


if __name__ == '__main__':
    sys.exit(main())
```

**Markers:**
- `# [CLI]` — Run directly from command line
- `# [LIBRARY]` — Imported by other scripts, not run directly
- `# [ORCHESTRATOR]` — Pipeline controller that calls other scripts via subprocess
- `# [HYBRID]` — Both importable and has a CLI interface

**Exit codes:**
- `0` — Success
- `1` — Error (validation, file not found, bad input)
- `2` — Cookie/auth failure (scrapers only — triggers user alert)

**Rules:**
- Always use `from utils import ...` for JSON I/O, rate limiting, logging
- Never use raw `json.load`/`json.dump` — use `load_json`/`save_json`
- Never use inline rate limiters — use `RateLimiter` from utils
- Use `log_ok`/`log_error`/`log_warn` instead of raw `print()` for status messages
- Use `datetime.now(timezone.utc).isoformat()` for timestamps (never naive datetime)

## Normalized Lead Schema

The 17 canonical fields produced by `execution/lead_normalizer.py`. Every normalizer function must output exactly these fields:

| Field | Type | Example |
|-------|------|---------|
| `first_name` | str | "John" |
| `last_name` | str | "Smith" |
| `name` | str | "John Smith" |
| `title` | str | "CEO" |
| `email` | str | "john@acme.com" |
| `email_status` | str | "verified" or "" |
| `linkedin_url` | str | "https://linkedin.com/in/johnsmith" |
| `city` | str | "Riga" |
| `country` | str | "Latvia" |
| `company_name` | str | "Acme Corp" |
| `company_website` | str | "https://acme.com" |
| `company_linkedin` | str | "https://linkedin.com/company/acme" |
| `company_phone` | str | "+371 12345678" |
| `company_domain` | str | "acme.com" |
| `company_country` | str | "Latvia" (filled by enrichment, often empty initially) |
| `industry` | str | "Information Technology" |
| `source` | str | "olympus" / "codecrafter" / "peakydev" |

**Rules:**
- Missing values = empty string `""`, never `None`
- `source` must match the scraper's registry key
- `company_domain` derived from `company_website` if not provided (via `extract_domain_from_url()`)

## Directive Structure

Every directive in `directives/` follows this format:

```markdown
# Title

**Status:** Active | Draft | Deprecated
**Created:** YYYY-MM-DD
**Scripts:** `execution/script1.py`, `execution/script2.py`

## Purpose
1-2 sentences on what this directive accomplishes and why it exists.

## When to Use
Conditions or triggers for using this workflow.

## Workflow
Numbered steps with bash code blocks for CLI commands.

## Decision Points
Edge cases, user choices, error recovery.

## Primary Scripts
Bulleted list of execution/ scripts used, with one-line descriptions.
```

**Rules:**
- Header metadata (Status, Created, Scripts) is required
- Workflow steps must include actual CLI commands, not just descriptions
- Reference execution scripts by exact filename
- Keep directives as source of truth — skills reference them, not the other way around

## Skill Structure

Every skill in `.claude/skills/*/SKILL.md`:

```yaml
---
name: skill-name
description: 1-2 sentence description
argument-hint: [example input format]
disable-model-invocation: true  # true for workflows that cost money or modify data
allowed-tools: Read, Grep, Glob, Bash(py execution/specific_script.py *)
---

## Objective
What the skill accomplishes.

## Inputs
Parse from $ARGUMENTS. Ask for missing:
- **Input 1** — description
- **Input 2** — description

## Procedure
Read `directives/relevant_directive.md` for the full workflow. Key steps:
1. Step one
2. Step two

## Primary Scripts
- `execution/script.py` — description
```

**Rules:**
- Skills are thin wrappers — they reference directives, never duplicate content
- `disable-model-invocation: true` for anything that costs money or modifies data
- `allowed-tools` must list the specific scripts the skill needs to run

## Integration Checklists

### Adding a New Scraper

1. Write scraper script in `execution/` with `# [CLI]` marker
2. Add entry to `SCRAPER_REGISTRY` in `execution/scraper_registry.py` — all fields required:
   - display_name, script, cli_template, country_arg
   - output_dir, output_prefix, campaign_filename
   - max_leads, min_leads, test_leads
   - needs_cookies, cookie_exit_code
   - supported_filters (set of strings)
   - location_type, location_transform, industry_taxonomy, industry_transform
   - preflight_notes, preflight_warnings
   - timeout, pricing, time_benchmark
3. Add `normalize_{name}()` function in `execution/lead_normalizer.py`
4. Add `elif source == '{name}'` branch in `normalize_lead()` dispatcher
5. Test with smallest allowed batch (e.g., 25 leads)
6. Verify all 17 normalized fields populate correctly
7. Update `directives/lead_generation_v5_optimized.md` — scraper reference table, selection guide
8. Update `.claude/skills/new-apollo-list/SKILL.md` — primary scripts list
9. Update `PROMPTS.md` if user-facing usage changed
10. Update MEMORY.md Key Scripts section

### Modifying a Filter

1. Update `execution/lead_filter.py` — add/change filter logic
2. Update `execution/lead_quality_analyzer.py` — ensure report shows the new filter option
3. Update `directives/lead_quality_filtering.md` — add filter to workflow steps, update flag list
4. Update `.claude/skills/quality-filter/SKILL.md` — if flag syntax changed
5. If filter is auto-applied by orchestrator: update `execution/fast_lead_orchestrator.py`
6. Test: `py execution/lead_filter.py --help` to verify flags
7. Test: run on a small sample to verify counts

### Modifying Enrichment

1. Update the enrichment script in `execution/`
2. Update the corresponding directive in `directives/`
3. If output fields changed: update `execution/lead_normalizer.py` or `execution/google_sheets_exporter.py`
4. If AI costs changed: update cost estimates in the directive

### Changing Scraper Field Mappings

1. Run a small test batch (25 leads) to capture actual raw output
2. Update `normalize_{scraper}()` in `execution/lead_normalizer.py`
3. Verify all 17 normalized fields populate correctly
4. Update field mapping documentation in `directives/lead_generation_v5_optimized.md`

### Adding a New Slash Command

1. Create `.claude/skills/{name}/SKILL.md` following skill structure above
2. Create or reference a directive — skill is a thin wrapper
3. Add to `PROMPTS.md` Common Workflows or commands section
4. Add to `.claude/skills/pipeline-overview/SKILL.md` — command table + decision tree
5. Add to `directives/README.md` if a new directive was created
6. Update MEMORY.md Slash Commands section

## When to Update What

| You changed... | Also update... |
|----------------|----------------|
| Scraper script | registry, normalizer, directive, skill, MEMORY |
| Filter logic | directive, skill, orchestrator (if auto-applied) |
| Field names in a scraper | normalizer, sheets exporter, directive field mappings |
| CLI flags on a script | directive (usage examples), skill (if it references that flag) |
| New directive | `directives/README.md` index |
| New skill | pipeline-overview, PROMPTS.md, MEMORY |
| Pricing or speed benchmarks | scraper registry, directive comparison tables |
| Any code change | changelog entry via `py execution/changelog_manager.py add ...` |

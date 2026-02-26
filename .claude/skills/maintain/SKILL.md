---
name: maintain
description: Run lightweight structural health checks on the codebase — verify consistency between registry, normalizer, directives, skills, and scripts. Use after making changes or periodically.
argument-hint: [full | registry | normalizer | directives | markers | imports]
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(py execution/system_health_check.py *), Bash(py execution/changelog_manager.py *)
---

## Objective

Run structural consistency checks across the codebase. Find misalignments between the scraper registry, normalizer, directives, skills, and scripts. Report issues and offer to fix them.

This is NOT a deep audit (`/system-audit` does that). This is a quick pass that catches:
- Missing registry entries for new scrapers
- Missing normalizer functions
- Broken script references in directives/skills
- Missing script markers
- Syntax errors in scripts

## Inputs

Parse from `$ARGUMENTS`. Default scope is `full`.

- **Scope** — `full`, `registry`, `normalizer`, `directives`, `markers`, `imports`

## Procedure

1. Run health check:
   ```bash
   py execution/system_health_check.py --check SCOPE
   ```
   (Omit `--check` for full scope.)

2. Read the output. Group findings into:
   - **Failures** — things that are broken and will cause runtime errors
   - **Warnings** — things that are inconsistent but not immediately broken

3. Present findings to user:
   - Show count summary first
   - Then list each finding with category and details
   - For each failure, suggest what needs to change

4. If user approves fixes:
   - Fix each issue following `directives/coding_standards.md` integration checklists
   - Re-run health check to verify
   - Log changes: `py execution/changelog_manager.py add --type fix --summary "..." --files ... --tags maintenance`

5. If clean (no findings):
   - Report "All checks passed" with counts per category

## When to Run

- After adding or modifying a scraper
- After adding or modifying a directive or skill
- After any session with 5+ files changed
- Monthly, or when user requests it
- Before a system audit (quick sanity check first)

## Difference from /system-audit

| | /maintain | /system-audit |
|---|----------|---------------|
| Speed | ~10 seconds | 30-60 minutes |
| Depth | Structural consistency | Semantic correctness |
| Finds | Missing files, broken references, schema drift | Logic errors, data flow bugs, dead code |
| AI needed | Minimal (run script, read output) | Heavy (review every file) |
| When | After changes, periodically | Before versions, after large features |

## Primary Scripts

- `execution/system_health_check.py` — deterministic structural checks
- `execution/changelog_manager.py` — log any fixes made

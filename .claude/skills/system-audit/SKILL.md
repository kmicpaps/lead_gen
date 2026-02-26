---
name: system-audit
description: Run a systematic audit of the codebase, log findings, fix issues, and generate reports.
argument-hint: [full | execution | directives | skills | FILE_PATH]
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(py execution/audit_logger.py *), Bash(py execution/changelog_manager.py *), Bash(py execution/*.py --help)
---

## Objective

Run a structured audit of the lead generation system, log all findings, fix issues with user approval, and generate a report.

## Inputs

Parse from `$ARGUMENTS`. Default scope is `full` if not specified:

- **Scope** — `full`, `execution`, `directives`, `skills`, or a specific file path

## Procedure

Read `directives/system_maintenance.md` for the full audit SOP. Key steps:

1. **Start audit**: `py execution/audit_logger.py start --scope SCOPE --summary "..."`
2. **Review files** in scope — check for:
   - Logic errors (wrong conditions, swapped args, off-by-one)
   - Data flow issues (field name mismatches, lost data, wrong variable)
   - Dead code (unused imports, unreachable branches, orphan functions)
   - Documentation drift (wrong script names, outdated flags, stale examples)
   - Missing features referenced but not implemented
   - Performance issues (sequential when parallel, unnecessary I/O)
   - Security concerns (secrets in code, unsanitized input)
3. **Log each finding**: `py execution/audit_logger.py finding --audit ID --severity LEVEL --category CAT --summary "..." --file PATH`
4. **Present findings** to user, grouped by severity
5. **Fix with approval** — fix issues the user approves, skip what they defer
6. **Log each fix**:
   - `py execution/audit_logger.py fix --finding FID --description "..."`
   - `py execution/changelog_manager.py add --type fix --severity LEVEL --summary "..." --files FILE1 FILE2`
7. **Generate report**: `py execution/audit_logger.py report --audit ID`
8. **Update MEMORY.md** if 5+ files changed or significant patterns discovered

## Severity Definitions

| Level | Meaning |
|-------|---------|
| critical | Data loss, security hole, or system crash |
| high | Wrong output, silent data corruption, broken pipeline step |
| medium | Degraded quality, inefficiency, maintainability concern |
| low | Style, minor inconsistency, documentation drift |
| info | Observation, suggestion, no immediate action needed |

## What to Check by Scope

- **execution**: All `execution/*.py` — logic, data flow, imports, error handling
- **directives**: All `directives/*.md` — script references, flag names, step accuracy
- **skills**: All `.claude/skills/*/SKILL.md` — descriptions, procedures, flag references
- **full**: All of the above + `CLAUDE.md`, `PROMPTS.md`, `docs/`

## Decision Points

- **Critical/High findings**: Fix immediately (with user approval if paid APIs involved)
- **Medium findings**: Present batch, let user choose which to fix
- **Low/Info findings**: Log and include in report, fix only if quick

## Primary Scripts

- `execution/audit_logger.py` — finding tracking, status updates, reports
- `execution/changelog_manager.py` — change logging, markdown generation

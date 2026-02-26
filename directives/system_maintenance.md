# System Maintenance & Audit Logging

**Status:** Active
**Created:** 2026-02-26
**Scripts:** `execution/changelog_manager.py`, `execution/audit_logger.py`

## Purpose

Track changes, log issues found during audits, and maintain a queryable history of the system's evolution. Ensures institutional knowledge survives across AI agent sessions.

## When to Run Audits

Run a system audit when:
- Preparing for a new pipeline version (before starting feature work)
- After completing a large feature (5+ files changed)
- Monthly maintenance check
- After discovering a bug in production use
- User explicitly requests: `/system-audit`

## Quick Maintenance vs Deep Audit

For quick structural checks (broken references, missing registry entries, schema drift):
- Use `/maintain` — runs `execution/system_health_check.py`, takes ~10 seconds
- Run after any session where you modified scripts, directives, or skills

For deep semantic audits (logic errors, data flow bugs, dead code):
- Use `/system-audit` — follows the full audit procedure below, takes 30-60 minutes

Standards reference for coding conventions and integration checklists: `directives/coding_standards.md`

## Audit Procedure

### Step 1: Start the audit

```bash
py execution/audit_logger.py start --scope full --summary "Audit Round N: description"
```

Note the audit ID printed — you'll need it for logging findings.

### Step 2: Review execution scripts

For each script in `execution/` (skip `_archived/`, `__pycache__/`):
1. Check imports resolve (no broken sibling imports)
2. Check CLI `--help` matches actual behavior
3. Check field names match `lead_normalizer.py` schema
4. Check error handling (no bare except, no silent failures)
5. Check for dead code (unused variables, unreachable branches)
6. Check utils.py usage (raw `json.load` → `load_json`, inline rate limiters → `RateLimiter`)

### Step 3: Review directives

For each directive in `directives/`:
1. Script references exist and match current filenames
2. CLI flags documented match actual script `--help`
3. Step numbers are sequential and match current pipeline
4. No references to archived/removed scripts

### Step 4: Review skills

For each skill in `.claude/skills/`:
1. Script references match `execution/` scripts
2. `allowed-tools` match what the procedure needs
3. Procedure steps are consistent with their source directive

### Step 5: Log findings

For each issue found:

```bash
py execution/audit_logger.py finding --audit AUDIT_ID \
    --severity {critical|high|medium|low|info} \
    --category {logic_error|data_flow|dead_code|missing_feature|documentation|performance|security|style} \
    --summary "..." --file path/to/file.py --line NNN
```

### Step 6: Fix and log

After fixing each issue:

1. Log the fix in changelog:

```bash
py execution/changelog_manager.py add --type fix --severity SEVERITY \
    --summary "..." --files path/to/file.py --tags audit-round-N
```

2. Mark the finding as fixed:

```bash
py execution/audit_logger.py fix --finding FINDING_ID \
    --description "..." --changelog-id CHANGELOG_ENTRY_ID
```

### Step 7: Generate reports

```bash
py execution/audit_logger.py report --audit AUDIT_ID
py execution/changelog_manager.py report
```

### Step 8: Update knowledge base

- Update MEMORY.md with compressed summary (2-5 lines)
- If the audit was substantial (20+ findings), create `docs/CONTEXT_audit_roundN.md` with detailed notes

## Change Logging Protocol

### After fixing bugs (during any workflow, not just audits):

```bash
py execution/changelog_manager.py add --type fix --severity high \
    --summary "Fixed X in Y" --files execution/script.py --tags context
```

### After completing feature work:

```bash
py execution/changelog_manager.py add --type feature \
    --summary "Added Z capability" --files file1.py file2.py --tags feature-name
```

Then update MEMORY.md summary.

### After refactoring:

```bash
py execution/changelog_manager.py add --type refactor \
    --summary "Consolidated duplicate auth code" --files execution/google_sheets_exporter.py
```

### After updating directives:

```bash
py execution/changelog_manager.py add --type directive \
    --summary "Updated lead_generation_v5_optimized: added country verification" \
    --files directives/lead_generation_v5_optimized.md
```

### After deprecating scripts/features:

```bash
py execution/changelog_manager.py add --type deprecation \
    --summary "Moved error_handler.py to _archived" --files execution/_archived/error_handler.py
```

## When to Update MEMORY.md vs Create Context Doc

| Situation | Action |
|-----------|--------|
| Bug fix (1-3 files) | Changelog entry only |
| Small feature (< 5 files) | Changelog entry + 1-2 line MEMORY.md update |
| Large feature (5+ files) | Changelog entries + MEMORY.md section + `docs/CONTEXT_*.md` |
| Full audit (20+ findings) | Changelog entries + MEMORY.md section + `docs/CONTEXT_audit_*.md` |
| New client onboarded | MEMORY.md "Active Clients" update only |
| New learning discovered | MEMORY.md "Key Learnings" update only |

## Severity Definitions

| Level | Meaning | Examples |
|-------|---------|----------|
| critical | Data loss, wrong data delivered to client, security issue | Wrong leads exported, PII leaked |
| high | Silent data quality degradation, logic errors affecting output | OR→AND filter bug, wrong variable passed |
| medium | Functional but suboptimal, missing error handling | Silent failure on API error, duplicate code |
| low | Style, documentation, minor improvements | Wrong filename in docstring, dead code |
| info | Observations, not issues | "This pattern could be improved later" |

## Category Definitions

| Category | What it covers |
|----------|---------------|
| logic_error | Wrong boolean logic, wrong variable, wrong comparison |
| data_flow | Field name mismatch, wrong data passed between functions |
| dead_code | Unused variables, unreachable branches, obsolete functions |
| missing_feature | Gap that should exist but doesn't |
| documentation | Wrong docs, outdated references, missing help text |
| performance | Unnecessary work, N+1 patterns, missing concurrency |
| security | Credential exposure, injection, missing validation |
| style | Inconsistent patterns, naming, formatting |

## Edge Cases

- If a fix touches 10+ files, consider whether it's really a refactor (use `type=refactor`)
- If an audit finding is "not a bug" (intentional design), mark as `wontfix` with explanation
- If you discover a bug during normal work (not an audit), still log it in changelog but don't create a full audit record for a single finding
- Batch related findings into a single changelog entry when they share the same root cause (e.g. "dead lead_map in 3 scripts")

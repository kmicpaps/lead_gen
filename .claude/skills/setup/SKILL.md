---
name: setup
description: Check workspace readiness after a fresh clone or move. Verifies dependencies, API keys, credentials, and system health. Guides through fixing any issues.
argument-hint:
disable-model-invocation: true
allowed-tools: Read, Bash(py execution/setup_wizard.py *), Bash(pip install *), Bash(mkdir *), Bash(cp *)
---

## Objective

Verify the workspace is fully operational and guide the user through fixing any missing pieces. This is the first command to run after cloning the repo or moving it to a new machine.

## Procedure

1. Run the setup wizard:
   ```bash
   py execution/setup_wizard.py
   ```

2. Read the output. For each failing check, guide the user:

   **Missing Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   **Missing .env file:**
   ```bash
   cp .env.example .env
   ```
   Then tell the user to open `.env` and fill in their API keys. Read `.env.example` to show them which keys are needed and where to get them.

   **Missing API key:** Explain where to get it (the source is shown in the wizard output). Ask the user to fill it in and re-run.

   **Missing credentials.json (Google OAuth):**
   Walk the user through:
   1. Go to https://console.cloud.google.com
   2. Create a project (or select existing)
   3. Enable Google Sheets API and Google Drive API
   4. Create OAuth 2.0 "Desktop application" credentials
   5. Download the JSON file and save as `credentials.json` in project root
   6. First Sheets export will open a browser for OAuth consent

   **APOLLO_COOKIE format warning:**
   Explain: Olympus scraper needs Apollo session cookies in JSON array format.
   1. Log into https://app.apollo.io
   2. Use browser DevTools or EditThisCookie extension
   3. Export cookies as JSON array
   4. Paste into `.env` as `APOLLO_COOKIE=[{"name":"...","value":"..."},...]`
   This is optional — CodeCrafter and PeakyDev scrapers work without it.

   **Missing directories:** Create them automatically.

3. After user makes changes, re-run the wizard to verify:
   ```bash
   py execution/setup_wizard.py
   ```

4. When all checks pass: "Workspace ready. Type `/pipeline-overview` to see all available commands."

## What Gets Checked

| Category | Checks | Required? |
|----------|--------|-----------|
| Python dependencies | All packages in requirements.txt importable | Yes |
| .env file | File exists with API key template | Yes |
| APIFY_API_KEY | Apollo scraper access | Yes |
| ANTHROPIC_API_KEY | Primary AI (enrichment, classification) | Yes |
| OPENAI_API_KEY | Fallback AI (industry filtering) | Yes |
| APOLLO_COOKIE | Olympus scraper auth (JSON array) | Optional |
| LeadMagic-X-API-Key | Email verification | Optional |
| credentials.json | Google Sheets export | Yes (for exports) |
| Directory structure | campaigns/, .tmp/ | Yes |
| System health | Registry, normalizer, directives, scripts | Yes |

## Primary Scripts

- `execution/setup_wizard.py` — deterministic workspace readiness checks
- `execution/system_health_check.py` — structural consistency (called by setup_wizard)

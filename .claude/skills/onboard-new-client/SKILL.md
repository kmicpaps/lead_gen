---
name: onboard-new-client
description: Create a new client folder with metadata, ICP, and campaign structure ready for lead generation campaigns.
argument-hint: [company_name] [website_url]
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(py execution/client_manager.py *), Bash(py execution/client_discovery.py *)
---

## Objective

Set up a complete client folder structure with populated metadata, ready to run campaigns.

## Inputs

Parse from `$ARGUMENTS`. Ask for anything missing:

- **Company name** (required)
- **Website URL** (recommended) — enables AI-powered discovery
- **Contact email** (optional)
- **Industry** (optional)
- **What they sell** (optional)
- **Target audience** (optional)
- **Target locations** (optional)

## Procedure

Read `directives/client_management.md` for the full client management workflow.

Key steps:
1. If website URL provided, run discovery first:
   ```bash
   py execution/client_discovery.py --url WEBSITE_URL
   ```
   Present the ICP findings for user review.

2. Derive `client_id` from company name (lowercase, underscores, no special chars)

3. Create client folder using the template structure (see `campaigns/_template/README.md`):
   ```
   campaigns/{client_id}/
   ├── client.json
   ├── apollo_lists/
   └── google_maps_lists/
   ```

4. Populate `client.json` with:
   - Client metadata (name, website, contact)
   - ICP from discovery (or user input)
   - Empty campaign history

5. Present the populated `client.json` for user review before saving

## Primary Scripts

- `execution/client_manager.py` — client folder management
- `execution/client_discovery.py` — AI website analysis for ICP generation

## Decision Points

- **Website provided**: Run discovery automatically to suggest ICP.
- **No website**: Ask user to fill in ICP details manually.
- **Client already exists**: Warn user and ask if they want to update the existing client.

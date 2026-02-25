---
name: deduplicate-leads
description: Remove duplicate leads across multiple campaigns for the same client to prevent duplicate outreach.
argument-hint: [client_name]
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(py execution/cross_campaign_deduplicator.py *)
---

## Objective

Find and remove duplicate leads that appear across multiple campaigns for the same client, ensuring no one gets contacted twice.

## Inputs

Parse from `$ARGUMENTS`:

- **Client name** (required) — must have multiple campaigns in `campaigns/{client}/`

## Procedure

Read `directives/cross_campaign_deduplication.md` for the full process.

### Step 1: Dry Run

Always run a dry run first to show the overlap before making changes:

```bash
py execution/cross_campaign_deduplicator.py --client-id CLIENT_NAME --dry-run
```

### Step 2: Present Report

Show the user:
- Total leads across all campaigns
- Number of duplicates found
- Which campaigns have overlap
- How many unique leads remain

### Step 3: User Confirms

Wait for explicit approval before applying.

### Step 4: Apply

```bash
py execution/cross_campaign_deduplicator.py --client-id CLIENT_NAME
```

## Primary Scripts

- `execution/cross_campaign_deduplicator.py` — handles the full dedup logic

## Decision Points

- **No duplicates found**: Report clean result, no action needed.
- **High overlap (>50%)**: Note this is expected for rescrapes of similar Apollo URLs.

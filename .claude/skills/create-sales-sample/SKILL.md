---
name: create-sales-sample
description: Create a demo deliverable for a prospect showing the full lead generation capability — business analysis, sample leads, and email templates.
argument-hint: [prospect_website_url]
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(py execution/generate_sales_sample.py *), Bash(py execution/client_discovery.py *)
---

## Objective

Create a compelling sales sample that demonstrates the lead generation service to a prospective client. Includes business analysis, sample enriched leads, and example email templates.

## Inputs

Parse from `$ARGUMENTS`. Ask for anything missing:

- **Prospect website URL** (required) — the company you're pitching to
- **Company name** (optional) — inferred from website if not provided
- **Their target market** (optional) — if known, speeds up the process

## Procedure

Read `directives/generate_sales_sample.md` for the full multi-phase workflow.

### Phase 1: Discovery (Automated)

Run website analysis to understand the prospect's business:
```bash
py execution/client_discovery.py --url PROSPECT_URL
```

Present findings: what they sell, who they serve, recommended ICP, Apollo filter suggestions.

**Wait for user to review** before proceeding.

### Phase 2: User Provides Apollo URL

After reviewing the ICP suggestions, the user:
1. Opens Apollo with suggested filters
2. Refines in the browser UI
3. Pastes the final URL back

### Phase 3: Generate Sample

```bash
py execution/generate_sales_sample.py complete \
    --prospect-url PROSPECT_URL \
    --apollo-url "APOLLO_URL"
```

### Output

- Markdown report with:
  - Business analysis of the prospect
  - Sample enriched leads for their ICP
  - Example cold email templates
  - Professional formatting for review

## Primary Scripts

- `execution/generate_sales_sample.py` — orchestrates the full sample workflow
- `execution/client_discovery.py` — website analysis

## Decision Points

- **Discovery results look wrong**: Ask user to correct before proceeding to Apollo.
- **Apollo URL needed**: Pause after Phase 1 and wait for user input.

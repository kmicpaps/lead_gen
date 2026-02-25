---
name: cold-email-planning
description: Generate personalized cold email sequences for a client's lead list using reference copy style, compliance rules, and best practices.
argument-hint: [client_name]
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(py execution/*)
---

## Objective

Generate effective cold email sequences tailored to a client's ICP, using their reference copy style and current best practices. Produces ready-to-import email variants for sequencer tools (Instantly, Lemlist, etc.).

## Inputs

Parse from `$ARGUMENTS`. Ask for anything missing:

- **Client name** (required) — must exist in `campaigns/`
- **Lead list** (optional) — which campaign/list to personalize for
- **Number of emails in sequence** (optional, default 3)
- **Tone** (optional) — casual / professional / direct
- **Reference copy style** (optional) — describe or "check the client's reference_copies folder"

## Procedure

Read `directives/cold_email_copywriting.md` for the **complete directive** — this is the most detailed SOP. Follow it exactly.

Also read:
- `docs/anti_ai_writing_rules.md` if it exists (critical for natural-sounding copy)
- `docs/cold_email_best_practices.md` for compliance by country
- `docs/2026-02_cold_email_deep_dive.md` for frameworks

Key steps:
1. Load client context from `campaigns/{client}/client.json`
2. Load reference copies from `campaigns/{client}/reference_copies/` if they exist
3. Understand the ICP, value proposition, and pain points
4. Ask user for sequence parameters (length, tone, CTA type)
5. Generate email sequences following the directive's frameworks
6. Present for user review

## Critical Rules (from directive)

- **Plain text ONLY** — no HTML, no bold, no colors, no images
- **50-100 words per email** — shorter = higher reply rate
- **No links in Email 1** — zero links in first touch
- **No tracking pixels or open tracking**
- **No attachments, no calendar links**
- **Goal of Email 1 = get a REPLY**, not book a meeting
- **Subject lines under 50 characters**
- **Check country compliance** before sending (Germany, Italy, Poland = risky)

## Output

- Email sequence templates with personalization variables ({{first_name}}, {{company}}, etc.)
- Subject line A/B variants
- Spintax for variation
- Compliance checklist for target countries

## Decision Points

- **No reference copies exist**: Ask user for examples of emails they like, or generate from scratch using directive frameworks.
- **Target country is risky** (DE, IT, PL, JP, KR): Warn user about compliance risks before generating.
- **Lead list has no personalization data**: Suggest running enrichment first (icebreakers, casual names).

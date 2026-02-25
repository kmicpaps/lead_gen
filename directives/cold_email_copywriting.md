# Cold Email Copywriting

> Reference research: `docs/2026-02_cold_email_deep_dive.md`, `docs/cold_email_best_practices.md`, `docs/cold_outreach_strategy.md`
> Anti-AI writing rules: `docs/anti_ai_writing_rules.md` (MUST follow for all generated copy)

## Goal
Generate effective cold email sequences using a reference copy library for tone/structure guidance, combined with client context and lead personalization. Produces ready-to-use email variants for sequencer tools (Instantly, Lemlist, etc.).

## Input
- Client context (from `client.json` - value proposition, ICP, pain points)
- Lead data (from enriched leads - name, company, title, icebreaker)
- Reference copies (user-provided examples of effective emails)
- Campaign parameters (tone, CTA type, sequence length)

## Tools
- `execution/email_copywriter.py` - AI-powered email generator (to be created)
- Reference copies in `campaigns/{client}/reference_copies/`

## Output
- Email sequence variants (JSON for import to sequencer)
- Subject line A/B variants
- Compliance checklist

---

## Critical Rules (2025-2026 Best Practices)

These rules override any older assumptions. Based on practitioner data and benchmarks.

### Format Rules
- **Plain text ONLY** — no HTML, no bold, no colors, no images. Plain text goes to Primary inbox; HTML goes to Promotions.
- **No links in Email 1** — zero links in the first email. Max 1 link in follow-ups. Links trigger spam filters.
- **No tracking pixels or open tracking** — damages deliverability.
- **No attachments** — ever, in cold email.
- **No calendar links in cold emails** — too presumptuous from a stranger.

### Length Rules
- **50-100 words per email** (HIGHEST reply rate). Research: 50-125 words significantly outperform longer emails.
- **Under 100 words for Email 1** — shorter is better for first touch.
- **Under 50 characters for subject lines** — mobile shows 30-40 chars.

### Copy Rules
- **Lead with their problem, not your product** — never open with "My name is X and I work at Y."
- **One CTA per email** — ask a question, don't pitch a meeting.
- **Goal of Email 1 is a REPLY, not a meeting** — lower the ask.
- **Sound like a human texting a professional acquaintance** — not a marketing email.
- **Spintax for variation** — never send identical content across hundreds of sends (triggers spam filters).

### The Cold-to-Warm Bridge (Key Pattern)
The modern cold email model is NOT "cold email → book meeting → pitch."

It's: **Cold Email → Get Reply → Deliver Value (Loom/audit) → Meeting → Close**

This maps to the pitch deck + Loom workflow already built into this workspace.

### Micro-Segmentation (The #1 Differentiator)
**Never send the same email to 5,000 people.** Instead:
- Segment into 10 lists of 200-500 leads
- Tailor each email per segment (different angle, different pain point)
- 200-500 prospects per campaign is the sweet spot
- Result: 8-15% reply rate vs 3-5% for unsegmented blasts

**#1 predictor of success is LIST QUALITY, not copy quality.**

---

## Reference Copy Library

### Location
```
campaigns/{client_id}/reference_copies/
├── emails.json           # Full email examples
├── subject_lines.json    # Subject line examples (optional)
└── snippets.json         # Reusable copy snippets (optional)
```

### emails.json Format
```json
{
  "client_id": "acme_corp",
  "updated_at": "2026-02-03T10:00:00Z",
  "copies": [
    {
      "id": "intro_casual_1",
      "type": "full_email",
      "subject": "Quick question about {{company}}'s growth",
      "body": "Hi {{first_name}},\n\n{{icebreaker}}\n\nI help companies like {{company}} increase their ad ROI by 40%+ through optimized Google Ads campaigns.\n\nWould you be open to a quick call this week to see if we might be a fit?\n\nBest,\n{{sender_name}}",
      "style": "casual",
      "use_case": "initial_outreach",
      "performance": {
        "open_rate": 0.45,
        "reply_rate": 0.08,
        "sample_size": 500
      },
      "notes": "Works well for marketing decision-makers"
    },
    {
      "id": "followup_value_1",
      "type": "full_email",
      "subject": "Re: Quick question about {{company}}'s growth",
      "body": "Hi {{first_name}},\n\nJust following up on my previous email.\n\nI recently helped a similar company in {{industry}} reduce their cost-per-lead by 35% while increasing qualified leads.\n\nWould love to share how we did it and see if it could work for {{company}}.\n\n15 minutes this week?\n\n{{sender_name}}",
      "style": "casual",
      "use_case": "followup_1",
      "performance": {
        "open_rate": 0.38,
        "reply_rate": 0.05
      },
      "notes": "Use 3-4 days after initial email"
    }
  ]
}
```

### subject_lines.json Format (Optional)
```json
{
  "client_id": "acme_corp",
  "subject_lines": [
    {
      "text": "Quick question about {{company}}",
      "style": "question",
      "open_rate": 0.48
    },
    {
      "text": "{{first_name}}, saw your work at {{company}}",
      "style": "personal",
      "open_rate": 0.52
    },
    {
      "text": "Idea for {{company}}'s growth",
      "style": "value",
      "open_rate": 0.41
    }
  ]
}
```

### snippets.json Format (Optional)
```json
{
  "client_id": "acme_corp",
  "snippets": {
    "value_props": [
      "increase ad ROI by 40%+",
      "reduce cost-per-lead by 35%",
      "scale your campaigns without wasting budget"
    ],
    "social_proof": [
      "We've helped 50+ companies in {{industry}} achieve similar results",
      "Our average client sees results within 30 days"
    ],
    "ctas": [
      "Would you be open to a quick call this week?",
      "15 minutes this week work for you?",
      "Mind if I send over a few ideas?"
    ]
  }
}
```

---

## Adding Reference Copies

### Manual Method
1. Create `campaigns/{client_id}/reference_copies/` folder
2. Create `emails.json` with your best-performing emails
3. Use the format above, including performance metrics if available

### From Existing Sequences
```bash
# Import from CSV export (Instantly, Lemlist)
py execution/email_copywriter.py import-copies --client-id acme_corp --file my_sequences.csv
```

### Best Practices for Reference Copies
1. **Include 3-5 full emails** minimum for good variety
2. **Include both initial and followup** emails
3. **Add performance data** when available (helps AI prioritize styles)
4. **Note the use case** (initial, followup_1, followup_2, breakup)
5. **Describe the style** (casual, formal, direct, value-focused)

---

## Email Generation Process

### Step 1: Load Context
```python
# Automatically loaded from client folder
- client.json (company info, ICP, value proposition)
- reference_copies/emails.json (tone and structure examples)
```

### Step 2: Prepare Lead Data
Each lead should have:
- `first_name` (required)
- `company` or `org_name` (required)
- `title` (optional but recommended)
- `icebreaker` (optional - from icebreaker enrichment)
- `industry` (optional)
- `linkedin_bio` (optional)

### Step 3: AI Generation
Send to AI with structured prompt:

```
You are writing cold outreach emails for a B2B company.

CLIENT CONTEXT:
- Company: {client_name}
- Product/Service: {product_description}
- Value Proposition: {value_proposition}
- Target Pain Points: {pain_points}

REFERENCE COPIES (use these as tone/structure guides):
{reference_emails}

LEAD INFORMATION:
- Name: {first_name} {last_name}
- Company: {company}
- Title: {title}
- Industry: {industry}
- Personalization: {icebreaker}

Generate a {sequence_length}-email sequence for this lead.

For each email, provide:
1. Subject line (under 40 chars, lowercase, personalized)
2. Body (50-100 words max, plain text, no HTML)
3. Purpose (hook / value_add / proof / breakup)
4. Spintax variants for key phrases (2-3 alternatives per variable phrase)

RULES:
- Match the tone and style of the reference copies
- Use {{first_name}}, {{company}}, etc. as placeholders
- Include the icebreaker naturally in email 1 if provided
- Email 1: ZERO links. Goal is to get a reply, NOT book a meeting.
- Email 1: Never say what you sell. Never say "My name is X."
- Email 1: End with a question, not a pitch.
- Each followup must add new value (case study, stat, offer)
- Never write "just checking in" or "following up on my last email"
- Final email: polite breakup ("timing isn't right") — removes pressure
- Write like texting a professional acquaintance, not a marketing email
- No spam trigger words (free, guarantee, act now, click here)
- Include unsubscribe mechanism placeholder in signature

Return as JSON array.
```

### Step 4: Output Variants
Generate 2-3 variants per position in sequence for A/B testing:
- 2-3 subject line variants
- 2-3 body variants (different angles/hooks)

---

## Template Placeholders

### Standard Placeholders
| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{{first_name}}` | Lead's first name | "John" |
| `{{last_name}}` | Lead's last name | "Smith" |
| `{{full_name}}` | Full name | "John Smith" |
| `{{company}}` | Company name | "Acme Corp" |
| `{{title}}` | Job title | "Marketing Director" |
| `{{industry}}` | Industry | "SaaS" |
| `{{icebreaker}}` | Personalized icebreaker | "Saw your focus on..." |
| `{{sender_name}}` | Your name | "Alex" |
| `{{sender_company}}` | Client company | "Acme Corp" |

### Conditional Placeholders
```
{{#if icebreaker}}
{{icebreaker}}
{{else}}
I came across {{company}} and was impressed by your work.
{{/if}}
```

---

## Sequence Types

**Key stat: 60% of all cold email replies come from follow-ups.** Never send just 1 email.

### Sequence Length Impact

| Length | Total Reply Rate | Notes |
|--------|-----------------|-------|
| 1 email | 1-3% | Never do this |
| 2-3 emails | 5-8% | Minimum viable |
| **3-4 emails** | **8-12%** | **Sweet spot for 2025-2026** |
| 5-7 emails | 10-15% | Diminishing returns |

**3-step sequences outperform longer ones in 2025.** Test 3 vs 4.

### Recommended: 4-Email Sequence (Default)
```
Email 1 (Day 1) — The Hook: 50-80 words. Observation + problem + soft CTA.
Email 2 (Day 3-4) — The Value Add: Same thread. 40-70 words. One new data point or case study.
Email 3 (Day 7-8) — The Proof/Offer: 50-100 words. Specific result or offer resource (Loom, case study).
Email 4 (Day 12-14) — The Breakup: 30-50 words. "Looks like timing isn't right." Removes pressure, often triggers response.
```

**Breakup emails get 20-30% of total positive replies.** Never skip the breakup.

### Compact 3-Email Sequence
```
Email 1 (Day 1): Observation + problem + soft question CTA
Email 2 (Day 3): Case study / social proof + stronger CTA
Email 3 (Day 7): Breakup — "timing isn't right, feel free to reach out later"
```

### Extended 5-Email Sequence (High-value targets)
```
Email 1 (Day 1): Personalized hook + soft CTA
Email 2 (Day 3): Value-focused follow-up (new angle)
Email 3 (Day 7): Case study / social proof
Email 4 (Day 12): Loom offer or direct ask
Email 5 (Day 21-28): Hail Mary — new thread entirely, different hook
```

## Proven Copy Frameworks

### Framework 1: "Observation + Question" (Most Popular, Highest Performing)
```
Subject: {{first_name}}, quick thought

Hi {{first_name}},

Noticed {{company}} is using Typeform for your coaching assessment --
smart approach to qualifying leads.

Most coaches I talk to find their quiz completion rates plateau
around 40-50% because the question flow isn't optimized for
engagement scoring.

Curious -- are you seeing similar numbers, or have you cracked it?

{{signature}}
```

### Framework 2: PAS (Problem-Agitate-Solve)
```
Subject: your lead magnet

{{first_name}},

Most coaching businesses I audit are converting website visitors
at 3-5% with their PDF download pages.

That means for every 100 people who land on your site, 95+ leave
without ever entering your world.

Would it be worth a 10-minute chat to see if there's a quick
fix for {{company}}'s opt-in flow?

{{signature}}
```

### Framework 3: QVC (Alex Berman)
```
Subject: idea for {{company}}

{{first_name}},

Love what you're doing with {{specific_observation}}.

I have an idea that could help {{company}} turn your existing
website traffic into 3-5x more leads without changing your ad spend.

Would it be worth 2 minutes of your time for me to share it?

{{signature}}
```
**Berman's rules:** Never say what you sell in Email 1. Never include links. Never use more than 5 sentences. Goal of Email 1 is ONLY to get a reply.

### Framework 4: "Before-After-Bridge" (BAB)
```
Subject: coaching leads

{{first_name}},

Right now, most coaches in {{niche}} are spending $15-25 per
lead on PDF downloads that never get read.

Imagine if the same traffic converted at 35-50% through an
interactive quiz that pre-qualifies prospects before they book.

I put together a 2-minute breakdown of how this works.
Want me to send it over?

{{signature}}
```

### Framework 5: Case Study Follow-Up (Best for Email 2-3)
```
Subject: re: {{previous_subject}}

{{first_name}},

Quick follow-up -- thought you might find this relevant.

A {{niche}} coach we worked with was getting 4% opt-in rates
on her PDF guide. We rebuilt it as an interactive assessment
and her opt-in rate went to 38% within the first month.

Same traffic, same ads -- just a different lead capture approach.

Happy to walk you through what we changed if you're curious.

{{signature}}
```

### Spintax for Email Variation
Use spintax to prevent identical content across sends (triggers spam filters):
```
{Hey|Hi|Hello} {{first_name}},

{Noticed|Saw|Came across} {{company}}'s {website|coaching practice}
{while researching|recently} -- {love what you're building|impressive work}.

{Quick question|Curious about something}: {your lead magnet|your opt-in page}
{seems like it could|looks like it might} {convert better|capture more leads}
{with a few tweaks|with a different approach}.

{Would it be worth|Is it worth} {a quick chat|a 10-minute conversation}?

{{signature}}
```

## Follow-Up Best Practices

### The Bump (Day 2-3)
```
{{first_name}}, Wanted to make sure this didn't get buried -- any thoughts on the above?
```

### New Value (Day 5-7)
Add one new data point or case study. Under 60 words.

### The Breakup (Day 10-14)
```
Haven't heard back, so I'll assume the timing isn't right. Totally get it.
If improving your lead capture ever moves up the priority list, feel free to reach out.
All the best with {{company}}.
```

## Negative Reply Handling

| Reply Type | Response | Future Action |
|-----------|---------|---------------|
| Hard no | "Done -- removed. If [topic] ever comes up, feel free to reach out." | Remove immediately. Never re-contact. |
| Soft no (timing) | "Totally understand. Check back in a few months?" | Set 90-day follow-up |
| Redirect | "Happy to -- what's the best way to reach them?" | Follow up with referral |
| Skepticism | "Fair question -- found your email on your website. Here's my LinkedIn." | Be transparent. Some convert. |
| Already have it | "Nice! What platform? I specialize in optimization." | Pivot to audit offer |
| Angry | "Apologies -- removed. Won't happen again." | Remove. Don't engage further. |

---

## Command Examples

### Generate Sequence for Campaign
```bash
py execution/email_copywriter.py generate \
  --client-id acme_corp \
  --leads .tmp/enriched_leads.json \
  --sequence-type standard \
  --output-dir campaigns/acme_corp/email_sequences/
```

### Generate with Custom Tone
```bash
py execution/email_copywriter.py generate \
  --client-id acme_corp \
  --leads .tmp/enriched_leads.json \
  --tone casual \
  --cta-type soft \
  --sequence-length 3
```

### Preview Without Saving
```bash
py execution/email_copywriter.py preview \
  --client-id acme_corp \
  --lead-sample 5
```

### Export for Instantly
```bash
py execution/email_copywriter.py export \
  --format instantly \
  --input campaigns/acme_corp/email_sequences/latest.json \
  --output campaigns/acme_corp/email_sequences/instantly_import.csv
```

---

## Output Format

### JSON Output (for processing)
```json
{
  "campaign_id": "acme_corp_latvia_20260203",
  "generated_at": "2026-02-03T10:00:00Z",
  "sequence_type": "standard",
  "leads": [
    {
      "lead_id": "lead_001",
      "email": "john@acme.com",
      "first_name": "John",
      "company": "Acme Corp",
      "sequence": [
        {
          "position": 1,
          "delay_days": 0,
          "subject_variants": [
            "Quick question about Acme's growth",
            "John, saw your focus on digital marketing"
          ],
          "body_variants": [
            "Hi John,\n\nI noticed Acme's recent push into...",
            "Hi John,\n\nYour work on digital transformation..."
          ]
        },
        {
          "position": 2,
          "delay_days": 3,
          "subject_variants": ["Re: Quick question..."],
          "body_variants": ["Just following up..."]
        }
      ]
    }
  ]
}
```

### CSV Export (for Instantly/Lemlist)
```csv
email,first_name,company,subject_1,body_1,subject_2,body_2,subject_3,body_3
john@acme.com,John,Acme Corp,"Quick question...","Hi John...","Re: Quick...","Following up..."
```

---

## Legal Compliance by Region

> Full details: `docs/cold_email_best_practices.md` Section 1

### Safe Countries for Cold B2B Email

| Country | Safety | Key Rule |
|---------|--------|----------|
| **United States** | SAFEST | Opt-out only. No prior consent needed. Include physical address + unsubscribe. |
| **United Kingdom** (Ltd/LLP companies) | SAFE | Opt-out for corporate subscribers. **Caution:** Sole traders = same as consumers (need consent). |
| **France** | SAFE | CNIL permits B2B cold email with opt-out. |
| **Netherlands, Ireland, Belgium** | SAFE | Permitted if relevant to professional role. |
| **Nordics** (SE, DK, FI, NO) | SAFE | Generally permissive B2B. |
| **Australia, New Zealand** | SAFE (conditions) | Inferred consent from publicly listed email. |
| **Canada** | CAUTION | CASL: Narrow exception only. Up to CAD $10M fines. Verify each contact individually. |

### Countries to AVOID

| Country | Risk | Why |
|---------|------|-----|
| **Germany** | HIGH | UWG treats unsolicited email as unfair competition |
| **Italy** | HIGH | Garante has fined B2B cold emailers |
| **Poland** | HIGH | Prior consent required by Telecom Law |
| **Japan, South Korea** | HIGH | Prior opt-in required |
| **Brazil** | MEDIUM-HIGH | LGPD unclear on B2B exceptions |

### Compliance Checklist (All Campaigns)

**CAN-SPAM (US) — 7 Requirements:**
- [ ] Accurate "From" and routing info (no spoofing)
- [ ] Subject line not deceptive (no "Re:" on first email)
- [ ] Identifiable as advertising (context sufficient, no disclaimer needed)
- [ ] Physical mailing address included (PO Box or virtual office OK)
- [ ] Clear opt-out mechanism (unsubscribe link or "reply STOP")
- [ ] Honor opt-outs within 10 business days
- [ ] You're responsible for third-party senders

**GDPR (EU) — Legitimate Interest:**
- [ ] Legitimate interest documented (B2B direct marketing = explicitly recognized)
- [ ] Content relevant to professional role
- [ ] Clear identification of sender (company name, address, contact)
- [ ] Easy opt-out in every email (honored immediately, not 10 days)
- [ ] Right to erasure — if asked, delete data entirely (not just unsubscribe)
- [ ] Data minimization (only name, email, company)

**UK PECR (Additional):**
- [ ] Target is a corporate subscriber (Ltd, LLP, PLC) — NOT a sole trader
- [ ] Honest subject lines

**Universal Best Practices:**
- [ ] No false claims or misleading statements
- [ ] Personalization is accurate (names, companies verified)
- [ ] Reply-to address is monitored daily
- [ ] Unsubscribe link functional for 60+ days after send

---

## Quality Guidelines

### Subject Lines (Ranked by Open Rate)

| Pattern | Avg Open Rate | Example |
|---------|--------------|---------|
| Personalized with first name | 35-50% | `{{first_name}}, quick question` |
| Question format | 32-45% | `Struggling with lead gen?` |
| Lowercase, casual | 30-45% | `your lead magnet` |
| Reference to company | 35-50% | `idea for {{company}}` |
| Short (1-4 words) | 30-42% | `quick thought` |

**Rules:**
- Under 50 characters (ideally under 40) — mobile shows 30-40 chars
- Use lowercase for casual, personal feel
- Questions outperform statements by 10-20%
- Match colleague email tone — if a colleague wouldn't write it, it's too salesy
- **NEVER:** all caps, emojis, "Partnership opportunity", "FREE", dollar signs, "Re:" on a first email

### Body Copy
- **50-100 words** — this is the sweet spot (NOT 150-250)
- Plain text only, no HTML formatting
- One clear CTA per email — ask a question, not for a meeting
- Mobile-friendly (short paragraphs, 1-2 sentences each)
- Natural, conversational tone — write like texting a professional
- Zero links in Email 1, max 1 link in follow-ups

### Structure
```
[1-line personalized opening — shows you did research]
[1-2 sentences about the problem they likely have]
[1 sentence: your result/proof]
[1-line CTA — question format, easy to say yes to]
[Signature — name, title, company, one contact method]
```

### CTAs (Ranked by Reply Rate)

| CTA Type | Effectiveness | Example |
|----------|-------------|---------|
| Interest-based question | HIGHEST | "Would it be worth exploring?" |
| Low-commitment question | HIGH | "Mind if I send a 2-min video?" |
| Binary question | HIGH | "Is this relevant, or totally off base?" |
| Offer a resource | MODERATE | "Happy to share the case study if useful" |
| Calendly link | LOW | Too presumptuous for cold email |
| "Let's hop on a call" | LOWEST | Too big an ask from a stranger |

**The best CTAs lower the commitment bar. Ask for interest first. Book the call 2-3 replies later.**

### Personalization Tiers

| Tier | Type | Reply Rate Lift | Effort | When to Use |
|------|------|----------------|--------|-------------|
| 1 | Name/company merge | Baseline | Automated | All leads |
| 2 | Industry/role relevance | +10-15% over T1 | Low (segmented) | All leads |
| 3 | Specific observation (AI or manual) | +20-40% over T1 | 2-3 min/lead | B-leads |
| 4 | Content reference (their post/site) | +30-50% over T1 | 5+ min/lead | A-leads |
| 5 | Custom asset (Loom, audit, mockup) | +100-300% over T1 | 10-20 min/lead | Top 5% only |

**Sweet spot for scale: Tier 2-3.** Segment by niche + one AI-generated observation per lead. Gets 80% of personalization benefit for 20% of effort.

### Opening Lines

**What works:**
- Referencing their specific content or recent post
- Referencing a trigger event ("Congrats on launching...")
- Referencing their tech stack ("Noticed you're using Typeform...")
- A genuine, specific compliment about their work

**What kills conversion:**
- "I hope this email finds you well"
- "My name is X and I work at Y"
- "I'm reaching out because..."
- "We are a leading provider of..."
- "I was browsing your LinkedIn and..." (everyone knows it's automated)

---

## Integration with Workflow

### Full Workflow
```bash
# 1. Scrape leads
py execution/fast_lead_orchestrator.py --client-id acme_corp ...

# 2. Enrich leads (email, LinkedIn, icebreakers)
py execution/linkedin_enricher.py --input leads.json
py execution/ai_icebreaker_generator.py --input linkedin_enriched.json

# 3. Generate email sequences
py execution/email_copywriter.py generate \
  --client-id acme_corp \
  --leads icebreaker_enriched.json

# 4. Export to sequencer
py execution/email_copywriter.py export --format instantly ...

# 5. Import to Instantly/Lemlist and launch
```

---

## Error Handling

### Missing Reference Copies
- If no `reference_copies/emails.json`, use built-in default templates
- Warn user that output may not match their style
- Suggest adding reference copies for better results

### Missing Lead Data
- `first_name` missing: Skip lead or use "there" as fallback
- `company` missing: Skip lead
- `icebreaker` missing: Use generic opening or skip personalization

### AI Generation Errors
- Rate limit: Wait and retry
- Invalid output: Retry up to 3 times
- Timeout: Use shorter prompt or split batch

---

## What Kills Response Rates (Anti-Patterns)

| Mistake | Fix |
|---------|-----|
| Talking about yourself first | Lead with their problem |
| Too many links | Max 1 link. Zero in Email 1. |
| Feature dumping | Share one result: "Helped a health coach go from 4% to 38% opt-in" |
| Weak subject line | Test 3-5 variants before scaling |
| Too formal | Write like you'd text a professional acquaintance |
| No clear CTA | End with one specific, low-commitment question |
| Asking for too much too fast | Ask for interest first, not a meeting |
| HTML formatting | Plain text only. No bold, colors, images. |
| Not following up | 60% of replies come from follow-ups |
| Lying in subject line | "Re: Our conversation" when you've never spoken destroys trust |
| Calendar links in first email | Too presumptuous |
| Over 120 words | Anything above this drops reply rates significantly |
| Fake personalization | "I was browsing your LinkedIn..." — everyone knows |

## Benchmarks & Metrics

### Campaign Performance Targets (Month 3+)

| Metric | Target | If Below |
|--------|--------|----------|
| Emails sent/month | 2,000-4,000 | Add accounts/domains |
| Open rate | >40% | A/B test subjects, check SPF/DKIM/DMARC |
| Reply rate | >5% | Improve personalization, opening line |
| Positive reply rate | >2% | Review offer/CTA/targeting |
| Bounce rate | <2% | Clean list, use verification |
| Spam complaints | <0.1% | Pause if >0.3%. Check content. |

### Industry Benchmarks (2025-2026)

| Metric | Average | Good | Great | Top 1% |
|--------|---------|------|-------|--------|
| Open rate | 27-40% | 40-50% | 50-60% | 65%+ |
| Reply rate | 3-5% | 5-8% | 8-15% | 15-25% |
| Positive reply rate | 1-2% | 2-4% | 4-8% | 8%+ |
| Bounce rate | 2-5% | <2% | <1% | <0.5% |

### Diagnostic Table

| Low Metric | Likely Cause | Fix |
|-----------|-------------|-----|
| Open rate <25% | Subject line or deliverability | A/B test subjects, check SPF/DKIM/DMARC |
| Reply rate <2% | Copy, targeting, or CTA | A/B test opening + CTA, narrow targeting |
| Positive reply <1% | Offer mismatch or wrong audience | Review ICP, test different angles |
| Meetings <50% of positive replies | Booking friction or slow follow-up | Reply within 2 hours, Calendly after interest |
| Show rate <75% | No confirmation/reminder | Calendar invite + remind 24h + 1h before |

### A/B Testing Priority

Test ONE variable at a time. 200+ sends per variant.

| Priority | Variable | Expected Impact |
|----------|----------|-----------------|
| 1 | Subject line | Can 2-3x open rate |
| 2 | Opening line | Can 1.5-2x reply rate |
| 3 | CTA | Can 1.5-2x reply rate |
| 4 | Email length | Can 1.2-1.5x reply rate |
| 5 | Send time | Can 1.1-1.3x open rate |

### Optimal Send Times
- **Best days:** Tuesday (best), Wednesday, Thursday
- **Best times (recipient local):** 8-10 AM (best), 1-2 PM, 4-5 PM
- **For coaches/solopreneurs:** Test 7-9 PM evening sends

## Sending Infrastructure Requirements

> Full details: `docs/cold_email_best_practices.md` Sections 3-4

### Domain Setup
- **NEVER send cold email from primary business domain**
- Use variants: getbrand.com, trybrand.com, brand.co, brand.io
- 2-3 email accounts per domain
- Budget 2-3 replacement domains per quarter (domains get burned)
- SPF, DKIM, DMARC on every domain (non-negotiable)

### Volume per Account
| Account Type | Max Cold/Day | Max Total/Day |
|-------------|-------------|---------------|
| Google Workspace (new) | 20-30 | 40-50 |
| Google Workspace (warmed 4+ weeks) | 30-40 | 50-75 |
| Microsoft 365 (warmed) | 30-50 | 60-80 |

### Warmup Timeline
| Week | Volume | Activity |
|------|--------|----------|
| 1 | 5-10/day | Manual emails + warmup tool |
| 2 | 10-20/day | Warmup + small cold sends (5-10) |
| 3 | 20-30/day | Gradual increase. Monitor bounces. |
| 4+ | 30-50/day | Full volume. Keep warmup running. |

### When to Replace a Domain
- Google Postmaster Tools shows "Bad" reputation
- Consistently landing in spam
- Blacklisted on 2+ major lists (check MXToolbox)
- Open rates below 15%
- Spam complaints above 0.3%

---

## Limitations

1. **Reference copies needed**: Best results require user-provided examples
2. **AI variability**: Output may vary between runs
3. **Manual review recommended**: Always review before sending
4. **Sequencer-specific**: Export formats may need adjustment
5. **No tracking integration**: Doesn't connect to email analytics

## Future Enhancements

1. **Performance learning**: Use reply data to improve templates
2. **Sequencer API integration**: Direct push to Instantly/Lemlist
3. **Multi-language support**: Generate emails in target language
4. **Tone analyzer**: Score emails for professionalism/casualness
5. **Spam score checker**: Predict deliverability issues
6. **Spintax generator**: Auto-generate spintax variants from base copy
7. **Lead temperature scoring**: Score leads by engagement signals

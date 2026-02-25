# Anti-AI Writing Rules for Cold Email

> Reference document for all cold email copy generation. These rules apply to templates, AI-generated icebreakers, and any automated copy in the pipeline.

## Why This Matters

Prospects receive 10-20 cold emails per week. AI-generated ones share recognizable patterns. If your email looks like the other 15 AI emails they got this week, it goes straight to trash. The goal is not "good copy" -- it's "copy that doesn't trigger the AI detector in the reader's brain."

---

## Banned Patterns

### 1. "Compliment -- But" Structure
The #1 AI giveaway. Nearly every AI icebreaker follows:

> "Your [thing] is [positive adjective] -- but [problem statement]. A [solution] would [outcome]."

**Why it fails:** Prospects getting 2-3 of these from the same campaign instantly see the pattern. It's the AI equivalent of a fingerprint.

**Fix:** Lead with the observation or problem directly. Skip the fake compliment.
- BAD: "Your website looks great -- but it loads slowly on mobile."
- GOOD: "Jūsu lapa ielādē 12s mobilajā. Vidējais ir 2.5s."

### 2. Em-Dash Character
The Unicode em-dash (—) appears in ~59% of AI-generated text. Real humans writing quick emails use `--` at best, or restructure into separate sentences.

**Fix:** Never use — in templates. Use periods or `--` if absolutely needed.
- BAD: "Jūsu lapa nav optimizēta mobilajam — vairāk kā 70% meklējumu notiek telefonos"
- GOOD: "Jūsu lapa nav optimizēta mobilajam. 70% meklē no telefona."

### 3. "I noticed..." / "I came across..."
Stock AI opener. Our own directive flags "I was browsing your LinkedIn and..." as "everyone knows it's automated."

**Fix:** State the observation directly without framing it as a discovery.
- BAD: "Es pamanīju, ka Jūsu mājaslapa ielādējas lēni."
- GOOD: "Jūsu lapa ielādē 12s mobilajā."

### 4. Bullet-Point Lists in Email Body
Plain text cold emails don't have bullet points or numbered lists. Real people write sentences.

**Fix:** Convert any list into 2-3 short sentences.

### 5. Transition Words
"Furthermore", "Additionally", "Moreover", "In addition" -- AI loves these. Humans never use them in short emails.

**Fix:** Just start the next sentence. No connective tissue needed in a 60-word email.

### 6. Symmetrical Sentence Structure
AI writes parallel constructions: "X does Y. X also does Z. This means W."

**Fix:** Vary sentence lengths aggressively. Mix questions with statements. Let it feel slightly messy.

### 7. Hedging Language
"might be able to", "could potentially", "it's possible that" -- AI hedges everything to sound safe.

**Fix:** Be direct. "Palīdzam" not "varētu palīdzēt." Match Oto's existing tone (confident, direct).

### 8. Perfect Grammar Everywhere
Real Latvian business emails have minor informalities. AI produces grammatically perfect text that feels sterile.

**Fix:** Match the sender's natural writing style. Contractions, colloquial phrasing, occasional short fragments are OK.

---

## Icebreaker / Insight Line Rules

The `{{insight_lv}}` merge field is the data-driven observation inserted into each email.

- **Max 15 words.** It's a HOOK, not a paragraph.
- **State the fact. Don't explain why it matters.** The email body does that.
- **No em-dashes. Use periods.**
- **Use actual numbers from the lead's data** (load time, score, etc.)

### Word Count Comparison

| Type | Avg Words | Target |
|------|-----------|--------|
| Bad AI icebreaker | 41 | -- |
| Good insight hook | 8-15 | This |
| Oto's actual style | 10-20 per sentence | Reference |

### Examples

BAD (41 words):
> "Jūsu mājaslapa ielādējas 12.6 sekundēs mobilajā ierīcē -- tas ir 5 reizes lēnāk nekā nozares vidējais rādītājs, kas ir 2.5 sekundes, un tas nozīmē, ka potenciālie klienti aiziet."

GOOD (11 words):
> "Jūsu lapa ielādē 12s mobilajā. Vidējais ir 2.5s."

---

## Structural Variety Rules

If a prospect receives emails from the same campaign, or if a spam filter analyzes a batch, repeating structures get flagged. Each template MUST feel structurally distinct.

### 6 Opener Patterns (rotate across segments)

1. **Bare fact:** "Jūsu lapa ielādē 12s mobilajā."
2. **Question:** "Cik ātri ielādējas Jūsu lapa mobilajā?"
3. **Context first:** "70% klientu meklē no telefona."
4. **Comparison:** "Vidējā lapa ielādē 2.5s. Jūsu -- 12s."
5. **Direct action:** "Pārbaudīju Jūsu lapu ar Google rīku."
6. **Result-first:** "Lēna lapa maksā klientus."

### Spintax for Within-Segment Variety

Even within a segment, use `{A|B|C}` spintax so no two emails are identical:
```
{Sveiki|Labdien},

{Pārbaudīju|Apskatīju|Palūkoju} {{business_name}} {mājas lapu|interneta lapu}.
{{insight_lv}}
```

---

## QA Checklist (Automated)

The `cold_email_exporter.py --qa` flag should scan for these before export:

| Check | Threshold | Action |
|-------|-----------|--------|
| Em-dash (—) in any field | 0 allowed | ERROR: replace with period or `--` |
| Insight field > 15 words | 0 allowed | ERROR: shorten |
| "Compliment-But" pattern (positive adj + "bet"/"taču"/"tomēr") | 0 allowed | WARN: restructure |
| Total email body > 100 words | 0 allowed | ERROR: cut |
| Same first word in >2 sentences across batch | flag | WARN: vary openers |
| Bullet points or list markers | 0 allowed | ERROR: rewrite as sentences |
| Hedging words: "iespējams", "varētu", "varbūt" | flag | WARN: make direct |

---

## Why Templates > Per-Lead AI Generation

For campaigns under 1,000 leads, hand-written templates with merge fields beat AI-generated unique copy:

1. **QA once, not 349 times.** Review 10 templates for AI patterns. Done.
2. **Spintax + lead data = unique enough.** Each email differs by business name, insight, niche, city, and spintax choices.
3. **Latvian grammar accuracy.** AI makes mistakes with Latvian noun cases and inflections. Native-reviewed templates are safer.
4. **The data IS the personalization.** "Your site loads in 12s" is more impactful than any AI-generated sentence.
5. **No AI cost.** Template merging is free and deterministic.

**When to switch to AI-generated:** If scaling past 1,000+ leads per campaign with highly diverse segments where 10 templates feel insufficient.

---

## References

- `directives/cold_email_copywriting.md` -- copy frameworks, sequence structure
- `docs/2026-02_cold_email_deep_dive.md` Section 6.4 -- "The AI Saturation Problem"
- `docs/cold_email_best_practices.md` Section 2.2-2.6 -- tone and structure
- `campaigns/_template/reference_copies/200 iq.md` -- Oto's actual Latvian writing style
- `campaigns/_template/reference_copies/examples.md` -- English reference copies

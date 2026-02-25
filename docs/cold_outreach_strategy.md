# FixMyWorkflow Cold Outreach Strategy Report

> Comprehensive research on hyper-personalized outreach strategies for selling quiz funnel services to coaches and consultants.
> Compiled: February 2026 | Sources: 50+ industry reports, benchmarks, and case studies (2024-2026)

---

## Table of Contents

1. [Business Context](#1-business-context)
2. [The Target Market: Coaches](#2-the-target-market-coaches)
3. [Where Coaches Hang Out](#3-where-coaches-hang-out)
4. [Outreach Strategy Deep Dives](#4-outreach-strategy-deep-dives)
   - 4.1 Loom/Video Outreach
   - 4.2 Cold Email at Scale
   - 4.3 LinkedIn DM Strategies
   - 4.4 Multi-Channel Warm-Up Sequences
   - 4.5 Instagram DM Outreach
   - 4.6 Facebook Group Prospecting
   - 4.7 Hybrid Multi-Channel Approaches
   - 4.8 Community/Referral-Based
5. [Strategy Comparison Matrix](#5-strategy-comparison-matrix)
6. [Lead Sourcing Methods](#6-lead-sourcing-methods)
   - 6.1 Apify Scraping Playbook
   - 6.2 Free/Low-Cost Methods
   - 6.3 Finding the Warmest Leads (Intent Signals)
7. [Lead Qualification Framework](#7-lead-qualification-framework)
8. [Pipeline Management](#8-pipeline-management)
9. [The Unit Economics](#9-the-unit-economics)
10. [Recommended Strategy](#10-recommended-strategy)
11. [Sources](#11-sources)

---

## 1. Business Context

### The Business: FixMyWorkflow

FixMyWorkflow (magnet.fixmyworkflow.com) is a quiz funnel agency targeting coaches and consultants. The core value proposition: help coaches replace low-converting PDF lead magnets with interactive quiz funnels built on ScoreApp, dramatically increasing their lead capture and qualification rates.

### Products & Offers

| Offer | Price | Delivery | Description |
|-------|-------|----------|-------------|
| **Quiz Funnel Roadmap** (primary focus) | $497 | 1 week | 45-min audit + strategy session. Coach walks away with quiz strategy, question framework, scoring logic, and results page plan. The foot-in-the-door offer. |
| **Custom Quiz Build** (limited, 1-2/month) | $2,500+ | 2-4 weeks | Full ScoreApp quiz funnel: landing page, questions, scoring logic, results tiers, email follow-up sequence, analytics. Cherry-picked clients only. |
| **$27 Tripwire Digital Product** | $27 | Instant digital delivery | Self-serve quiz funnel toolkit. Entry point in the existing funnel: Quiz → $27 Tripwire → Upsell Sequence → $497 Upsell. Currently unfunded (no ad budget to drive traffic). |
| **ScoreApp Affiliate** | Recurring commission | Passive | Every client who signs up for ScoreApp through FixMyWorkflow generates ongoing affiliate revenue. Stacks passive income on top of service fees. |

### Revenue Goals

| Metric | Target |
|--------|--------|
| Primary goal | Close 2x $497 deals per week consistently |
| Weekly revenue | ~$994/week from $497 deals |
| Monthly revenue | ~$4,300/month baseline |
| Stretch (with upsells) | $5,000-$7,000/month (1x $2,500 deal + $497 deals + affiliate) |
| Delivery capacity | 2-3 $497 builds/week (1-week turnaround each) |
| $2,500 capacity | 1 per month max (too niche to outsource, requires full attention) |

### Why Focus on $497 Over $2,500

1. **Speed of delivery** — $497 builds are standardized ScoreApp setups. Can be delivered in 1 week. Can handle 2-3 simultaneously.
2. **Portfolio building** — Each $497 build adds to the case study library, making future sales easier.
3. **ScoreApp affiliate stacking** — Every client who stays on ScoreApp generates recurring commission. Volume = more recurring revenue.
4. **Outsourcing path** — $497 builds can eventually be offloaded to freelancers (ScoreApp is accessible enough). $2,500 projects are too niche and complex.
5. **Consistency over peaks** — 2x $497/week = predictable $4K+/month. One $2,500 deal/month is a bonus, not the foundation.
6. **Upsell pipeline** — The best $497 clients naturally want more. Cherry-pick favorites for $2,500 upgrades.

### Existing Systems & Tools

| System | Status | Purpose |
|--------|--------|---------|
| **Pitch Deck Generator** | Built | `execution/create_pitch_deck.py` — AI-generates personalized 10-slide pitch decks for cold outreach. Clones Google Slides template, replaces 103 placeholders with lead-specific content. |
| **Proposal Generator** | Built | `execution/create_project_workflow.py` — Multi-template proposal generator with Notion integration. Creates project, note with proposal, and tasks automatically. |
| **Loom Workflow** | Manual | Record personalized Loom walking through the pitch deck. Show lead's specific niche, pain points, quiz opportunities. |
| **Notion CRM** | Existing (needs outreach pipeline) | Already used for projects, notes, tasks. Needs a "Cold Outreach Pipeline" database for tracking leads through stages. |
| **Instantly** | Active account | Cold email sending platform. Already set up. Has spare email addresses for sending. |
| **Apify** | Active account | Web scraping platform. Used for lead sourcing. |
| **Existing Funnel** | Built, unfunded | Quiz → $27 Tripwire → Upsell Email Sequence → $497 Upsell. Complete but no ad budget to drive traffic. This funnel could be activated once revenue allows ad spend. |
| **n8n** | Available | Automation platform. Can be used to connect Apify scraping → lead enrichment → CRM → outreach sequences. |

### Key Constraint: Bootstrap Budget

No spare cash for ads or expensive tools. The outreach strategy must work with:
- **Instantly** (already have it)
- **Apify** (already have it)
- **Spare email addresses** (already have them)
- **Free or very cheap tools** for everything else
- **Sweat equity** — willing to put in 5+ hours/day of manual outreach work early on
- **Total tool budget**: Under $100/month for new tools

### The Existing Funnel (Currently Dormant)

```
[Quiz Lead Magnet] → [$27 Tripwire Digital Product] → [Upsell Email Sequence] → [$497 Quiz Funnel Roadmap]
```

This funnel is built and ready. The bottleneck is traffic — no ad budget to drive prospects into it. Cold outreach serves a dual purpose:
1. **Direct sales** — Close $497 deals through personalized outreach
2. **Funnel feeding** — Leads who aren't ready for $497 can be pointed to the quiz → tripwire funnel for a smaller conversion

Once revenue from cold outreach reaches $1,000-$2,000/month, a portion can be allocated to ads driving traffic to the quiz funnel, creating a second revenue stream.

---

## 2. The Target Market: Coaches

### Market Size

- **232,000+** coaches in the US alone — a **$16 billion** industry that has more than doubled since 2016 (BusinessWire / ResearchAndMarkets)
- **122,974** coach practitioners worldwide, up 54% since 2019 (ICF Global Survey)
- Global executive coaching market: **$9.3 billion**, projected $27B by 2032
- US business coaching: **$18.1 billion**, growing 5.3% annually
- Average coaching fee: **$234/hour** globally
- Average US coach income: **$71,719/year**
- Average workload: **11.6 hours/week** coaching, **12.4 active clients**

### Demographics

- **74% female**, majority Gen X (53%) and Boomers (35%)
- Most are solopreneurs (1-person operations)
- Tech-savvy enough to use basic SaaS tools but not developers
- Value relationships and personal connections over hard sales

### Why Coaches Need Quiz Funnels

The data makes a compelling case:

| Metric | PDF Lead Magnet | Quiz Lead Magnet | Improvement |
|--------|-----------------|------------------|-------------|
| Opt-in conversion rate | 3-10% | 30-50% | 3-10x |
| Engagement time | Seconds (download and forget) | ~4 minutes | 40x+ |
| Lead qualification | None (everyone gets the same PDF) | Automatic (scoring segments leads) | Infinite |
| Quiz completion rate | N/A | 65-75% (with proper design) | N/A |
| Quiz-to-lead conversion | N/A | 8-18% (EU, ungated results) | N/A |
| Ads mentioning "quiz" | N/A | 20% lower CPC | Cheaper traffic |

Sources: Interact (80M+ leads generated), ScoreApp, EU quiz case studies research

### The Coach's Core Problem

Most coaches are stuck in a loop:
1. Create a PDF lead magnet ("10 Steps to Transform Your Life")
2. Run ads or post on social → drive traffic to opt-in page
3. Get 3-10% conversion → most visitors bounce
4. Downloaded PDFs never get read → leads go cold
5. Discovery calls are filled with unqualified tire-kickers
6. Coach wastes time on calls that don't convert

**A quiz funnel fixes this by:**
- Engaging prospects for 4+ minutes (not 4 seconds)
- Qualifying leads through scoring before the call
- Segmenting results pages by readiness level
- Creating a natural conversation starter ("Your quiz said X — let's talk about that")
- Building a value ladder (low scorers get free content, high scorers get call invites)

---

## 3. Where Coaches Hang Out

### Platform Usage by Coach Type

| Coach Type | Primary Platform | Secondary | Tertiary |
|---|---|---|---|
| Executive/Business Coach | LinkedIn | Facebook Groups | YouTube |
| Life Coach | Instagram | Facebook Groups | TikTok |
| Health/Wellness Coach | Instagram | TikTok | Facebook Groups |
| Mindset Coach | Instagram | TikTok | YouTube |
| Career Coach | LinkedIn | YouTube | Facebook Groups |
| Fitness Coach | Instagram | TikTok | YouTube |
| Relationship Coach | Instagram | TikTok | YouTube |

### LinkedIn (Primary for B2B coaches)
- 80% of B2B social media leads come from LinkedIn
- Executive coaches, business coaches, and career coaches treat it as their primary content + acquisition platform
- Thought leadership posts, newsletter publishing, and direct outreach are standard
- LinkedIn Groups: International Coach Federation (~100K members), Coaching Zone, Professional Life Coaches Network

### Instagram (Primary for life/wellness/mindset coaches)
- Visual-centric, ideal for inspirational content, testimonials, behind-the-scenes
- Heavy hashtag culture: #lifecoach, #businesscoach, #coachesofinstagram, #coachingbusiness
- Many coaches list their email in bio or have a "Contact" button on business profiles
- Coaches with <1,000 followers see 79.5% more interactions using 11+ hashtags

### Facebook Groups (All coach types — the community hub)
- Described as "engagement goldmines" for coaches
- Key groups: Speakers/Authors/Coaches, Simply Smart Business, Step into the Spotlight, The Good Alliance
- Best for nurturing, live streams, group coaching programs
- Pensight maintains a curated list of Top 100 Facebook Groups for Coaches

### TikTok (Growing — younger/newer coaches)
- Life, relationship, business, and career coaching all thrive on TikTok
- 40/60 split recommended: 40% trend content, 60% evergreen coaching advice
- Functions more as a discovery platform than a community
- Good for finding newer coaches who are actively marketing

### YouTube (Long-form thought leaders)
- Major coaching channels: Tony Robbins, Mel Robbins, Brooke Castillo (Life Coach School — $37M revenue), Brendon Burchard
- Second-largest search engine — ideal for evergreen content
- Comment sections on coaching videos are prospecting goldmines

### Coach Communities & Directories

**Online communities:**
- Mighty Networks — home to Tony Robbins, Marie Forleo, Jim Kwik communities. More $1M communities than any other platform
- Skool — co-owned by Alex Hormozi. Strong gamification. Popular with coaching paid communities
- Circle.so — course + community combos. Many coaches use this

**Directories (scrapable lead sources):**
- ICF Credentialed Coach Finder — 50,000+ credentialed coaches globally
- Noomii — 10,000+ coaches with specialty and location data
- Coach.me — 5,000+ coaches, pricing visible
- Life Coach Directory — UK-focused, 1,000+ coaches

### Tools Coaches Use (Tech Stack Signals)

If a coach is paying for these, they're a real business:
- **All-in-one platforms:** Kajabi ($179/mo), Kartra ($59/mo), ClickFunnels
- **Coach-specific:** Paperbell (100K+ clients served), CoachAccountable, Simply.Coach, Practice.do
- **Scheduling:** Calendly, Acuity Scheduling
- **Quiz/Assessment:** ScoreApp, Typeform, Interact, Outgrow
- **Email:** ConvertKit (Kit), Mailchimp, ActiveCampaign
- **Community:** Mighty Networks, Skool, Circle.so
- **Courses:** Teachable, Thinkific, LearnWorlds

### Content Coaches Consume

**Top podcasts coaches listen to:**
- The Life Coach School Podcast (Brooke Castillo)
- Make Money as a Life Coach (Stacey Boehman)
- Natural Born Coaches (Marc Mawhinney)
- The Marie Forleo Podcast
- Business Coaching Secrets (Karl Bryan)

**Newsletters:**
- The Launchpad Newsletter (45,000 readers, 30-40% open rates)
- CoachRanks Insider (marketing for coaches)
- Fulfillment@Work (10,000+ subscribers, executive coaching)

---

## 4. Outreach Strategy Deep Dives

### 4.1 Loom/Video Outreach

#### How It Works

The dominant framework is the **"Trojan Horse" method**, popularized by ListKit (who claim $10M+ generated):

1. **Initial cold email** — Position as someone genuinely interested in their brand. Reference their website, social media, or recent work. Do NOT pitch.
2. **Identify a specific problem** — Mention something concrete about their business you can demonstrate expertise on. This must be real, specific, and verifiable.
3. **Ask permission to share a video** — "Mind if I share a quick video explaining further?" Filters for warm leads who are already curious. Only record Looms for people who reply "yes."
4. **Deliver the personalized Loom** — Screen-record showing THEIR actual website/funnel with your face in the corner. Point out specific issues and opportunities. Keep focus on value, not pitching.
5. **Soft CTA** — "Happy to hop on a quick call if you're open to it."

#### Video Specifications

| Element | Recommendation |
|---------|---------------|
| Length | 60-90 seconds cold, up to 3-5 minutes for warm/follow-up |
| Format | Screen recording of THEIR website + face bubble |
| Tone | Scrappy, authentic — not overproduced |
| Must include | Prospect's name, their actual site on screen, one specific insight |
| Must avoid | Pricing, service pitches, generic scripts |
| CTA | Thumbnail in email, timestamp highlights ("Check out 1:45...") |

#### Performance Data

| Metric | Rate | Source |
|--------|------|--------|
| Open rate (email with Loom thumbnail) | 70-91% | ListKit |
| Reply rate (personalized Loom) | 19-43% | Intercom + ListKit |
| Calls booked per 1,000 emails (with Loom vs. text-only) | 6x more | Loom.com |
| Reply rate lift vs. text-only email | 2-5x | Multiple sources |
| Standard cold email reply rate (comparison) | 3-5.1% | Industry avg 2025 |

#### Time Investment

- **Permission-based approach:** ~2-3 min for initial email, then 2-5 min per Loom only for warm replies
- **Cold Loom approach:** ~5-8 min per lead (research + record + send)
- **At scale with tools (Loom Variables, Personalize.com):** ~2-3 min per video with dynamic name swaps
- **Daily capacity:** 10-20 personalized Looms for a solo operator

#### Revenue Model (20 Looms/day, $497 offer)

| Metric | Conservative | Optimistic |
|--------|-------------|-----------|
| Looms sent/month (22 working days) | 440 | 440 |
| Replies (15-43%) | 66 | 189 |
| Positive replies (30% of replies) | 20 | 57 |
| Meetings booked (50% of positive) | 10 | 28 |
| Clients closed (30%) | 3 | 8 |
| Revenue at $497/deal | **$1,491** | **$3,976** |

#### Who's Teaching This

- **ListKit / Christian Lovelock** — Built agency to $100K+/month using this method
- **Rya Tul / Beyond Agency Profits** — Teaches personalized Loom at scale. 3-part formula: Dramatic Demonstration + 3-5 Step Plan + Easy-Yes Offer
- **Intercom sales team** — Documented 19% reply rate increase, $120K in self-sourced deals

#### Pros & Cons

**Pros:**
- Dramatically higher reply rates (2-5x vs. text-only)
- Builds trust before the call
- Demonstrates expertise visually (show, don't tell)
- Hard to fake personalization — prospects know you invested effort
- Face + voice builds connection
- Maps perfectly to FixMyWorkflow's existing pitch deck system

**Cons:**
- Time-intensive: 5-8 min per lead minimum
- Doesn't scale past ~20/day without tools or VAs
- Requires on-camera comfort
- Permission-based approach adds friction (extra step)
- Video fatigue is increasing as more adopt this method
- Burnout risk HIGH at 20/day for 6+ months

---

### 4.2 Cold Email at Scale

#### How It Works

1. **Build targeted lead list** — Use Apify, Apollo, or ListKit for verified coach emails
2. **Set up sending infrastructure** — 3-5 email accounts on separate domains, warm up for 2-3 weeks
3. **Write the sequence** — 4-7 emails over 14-21 days
4. **Automate sending** — Use Instantly (already available)
5. **Handle replies manually** — Book calls from warm replies

#### The Sequence Template

**Email 1 (Day 1) — The Hook:**
- Subject with personalization: "{FirstName}, quick question about your [niche] lead magnet"
- 2-3 sentences max. One specific observation about their business
- Soft CTA: question, not a pitch

**Email 2 (Day 3-4) — Value Follow-Up:**
- Same thread. Add one new value point or social proof
- Share a stat: "Coaches who switch from PDFs to quizzes see 3-5x more leads"

**Email 3 (Day 7-8) — The Loom Offer:**
- Offer to send a personalized video: "I put together a quick quiz strategy for your [niche] business"
- Or share a relevant case study

**Email 4 (Day 12-14) — The Breakup:**
- "Looks like the timing might not be right"
- Removes pressure, often triggers response
- "No worries if not — just didn't want to leave you hanging"

**Emails 5-7 (Day 17-21) — Optional:**
- Switch angle or offer type
- New subject line, new thread
- Final "closing the loop" message

#### Performance Data (2025 Benchmarks)

| Metric | Average | Top 10% Performers |
|--------|---------|-------------------|
| Open rate | 27-40% | 50-60% |
| Reply rate | 3-5.1% | 15-25% |
| Reply rate (consulting/coaching firms) | 7.88% | 10-11% |
| Positive reply rate | 1-3% | 5-8% |
| Meeting booking rate | 0.5-2% | 3-5% |
| Reply rate WITH personalization | 17% | — |
| Reply rate WITHOUT personalization | 7% | — |
| Replies from follow-ups (not first email) | 60% of all replies | — |

Sources: Instantly benchmarks, Digital Bloom 2025, Backlinko, Built for B2B 2025

#### Best Performing Hook Types for Coaching

| Hook Type | Reply Rate | Example |
|-----------|-----------|---------|
| Timeline hooks ("noticed you recently...") | 10.67% | "Noticed you just launched your coaching practice..." |
| Numbers hooks ("saw your revenue grew by...") | 9.10% | "Saw you hit 5K followers this month..." |
| Question hooks | 7-8% | "Quick question about your lead magnet..." |
| Generic / no hook | 3-4% | "I help coaches get more clients..." |

#### Revenue Model (100 emails/day via Instantly, $497 offer)

| Metric | Conservative | Optimistic |
|--------|-------------|-----------|
| Emails sent/month | 2,200 | 2,200 |
| Replies (5-8%) | 110 | 176 |
| Positive replies (30% of replies) | 33 | 53 |
| Meetings booked (50% of positive) | 17 | 26 |
| Clients closed (30%) | 5 | 8 |
| Revenue at $497/deal | **$2,485** | **$3,976** |

#### Infrastructure (Using What You Already Have)

| Component | Tool | Cost | Status |
|-----------|------|------|--------|
| Sending platform | Instantly | Already have | Active |
| Email accounts | Spare addresses | Already have | Active |
| Domain warm-up | Instantly built-in | $0 | Ready |
| Lead data | Apify + free email finders | $5-15/mo | Active |
| Email verification | Snov.io/Hunter.io free tiers | $0 | Available |

#### Key Statistics

- Cold email reply rates dropped 27% year-over-year (7% in 2024 → 5.1% in 2025)
- BUT top performers still hit 15-25% through tight targeting
- Smaller campaigns (1-200 prospects) get 18% reply rate vs. 8% for 1,000+
- Follow-ups account for 60% of all replies — most people stop too early
- ROI of cold email: $42 return per $1 spent when done well
- Cost per lead: $30-50, cost per meeting: ~$110, cost per client: ~$440

#### Pros & Cons

**Pros:**
- Highest ROI of any channel ($42 per $1 spent)
- Most scalable (1,000+ emails/day possible)
- Cheapest per-contact cost
- Automation handles most work (already have Instantly)
- A/B testing is fast and easy
- Works while you sleep

**Cons:**
- Deliverability increasingly challenging (Google/Microsoft tightening anti-spam)
- Requires technical setup (domains, warm-up, SPF/DKIM/DMARC)
- Coaches' inboxes are saturated with cold email
- 2-3 week warm-up before you can send volume
- Template-sounding emails get ignored
- Domain burning is real — budget for replacing 2-3/quarter
- Burnout risk MEDIUM (automated, but list building needs constant attention)

---

### 4.3 LinkedIn DM Strategies

#### How It Works

The highest-performing framework follows a "trigger + teaser" model:

1. **Trigger** — Why you're reaching out NOW (saw their post, noticed a job change, content they shared)
2. **Teaser** — A compelling reason to respond (insight, resource, result for a similar client)
3. **Question** — End with a question, not a pitch

#### The 4-Step Sequence (Documented at 37% Reply Rate — Mailshake Study)

**Step 1 — Soft Connect (Day 0):**
> "I noticed you liked [Person]'s recent post about [topic]. If you're interested, I've got a 2-minute video on [related value]."

**Step 2 — Video Follow-Up (Day 2):**
> Short Loom or Vidyard video referencing the connection

**Step 3 — Voice Note (Day 4):**
> 30-45 second LinkedIn voice note with qualifying question. Must send from mobile app.

**Step 4 — Text Nudge (Day 6):**
> "Any thoughts?"

**Documented results:** 588 contacts → 206 replies (37%) → 41 meetings (20% of replies) → 27 opportunities (66% of meetings). Time: 30 minutes/day.

#### LinkedIn Voice Notes

- Boost replies by 30-40% vs. text-only DMs
- Must send via mobile app (1st-degree connections only)
- Optimal length: 30-45 seconds
- Script: Greeting → Personalized Hook → Value Teaser → Soft Close
- Always follow with a one-line text recap

#### LinkedIn Benchmarks (Expandi H1 2025 — 70,130+ campaigns)

| Metric | Rate |
|--------|------|
| Average connection acceptance rate | 29.61% |
| Builder campaign (warm-up) reply rate | 7.22% |
| Messenger campaign (DM to 1st-degree) reply rate | 16.86% |
| Connection request with personalized note | 9.36% |
| Connection request without message | 5.44% |
| AI-assisted message reply rate | 7.66% |
| Non-AI message reply rate | 6.50% |

#### Free LinkedIn Limits (No Sales Navigator)

- ~250-350 commercial-use people searches per month before throttle
- After limit: only 3 results per search
- Basic filters: location, industry, current company, school, keywords
- You do NOT get: Boolean depth, saved leads, InMail
- Tips: search by job title not keyword, browse "People Also Viewed" sidebar, use 2nd-degree filter

#### Revenue Model (25 connection requests/day, free LinkedIn, $497 offer)

| Metric | Conservative | Optimistic |
|--------|-------------|-----------|
| Connection requests/month (22 days) | 550 | 550 |
| Accepted (30%) | 165 | 165 |
| Replies from sequence (7-10%) | 12-16 | 28 |
| Positive replies (~48%) | 6-8 | 13 |
| Meetings booked (50%) | 3-4 | 7 |
| Clients closed (30%) | 1 | 2 |
| Revenue at $497/deal | **$497** | **$994** |

#### Pros & Cons

**Pros:**
- Higher reply rates than cold email (10-17% vs. 3-5%)
- Conversational and natural feel
- Voice notes are a massive differentiator (30-40% lift)
- Profile establishes credibility before the message
- Free tier is usable for initial outreach

**Cons:**
- Platform limits on daily activity (100 requests/week free)
- Account restriction risk with automation
- Sales Navigator costs $99/mo for advanced targeting
- Slower than email — can't blast hundreds/day
- Coaches increasingly wary of LinkedIn DMs from strangers

---

### 4.4 Multi-Channel Warm-Up Sequences

#### How It Works

Become a familiar face BEFORE you pitch. Warm leads across multiple platforms over 7-14 days so when you make your ask, you're a recognized name.

#### The Documented Playbook

**Days 1-2: Silent Engagement**
- View their LinkedIn profile (they get a notification)
- Follow their company page
- Like 1-2 of their recent posts

**Days 3-4: Visible Engagement**
- Leave a thoughtful comment on a LinkedIn post (genuine insight, not "Great post!")
- If on Instagram, follow and like a recent post
- If they have a newsletter, subscribe

**Day 5: Connection Request**
- Short personalized note: "Saw your post on [topic] — resonated with something we're working on"
- Acceptance rate with warm-up: ~30-40% (vs. 15-20% cold)

**Days 6-7: First Value Touch**
- Personalized LinkedIn voice note (30-45 seconds)
- Reference a specific post or signal
- Follow voice note with one-line text recap

**Days 8-10: The Pitch**
- If no response to voice note: "Any thoughts?" nudge
- If engaged: suggest a call or offer a Loom
- If switching to email: "We connected on LinkedIn last week" (now warm)

**Days 11-14: Follow-Up Sequence**
- Switch to email if LinkedIn went quiet
- Send a Loom video as escalation
- Final: "No worries if timing's off — happy to reconnect later"

#### Results: Warm-Up vs. Cold

| Approach | Connection Accept | Reply Rate | Meeting Conversion |
|----------|------------------|------------|-------------------|
| Cold DM (no warm-up) | 15-20% | 5-7% | 1-2% |
| Warm-up sequence (7+ days) | 29-40% | 10-17% | 3-5% |
| Multi-channel (warm-up + email) | 30-40% | 15-22% | 5-8% |

Sources: Expandi H1 2025 (70,130+ campaigns), Belkins 2025, SalesBread

#### Revenue Model (5 leads/week deep warm-up, $497 offer)

| Metric | Conservative | Optimistic |
|--------|-------------|-----------|
| Leads approached/month | 20 | 20 |
| Meaningful replies (20-35%) | 4 | 7 |
| Meetings booked (50%) | 2 | 3-4 |
| Clients closed (30-35%) | 1 | 1-2 |
| Revenue at $497/deal | **$497** | **$994** |

#### Pros & Cons

**Pros:**
- 2x higher connection acceptance and reply rates vs. cold
- Builds genuine trust and familiarity
- Multi-channel touches increase frequency without being spammy
- Follow-ups account for 50-70% of total responses
- Feels natural to the prospect

**Cons:**
- Extremely time-intensive (7-14 days per batch)
- Hard to scale past ~30-50 active warm-ups simultaneously
- Requires active social presence (posting, commenting regularly)
- Complex to manage across platforms without tools
- Slow — could take 4-8 weeks to close first client

---

### 4.5 Instagram DM Outreach

#### How It Works

1. Follow the prospect's account
2. Engage with 3-5 stories/posts over a few days (reactions, genuine comments)
3. Reply to a story with a relevant observation or question
4. Transition to DM with a value-first message referencing their content
5. Keep asking questions — if support comes up organically, offer relevant help
6. Suggest a call only after genuine rapport

#### Performance Data

- Average reply rate: ~10%
- Optimized strategies: up to 36% positive reply rate
- 25% higher response when personalized (HubSpot 2024)
- Less saturated with sales messages than LinkedIn
- More personal feel — prospects check Instagram more frequently

#### Best For

Life coaches, health/wellness coaches, mindset coaches, fitness coaches — the coaches who are most active on Instagram rather than LinkedIn. Particularly effective because Instagram feels less "salesy."

#### Volume

- 20-30 personalized DMs per day (within Instagram's behavioral guidelines)
- Takes about 20-30 minutes/day for sourcing + engagement + sending

#### Pros & Cons

**Pros:**
- Less saturated than LinkedIn for coaching market
- More casual, lower guard from prospects
- Story replies create natural conversation starters
- Good for coaches who aren't on LinkedIn

**Cons:**
- Harder to automate safely
- No email data directly — requires enrichment
- Slower rapport-building required
- Less professional context than LinkedIn

---

### 4.6 Facebook Group Prospecting

#### How It Works

1. Join 8-12 coaching-related Facebook groups (2K-20K members — too big is too noisy)
2. Provide value for 2-4 weeks (answer questions, share insights)
3. Identify members posting about lead gen struggles
4. Send friend request with context: "Loved your comment in [Group] about [topic]"
5. After acceptance, engage with their content for a few days
6. Send a DM referencing group interactions

#### Target Groups

- "Online Coaches & Course Creators" (100K+ members)
- "Clients for Coaches" / "Get More Coaching Clients"
- "Female Coaches & Consultants"
- "Coaching Business Lounge"
- Niche-specific: "Health Coach Network," "Business Coach Community"

#### Performance Data

- Slowest channel but produces the warmest leads
- Shared community context makes outreach feel natural
- Referral-like close rate: 24-30% (vs. 2% cold)
- Time investment: 30 min/day scrolling and engaging

#### Revenue Model

| Period | Warm Leads | Closes | Revenue |
|--------|-----------|--------|---------|
| Months 1-3 | 1-2/week | 0-1/month | $0-$497 |
| Months 4-6 | 3-5/week | 1-2/month | $497-$994 |
| Months 6+ | 5-10/week | 2-3/month | $994-$1,491 |

#### Pros & Cons

**Pros:**
- Highest quality leads (shared context, warm)
- Free — zero tool cost
- Builds reputation and authority
- Compounds over time
- Feels like networking, not selling

**Cons:**
- Slowest time-to-first-client (4-12 weeks)
- Low scalability ceiling (3-5 active communities max)
- Requires patience and consistent engagement
- Cannot be automated
- Results compound slowly

---

### 4.7 Hybrid Multi-Channel Approaches

#### The Dominant 2025 Playbook: LinkedIn + Email + Video

66.9% of outbound campaigns now use LinkedIn + email together. Multi-channel sequences increase engagement by **287%** vs. single-channel (Expandi 2025).

#### The Documented Sequence

**Week 1: Warm-Up Phase**

| Day | Channel | Action |
|-----|---------|--------|
| 1 | LinkedIn | View their profile |
| 2 | LinkedIn | Like 2 recent posts |
| 3 | LinkedIn + Instagram | Thoughtful comment + follow on Instagram |
| 4 | LinkedIn | Connection request |
| 5 | Email | Cold email #1 (hook + specific observation) |

**Week 2: Engagement Phase**

| Day | Channel | Action |
|-----|---------|--------|
| 7 | LinkedIn | Voice note after acceptance (30-45 sec) |
| 8 | Email | Cold email #2 (follow-up, add value) |
| 9 | LinkedIn | "Any thoughts?" nudge |
| 10 | LinkedIn | Engage with another post |
| 12 | Email | Cold email #3 (case study or Loom offer) |

**Week 3: Conversion Phase**

| Day | Channel | Action |
|-----|---------|--------|
| 14 | Loom | Personalized video showing their business |
| 14 | Email | Email #4 with Loom thumbnail |
| 16 | LinkedIn | "Sent you something via email — curious if it resonated" |
| 18 | Email | Breakup: "Looks like timing isn't right..." |

#### Results Comparison

| Approach | Reply Rate | Meetings per 100 Leads |
|----------|-----------|----------------------|
| Cold email only | 3-5% | 1-2 |
| LinkedIn DM only | 10-17% | 3-5 |
| Email + LinkedIn | 15-22% | 5-8 |
| Email + LinkedIn + Video | 20-35% | 8-12 |
| Full warm-up + all channels | 25-40% | 10-15 |

#### The Mailshake Case Study (37% Reply Rate)

Documented with real numbers:

1. Soft Connect (Day 0): LinkedIn connection request. 70% acceptance.
2. Video Message (Day 2): Short Loom referencing the connection.
3. Voice Note (Day 4): LinkedIn audio with qualifying question.
4. Text Nudge (Day 6): "Any thoughts?"

**Results:** 588 contacts → 206 replies (37%) → 41 meetings booked (20% of replies) → 27 opportunities (66% of meetings). Time: 30 minutes/day.

#### Pros & Cons

**Pros:**
- Highest overall conversion rates (287% engagement increase)
- Multiple touchpoints without feeling spammy
- If one channel fails, others compensate
- Builds omnipresence
- Voice notes + video = strong personal connection

**Cons:**
- Most complex to set up and manage
- Requires 3-5 tools working together
- $200-400/month in tool costs at full stack
- Max ~50-100 active leads simultaneously
- Requires comfort with video, voice, and writing
- Easy to lose track without CRM

---

### 4.8 Community/Referral-Based Outreach

#### How It Works

Provide consistent value in 3-5 coaching communities. Build reputation over time. Leads come inbound from people who saw your helpful posts/comments.

#### Performance Data

- Referral close rate: 24.7-26% (vs. ~2% cold outreach)
- Referral leads close 30% faster
- 84% of B2B buyers start with a referral (HBR)
- Referral leads have 16% higher lifetime value
- Cost per referral lead: ~$52 (cheapest of all channels)

#### Revenue Model

| Period | Revenue/month | Notes |
|--------|-------------|-------|
| Months 1-3 | $0-$497 | Building reputation. No direct revenue yet |
| Months 4-6 | $994-$1,491 | 2-3 clients/month from community presence |
| Months 6+ | $1,491-$2,982+ | Compounding. Inbound leads start flowing |

#### Pros & Cons

**Pros:**
- Highest close rate of any channel
- Lowest burnout risk — feels like networking
- Most sustainable long-term approach
- Compounds over time
- Zero tool cost

**Cons:**
- Longest time-to-first-client (4-12 weeks)
- Low scalability ceiling
- Cannot be primary revenue driver early on
- Requires genuine expertise and patience

---

## 5. Strategy Comparison Matrix

### Performance Comparison

| Strategy | Reply Rate | Close Rate (from meeting) | Time per Lead | Meetings/Month | Closes/Month | Revenue/Month ($497) |
|----------|-----------|--------------------------|---------------|---------------|-------------|---------------------|
| **Loom Video (20/day)** | 15-43% | 25-30% | 5-8 min | 10-28 | 3-8 | $1,491-$3,976 |
| **Cold Email (100/day)** | 3-8% | 25-30% | 1-2 min | 17-26 | 5-8 | $2,485-$3,976 |
| **LinkedIn DMs** | 10-17% | 25-30% | 5-10 min | 3-7 | 1-2 | $497-$994 |
| **Warm-Up Sequence** | 20-35% | 30-35% | 60-70 min total | 2-4 | 1-2 | $497-$994 |
| **Instagram DMs** | 10-36% | 25-30% | 5-10 min | 3-5 | 1-2 | $497-$994 |
| **Facebook Groups** | 15-30% (warm) | 25-30% | 15-30 min | 1-3 | 0-1 | $0-$497 |
| **Hybrid Multi-Channel** | 25-40% | 30-35% | 15-20 min | 8-15 | 2-5 | $994-$2,485 |
| **Community/Referral** | N/A (inbound) | 25-30% | 20-40 hrs/mo | 1-3 | 0-1 | $0-$497 |

### Economics Comparison

| Strategy | Monthly Time | Tool Cost/Mo | Cost per Lead | Cost per Meeting | Cost per Client | Burnout Risk | Scalability |
|----------|-------------|-------------|--------------|-----------------|----------------|-------------|-------------|
| **Loom (20/day)** | 77-110 hrs | $15 (Loom) | $5-15 | $30-80 | $120-320 | HIGH | Medium |
| **Cold Email** | 20-40 hrs | $0 (have Instantly) | $0.02-0.05 | ~$110 | ~$440 | MEDIUM | Highest |
| **LinkedIn DMs** | 20-40 hrs | $0 (free tier) | $0.50-1.00 | $80-150 | $320-600 | LOW-MED | Medium |
| **Warm-Up Sequence** | 20-24 hrs | $0-100 | $20-40 | $60-120 | $200-400 | LOW | Low |
| **Instagram DMs** | 10-15 hrs | $0 | Free-$0.50 | $50-100 | $200-400 | LOW | Medium |
| **Facebook Groups** | 10-15 hrs | $0 | Free | Low (organic) | ~$200 | LOW | Low |
| **Hybrid** | 40-60 hrs | $200-400 | $2-5 | $150-250 | $300-500 | MEDIUM | Low-Med |
| **Community** | 20-40 hrs | $0-100 | ~$52 | Low | ~$200 | LOW | Low |

### Timeline Comparison

| Strategy | First Reply | First Meeting | First Client | Steady State (2/week) |
|----------|------------|---------------|-------------|---------------------|
| **Loom** | Week 1-2 | Week 2-3 | Week 3-4 | Month 3-4 |
| **Cold Email** | Week 1-2 | Week 2-3 | Month 1-2 | Month 3-4 |
| **LinkedIn DMs** | Week 1 | Week 2 | Month 1-2 | Month 4+ |
| **Warm-Up** | Week 2-3 | Week 3-4 | Month 2-3 | Month 5+ |
| **Instagram DMs** | Week 1-2 | Week 2-3 | Month 1-2 | Month 4+ |
| **Facebook Groups** | Week 3-4 | Month 2 | Month 2-3 | Month 5+ |
| **Hybrid** | Week 1-2 | Week 2-3 | Month 1-2 | Month 3-4 |
| **Community** | Month 1-2 | Month 2-3 | Month 3-4 | Month 6+ |

---

## 6. Lead Sourcing Methods

### 6.1 Apify Scraping Playbook

Since Apify is already available, here's how to use it for each channel:

#### Google Maps (BEST ROI — Start Here)

| Actor | Cost | What You Get |
|-------|------|-------------|
| `compass/crawler-google-places` | ~$4/1,000 places | Name, phone, website, address, rating, 40+ fields |
| `lukaskrivka/google-maps-with-contact-details` | ~$9/1,000 | Same as above + crawls website for emails (40-60% hit rate) |
| `compass/google-maps-extractor` | ~$3/1,000 | Faster, fewer enrichment features |

**Search queries:** "life coach" + [city], "business coach" + [city], "health coach" + [city], etc.
**Gotcha:** Max ~120 results per query. Split by city/neighborhood.
**n8n template:** #5743 "Scrape Google Maps Leads using Apify + GPT + Airtable"

#### Tech Stack Detection (YOUR UNFAIR ADVANTAGE)

| Actor | Cost | What You Get |
|-------|------|-------------|
| `misterkhan/website-tech-stack-scanner` | $5/1,000 URLs | Detects 7,000+ technologies across 8 inspection tiers |
| `alizarin_refrigerator-owner/tech-stack-detector` | $5/1,000 URLs | Python API available |

**Workflow:** Feed website URLs from Google Maps → detect ScoreApp, Typeform, Interact, etc. → segment leads into 3 buckets:
- **Already on ScoreApp** → audit/optimization pitch
- **On Typeform/Interact** → migration pitch ("upgrade to a real scoring engine")
- **No quiz tool** → full build pitch

**Cost for 1,000 fully enriched, tech-segmented coaching leads: ~$9-14**

#### Instagram Scraping

| Actor | Cost | What You Get |
|-------|------|-------------|
| `apify/instagram-profile-scraper` | ~$2.60/1,000 profiles | Username, bio, website URL, follower count |
| `apify/instagram-hashtag-scraper` | $0.016/hashtag + $0.0004/post | Posts by hashtag |
| `scraper-mind/instagram-profile-email-scraper-by-keyword` | ~$0.03/email | Email extraction from bios |
| `apify/local-lead-generation-agent` | $30/1,000 leads | AI-scored leads with emails (highest quality) |

**Hashtags to scrape:** #lifecoach, #businesscoach, #coachingbusiness, #onlinecoach, #healthcoach, #coachesofinstagram, #leadmagnet, #quizfunnel
**Email hit rate:** Only 10-20% of coaching profiles have public email. Requires enrichment.

#### Facebook Group Scraping

| Actor | Cost | What You Get |
|-------|------|-------------|
| `curious_coder/facebook-group-member-scraper` | Compute-based (needs cookies) | Full member lists, unlimited members |
| `apify/facebook-posts-scraper` | Compute-based | Posts with author details, engagement |
| `memo23/facebook-search-groups-scraper` | Compute-based | Find coaching groups by keyword |

**Gotcha:** Public groups only for official scrapers. Private groups require cookies (ToS violation risk). No email addresses — requires cross-referencing.

#### LinkedIn Scraping

| Actor | Cost | Risk |
|-------|------|------|
| `supreme_coder/linkedin-profile-scraper` (NO COOKIE) | $3/1,000 | ZERO — safest option |
| `harvestapi/linkedin-profile-search` (NO COOKIE) | $0.10/page + $0.004/profile | ZERO |
| `harvestapi/linkedin-profile-search` (with email) | $0.10/page + $0.01/profile | LOW |
| `curious_coder/linkedin-sales-navigator-search-scraper` | $0.15/1,000 (needs SN cookies) | HIGH |

**Recommendation:** Use no-cookie scrapers only. $3/1,000 profiles with zero ban risk. Email hit rate via independent lookup: ~30-50%.

#### TikTok Scraping

| Actor | Cost | What You Get |
|-------|------|-------------|
| `clockworks/tiktok-hashtag-scraper` | $5/1,000 results | Videos by hashtag |
| `clockworks/tiktok-profile-scraper` | $5/1,000 results | Profile details |

**Quality:** LOW-MEDIUM. No email data. Bio links need secondary scraping. Best for identifying coaching content creators, then enriching elsewhere.

#### Coaching Directory Scraping

No pre-built actors. Use generic scrapers:
- `apify/cheerio-scraper` — $0.25/1,000 pages (fast, static HTML)
- `apify/puppeteer-scraper` — compute-based (JS-rendered pages)

**Targets:** Noomii (10K+ coaches), ICF Coach Finder (50K+), Life Coach Directory
**Quality:** VERY HIGH. Every result is a verified, practicing coach.
**Requires:** Writing custom JavaScript page function. Not no-code.

#### Google SERP Scraping

| Actor | Cost | Use Case |
|-------|------|---------|
| `apify/google-search-scraper` | $0.50/1,000 pages | Find coaches with quizzes, PDF lead magnets, lead gen complaints |

**Useful queries:**
```
"take my quiz" coach OR coaching
"powered by typeform" coaching
"free guide" coaching "download"
"coaching" "lead magnet" "not working"
site:scoreapp.com "coach"
```

#### Recommended Apify Budget Scenarios

**$50/month (Starter — recommended to begin):**
- 5,000 Google Maps leads ($20-45)
- 1,000 tech stack detections ($5)
- Total output: ~5,000 leads, 1,000 tech-segmented
- Expected emails: 2,000-3,000

**$150/month (Growth):**
- 10,000 Google Maps leads ($40-90)
- 5,000 tech detections ($25)
- 2,000 Instagram profiles ($5.20)
- 2,000 LinkedIn no-cookie profiles ($6)
- Total output: ~10,000 multi-source leads
- Expected emails: 5,000-7,000

---

### 6.2 Free/Low-Cost Methods

#### Google Dorking (Free — 30 min/day → 25-35 leads/week)

**Finding coaches with quizzes:**
```
"take my quiz" coach OR coaching
"take the assessment" coaching OR consultant
"powered by typeform" coaching
"powered by interact" coach
inurl:scoreapp.com coaching OR coach
```

**Finding coaches with PDF lead magnets (upgrade pitch):**
```
"free guide" coaching "download"
"free checklist" coach "email"
"grab your free" coaching guide
inurl:leadpages.net coaching
inurl:ck.page coach OR coaching
```

**Finding coaches with lead gen problems:**
```
"not getting enough clients" coach site:reddit.com
"lead magnet" "not converting" coaching
"coaching" "quiz funnel" OR "lead magnet" "not working"
```

**Finding newly launched coaches:**
```
"just launched" coaching practice 2025 OR 2026
"certified coach" "now accepting clients" 2025 OR 2026
```

#### Free LinkedIn Search (20 min/day → 15-20 leads/week)

- Search "Life Coach", "Business Coach" in People filter
- Browse "People Also Viewed" sidebar (doesn't cost a search)
- Use 2nd-degree connection filter (warmer leads)
- Post content about quiz funnels — track who engages
- Search Posts for "lead magnet coaching," "quiz funnel coach"
- Limit: ~250-350 searches/month before throttle

#### Instagram Manual Prospecting (20 min/day → 35-50 leads/week)

- Follow hashtags: #lifecoach, #businesscoach, #coachingbusiness, #leadmagnet, #quizfunnel
- Check 10-15 profiles per session
- Look for: email in bio, website link, lead magnet type
- Like/comment on 1-2 recent posts (genuine engagement)
- Note: email from bio, website, current lead magnet type

#### Facebook Group Prospecting (30 min/day → 8-12 leads/week)

- Join 8-12 groups with 2K-20K members
- Search within groups for: "lead magnet," "quiz funnel," "not getting leads"
- Engage genuinely for 2-4 weeks before DMing
- Document: name, profile, niche, website, pain points mentioned

#### Email Finding Tools — Free Tiers

| Tool | Free Tier | Best For |
|------|-----------|---------|
| Hunter.io | 25 searches + 50 verifications/month | Domain-based email lookup |
| Snov.io | 50 credits/month | Email finding + verification |
| Apollo.io | Unlimited email credits (fair use), 10 exports/month | Largest free database (210M+ contacts) |
| Clearbit Connect | ~100 lookups/month (Gmail extension) | Name + company → email |
| RocketReach | 5 lookups/month | Verifying specific people |

**Combined free capacity:** ~75-100 verified email lookups/month.

#### Tech Stack Detection — Free Tools

| Tool | Cost | What It Does |
|------|------|-------------|
| Wappalyzer (browser extension) | 50 free lookups/month | Visit a site → instantly see tech stack |
| WhatRuns (browser extension) | Free, unlimited | Identifies frameworks, analytics, plugins |
| Stackcrawler (web tool) | Free | Enter URL → full tech breakdown |
| SimilarTech (extension) | Free | Detects marketing, analytics, conversion tools |

**What to look for:**
- ScoreApp/Typeform/Interact detected → already believes in quizzes, pitch optimization
- Only Mailchimp/ConvertKit opt-in forms → using basic capture, pitch upgrade
- No lead capture at all → biggest opportunity, needs everything
- Calendly/Acuity but no funnel → has booking but no qualification step

#### Google Alerts (Passive — 5 min/day → 3-5 leads/week)

Set up daily alerts at google.com/alerts:
```
"coach" "quiz funnel" -site:reddit.com
"coaching business" "lead magnet" "not working"
"coach" "ScoreApp" OR "score app"
"consultant" "quiz" "lead generation"
"coach" "need help" "quiz" OR "assessment"
```

#### Reddit/Quora Monitoring (15 min/day → 2-4 leads/week)

- **Subreddits:** r/lifecoaching, r/coaching, r/Entrepreneur, r/smallbusiness, r/digitalmarketing
- **Search for:** "lead magnet not converting," "how to get coaching clients," "quiz funnel"
- **Strategy:** Answer genuinely in public threads. Note the poster's info. Connect on LinkedIn where selling happens.

#### Meta Ad Library (Free — Gold Mine)

- URL: facebook.com/ads/library (no login required)
- Search: "life coach," "business coach," "health coach," etc.
- Filter: Active ads, your target country
- Look for ads with "free guide" or "download" CTAs → PDF-based leads (upgrade pitch)
- Look for ads with "take the quiz" CTAs → existing quiz users (audit pitch)
- **Why these leads are warm:** They're already SPENDING MONEY on lead gen. Budget mindset exists.

#### Weekly Lead Sourcing Summary (All Free Methods)

| Method | Time/Day | Leads/Week | Cost |
|--------|----------|------------|------|
| LinkedIn free search | 20 min | 15-20 | $0 |
| Google dorking | 30 min | 25-35 | $0 |
| Facebook Groups | 30 min | 8-12 | $0 |
| Instagram | 20 min | 35-50 | $0 |
| Email finding (supporting) | 10 min | N/A | $0 |
| Tech stack detection (supporting) | 5 min | N/A | $0 |
| Google Alerts (passive) | 5 min | 3-5 | $0 |
| Reddit/Quora | 15 min | 2-4 | $0 |
| Meta Ad Library | 15 min | 5-10 | $0 |
| **TOTAL** | **~2.5 hrs/day** | **93-136 raw leads** | **$0** |

---

### 6.3 Finding the Warmest Leads (Intent Signals)

Not all coaches are equal. Prioritize by intent signal — hottest first:

#### Signal 1: Coaches with a Broken Quiz (HOTTEST)

Already using ScoreApp/Typeform/Interact but getting poor results. They believe in quizzes — they just need someone to fix theirs.

**How to find:**
- Tech stack detection (Apify or Wappalyzer)
- Google: `"take my quiz" coach`, `"powered by typeform" coaching`
- Take their quiz yourself. Screenshot UX issues, poor scoring, weak results pages
- BuiltWith: trends.builtwith.com/websitelist/ScoreApp (lists all ScoreApp users)

**Pitch:** "I took your quiz and found 3 things that would double your completion rate. Want me to walk you through them?"

#### Signal 2: Coaches Posting About Lead Gen Problems

Self-diagnosed problem. They know marketing isn't working.

**Where to find:**
- Facebook Groups: search "lead magnet not converting," "not getting leads," "quiz vs PDF"
- Reddit: r/lifecoaching, r/Entrepreneur, r/coaching
- LinkedIn posts about marketing frustrations
- YouTube comments on "how to get coaching clients" videos

**Key buying-intent phrases:**
- "My lead magnet isn't converting"
- "I need a better way to get leads"
- "Has anyone tried quiz funnels?"
- "PDF downloads aren't turning into clients"
- "I'm getting opt-ins but nobody books a call"

#### Signal 3: Coaches Running Ads to PDF Opt-Ins

Already spending money on lead gen. Quiz would dramatically improve ad ROI.

**How to find:**
- Meta Ad Library (free): search coaching keywords, look for "free guide" CTAs
- Coaches running ads for weeks/months have meaningful budget
- Screenshot their ad + landing page for Loom audit content

**Pitch:** "You're running ads to a PDF opt-in. What if you sent the same traffic to a quiz that converts at 30-50% instead of 3-10%?"

#### Signal 4: Coaches with PDF Lead Magnets

The single most common coach lead magnet. Perfect upgrade candidate.

**How to find:**
- Google: `"free guide" coaching "download"`, `"grab your free" coaching guide`
- Instagram bios often link to PDF download pages
- Landing page builder searches: `inurl:leadpages.net coaching`

**The conversion pitch:** Quiz lead magnets convert at 30-50% vs. 3-10% for PDFs. Same traffic, completely different results.

#### Signal 5: Coaches Who Just Launched

Newly certified. Have the credential but not the clients. Hungry for client acquisition. $497 is accessible.

**How to find:**
- ICF directory: filter by recently credentialed
- LinkedIn: "new position" signals for "Coach" titles
- Coaching program alumni groups
- Social media: "I'm officially launching my coaching practice!" posts

#### Signal 6: ScoreApp Competitor Users

On Interact, Outgrow, Typeform, Riddle, Pointerpro, LeadQuizzes. Already believe in quizzes.

**How to find:**
- BuiltWith technology lists
- Google: `"powered by interact" coach`, `"powered by outgrow" coaching`
- Review sites: G2, Capterra (coaches complaining about current tool)

**Pitch:** "You already understand quiz funnels. Let me optimize yours for maximum conversion."

#### Signal 7: Coaches Posting About Low Conversion Rates

Diagnosed their own problem. Need the solution.

**Where to find:**
- Facebook Groups: search "conversion rate," "not converting," "nobody books a call"
- Reddit threads about coaching client acquisition
- LinkedIn posts about marketing frustrations

#### Warmth Ranking (Prioritize in This Order)

| Tier | Lead Type | Temperature | Approach |
|------|-----------|-------------|----------|
| 1 | Broken quiz owner | Hottest | Loom audit of their quiz + DM |
| 2 | Posting about lead gen problems | Very warm | Engage in community + DM |
| 3 | Running ads to PDF opt-in | Warm | Ad Library research + Loom audit |
| 4 | Has PDF lead magnet | Warm | Loom showing quiz vs PDF |
| 5 | Using competitor quiz tool | Warm | Loom with improvement ideas |
| 6 | Newly launched coach | Lukewarm | Educational DM + case study |
| 7 | No online presence | Cold | Not worth pursuing for $497 |

---

## 7. Lead Qualification Framework

### The 3-Minute Qualification Check

For every lead, spend no more than 3 minutes:

**60 seconds — Visit their website:**
- Does it exist and look professional?
- What lead magnet do they have? (PDF, quiz, webinar, nothing?)
- Is there a clear coaching offer with pricing?
- Run Wappalyzer — what tools are they using?

**60 seconds — Check social presence:**
- Active? (Last post <30 days ago)
- Follower count: 1K-50K = sweet spot
- Posting about their business, not just personal?

**60 seconds — Score the lead:**

| Signal | Points |
|--------|--------|
| Has website with clear coaching offer | +3 |
| Currently uses a PDF/checklist lead magnet | +3 |
| Mentions struggling with lead gen | +3 |
| Has an email list (mentions it, has opt-in) | +2 |
| Active on social media (weekly+) | +2 |
| 1K-50K audience size | +2 |
| Already uses a quiz tool (ScoreApp, Typeform) | +2 |
| Charges $1K+ for coaching | +2 |
| Has booking page (Calendly, Acuity) | +1 |

**8+ points = A-lead** → Create pitch deck + record Loom
**5-7 points = B-lead** → Text-only email sequence, Loom if they reply
**Under 5 = skip**

### Best Coaching Niches for Quiz Funnels

**Tier 1 — Perfect fit (quiz is a no-brainer):**
- Business/executive coaching → "What type of leader are you?"
- Health/wellness coaching → "What is your wellness score?"
- Fitness coaching → "What is your fitness personality?"
- Career coaching → "What is your career readiness level?"
- Financial coaching → "How healthy are your money habits?"

**Tier 2 — Strong fit (needs creative framing):**
- Life coaching → "What is holding you back?"
- Relationship coaching → "What's your communication style?"
- Mindset coaching → "What is your mindset archetype?"
- Parenting coaching → "What is your parenting style?"

### Disqualification Signals (Skip Immediately)

- No website AND no social media presence
- No defined coaching offer (still "figuring it out")
- Charges under $200 for coaching (can't justify $497 investment)
- Last posted 60+ days ago (may have abandoned)
- Already has a sophisticated, well-performing quiz funnel
- Explicitly resistant to spending money on marketing

---

## 8. Pipeline Management

### Notion CRM Database (Recommended — Already Using Notion)

Create a "Cold Outreach Pipeline" database with these properties:

| Property | Type | Purpose |
|----------|------|---------|
| Lead Name | Title | Full name |
| Company/Brand | Text | Their coaching brand |
| Niche | Select | Life, Business, Health, Fitness, Career, Executive, Other |
| Website | URL | Their website |
| Email | Email | Contact email |
| LinkedIn | URL | Profile link |
| Instagram | URL | Handle/link |
| Lead Source | Select | Google Maps, Instagram, LinkedIn, Facebook, Ad Library, Directory, Referral |
| Lead Score | Number | Qualification score (0-20) |
| Stage | Select | New → Researched → Deck Created → Loom Sent → Replied → Meeting Booked → Proposal Sent → Closed Won → Closed Lost → Nurture |
| Current Lead Magnet | Select | None, PDF, Quiz (basic), Quiz (advanced), Webinar, Other |
| Tech Stack | Multi-select | ScoreApp, Typeform, Mailchimp, ConvertKit, Kajabi, WordPress, etc. |
| Pain Points | Text | Observed lead gen struggles |
| Loom URL | URL | Link to recorded Loom |
| Pitch Deck URL | URL | Link to Google Slides deck |
| First Contact Date | Date | When you first reached out |
| Last Contact Date | Date | Last touchpoint |
| Next Action | Text | What to do next |
| Next Action Date | Date | When to do it |
| Touch Count | Number | Total outreach touches |
| Notes | Text | Anything relevant |

### Key Views

1. **"Today's Actions"** — Filter: Next Action Date = Today, Sort by Lead Score descending
2. **"Pipeline Board"** — Kanban grouped by Stage
3. **"A-Leads"** — Filter: Lead Score >= 8, Sort by Last Contact Date ascending
4. **"Ready for Loom"** — Filter: Stage = Researched AND Lead Score >= 8
5. **"Follow-Up Due"** — Filter: Next Action Date <= Today AND Stage not in [Closed Won, Closed Lost]

### Pipeline Size Targets

Always have leads at every stage simultaneously:

| Stage | Target Count |
|-------|-------------|
| New leads being researched | 20-30 |
| Pitch decks being created | 5-8 |
| Active sequences (touches 1-7) | 40-50 |
| Meetings scheduled | 3-4/week |
| Proposals sent | 2-3/week |
| **Total active pipeline** | **70-90 leads** |

---

## 9. The Unit Economics

### Working Backwards from 2 Closes/Week

```
TARGET:       2 closes/week x $497 = $994/week ≈ $4,300/month
Close rate:   30% from meetings (warm leads who watched Loom)
Meetings:     2 ÷ 0.30 = 7 meetings/week
Book rate:    50% of replies book a call
Replies:      7 ÷ 0.50 = 14 replies/week
Reply rate:   15% (personalized Loom outreach)
Sequences:    14 ÷ 0.15 = ~93 active sequences running
Qualify rate: 60% pass the 3-minute check
Raw leads:    93 ÷ 0.60 = ~155/week to start the pipeline
```

**BUT once the pipeline is full (after weeks 3-4), you only add 25-30 NEW leads/week** to replace leads that cycle out.

### The Ramp-Up Period

- **Weeks 1-2:** Pure sourcing and research. Build pipeline to 60+ leads. Create first 10-15 pitch decks. Send first sequences.
- **Weeks 3-4:** First replies arrive. First meetings booked. Refine Loom script. Close 0-1.
- **Weeks 5-8:** Pipeline full. Sequences running. Hit 1-2 closes/week.
- **Week 9+:** Consistent 2 closes/week with maintained daily discipline.

### Monthly Revenue Trajectory

| Month | Closes | Revenue | Cumulative | Notes |
|-------|--------|---------|------------|-------|
| Month 1 | 2-4 | $994-$1,988 | $994-$1,988 | Ramp-up. Pipeline building. First Looms. |
| Month 2 | 6-8 | $2,982-$3,976 | $3,976-$5,964 | Pipeline flowing. Refining process. |
| Month 3 | 8-10 | $3,976-$4,970 | $7,952-$10,934 | Steady 2/week. Consider first $2.5K deal. |
| Month 4 | 8-10 + upsells | $5,000-$7,000 | $12,952-$17,934 | Offload $497 builds. Take $2.5K deals. Stack affiliate. |
| Month 6 | 8-10 + ads | $6,000-$10,000+ | — | Activate quiz funnel with ad budget from revenue. |

### Revenue Stacking Model (Month 6+)

| Stream | Monthly Revenue |
|--------|----------------|
| 2x $497 builds/week (cold outreach) | $3,976 |
| 1x $2,500 build/month (cherry-picked upsell) | $2,500 |
| ScoreApp affiliate (cumulative, ~$10-15/mo per active user x 20 clients) | $200-$300 |
| $27 tripwire sales (quiz funnel, once funded with ads) | $200-$500 |
| **Total** | **$6,876-$7,276** |

### Tool Budget

| Tool | Cost | Status |
|------|------|--------|
| Instantly | Already have | Active |
| Apify (on demand) | ~$5-15/mo | Active |
| Loom Business | $15/mo | Needed |
| Google Workspace (sending domain) | $7/mo | Needed |
| Apollo/Hunter/Snov.io free tiers | $0 | Available |
| Wappalyzer free | $0 | Available |
| Google Alerts | $0 | Available |
| Notion (existing) | $0 | Active |
| **TOTAL NEW SPEND** | **~$22-37/month** | |

---

## 10. Recommended Strategy

### The FixMyWorkflow Outreach Stack

Given the constraints (bootstrap budget, $497 focus, existing tools, willingness to grind), here's the recommended approach:

#### Layer 1: Cold Email Engine (Primary Revenue Driver)

**Tool:** Instantly (already have) + spare email addresses (already have)
**Volume:** 100-200 emails/day
**Investment:** 1-2 hrs/day for list building, 30 min/day for reply handling
**Expected output:** 5-8 closes/month at $497

**Why this is Layer 1:** Highest scalability, lowest per-lead cost, already have the infrastructure. Cold email is the volume play that feeds the pipeline. At $497 per deal, you need volume — and email delivers it.

**Sequence:** 4-email sequence over 14 days → breakup email at day 14 → graduates to Loom if they show interest.

#### Layer 2: Loom Video (Conversion Multiplier)

**Tool:** Loom Business ($15/mo)
**Volume:** 2-5 Looms/day (only for A-leads and warm replies)
**Investment:** 30-60 min/day
**Expected output:** Doubles close rate on leads who receive Loom

**Why this is Layer 2:** You don't Loom everyone. You Loom the hottest leads (score 8+) and anyone who replies positively to email. This is where the pitch deck system (`create_pitch_deck.py`) shines — generate a personalized deck, walk through it on Loom, blow their mind.

**Process:**
1. A-lead identified → run `create_pitch_deck.py` → review deck
2. Record 2-3 minute Loom walking through the deck
3. Send via email: "Made this for you, {Name}"
4. Follow up at day 3 and day 7

#### Layer 3: LinkedIn Engagement (Trust Builder)

**Tool:** Free LinkedIn (no Sales Navigator yet)
**Volume:** 15-25 connection requests/day, 10-15 comments/day
**Investment:** 30-45 min/day
**Expected output:** Warms cold leads, 1-2 extra closes/month

**Why this is Layer 3:** LinkedIn serves as a trust signal. When a coach gets your cold email, they Google your name or check LinkedIn. If they see you actively posting about quiz funnels and engaging with coaching content, you're credible. This also surfaces organic leads who engage with your content.

**Daily routine:**
- Send 15-25 connection requests to coaches (free search)
- Comment on 5-10 coaching-related posts (genuine insights)
- Post 2-3x/week about quiz funnel results, ScoreApp tips, case studies

#### Layer 4: Community Presence (Long-Term Compound)

**Tool:** Free (Facebook Groups, Reddit)
**Volume:** 3-5 active communities
**Investment:** 15-30 min/day
**Expected output:** 1-2 warm inbound leads/month after month 3

**Why this is Layer 4:** This is the slow burn. Join 3-5 coaching Facebook Groups. Answer questions about lead magnets. Share quiz funnel insights. Over 3-6 months, coaches start recognizing your name and reaching out. Also feeds your LinkedIn content.

#### Layer 5: Dormant Funnel Activation (Month 3+)

**Tool:** Existing quiz → $27 tripwire → $497 upsell funnel
**Trigger:** When cold outreach revenue hits $2K+/month, allocate $200-$500/month to ads
**Investment:** Ad spend only (funnel is built)
**Expected output:** Additional $500-$1,500/month in automated revenue

**Why this is Layer 5:** The funnel exists but needs traffic. Once cold outreach generates consistent revenue, a portion funds ads. This creates a second, more passive revenue stream that compounds alongside outreach.

### Your Daily Routine (5 hours/day)

| Block | Time | Activity | Output |
|-------|------|----------|--------|
| **Sourcing** | 8:00-9:30 | Apify scrapes review + Google dorking + LinkedIn search + qualify leads | 5-8 new qualified leads |
| **Pitch Decks** | 9:30-10:15 | Run `create_pitch_deck.py` for top 2 A-leads | 2 decks ready |
| **Looms + Outreach** | 10:15-11:30 | Record 2-3 Looms, queue new email sequences in Instantly, send follow-ups | 2-3 Looms + 10-15 new emails |
| **LinkedIn** | 11:30-12:00 | Connection requests, comments, DM warm replies | 15-25 connections + 10 comments |
| **Meetings + Admin** | 13:00-14:00 | Take 1-2 calls (15-20 min each), update Notion pipeline | 1-2 meetings, clean pipeline |

### Upgrade Path (When Revenue Allows)

| Revenue Milestone | Upgrade | Cost | Impact |
|------------------|---------|------|--------|
| $2K/month | LinkedIn Sales Navigator | $99/mo | 50+ filters, unlimited search, InMail |
| $3K/month | Ad budget for quiz funnel | $200-500/mo | Activates dormant funnel |
| $4K/month | Apify Growth plan | $49/mo | 10K+ leads/month automated |
| $5K/month | Freelancer for $497 builds | Variable | Frees time for $2.5K deals + outreach |
| $7K/month | LinkedIn automation (Expandi) | $99/mo | Automates LinkedIn sequences |

### The Positioning: "Quiz Funnel Roadmap" vs. "Lead Magnet Makeover"

Research shows the name matters. Use two versions depending on the audience:

- **"Quiz Funnel Roadmap"** — For coaches who already know about quizzes. They know the tool, they want the strategy. Use for leads found via ScoreApp/Typeform detection, quiz-related communities.

- **"Lead Magnet Makeover Session"** — For coaches with PDF lead magnets who haven't heard of quiz funnels. Positions as an upgrade to what they already have, not something entirely new. Use for leads found via PDF detection, general coaching communities.

Both frame the $497 as getting a **specific deliverable** (not just a call): "You walk away with a complete quiz funnel roadmap — the questions, the scoring logic, the results pages, and the follow-up sequence — all customized for your niche."

### Objection Handling (Top 5)

**"$497 is too expensive for a call"**
→ "You're not paying for a call. You're paying for a custom quiz funnel strategy that would normally take $2,500+ to develop through trial and error. This gets you the same clarity in 45 minutes. Plus, if you move forward with a full build, the $497 gets credited toward the project."

**"I can figure this out myself"**
→ "You absolutely could. Most coaches who build their own quiz get 5-10% opt-in rates. With proper question sequencing and scoring logic, we routinely hit 35-45%. The question is whether 40-80 hours of research and testing is worth more than $497."

**"Never heard of quiz funnels"**
→ "Quiz lead magnets convert at 30-50% vs. 3-10% for PDFs. Same traffic, completely different results. Let me show you 3 examples from coaches in your niche."

**"Tried a quiz before, didn't work"**
→ "What went wrong? Most quiz funnels fail because of wrong questions, bad scoring logic, or no follow-up sequence. That's exactly what the roadmap fixes."

**"Skip the audit, just build it"**
→ "The roadmap IS the foundation. Without understanding your audience and offer, building a quiz is guessing. And the $497 gets credited toward a full build — so it's not an extra cost."

---

## 11. Sources

### Market & Demographics
- [US Professional Coaching Industry Report 2025](https://www.businesswire.com/news/home/20251204763253/en/) — BusinessWire / ResearchAndMarkets
- [ICF Coaching Statistics 2025](https://simply.coach/blog/icf-coaching-statistics-industry-insights/) — Simply.Coach
- [150+ Coaching Industry Statistics](https://entrepreneurshq.com/coaching-industry-statistics/) — EntrepreneursHQ
- [Coaching Industry Market Size](https://luisazhou.com/blog/coaching-industry-market-size/) — Luisa Zhou

### Platform Usage & Communities
- [Best Social Media Platforms for Coaches](https://meetedgar.com/blog/the-best-social-media-platforms-for-coaches) — MeetEdgar
- [Facebook for Coaches](https://luisazhou.com/blog/facebook-for-coaches/) — Luisa Zhou
- [LinkedIn Groups for Coaches](https://www.thecoachingtoolscompany.com/10-great-linkedin-groups-you-may-want-to-check-out/) — Coaching Tools Company
- [TikTok for Coaches](https://paperbell.com/blog/tiktok-for-coaches/) — Paperbell
- [Top 100 Facebook Groups for Coaches](https://pensight.com/100-facebook-groups-for-coaches-to-get-clients) — Pensight
- [Best Life Coaches on YouTube](https://paperbell.com/blog/best-life-coaches-on-youtube/) — Paperbell

### Loom/Video Outreach
- [ListKit: Loom Video Cold Email Strategy](https://www.listkit.io/blog/loom-video-cold-email-outreach-strategy) — ListKit
- [Loom: Intercom Customer Story](https://www.loom.com/customers/intercom) — Loom
- [Loom: Video Prospecting Tips](https://www.loom.com/blog/video-prospecting) — Loom
- [Beyond Agency Profits: Loom Outreach at Scale](https://www.beyondagencyprofits.com/loom-videos/) — Rya Tul

### LinkedIn & DM Strategies
- [State of LinkedIn Outreach H1 2025](https://expandi.io/blog/state-of-li-outreach-h1-2025/) — Expandi
- [B2B LinkedIn Outreach Benchmarks 2025](https://belkins.io/blog/linkedin-outreach-study) — Belkins
- [LinkedIn Messaging Benchmarks 2025](https://www.alsona.com/blog/linkedin-messaging-benchmarks-whats-a-good-reply-rate-in-2025) — Alsona
- [The 4-Step LinkedIn Sales Sequence](https://mailshake.com/blog/linkedin-sales-sequence/) — Mailshake
- [LinkedIn Voice Messages for Lead Gen 2025](https://www.unkoa.com/linkedin-voice-messages-for-lead-generation-the-2025-solo-agency-hack-for-30-higher-reply-rates/) — Unkoa
- [LinkedIn Outreach Stats 2026](https://salesbread.com/linkedin-outreach-stats/) — SalesBread

### Cold Email
- [Cold Email Reply Rate Benchmarks](https://instantly.ai/blog/cold-email-reply-rate-benchmarks/) — Instantly
- [Cold Email Benchmarks 2025](https://www.builtforb2b.com/blog/b2b-cold-email-benchmark-2025) — Built for B2B
- [Cold Outbound Reply-Rate Benchmarks 2025](https://thedigitalbloom.com/learn/cold-outbound-reply-rate-benchmarks/) — The Digital Bloom
- [Cold Email Statistics 2025](https://martal.ca/b2b-cold-email-statistics-lb/) — Martal
- [ROI of Cold Email](https://instantly.ai/blog/cold-email-outreach-roi/) — Instantly
- [Cold Email Copy for Coaches](https://instantly.ai/blog/cold-email-copy-that-gets-replies-targeting-coaches/) — Instantly

### Multi-Channel & Hybrid
- [Multichannel Outreach Guide](https://evaboot.com/blog/multichannel-outreach) — Evaboot
- [Cold Outreach Strategies 2026](https://zintlr.com/blog/cold-outreach-that-actually-works-2026-email-linkedin-tips/) — Zintlr
- [Turn Cold Leads Into Warm Leads](https://leadconnect.io/blog/cold-outreach-warm-outreach/) — LeadConnect

### Economics & ROI
- [Economics of Cold B2B Outreach 2025](https://www.marketowl.ai/ai-digital-marketing-today/the-2025-economics-of-cold-b2b-outreach-best-practices-cost-breakdown-and-roi-for-linkedin-email) — MarketOwl
- [Average Cost Per Lead by Industry](https://firstpagesage.com/reports/average-cost-per-lead-by-industry/) — First Page Sage
- [B2B Sales Conversion Rate by Industry 2025](https://serpsculpt.com/reports/b2b-sales-conversion-rate-by-industry/) — SerpSculpt
- [B2B Referral Statistics 2025](https://www.thinkimpact.com/b2b-referral-statistics/) — ThinkImpact

### Lead Sourcing & Scraping
- [Apify Instagram Profile Scraper](https://apify.com/apify/instagram-profile-scraper)
- [Apify Google Maps Scraper](https://apify.com/compass/crawler-google-places)
- [Apify LinkedIn Profile Scraper (No Cookie)](https://apify.com/supreme_coder/linkedin-profile-scraper)
- [Apify Website Tech Stack Scanner](https://apify.com/misterkhan/website-tech-stack-scanner)
- [BuiltWith ScoreApp Trends](https://trends.builtwith.com/websitelist/ScoreApp)
- [n8n Apify + Google Maps Template](https://n8n.io/workflows/5743-scrape-google-maps-leads-email-phone-website-using-apify-gpt-airtable/)
- [n8n Instagram Lead Gen Template](https://n8n.io/workflows/7373-generate-qualified-instagram-leads-from-hashtags-with-apify-and-google-sheets/)

### Qualification & Positioning
- [Quiz Conversion Rate Report 2026](https://www.tryinteract.com/blog/quiz-conversion-rate-report/) — Interact
- [Quiz Funnels vs Lead Magnets](https://www.kyleads.com/blog/quiz-funnels-vs-lead-magnets/) — KyLeads
- [ScoreApp Lead Magnets for Coaches](https://www.scoreapp.com/lead-magnets-coaches/) — ScoreApp
- [How to Sell Website Audits](https://www.funnelpacks.com/how-to-sell-website-audits/) — FunnelPacks
- [Coaching Hashtags](https://lovelyimpact.com/coaching-hashtags/) — Lovely Impact

### Strategy Frameworks
- [Alex Hormozi's $100M Cold Email Strategy](https://oncely.com/blog/alex-hormozis-100m-cold-email-strategy-a-comprehensive-analysis/) — Oncely
- [$100M Leads](https://www.acquisition.com/books) — Alex Hormozi
- [LinkedIn Search Limits](https://www.salesrobot.co/blogs/bypass-linkedin-search-limit) — SalesRobot
- [Google Dorks Cheat Sheet](https://www.stationx.net/google-dorks-cheat-sheet/) — StationX
- [Wappalyzer Alternatives](https://stackcrawler.com/blog/top-wappalyzer-alternatives) — Stackcrawler

### Coach Tools & Platforms
- [Paperbell Review](https://quso.ai/blog/paperbell-review-features-pros-cons-alternatives) — Quso.ai
- [Kartra vs Kajabi vs ClickFunnels 2026](https://kartra.com/blog/kartra-vs-kajabi-vs-clickfunnels-2026/) — Kartra
- [Mighty Networks](https://www.mightynetworks.com/)
- [Apollo.io](https://www.apollo.io/)
- [Dux-Soup LinkedIn Automation](https://www.dux-soup.com/blog/find-coaching-leads-on-autopilot-using-linkedin-automation-in-the-cloud)

### CRM & Pipeline
- [HubSpot vs Notion](https://www.breakcold.com/blog/hubspot-vs-notion) — Breakcold
- [Notion CRM Guide](https://www.folk.app/articles/how-to-use-notion-as-a-crm-a-step-by-step-guide-and-best-alternatives) — Folk App

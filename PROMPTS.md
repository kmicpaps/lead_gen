# Prompt Library

## Slash Commands (Recommended)

The fastest way to run common workflows. Type the command directly — no copy-pasting needed:

| Task | Slash Command | Example |
|------|--------------|---------|
| New Apollo campaign | `/new-apollo-list` | `/new-apollo-list acme_corp https://app.apollo.io/... 2000` |
| Rescrape for more leads | `/find-more-leads` | `/find-more-leads acme_corp https://app.apollo.io/...` |
| Google Maps leads | `/gmaps-leads` | `/gmaps-leads acme_corp Riga "lawyers, accountants"` |
| Build Apollo URL | `/build-apollo-url` | `/build-apollo-url construction owners Latvia 10-50 employees` |
| Quality filter leads | `/quality-filter` | `/quality-filter path/to/leads.json` |
| Cross-campaign dedup | `/deduplicate-leads` | `/deduplicate-leads acme_corp` |
| Research a client | `/research-client` | `/research-client https://example.com` |
| Plan cold emails | `/cold-email-planning` | `/cold-email-planning acme_corp` |
| Sales demo sample | `/create-sales-sample` | `/create-sales-sample https://prospect.com` |
| Onboard new client | `/onboard-new-client` | `/onboard-new-client "Acme Corp" https://acme.com` |
| What can I do? | `/pipeline-overview` | `/pipeline-overview` |

Not sure which to use? Type `/pipeline-overview` for a decision tree.

---

## Copy-Paste Templates

For enrichment tasks, CSV imports, and admin/setup — use the templates below. Copy the prompt block, replace `[PLACEHOLDERS]`, and paste into a Claude session.

---

## Lead Generation

### 1. New Apollo Campaign

**What:** Scrape leads from an Apollo search URL, deduplicate, filter for quality, and export to Google Sheets.
**When:** You have an Apollo URL with filters ready and want a clean lead list for outreach.

**Prompt:**
```
Familiarize yourself with the workspace, directives, and execution scripts.

I need a new Apollo lead campaign:
- Client: [CLIENT_NAME]
- Apollo URL: [PASTE THE FULL APOLLO URL]
- Target leads: [NUMBER, e.g. 2000]
- Scrapers: [all / skip olympus / codecrafter + peakydev only]
- Enrichment: [none / industry only / full (industry + icebreakers)]

Create a new campaign folder, scrape, deduplicate against existing campaigns
for this client, run quality filtering (present me the analysis and let me
choose which filters to apply), and export the final list to Google Sheets.
```

**You'll get:**
- Google Sheet link with filtered, deduplicated leads
- Quality report showing what was filtered and why
- Updated client.json with campaign metadata

**Tips:**
- Say "skip olympus" if Apollo cookies are expired or you don't want to deal with cookie refresh
- PeakyDev has a minimum of 1000 leads per run — if your Apollo list is small, mention that
- If you have existing leads in a CSV you want to deduplicate against, mention the file name
- For rescraping an existing list, use prompt #2 instead

---

### 2. Rescrape Existing Apollo List (Find More Leads)

**What:** Run scrapers again on an Apollo URL you've already used, deduplicate against all previous results, and get only the new leads.
**When:** You've already scraped this list before but Apollo's database has updated, or you want to pull from a different scraper.

**Prompt:**
```
Familiarize yourself with the workspace, directives, and existing campaign lists.

I need to find MORE leads for an existing Apollo list:
- Client: [CLIENT_NAME]
- Apollo URL: [PASTE THE FULL APOLLO URL]
- List name/description: [e.g. "Latvia HR Coaching Leaders"]
- Target leads per scraper: [NUMBER, default 5000]
- Scrapers: [all / skip olympus / codecrafter + peakydev only]

Create a new campaign folder (don't merge into the old one), scrape,
deduplicate against ALL existing campaigns for this client, run quality
filtering (let me choose filters), and export only the truly new leads
to Google Sheets.
```

**You'll get:**
- Google Sheet with only new leads (not in any previous campaign)
- Breakdown of how many were duplicates vs truly new
- Quality filter report

**Tips:**
- Expect high overlap (40-70%) since it's the same Apollo query — that's normal
- The more previous campaigns exist for this client, the more dedup will remove
- If you also have a CSV export of the previous list, mention it for extra dedup safety

---

### 3. Google Maps Local Business Scraping

**What:** Scrape businesses from Google Maps by location + niche, extract website contacts, and export to Google Sheets.
**When:** You want local business leads (restaurants, agencies, contractors, etc.) in a specific area.

**Prompt:**
```
Familiarize yourself with the workspace and the Google Maps lead generation directive.

I need Google Maps leads:
- Client: [CLIENT_NAME]
- Location: [CITY, REGION, or COUNTRY]
- Niches to scrape: [e.g. "marketing agencies, web design studios, PR firms"]
- Max results per niche: [NUMBER, e.g. 200]
- Extract website contacts: [yes / no]

Scrape Google Maps, extract contacts from websites if requested, and export
each niche to a separate tab in Google Sheets.
```

**You'll get:**
- Google Sheet with tabs per niche
- Business name, address, phone, website, rating, reviews
- Extracted contacts (email, phone from websites) if requested

**Tips:**
- More specific niches give better results than broad ones
- Website contact extraction takes longer but gives you direct email addresses
- Google Maps has a natural limit of ~120 results per search query — use specific niches

---

### 4. Apollo URL Crafter (Build Search URL from Description)

**What:** Convert a natural language description of desired leads into a working Apollo search URL.
**When:** You know what kind of leads you want but haven't built the Apollo URL yet.

**Prompt:**
```
Familiarize yourself with the Apollo URL crafter directive.

I need an Apollo search URL for:
- Target audience: [DESCRIBE WHO, e.g. "construction company owners in Latvia"]
- Company size: [e.g. "10-200 employees" or "any"]
- Additional filters: [e.g. "exclude staffing agencies" or "none"]

Build the Apollo URL, show me the filter summary, and give me the URL
to review in Apollo's UI. I'll refine it there and paste back the final
version when ready.
```

**You'll get:**
- Structured filter breakdown (titles, seniority, industries, locations, company size)
- Apollo URL ready to open in browser
- Filter gap analysis (what each scraper supports vs drops)

**Tips:**
- This is Step 0 before running any scraping campaign
- After you open the URL in Apollo and adjust filters visually, paste back the refined URL for scraping
- If you already have an Apollo URL, skip this and go straight to Prompt #1 (New Apollo Campaign)

---

## Lead Processing

### 4. Quality Filter a Lead List

**What:** Analyze a scraped lead list for quality issues and apply filters you choose (email, phone country code, title, industry).
**When:** You have a lead file and want to clean it up before outreach.

**Prompt:**
```
Familiarize yourself with the lead quality filtering directive.

I need to quality-filter a lead list:
- Lead file: [PATH TO JSON FILE or describe which campaign/list]
- Apollo URL (for context): [PASTE URL if available, or "not available"]

Run the quality analyzer, show me the full report (email coverage, phone
codes, title breakdown, industry breakdown), and let me choose which
filters to apply.
```

**You'll get:**
- Detailed quality report with counts and percentages
- Menu of recommended filters with impact numbers
- Filtered lead file after you choose
- Google Sheet export if requested

---

### 5. Cross-Campaign Deduplication

**What:** Remove duplicate leads that appear across multiple campaigns for the same client.
**When:** A client has had multiple scraping campaigns and you want to ensure no one gets contacted twice.

**Prompt:**
```
Run cross-campaign deduplication for client [CLIENT_NAME].
First do a dry run to show me the overlap, then apply if the numbers look right.
```

**You'll get:**
- Report showing how many duplicates exist across campaigns
- Cleaned files with duplicates removed (after your approval)

---

### 6. Import & Compare External CSV

**What:** Compare a CSV file (e.g. from Google Sheets, Smartlead, or another tool) against your existing campaign leads.
**When:** You received a lead list from somewhere and want to know how many are new vs already in your system.

**Prompt:**
```
I have a CSV file I want to compare against existing leads:
- CSV file: [FILENAME — place it in .tmp/imports/ first]
- Compare against: [CLIENT_NAME's campaigns / a specific campaign / all campaigns]

Show me:
1. How many leads in the CSV overlap with existing campaigns
2. How many are truly new
3. Export the new-only leads to Google Sheets if there are enough
```

**You'll get:**
- Overlap report with counts
- List of new leads (if any)
- Optional Google Sheet export

**Tips:**
- Place the CSV in `.tmp/imports/` before starting
- CSV email field names vary ("Email", "E-mail", "email") — Claude handles this automatically

---

## Lead Enrichment

### 7. Industry Classification

**What:** Add industry labels to leads that are missing them, using AI website analysis.
**When:** Your lead list has gaps in the industry field and you need it for filtering or segmentation.

**Prompt:**
```
Familiarize yourself with the industry enrichment directive.

Enrich industry data for:
- Lead file: [PATH TO JSON FILE or describe which campaign]
- AI provider: [openai / anthropic]

Only enrich leads that are missing industry data. Show me coverage before and after.
```

**You'll get:**
- Enriched lead file with industry labels filled in
- Coverage report (before/after percentages)

**Tips:**
- OpenAI is cheaper for bulk enrichment; Anthropic is more accurate
- Most scraped leads already have industry from Apollo (95-99%) — check coverage first

---

### 8. LinkedIn Profile Enrichment

**What:** Enrich leads with LinkedIn profile data — bio, experience, education, tenure, follower count.
**When:** You need deeper personalization data for high-value outreach.

**Prompt:**
```
Familiarize yourself with the LinkedIn enrichment directive.

Enrich LinkedIn profiles for:
- Lead file: [PATH TO JSON FILE or describe which campaign]
- Max leads to enrich: [NUMBER, or "all"]

This uses the Lead Magic API — confirm the cost estimate before proceeding.
```

**You'll get:**
- Enriched lead file with LinkedIn bio, experience, education, tenure
- Cost breakdown

**Tips:**
- This costs credits per lead — use it for small, high-value lists
- Leads must have `linkedin_url` populated for this to work

---

### 9. Icebreaker Generation

**What:** Generate personalized icebreaker lines for each lead by scraping their company website and using AI.
**When:** You want personalized opening lines for cold emails.

**Prompt:**
```
Familiarize yourself with the icebreaker enrichment directive.

Generate icebreakers for:
- Lead file: [PATH TO JSON FILE or describe which campaign]
- Max leads: [NUMBER, or "all"]
- AI provider: [openai / anthropic]

Scrape company websites and generate personalized icebreaker lines.
```

**You'll get:**
- Enriched lead file with `icebreaker` field
- Report of how many websites were successfully scraped

**Tips:**
- This is the slowest enrichment (website scraping + AI) — expect 2-5 min per 100 leads
- Works best when leads have `website_url` populated

---

### 10. Casual Company Names

**What:** Convert formal legal company names (e.g. "SIA Latvijas Mobilais Telefons") to casual versions ("LMT") for friendlier emails.
**When:** Your leads have formal corporate names and you want natural-sounding references.

**Prompt:**
```
Generate casual company names for:
- Lead file: [PATH TO JSON FILE or describe which campaign]
- AI provider: [openai / anthropic]
```

**You'll get:**
- Enriched file with `casual_org_name` field added

---

### 11. Fix Baltic/Slavic Name Diacritics

**What:** Restore special characters (a, e, i, u, etc.) to names that were stripped to ASCII by Apollo.
**When:** You have Latvian, Lithuanian, or other Baltic/Slavic leads with anglicized names.

**Prompt:**
```
Fix name diacritics for:
- File: [PATH TO CSV or JSON FILE]
- File type: [csv / json]

Use LinkedIn URL slugs to restore the correct special characters.
```

**You'll get:**
- Fixed file with proper diacritics (e.g. "Janis Berzins" -> "Janis Berzins")

**Tips:**
- Leads must have `linkedin_url` for this to work — the diacritics come from the URL slug

---

## Sales & Outreach

### 12. Client Discovery (Website Analysis)

**What:** Analyze a prospect's website to understand their business, suggest an ICP, and recommend Apollo filters.
**When:** You're onboarding a new client and need to understand their business before building campaigns.

**Prompt:**
```
Familiarize yourself with the client discovery directive.

I need to research a potential client:
- Company website: [URL]
- Company name: [NAME]

Analyze their website, figure out what they sell and to whom, suggest an
ideal customer profile (ICP), and recommend Apollo filter parameters for
a lead generation campaign.
```

**You'll get:**
- Business summary (what they do, who they serve, value prop)
- Recommended ICP (titles, industries, company sizes, locations)
- Suggested Apollo filter configuration
- Draft client.json ready for onboarding

---

### 13. Cold Email Copywriting

**What:** Generate personalized cold email sequences using lead data and reference copy style.
**When:** You have a clean lead list and need email copy for outreach tools (Smartlead, etc.).

**Prompt:**
```
Familiarize yourself with the cold email copywriting directive.

Generate cold email sequences for:
- Client: [CLIENT_NAME]
- Lead list: [describe which campaign/list]
- Number of emails in sequence: [e.g. 3]
- Tone: [casual / professional / direct]
- Reference copy style: [describe or say "check the client's reference_copies folder"]

Include subject lines, body copy, and personalization tokens.
```

**You'll get:**
- Email sequence templates with personalization variables
- Subject line variations
- Ready to import into outreach tools

---

### 14. Sales Sample / Demo Deliverable

**What:** Create a demo deliverable to show a prospect what your lead generation service produces.
**When:** You're pitching a new client and want to show them a sample of what they'd get.

**Prompt:**
```
Familiarize yourself with the sales sample generation directive.

Create a sales sample for prospect:
- Company: [COMPANY NAME]
- Website: [URL]
- Their target market (if known): [describe, or "figure it out from the website"]

Generate a sample that includes business analysis, sample leads, enrichment
preview, and email template examples.
```

**You'll get:**
- Business analysis of the prospect
- Sample enriched leads for their ICP
- Example email templates
- Professional deliverable they can review

---

## Admin & Setup

### 15. Onboard a New Client

**What:** Create the full client folder structure with metadata, ready for campaigns.
**When:** Starting work with a new client for the first time.

**Prompt:**
```
Onboard a new client:
- Company name: [NAME]
- Website: [URL]
- Contact email: [EMAIL]
- Industry: [INDUSTRY]
- What they sell: [BRIEF DESCRIPTION]
- Target audience: [WHO THEY WANT TO REACH]
- Target locations: [COUNTRIES/REGIONS]

Create the client folder, client.json, and prepare the campaign structure.
If the website is provided, run a quick discovery to suggest ICP details.
```

**You'll get:**
- `campaigns/[client_id]/` folder with client.json, apollo_lists/, google_maps_lists/
- Populated ICP in client.json
- Ready to run campaigns

---

### 16. Add a New Directive / SOP

**What:** Document a new workflow as a reusable directive that Claude can follow in future sessions.
**When:** You've figured out a process that works and want to make it repeatable.

**Prompt:**
```
I want to create a new directive for this workspace.

The workflow is: [DESCRIBE WHAT THE WORKFLOW DOES]

Steps involved:
1. [STEP 1]
2. [STEP 2]
3. [STEP 3]
...

Scripts it uses (if any): [LIST SCRIPTS, or "none yet — may need new ones"]
Inputs needed: [WHAT THE USER PROVIDES]
Output: [WHAT THE DELIVERABLE IS]

Review the existing directive format in directives/, create a new directive
following the same conventions, and update directives/README.md with the
new entry.
```

**You'll get:**
- New `.md` file in `directives/`
- Updated README index
- Consistent format with existing directives

---

### 17. Add a New Scraper or Lead Source

**What:** Integrate a new Apify actor or external data source into the lead generation pipeline.
**When:** You found a new scraper on Apify or want to pull leads from a new source.

**Prompt:**
```
I want to add a new scraper/lead source to this workspace.

Source: [APIFY ACTOR NAME or API DESCRIPTION]
What it does: [DESCRIBE THE DATA IT RETURNS]
Apify actor URL: [URL if applicable]

Follow the 3-step scraper registration process:
1. Create execution/scraper_newname.py following existing scraper patterns
2. Add a registry entry in execution/scraper_registry.py
3. Add a normalize_newname() function in execution/lead_normalizer.py

See docs/CONTEXT_pipeline_v7_standardization.md for the full field reference.
Test with a small batch (25 leads) to verify field mapping before any paid runs.
```

**You'll get:**
- New scraper script in `execution/`
- Registry entry (orchestrator picks it up automatically)
- Updated normalizer with field mappings
- Test results for review before full scrape

---

### 18. Add Instructions for a New Task

**What:** Teach the workspace how to do something entirely new — could need a directive, a script, or both.
**When:** You want Claude to handle a task that isn't covered by existing workflows.

**Prompt:**
```
I want to add a new capability to this workspace.

The task: [DESCRIBE WHAT YOU WANT TO BE ABLE TO DO]
How often: [one-time / recurring]
Inputs: [WHAT INFORMATION IS NEEDED]
Output: [WHAT THE RESULT SHOULD LOOK LIKE]

Figure out whether this needs:
- A new directive only (if existing scripts cover it)
- A new script only (if it's a simple tool)
- Both (if it's a full workflow)

Follow the 3-layer architecture: directive for the SOP, script for the
deterministic work, you (Claude) for the decision-making.

Create whatever is needed, test it, and update the relevant README/indexes.
Also add a new prompt template to PROMPTS.md for this task.
```

**You'll get:**
- New directive and/or script as needed
- Updated indexes (directives/README.md)
- New prompt template added to PROMPTS.md
- Tested and working

---

## Quick Reference

### Where Things Live

| What | Where |
|------|-------|
| AI agent instructions | `CLAUDE.md` (root) |
| This prompt library | `PROMPTS.md` (root) |
| SOPs / workflows | `directives/` (see `directives/README.md` for index) |
| Python scripts / tools | `execution/` |
| Client data & campaigns | `campaigns/[client_name]/` |
| Temp files & scraper output | `.tmp/` (gitignored, regenerable) |
| External CSV imports | `.tmp/imports/` |
| API keys | `.env` |
| Reference docs | `docs/` |

### Active Clients

Check current clients with:
```
Look at the campaigns/ folder and list all active clients with their campaign history.
```

### Common Follow-Up Prompts

After a campaign or task, you might want to:

**Check results:**
```
Show me the lead counts and Google Sheet links for all campaigns for [CLIENT_NAME].
```

**Re-export with different filters:**
```
Re-run the quality filter on [CAMPAIGN NAME] with different criteria.
I want to [change what you want different].
```

**Add enrichment to existing leads:**
```
Add [industry / icebreaker / LinkedIn / casual name] enrichment to the
[CAMPAIGN NAME] leads for [CLIENT_NAME].
```

**Compare two lists:**
```
Compare the leads in [FILE/CAMPAIGN 1] against [FILE/CAMPAIGN 2].
Show me the overlap and what's unique to each.
```

**Clean up after a session:**
```
Clean up .tmp/ — delete any campaign-specific temp directories for campaigns
that are already saved in campaigns/. Keep the standard scraper output dirs.
```

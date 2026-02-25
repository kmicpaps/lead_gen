# Client Onboarding Form

Fill this out so we can find the right leads and write emails that actually sound like you.

---

## 1. About Your Company

**Company name:**
>

**Website:**
>

**What do you sell?** (1-2 sentences, plain English)
> Example: "We build custom software for fintech companies"

**What problem do you solve?** (Why do people pay you?)
> Example: "Companies waste months building internal tools. We do it in weeks."

---

## 2. Who Buys From You

**Job titles of people who say "yes" to deals:**
> Example: CTO, VP Engineering, Head of Product

**Company size that's the sweet spot:**
- [ ] 1-10 employees
- [ ] 11-50 employees
- [ ] 51-200 employees
- [ ] 201-500 employees
- [ ] 500+ employees

**Industries you've closed deals in:**
> Example: Fintech, SaaS, E-commerce

**Industries you WANT to break into:**
> Example: Healthcare, Insurance

**Geographic focus:**
> Example: DACH region, Nordics, US East Coast

**Any tech stack or keywords that signal a good fit?**
> Example: "Uses AWS", "Hiring engineers", "Series B+"

---

## 3. Your Best Customers

**Name 2-3 companies you've worked with** (we'll use these as reference points):
> 1.
> 2.
> 3.

**What made them good customers?**
> Example: "They had budget, moved fast, and actually implemented our recommendations"

**Red flags - who should we AVOID?**
> Example: "Agencies, companies under 20 people, anyone looking for hourly contractors"

---

## 4. Email Voice & Style

**Who's sending the emails?**
- Name:
- Title:
- LinkedIn (optional):

**How formal should emails be?**
- [ ] Very casual ("hey, saw your stuff...")
- [ ] Friendly professional ("Hi [Name], came across...")
- [ ] More formal ("Dear [Name], I noticed...")

**Anything you definitely DON'T want in emails?**
> Example: "Don't mention competitors", "No urgency tactics", "Don't say 'synergy'"

**Sample email you've sent that worked well** (optional, paste below):
>

---

## 5. Proof Points

**Quick win or stat you can mention:**
> Example: "Cut processing time by 60%", "Saved $200k in year one"

**Any awards, certifications, or logos that matter?**
> Example: "AWS Partner", "ISO certified", "Worked with [Big Name]"

---

## 6. Campaign Details

**How many leads do you want?**
- [ ] 50 (sample/test)
- [ ] 100-200 (small campaign)
- [ ] 500+ (full campaign)

**Timeline:**
> Example: "Need leads by Friday", "No rush, next week is fine"

**Anything else we should know?**
>

---

## Quick Reference (for our team)

After form is submitted, extract:

| Field | Maps To |
|-------|---------|
| Website | `client_discovery.py` input |
| Job titles | Apollo `person_titles` |
| Company size | Apollo `organization_num_employees_ranges` |
| Industries | Apollo `organization_industries` |
| Geography | Apollo `organization_locations` |
| Tech/keywords | Apollo `organization_keyword_tags` |
| Sender name | Email `{{sender_name}}` |
| Voice preference | AI prompt tone setting |
| Proof points | Email social proof line |
| Red flags | Lead filtering rules |

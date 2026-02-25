# [CLI] — run via: py execution/ai_lead_enricher.py --help
"""
AI Lead Enricher

Enriches leads with:
1. Industry categorization (from linkedin_industry or AI inference)
2. Company summary (from website content)
3. Personalized icebreaker (from linkedin + website data)

Usage:
    python ai_lead_enricher.py --input leads.json --client-context "Acme Corp provides software dev and AI consulting"
    python ai_lead_enricher.py --input leads.json --client-context "We sell CRM software" --output enriched.json
"""

import json
import argparse
import os
import sys
import time
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

from utils import RateLimiter


def extract_org_name(lead):
    """Extract organization name from nested structure or flat field."""
    org = lead.get('org_name', '')
    if isinstance(org, dict):
        return org.get('name', '')
    return str(org) if org else ''


def categorize_industry(lead, client, rate_limiter):
    """Categorize lead's industry from available data."""
    # First check if we already have linkedin_industry
    linkedin_industry = lead.get('linkedin_industry', '').strip()
    if linkedin_industry and linkedin_industry.lower() not in ['', 'unknown', 'n/a']:
        return linkedin_industry

    # Otherwise use AI to infer from website content
    website_content = lead.get('website_content', '').strip()
    company_name = extract_org_name(lead)

    if not website_content or len(website_content) < 50:
        return ''

    try:
        rate_limiter.acquire()

        prompt = f"""Based on the website content below, identify the company's primary industry.

Company: {company_name}
Website content (excerpt):
{website_content[:1000]}

Return ONLY the industry name (e.g., "Financial Services", "Healthcare Technology", "Manufacturing", "Software Development", "E-commerce").
Do not include any explanation, just the industry name."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a business analyst categorizing companies by industry."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=50
        )

        industry = response.choices[0].message.content.strip()
        return industry.strip('"').strip("'")
    except Exception as e:
        print(f"  Error categorizing industry for {company_name}: {e}", file=sys.stderr)
        return ''


def generate_company_summary(lead, client, rate_limiter):
    """Generate company summary from website content."""
    website_content = lead.get('website_content', '').strip()
    company_name = extract_org_name(lead)

    if not website_content or len(website_content) < 50:
        return ""

    try:
        rate_limiter.acquire()

        prompt = f"""Summarize this company based on their website content.

Company: {company_name}
Website content:
{website_content[:1500]}

Write a 1-2 sentence summary that captures:
1. What the company does (products/services)
2. Their key differentiator or target market

Be concise and factual. Use third person.
Return ONLY the summary, nothing else."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a business analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=150
        )

        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        print(f"  Error generating summary for {company_name}: {e}", file=sys.stderr)
        return ""


def generate_icebreaker(lead, client, rate_limiter, client_context=""):
    """Generate personalized icebreaker from available data."""
    company_name = extract_org_name(lead)
    title = lead.get('title', '')
    first_name = lead.get('first_name', '')

    # Gather personalization data
    linkedin_bio = lead.get('linkedin_bio', '').strip()
    linkedin_headline = lead.get('linkedin_headline', '').strip()
    website_content = lead.get('website_content', '').strip()
    industry = lead.get('industry', '') or lead.get('linkedin_industry', '')

    # Build context for AI
    personalization_context = []
    if linkedin_headline:
        personalization_context.append(f"LinkedIn headline: {linkedin_headline}")
    if linkedin_bio:
        personalization_context.append(f"LinkedIn bio: {linkedin_bio[:300]}")
    if website_content:
        personalization_context.append(f"Company website excerpt: {website_content[:500]}")

    if not personalization_context:
        # Fallback generic icebreaker
        return f"Noticed {company_name}'s work in the {industry or 'tech'} space - would be great to connect."

    try:
        rate_limiter.acquire()

        prompt = f"""Write a casual, human-sounding icebreaker for a cold email.

PROSPECT:
- Name: {first_name}
- Title: {title}
- Company: {company_name}
- Industry: {industry}
{chr(10).join(personalization_context)}

RULES - THIS IS CRITICAL:
1. Sound like a human typed this on their phone, not a marketing team
2. Keep it to 1-2 SHORT sentences (under 25 words total)
3. Reference ONE specific thing from their data
4. No corporate buzzwords: avoid "inspiring", "impressive", "remarkable", "passionate", "commitment", "synergy", "leverage"
5. No questions
6. No exclamation marks
7. Casual tone - like texting a work friend

GOOD examples:
- "Saw {company_name} is going hard on the AI stuff. Makes sense given your ML background."
- "Just came across {company_name} - the compliance angle is smart for the Nordics."
- "Your work with [specific project] caught my eye. Solid approach."

BAD examples (too corporate/AI-sounding):
- "I was impressed by your commitment to driving innovation..."
- "I came across your inspiring journey..."
- "It's remarkable how you've built..."

Return ONLY the icebreaker, nothing else."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional B2B sales copywriter specializing in personalized outreach."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )

        icebreaker = response.choices[0].message.content.strip()
        return icebreaker.strip('"').strip("'")
    except Exception as e:
        print(f"  Error generating icebreaker for {company_name}: {e}", file=sys.stderr)
        return f"Noticed {company_name}'s work in the {industry or 'tech'} space."


def main():
    parser = argparse.ArgumentParser(description='AI Lead Enricher - adds industry, summary, icebreaker')
    parser.add_argument('--input', required=True, help='Input JSON file with leads')
    parser.add_argument('--output', help='Output JSON file (defaults to overwriting input)')
    parser.add_argument('--client-context', default='', help='Brief description of what the sender/client does')
    parser.add_argument('--skip-existing', action='store_true', help='Skip leads that already have enrichment')
    args = parser.parse_args()

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment", file=sys.stderr)
        return 1

    client = OpenAI(api_key=api_key)

    # Load leads
    with open(args.input, 'r', encoding='utf-8') as f:
        leads = json.load(f)

    print(f"Loaded {len(leads)} leads")
    print(f"Client context: {args.client_context or '(none provided)'}")

    # Count what needs enrichment
    needs_industry = sum(1 for l in leads if not l.get('industry'))
    needs_summary = sum(1 for l in leads if not l.get('company_summary') and l.get('website_content'))
    needs_icebreaker = sum(1 for l in leads if not l.get('icebreaker'))

    print(f"\nNeeds industry: {needs_industry}")
    print(f"Needs summary: {needs_summary}")
    print(f"Needs icebreaker: {needs_icebreaker}")

    if args.skip_existing and needs_industry == 0 and needs_summary == 0 and needs_icebreaker == 0:
        print("\nNothing to enrich!")
        return 0

    # Rate limiter: 40 requests/sec (leaving headroom)
    rate_limiter = RateLimiter(40)

    print("\nEnriching leads...")
    start_time = time.time()
    enriched_count = 0

    for i, lead in enumerate(leads):
        company_name = extract_org_name(lead) or f"Lead {i+1}"
        made_changes = False

        # 1. Industry categorization
        if not lead.get('industry') or not args.skip_existing:
            industry = categorize_industry(lead, client, rate_limiter)
            if industry:
                lead['industry'] = industry
                made_changes = True

        # 2. Company summary
        if (not lead.get('company_summary') or not args.skip_existing) and lead.get('website_content'):
            summary = generate_company_summary(lead, client, rate_limiter)
            if summary:
                lead['company_summary'] = summary
                lead['company_summary_generated_at'] = datetime.now().isoformat()
                made_changes = True

        # 3. Icebreaker
        if not lead.get('icebreaker') or not args.skip_existing:
            icebreaker = generate_icebreaker(lead, client, rate_limiter, args.client_context)
            if icebreaker:
                lead['icebreaker'] = icebreaker
                lead['icebreaker_generated_at'] = datetime.now().isoformat()
                made_changes = True

        if made_changes:
            enriched_count += 1
            print(f"  [{i+1}/{len(leads)}] Enriched: {company_name}")
        else:
            print(f"  [{i+1}/{len(leads)}] Skipped: {company_name} (no changes needed)")

    elapsed = time.time() - start_time
    print(f"\nEnriched {enriched_count} leads in {elapsed:.1f}s")

    # Save
    output_path = args.output or args.input
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)

    print(f"Saved to: {output_path}")
    return 0


if __name__ == '__main__':
    sys.exit(main())

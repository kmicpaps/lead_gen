# [CLI] — run via: py execution/ai_fallback_enricher.py --help
"""
Add missing enrichments: generic icebreakers and company summaries
"""

import json
import argparse
import os
import sys
from datetime import datetime
from openai import OpenAI
import time
from utils import RateLimiter


def extract_org_name(lead):
    """Extract organization name from nested structure or flat field."""
    # Check company_name first (canonical), then org_name (scraper output)
    name = lead.get('company_name', '')
    if name:
        return str(name)
    org = lead.get('org_name', '')
    if isinstance(org, dict):
        return org.get('name', '')
    return str(org)


def generate_generic_icebreaker(lead, api_key, rate_limiter):
    """Generate a generic icebreaker when website content is unavailable."""
    try:
        rate_limiter.acquire()

        client = OpenAI(api_key=api_key)

        company_name = lead.get('casual_org_name') or extract_org_name(lead)
        title = lead.get('title', '')
        country = lead.get('country', '')

        prompt = f"""You are writing a brief, professional cold outreach icebreaker for a B2B prospect.

Lead information:
- Company: {company_name}
- Job title: {title}
- Location: {country}
- Industry: Precast concrete / construction

Write a 1-2 sentence professional icebreaker that:
1. Shows interest in their industry or role
2. Is professional but friendly
3. Mentions their company name naturally
4. Does NOT ask questions
5. Does NOT make assumptions about specific projects or activities

Example: "Saw that {company_name} is in the precast concrete space in {country}. Your role in {title} caught my attention."

Return ONLY the icebreaker text, nothing else."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional B2B copywriter."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )

        icebreaker = response.choices[0].message.content.strip()
        # Remove surrounding quotes if AI added them
        icebreaker = icebreaker.strip('"').strip("'")
        return icebreaker

    except Exception as e:
        print(f"Error generating generic icebreaker for {company_name}: {e}", file=sys.stderr)
        return f"Noticed {company_name}'s work in the construction industry. Would be great to connect."


def generate_company_summary(lead, api_key, rate_limiter):
    """Generate company summary from website content."""
    website_content = lead.get('website_content', '').strip()

    if not website_content or len(website_content) < 50:
        return ""

    try:
        rate_limiter.acquire()

        client = OpenAI(api_key=api_key)

        company_name = lead.get('casual_org_name') or extract_org_name(lead)

        prompt = f"""You are summarizing a company's website for sales research.

Company: {company_name}
Website content:
{website_content[:1500]}

Write a 1-2 sentence summary that captures:
1. What the company does (products/services)
2. Their key differentiator or focus area

Be concise and factual. Use third person.

Example: "HABA-Beton specializes in precast concrete elements for residential and commercial construction, with a focus on custom architectural solutions."

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
        print(f"Error generating company summary for {company_name}: {e}", file=sys.stderr)
        return ""


def main():
    parser = argparse.ArgumentParser(description='Add missing icebreakers and company summaries')
    parser.add_argument('--input', required=True, help='Input JSON file with leads')
    parser.add_argument('--output', help='Output JSON file (defaults to adding _complete suffix)')
    args = parser.parse_args()

    # Load API key
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment", file=sys.stderr)
        return 1

    # Load leads
    with open(args.input, 'r', encoding='utf-8') as f:
        leads = json.load(f)

    print(f"Loaded {len(leads)} leads")

    # Count what needs to be added
    missing_icebreakers = sum(1 for l in leads if not l.get('icebreaker'))
    missing_summaries = sum(1 for l in leads if not l.get('company_summary'))

    print(f"Missing icebreakers: {missing_icebreakers}")
    print(f"Missing company summaries: {missing_summaries}")

    if missing_icebreakers == 0 and missing_summaries == 0:
        print("Nothing to enrich!")
        return 0

    # Rate limiter: 50 requests/sec for OpenAI
    rate_limiter = RateLimiter(50)

    # Add missing fields
    print("\nEnriching leads...")
    start_time = time.time()

    for i, lead in enumerate(leads):
        # Add generic icebreaker if missing
        if not lead.get('icebreaker'):
            icebreaker = generate_generic_icebreaker(lead, api_key, rate_limiter)
            lead['icebreaker'] = icebreaker
            lead['icebreaker_generated_by'] = 'openai_generic'
            lead['icebreaker_generated_at'] = datetime.now().isoformat()
            print(f"  [{i+1}/{len(leads)}] Added generic icebreaker for {lead.get('casual_org_name', 'Unknown')}")

        # Add company summary if missing (and website content exists)
        if not lead.get('company_summary') and lead.get('website_content'):
            summary = generate_company_summary(lead, api_key, rate_limiter)
            if summary:
                lead['company_summary'] = summary
                lead['company_summary_generated_by'] = 'openai'
                lead['company_summary_generated_at'] = datetime.now().isoformat()
                print(f"  [{i+1}/{len(leads)}] Added company summary for {lead.get('casual_org_name', 'Unknown')}")

    elapsed = time.time() - start_time

    # Save enriched leads
    if args.output:
        output_path = args.output
    else:
        input_dir = os.path.dirname(args.input)
        input_basename = os.path.basename(args.input)
        input_name, input_ext = os.path.splitext(input_basename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(input_dir, f"{input_name}_complete{input_ext}")

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)

    print(f"\nCompleted in {elapsed:.1f}s")
    print(f"Enriched leads saved to: {output_path}")
    print(output_path)

    return 0


if __name__ == '__main__':
    sys.exit(main())

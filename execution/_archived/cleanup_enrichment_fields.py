"""
Clean up enrichment fields and transform data for Google Sheets export.

Removes metadata fields and transforms website_content to company_summary.

Usage:
    py execution/cleanup_enrichment_fields.py --input enriched_leads.json
"""

import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def generate_company_summary_openai(website_content, company_name, api_key):
    """Generate company summary using OpenAI"""
    try:
        import openai

        client = openai.OpenAI(api_key=api_key)

        prompt = f"""Summarize this company in 1-2 concise sentences based on their website content.

Company: {company_name}
Website content: {website_content[:1000]}

Write a brief, professional summary focusing on:
- What they do
- Key products/services
- Notable specializations

Keep it under 150 characters. Be specific and factual."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes companies."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100,
            timeout=30
        )

        summary = response.choices[0].message.content.strip()
        return summary if summary else None

    except Exception as e:
        print(f"Error generating summary for {company_name}: {e}", file=sys.stderr)
        return None


def cleanup_lead(lead, api_key=None):
    """Clean up a single lead by removing metadata and transforming fields"""

    # Remove metadata fields
    metadata_fields = [
        'casual_org_name_generated_by',
        'casual_org_name_generated_at',
        'icebreaker_generated_by',
        'icebreaker_generated_at',
        'website_scraped_url'
    ]

    for field in metadata_fields:
        if field in lead:
            del lead[field]

    # Transform website_content to company_summary
    if 'website_content' in lead and lead['website_content']:
        website_content = lead['website_content']
        company_name = lead.get('casual_org_name') or lead.get('company_name', '')

        # Generate summary if API key provided
        if api_key:
            summary = generate_company_summary_openai(website_content, company_name, api_key)
            if summary:
                lead['company_summary'] = summary
        else:
            # Fallback: use first 150 chars
            lead['company_summary'] = website_content[:150].strip()

        # Remove original website_content field
        del lead['website_content']

    return lead


def main():
    parser = argparse.ArgumentParser(description='Clean up enrichment fields')
    parser.add_argument('--input', required=True, help='Input JSON file')
    parser.add_argument('--output', help='Output JSON file (default: appends _cleaned)')
    parser.add_argument('--generate-summaries', action='store_true', help='Generate AI summaries')

    args = parser.parse_args()

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        base = os.path.splitext(args.input)[0]
        output_path = f"{base}_cleaned.json"

    # Load leads
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            leads = json.load(f)
    except Exception as e:
        print(f"Error loading {args.input}: {e}", file=sys.stderr)
        return 1

    print(f"Loaded {len(leads)} leads")

    # Get API key if generating summaries
    api_key = None
    if args.generate_summaries:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("Warning: OPENAI_API_KEY not found, using fallback summaries", file=sys.stderr)

    # Clean up leads
    cleaned_leads = []
    for lead in leads:
        cleaned_lead = cleanup_lead(lead.copy(), api_key)
        cleaned_leads.append(cleaned_lead)

    # Save cleaned leads
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_leads, f, indent=2, ensure_ascii=False)

    print(f"Cleaned leads saved to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

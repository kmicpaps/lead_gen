# [CLI] — run via: py execution/cleanup_and_enrich_leads.py --help
"""
Script to clean up invalid leads and add fallback icebreakers.
"""

import os
import sys
import json
import argparse
from datetime import datetime

def is_invalid_lead(lead):
    """Check if lead is a scraper notification or invalid entry."""
    name = lead.get('name', '') or lead.get('full_name', '')

    # Filter out scraper notifications with emojis or specific keywords
    invalid_indicators = [
        '👀', '⏳', '📈', '✅', '🚀',
        'Actor', 'Scanning pages', 'enhance scraping',
        'split URLs', 'Use employee sizes'
    ]

    if name:
        for indicator in invalid_indicators:
            if indicator in name:
                return True

    # Filter out leads with no meaningful data (no name AND no email)
    if not name and not lead.get('email'):
        return True

    return False

def get_company_name(lead):
    """Extract company name from lead in any format."""
    org_name = lead.get('org_name', '')

    if isinstance(org_name, dict):
        return org_name.get('name', '')
    elif isinstance(org_name, str):
        return org_name

    return lead.get('company_name', '')

def generate_generic_icebreaker(lead):
    """Generate a generic icebreaker based on available lead info."""
    name = lead.get('name', '') or lead.get('full_name', '')
    first_name = lead.get('first_name', '') or name.split()[0] if name else ''
    company_name = lead.get('casual_org_name', '') or get_company_name(lead)
    title = lead.get('title', '') or lead.get('job_title', '')

    # Template options
    if company_name and title:
        return f"Hi {first_name}, I noticed your work as {title} at {company_name}. I'd love to connect and explore potential collaboration opportunities in the precast concrete industry."
    elif company_name:
        return f"Hi {first_name}, I came across {company_name} and was impressed by your work in the concrete solutions space. Would love to connect and discuss potential synergies."
    elif title:
        return f"Hi {first_name}, I see you're working as {title} in the construction industry. I'd be interested in connecting to explore opportunities in precast concrete solutions."
    else:
        return f"Hi {first_name}, I came across your profile and noticed your experience in the construction industry. I'd love to connect and discuss opportunities in the precast concrete sector."

def main():
    parser = argparse.ArgumentParser(description='Clean up and enrich leads')
    parser.add_argument('--input', required=True, help='Input leads JSON file')
    parser.add_argument('--output', help='Output file path (optional)')

    args = parser.parse_args()

    try:
        # Load leads
        with open(args.input, 'r', encoding='utf-8') as f:
            leads = json.load(f)

        print(f"Loaded {len(leads)} leads")

        # Filter out invalid leads
        valid_leads = [lead for lead in leads if not is_invalid_lead(lead)]
        removed_count = len(leads) - len(valid_leads)
        print(f"Removed {removed_count} invalid/notification leads")

        # Add fallback icebreakers for leads without them
        icebreaker_count = 0
        for lead in valid_leads:
            if not lead.get('icebreaker'):
                lead['icebreaker'] = generate_generic_icebreaker(lead)
                lead['icebreaker_type'] = 'generic_fallback'
                icebreaker_count += 1

        print(f"Added {icebreaker_count} fallback icebreakers")
        print(f"Final lead count: {len(valid_leads)}")

        # Save cleaned data
        if args.output:
            output_path = args.output
        else:
            # Create output path in same directory
            output_dir = os.path.dirname(args.input)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"cleaned_leads_{timestamp}_{len(valid_leads)}leads.json")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(valid_leads, f, indent=2, ensure_ascii=False)

        print(f"\nCleaned leads saved to: {output_path}")
        print(output_path)  # Print path for caller to capture

        return 0

    except Exception as e:
        print(f"Error cleaning leads: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

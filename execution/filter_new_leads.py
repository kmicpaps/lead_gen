# [CLI] — run via: py execution/filter_new_leads.py --help
"""
Filter out new leads by comparing against a previous list.
Keeps only leads that don't exist in the previous list.
"""

import json
import sys
import argparse
from datetime import datetime
import os

def normalize_key(text):
    """Normalize text for matching (lowercase, strip whitespace)."""
    if not text:
        return ''
    return str(text).lower().strip()

def main():
    parser = argparse.ArgumentParser(description='Filter new leads by comparing against previous list')
    parser.add_argument('--previous', required=True, help='Path to previous leads JSON file')
    parser.add_argument('--new-scrape', required=True, help='Path to newly scraped leads JSON file')
    parser.add_argument('--output-dir', required=True, help='Output directory')

    args = parser.parse_args()

    try:
        # Load previous leads
        with open(args.previous, 'r', encoding='utf-8') as f:
            previous_leads = json.load(f)
        print(f"Loaded {len(previous_leads)} leads from previous list")

        # Load new scrape
        with open(args.new_scrape, 'r', encoding='utf-8') as f:
            new_scrape = json.load(f)
        print(f"Loaded {len(new_scrape)} leads from new scrape")

        # Build lookup of previous leads (by email and name+org)
        previous_emails = set()
        previous_name_org = set()

        for lead in previous_leads:
            email = normalize_key(lead.get('email'))
            if email:
                previous_emails.add(email)

            name = normalize_key(lead.get('name'))
            org = normalize_key(lead.get('company_name') or lead.get('org_name'))
            if name and org:
                previous_name_org.add((name, org))

        # Filter for new leads only
        new_leads = []
        duplicate_count = 0

        for lead in new_scrape:
            email = normalize_key(lead.get('email'))
            name = normalize_key(lead.get('name'))
            org = normalize_key(lead.get('company_name') or lead.get('org_name'))

            # Check if this lead existed in previous list
            is_duplicate = False

            if email and email in previous_emails:
                is_duplicate = True
            elif name and org and (name, org) in previous_name_org:
                is_duplicate = True

            if not is_duplicate:
                new_leads.append(lead)
            else:
                duplicate_count += 1

        print(f"\nFiltering complete:")
        print(f"  - Total in new scrape: {len(new_scrape)}")
        print(f"  - Duplicates (already in previous list): {duplicate_count}")
        print(f"  - New unique leads: {len(new_leads)}")

        # Save new leads
        os.makedirs(args.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"new_leads_only_{timestamp}_{len(new_leads)}leads.json"
        filepath = os.path.join(args.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(new_leads, f, indent=2, ensure_ascii=False)

        print(f"\nNew leads saved to: {filepath}")
        print(filepath)

        return 0

    except Exception as e:
        print(f"Error filtering leads: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

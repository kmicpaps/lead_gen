# [CLI] — run via: py execution/leads_deduplicator.py --help
"""
Merge and deduplicate leads from multiple sources.
Primary deduplication key: email (case-insensitive)
Fallback key: name + company_name/org_name (for leads without emails)
Merge strategy: Keep the record with most non-empty fields
"""

import os
import sys
import json
import csv
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_leads, save_leads, normalize_key

def count_non_empty_fields(lead):
    """Count how many fields have non-empty values."""
    return sum(1 for value in lead.values() if value and str(value).strip())

def merge_leads(existing, new):
    """
    Merge two lead records, preferring the one with more complete data.
    If both have same completeness, prefer newer record (new).
    Also track which sources contributed to this lead.
    """
    existing_count = count_non_empty_fields(existing)
    new_count = count_non_empty_fields(new)

    # Merge sources
    existing_sources = set(existing.get('source', '').split(',') if existing.get('source') else [])
    new_sources = set(new.get('source', '').split(',') if new.get('source') else [])
    combined_sources = ','.join(sorted(existing_sources | new_sources))

    # Choose the richer record
    if new_count > existing_count:
        base_record = new.copy()
    else:
        base_record = existing.copy()

    # Fill in any missing fields from the other record
    other_record = existing if new_count > existing_count else new
    for key, value in other_record.items():
        if key != 'source' and (not base_record.get(key) or not str(base_record.get(key)).strip()):
            base_record[key] = value

    base_record['source'] = combined_sources
    return base_record

def main():
    parser = argparse.ArgumentParser(description='Merge and deduplicate leads from multiple sources')
    parser.add_argument('--apollo-file', help='Path to Apollo leads JSON file (legacy)')
    parser.add_argument('--apify-file', help='Path to Apify leads JSON file (legacy)')
    parser.add_argument('--source-file', action='append', help='Path to source leads JSON file (can be used multiple times)')
    parser.add_argument('--output-dir', default='.tmp/merged', help='Output directory')
    parser.add_argument('--output-prefix', default='merged_leads', help='Output file prefix')
    parser.add_argument('--reference-csv', type=str,
                        help='CSV file to dedup against (removes leads whose email matches reference)')

    args = parser.parse_args()

    # Collect all input files
    input_files = []
    if args.apollo_file:
        input_files.append(('Apollo', args.apollo_file))
    if args.apify_file:
        input_files.append(('Apify', args.apify_file))
    if args.source_file:
        for source_file in args.source_file:
            # Extract source name from file path
            source_name = os.path.basename(source_file).split('_')[0].title()
            input_files.append((source_name, source_file))

    if not input_files:
        print("Error: At least one input file is required", file=sys.stderr)
        return 1

    try:
        all_leads = []

        # Load all source files
        for source_name, filepath in input_files:
            if os.path.exists(filepath):
                leads = load_leads(filepath)
                print(f"Loaded {len(leads)} leads from {source_name}")
                all_leads.extend(leads)
            else:
                print(f"Warning: {source_name} file not found: {filepath}", file=sys.stderr)

        if not all_leads:
            print("Error: No leads to process", file=sys.stderr)
            return 1

        print(f"\nTotal raw leads: {len(all_leads)}")
        print("Starting deduplication...")

        # Deduplication maps
        leads_by_email = {}  # Primary: email-based deduplication
        leads_by_name_org = {}  # Fallback: name+org deduplication for leads without emails

        duplicate_count = 0

        for lead in all_leads:
            email = normalize_key(lead.get('email'))
            name = normalize_key(lead.get('name'))
            org = normalize_key(lead.get('company_name') or lead.get('org_name'))

            # Primary deduplication by email
            if email:
                if email in leads_by_email:
                    # Duplicate found - merge
                    leads_by_email[email] = merge_leads(leads_by_email[email], lead)
                    duplicate_count += 1
                else:
                    leads_by_email[email] = lead
            # Fallback: deduplicate by name + org for leads without email
            elif name and org:
                key = (name, org)
                if key in leads_by_name_org:
                    # Duplicate found - merge
                    leads_by_name_org[key] = merge_leads(leads_by_name_org[key], lead)
                    duplicate_count += 1
                else:
                    leads_by_name_org[key] = lead
            else:
                # Lead has no email and insufficient data for name+org matching
                # Keep it but log warning
                try:
                    print(f"Warning: Lead with insufficient data for deduplication: {lead.get('name', 'Unknown')}")
                except UnicodeEncodeError:
                    print(f"Warning: Lead with insufficient data for deduplication (name contains special characters)")
                # Generate a unique key to avoid dropping it
                unique_key = f"unknown_{len(leads_by_name_org)}"
                leads_by_name_org[unique_key] = lead

        # Combine deduplicated leads
        merged_leads = list(leads_by_email.values()) + list(leads_by_name_org.values())

        # Reference CSV dedup (if provided)
        if args.reference_csv:
            ref_emails = set()
            with open(args.reference_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Try common email column names
                    email = (row.get('Email') or row.get('email') or row.get('EMAIL') or '').strip().lower()
                    if email:
                        ref_emails.add(email)
            before_ref = len(merged_leads)
            merged_leads = [l for l in merged_leads if normalize_key(l.get('email')) not in ref_emails]
            ref_removed = before_ref - len(merged_leads)
            print(f"\nReference CSV dedup ({os.path.basename(args.reference_csv)}):")
            print(f"  Reference emails: {len(ref_emails)}")
            print(f"  Removed: {ref_removed} ({ref_removed/max(before_ref,1)*100:.1f}%)")
            print(f"  Remaining: {len(merged_leads)}")

        print(f"\nDeduplication complete:")
        print(f"  - Raw leads: {len(all_leads)}")
        print(f"  - Duplicates removed: {duplicate_count} ({duplicate_count/len(all_leads)*100:.1f}%)")
        print(f"  - Unique leads: {len(merged_leads)}")

        # Count by source
        apollo_only = sum(1 for lead in merged_leads if lead.get('source') == 'apollo')
        apify_only = sum(1 for lead in merged_leads if lead.get('source') == 'apify')
        both_sources = sum(1 for lead in merged_leads if ',' in lead.get('source', ''))
        print(f"\nSource breakdown:")
        print(f"  - Apollo only: {apollo_only}")
        print(f"  - Apify only: {apify_only}")
        print(f"  - Both sources: {both_sources}")

        # Save merged results
        filepath = save_leads(merged_leads, args.output_dir, args.output_prefix)
        print(f"\nMerged leads saved to: {filepath}")
        print(filepath)  # Print filepath to stdout for caller to capture

        return 0

    except Exception as e:
        print(f"Error merging and deduplicating leads: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

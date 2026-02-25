# [CLI] — run via: py execution/analyze_human_filters.py --help
"""
Analyze Human Filtering Decisions

Compares an original lead list (JSON) with a human-filtered export (CSV)
to learn what the human kept/removed and why. Outputs structured learnings
to campaigns/{client_id}/filter_learnings.json.

Usage:
    py execution/analyze_human_filters.py \
        --original .tmp/filtered/example_client_latvia_clean_v3_11532leads.json \
        --human-filtered "Example Client Latvia —Manual filters.csv" \
        --client-id example_client \
        --output-dir campaigns/example_client
"""

import sys
import os
import json
import csv
import argparse
from collections import Counter
from datetime import datetime


def load_json_leads(filepath):
    """Load leads from JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_csv_leads(filepath):
    """Load leads from CSV file (Google Sheets export format)."""
    leads = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            leads.append(dict(row))
    return leads


def normalize_email(email):
    """Normalize email for matching."""
    return (email or '').strip().lower()


def get_field(lead, *field_names):
    """Get first non-empty value from multiple possible field names."""
    for name in field_names:
        val = lead.get(name, '')
        if val and str(val).strip():
            return str(val).strip()
    return ''


def build_email_set(leads):
    """Build a set of normalized emails from leads."""
    return {normalize_email(get_field(l, 'Email', 'email')) for l in leads
            if get_field(l, 'Email', 'email')}


def analyze(original, human_filtered):
    """
    Compare original and human-filtered lists.
    Returns analysis dict.
    """
    # Build email lookup
    kept_emails = build_email_set(human_filtered)
    original_emails = build_email_set(original)

    # Classify each original lead
    kept = []
    removed = []
    for lead in original:
        email = normalize_email(get_field(lead, 'Email', 'email'))
        if email and email in kept_emails:
            kept.append(lead)
        else:
            removed.append(lead)

    # Analyze removed leads
    removed_industries = Counter()
    removed_titles = Counter()
    removed_countries = Counter()
    removed_companies = Counter()

    for lead in removed:
        ind = get_field(lead, 'Industry', 'industry', 'LinkedIn Industry')
        title = get_field(lead, 'Job Title', 'title', 'job_title')
        country = get_field(lead, 'Country', 'country')
        company = get_field(lead, 'Company Name', 'company_name', 'org_name')

        if ind:
            removed_industries[ind] += 1
        if title:
            removed_titles[title] += 1
        if country:
            removed_countries[country] += 1
        if company:
            removed_companies[company] += 1

    # Analyze kept leads
    kept_industries = Counter()
    kept_titles = Counter()

    for lead in kept:
        ind = get_field(lead, 'Industry', 'industry', 'LinkedIn Industry')
        title = get_field(lead, 'Job Title', 'title', 'job_title')
        if ind:
            kept_industries[ind] += 1
        if title:
            kept_titles[title] += 1

    # Industry approval rates
    all_industries = Counter()
    for lead in original:
        ind = get_field(lead, 'Industry', 'industry', 'LinkedIn Industry')
        if ind:
            all_industries[ind] += 1

    industry_approval = {}
    for ind, total in all_industries.most_common():
        kept_count = kept_industries.get(ind, 0)
        industry_approval[ind] = {
            'total': total,
            'kept': kept_count,
            'removed': total - kept_count,
            'approval_rate': round(kept_count / total * 100, 1) if total > 0 else 0,
        }

    # Sort by approval rate ascending (most-rejected first)
    industry_approval_sorted = dict(
        sorted(industry_approval.items(), key=lambda x: x[1]['approval_rate'])
    )

    return {
        'summary': {
            'original_count': len(original),
            'kept_count': len(kept),
            'removed_count': len(removed),
            'approval_rate': round(len(kept) / max(len(original), 1) * 100, 1),
            'original_unique_emails': len(original_emails),
            'kept_unique_emails': len(kept_emails),
            'emails_not_in_original': len(kept_emails - original_emails),
        },
        'industry_approval': industry_approval_sorted,
        'removed_industries_top20': dict(removed_industries.most_common(20)),
        'removed_titles_top20': dict(removed_titles.most_common(20)),
        'removed_countries': dict(removed_countries.most_common()),
        'removed_companies_top20': dict(removed_companies.most_common(20)),
        'kept_industries_top20': dict(kept_industries.most_common(20)),
        'kept_titles_top20': dict(kept_titles.most_common(20)),
    }


def print_report(analysis):
    """Print a human-readable report."""
    s = analysis['summary']
    print("=" * 60)
    print("HUMAN FILTER ANALYSIS")
    print("=" * 60)
    print(f"  Original: {s['original_count']} leads")
    print(f"  Kept: {s['kept_count']} leads ({s['approval_rate']}%)")
    print(f"  Removed: {s['removed_count']} leads ({100 - s['approval_rate']}%)")
    if s['emails_not_in_original'] > 0:
        print(f"  NOTE: {s['emails_not_in_original']} emails in human-filtered not found in original")
    print()

    # Industry approval rates
    print("INDUSTRY APPROVAL RATES (lowest first):")
    print("-" * 60)
    for ind, data in analysis['industry_approval'].items():
        bar = '#' * int(data['approval_rate'] / 5)
        print(f"  {data['approval_rate']:5.1f}% [{data['kept']:4d}/{data['total']:4d}] {ind}")
        if len(list(analysis['industry_approval'].items())) > 30:
            # Only show industries with >10 leads for readability
            if data['total'] < 10:
                continue
    print()

    # Top removed titles
    print("TOP REMOVED TITLES:")
    for title, cnt in list(analysis['removed_titles_top20'].items())[:15]:
        print(f"  [{cnt}] {title}")
    print()

    # Top removed companies
    print("TOP REMOVED COMPANIES:")
    for company, cnt in list(analysis['removed_companies_top20'].items())[:10]:
        print(f"  [{cnt}] {company}")


def main():
    parser = argparse.ArgumentParser(description='Analyze human filtering decisions')
    parser.add_argument('--original', required=True, help='Path to original leads JSON')
    parser.add_argument('--human-filtered', required=True, help='Path to human-filtered CSV')
    parser.add_argument('--client-id', help='Client ID (for output path)')
    parser.add_argument('--output-dir', help='Output directory (default: campaigns/{client_id})')

    args = parser.parse_args()

    # Determine output directory
    output_dir = args.output_dir
    if not output_dir and args.client_id:
        output_dir = os.path.join('campaigns', args.client_id)
    if not output_dir:
        output_dir = '.'

    # Load data
    print(f"Loading original leads from {args.original}...")
    original = load_json_leads(args.original)
    print(f"  Loaded {len(original)} leads")

    print(f"Loading human-filtered leads from {args.human_filtered}...")
    human_filtered = load_csv_leads(args.human_filtered)
    print(f"  Loaded {len(human_filtered)} leads")
    print()

    # Analyze
    analysis = analyze(original, human_filtered)

    # Print report
    print_report(analysis)

    # Save learnings
    os.makedirs(output_dir, exist_ok=True)
    output = {
        'generated': datetime.now().isoformat(),
        'original_file': os.path.basename(args.original),
        'human_filtered_file': os.path.basename(args.human_filtered),
        **analysis,
    }

    filepath = os.path.join(output_dir, 'filter_learnings.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nFilter learnings saved: {filepath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

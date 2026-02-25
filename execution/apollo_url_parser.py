# [CLI] — run via: py execution/apollo_url_parser.py --help
"""
Apollo URL Parser
Extracts filter parameters from Apollo.io search URLs.

Example Apollo URL:
https://app.apollo.io/#/people?page=1&contactEmailStatusV2[]=verified&personTitles[]=ceo&personLocations[]=United%20States

This script parses the URL and returns a structured dictionary of filters.
"""

import sys
import json
import re
import argparse
from urllib.parse import urlparse, parse_qs, unquote


def parse_apollo_url(url):
    """
    Parse Apollo.io URL and extract filter parameters.

    Returns a dictionary with the following structure:
    {
        'titles': ['CEO', 'Founder'],
        'locations': ['United States', 'Washington DC'],
        'seniority': ['C-Level', 'Owner'],
        'industries': ['Marketing & Advertising'],
        'company_size': ['11-50', '51-200'],
        'email_status': ['verified'],
        'keywords': ['marketing', 'ppc'],
        'functions': ['Marketing', 'Sales']
    }
    """

    # Parse URL - Apollo uses hash fragment for parameters
    parsed = urlparse(url)

    # Extract query string from hash fragment (after #)
    if parsed.fragment:
        # Split fragment to get query part (after ?)
        if '?' in parsed.fragment:
            query_string = parsed.fragment.split('?', 1)[1]
        else:
            query_string = ''
    else:
        query_string = parsed.query

    # Parse query parameters
    params = parse_qs(query_string)

    # Initialize filter dictionary
    filters = {
        'titles': [],
        'locations': [],
        'org_locations': [],  # Organization locations (separate from person locations)
        'seniority': [],
        'industries': [],
        'company_size': [],
        'email_status': [],
        'keywords': [],
        'functions': [],
        'revenue': {},
        'funding': []
    }

    # Map Apollo parameters to our filter structure
    # Titles
    if 'personTitles[]' in params:
        filters['titles'] = [unquote(t) for t in params['personTitles[]']]

    # Locations (person)
    if 'personLocations[]' in params:
        filters['locations'] = [unquote(loc) for loc in params['personLocations[]']]

    # Locations (organization)
    if 'organizationLocations[]' in params:
        filters['org_locations'] = [unquote(loc) for loc in params['organizationLocations[]']]

    # Seniority
    if 'personSeniorities[]' in params:
        filters['seniority'] = [unquote(s) for s in params['personSeniorities[]']]

    # Industries (raw hex IDs from Apollo)
    if 'organizationIndustryTagIds[]' in params:
        filters['industries'] = [unquote(ind) for ind in params['organizationIndustryTagIds[]']]

    # Resolve hex IDs to human-readable industry names
    if filters['industries']:
        try:
            from apollo_industry_resolver import resolve_industry_ids
            resolved, unresolved = resolve_industry_ids(filters['industries'])
            filters['industries_resolved'] = resolved
            filters['industries_unresolved'] = unresolved
            if unresolved:
                import sys as _sys
                print(f"\nWARNING: {len(unresolved)} of {len(filters['industries'])} "
                      f"industry hex ID(s) could not be resolved.", file=_sys.stderr)
                print(f"Backup scrapers will NOT filter by these industries.", file=_sys.stderr)
                print(f"Fix with: py execution/apollo_industry_resolver.py --add HEX_ID \"Name\"",
                      file=_sys.stderr)
        except ImportError:
            filters['industries_resolved'] = []
            filters['industries_unresolved'] = filters['industries'][:]

    # Company size
    if 'organizationNumEmployeesRanges[]' in params:
        filters['company_size'] = [unquote(size) for size in params['organizationNumEmployeesRanges[]']]

    # Email status
    if 'contactEmailStatusV2[]' in params:
        filters['email_status'] = [unquote(status) for status in params['contactEmailStatusV2[]']]

    # Keywords
    if 'q_keywords' in params:
        filters['keywords'] = [unquote(kw) for kw in params['q_keywords']]

    # Organization keyword tags (e.g. precast concrete, prefabricated concrete)
    if 'qOrganizationKeywordTags[]' in params:
        org_keywords = [unquote(kw) for kw in params['qOrganizationKeywordTags[]']]
        filters['keywords'].extend(org_keywords)

    # Functions
    if 'personDepartments[]' in params:
        filters['functions'] = [unquote(func) for func in params['personDepartments[]']]

    # Revenue (min/max)
    if 'organizationMinRevenue' in params:
        filters['revenue']['min'] = params['organizationMinRevenue'][0]
    if 'organizationMaxRevenue' in params:
        filters['revenue']['max'] = params['organizationMaxRevenue'][0]

    # Funding
    if 'organizationFundingTypes[]' in params:
        filters['funding'] = [unquote(f) for f in params['organizationFundingTypes[]']]

    return filters


def extract_validation_keywords(filters):
    """
    Extract keywords for validation from parsed filters.
    Returns comma-separated string of keywords for validation.
    """
    keywords = []

    # Add titles
    keywords.extend(filters.get('titles', []))

    # Add resolved industry names (not raw hex IDs)
    keywords.extend(filters.get('industries_resolved', []))

    # Add keywords
    keywords.extend(filters.get('keywords', []))

    # Add seniority levels
    keywords.extend(filters.get('seniority', []))

    return ','.join(keywords) if keywords else ''


def main():
    parser = argparse.ArgumentParser(description='Parse Apollo URL and extract filters')
    parser.add_argument('--apollo-url', required=True, help='Apollo.io search URL')
    parser.add_argument('--output-format', choices=['json', 'text'], default='json', help='Output format')

    args = parser.parse_args()

    try:
        filters = parse_apollo_url(args.apollo_url)

        if args.output_format == 'json':
            print(json.dumps(filters, indent=2))
        else:
            print("=== APOLLO FILTERS ===")
            for key, value in filters.items():
                if value:  # Only show non-empty filters
                    print(f"{key}: {value}")

            print("\n=== VALIDATION KEYWORDS ===")
            print(extract_validation_keywords(filters))

        return 0

    except Exception as e:
        print(f"Error parsing Apollo URL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

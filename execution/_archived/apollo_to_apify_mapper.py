# [CLI] — run via: py execution/apollo_to_apify_mapper.py --help
"""
Apollo to Apify Filter Mapper
Converts Apollo filters to Apify-compatible filters with intelligent broadening.

Key principle: Apify filters should be BROADER than Apollo filters to capture similar leads.
Apollo is more restrictive, Apify casts a wider net.
"""

import sys
import json
import argparse


# Mapping tables for filter transformation
SENIORITY_BROADENING = {
    'ceo': 'C-Level,Owner',
    'founder': 'C-Level,Owner,Founder',
    'owner': 'Owner,C-Level',
    'president': 'C-Level,VP',
    'vp': 'VP,Director',
    'director': 'Director,Manager',
    'manager': 'Manager,Senior',
    'c-level': 'C-Level,Owner',
    'senior': 'Senior,Manager'
}

TITLE_TO_SENIORITY = {
    'ceo': 'C-Level',
    'cfo': 'C-Level',
    'cto': 'C-Level',
    'cmo': 'C-Level',
    'founder': 'Owner',
    'co-founder': 'Owner',
    'owner': 'Owner',
    'president': 'C-Level',
    'vice president': 'VP',
    'vp': 'VP',
    'director': 'Director',
    'manager': 'Manager'
}


def broaden_titles(apollo_titles):
    """
    Broaden job titles for Apify.

    Strategy:
    - Keep exact titles
    - Add related seniority levels
    - Add common variations
    """
    if not apollo_titles:
        return ''

    titles = []
    seniority_levels = set()

    for title in apollo_titles:
        title_lower = title.lower()

        # Add the original title
        titles.append(title)

        # Extract seniority from title
        for key, seniority in TITLE_TO_SENIORITY.items():
            if key in title_lower:
                seniority_levels.add(seniority)

    # Convert to comma-separated string
    return ','.join(titles)


def broaden_seniority(apollo_seniority):
    """
    Broaden seniority levels for Apify.

    Strategy:
    - If C-Level specified, include Owner
    - If VP specified, include Director
    - Generally cast wider net
    """
    if not apollo_seniority:
        return ''

    seniority_set = set()

    for level in apollo_seniority:
        level_lower = level.lower()

        # Add original level
        seniority_set.add(level)

        # Add broader levels
        if level_lower in SENIORITY_BROADENING:
            for broad_level in SENIORITY_BROADENING[level_lower].split(','):
                seniority_set.add(broad_level)

    return ','.join(seniority_set)


def broaden_locations(apollo_locations):
    """
    Broaden location filters for Apify.

    Strategy:
    - Extract country/state level locations
    - Remove overly specific city filters (can be applied separately)
    - Examples:
      "Washington DC" -> "United States" (state) + "Washington" (city param)
      "San Francisco, CA" -> "United States" + "San Francisco"
    """
    if not apollo_locations:
        return '', ''

    locations = []
    cities = []

    for loc in apollo_locations:
        loc_lower = loc.lower()

        # Check if it's a US location
        if 'united states' in loc_lower or 'usa' in loc_lower or 'us' in loc_lower:
            locations.append('United States')

            # Extract city if present
            if 'washington' in loc_lower or 'dc' in loc_lower:
                cities.append('Washington')
            elif 'san francisco' in loc_lower:
                cities.append('San Francisco')
            elif 'new york' in loc_lower:
                cities.append('New York')
            elif 'los angeles' in loc_lower:
                cities.append('Los Angeles')
            elif 'chicago' in loc_lower:
                cities.append('Chicago')
            # Add more city patterns as needed

        else:
            # Non-US location, keep as is
            locations.append(loc)

    # Deduplicate
    locations = list(set(locations))
    cities = list(set(cities))

    return ','.join(locations) if locations else '', ','.join(cities) if cities else ''


def broaden_industries(apollo_industries):
    """
    Broaden industry filters for Apify.

    Strategy:
    - Keep industry keywords
    - Remove numeric IDs (Apify uses text)
    - Add related industries
    """
    if not apollo_industries:
        return ''

    industries = []

    for ind in apollo_industries:
        # Skip numeric IDs
        if ind.isdigit():
            continue

        industries.append(ind)

        # Add related industries (example mappings)
        ind_lower = ind.lower()
        if 'marketing' in ind_lower:
            industries.append('advertising')
        elif 'advertising' in ind_lower:
            industries.append('marketing')
        elif 'software' in ind_lower:
            industries.append('technology')
        elif 'technology' in ind_lower:
            industries.append('software')

    # Deduplicate
    industries = list(set(industries))

    return ','.join(industries) if industries else ''


def map_apollo_to_apify(apollo_filters, broadening_level=1):
    """
    Map Apollo filters to Apify payload.

    Args:
        apollo_filters: Dictionary from parse_apollo_filters.py
        broadening_level: 1 (default), 2 (more broad), 3 (very broad)

    Returns:
        Dictionary with Apify-compatible filter parameters
    """

    apify_payload = {}

    # Job Titles - broaden slightly
    if apollo_filters.get('titles'):
        job_titles = broaden_titles(apollo_filters['titles'])
        if job_titles:
            apify_payload['job_titles'] = job_titles

    # Seniority - always broaden
    apollo_seniority = apollo_filters.get('seniority', [])

    # If no explicit seniority but we have titles, derive seniority
    if not apollo_seniority and apollo_filters.get('titles'):
        derived_seniority = set()
        for title in apollo_filters['titles']:
            title_lower = title.lower()
            for key, seniority in TITLE_TO_SENIORITY.items():
                if key in title_lower:
                    derived_seniority.add(seniority)
        apollo_seniority = list(derived_seniority)

    if apollo_seniority:
        seniority = broaden_seniority(apollo_seniority)
        if seniority:
            apify_payload['seniority'] = seniority

    # Locations - broaden to country/state level
    if apollo_filters.get('locations'):
        location, city = broaden_locations(apollo_filters['locations'])
        if location:
            apify_payload['location'] = location
        if city:
            apify_payload['city'] = city

    # Industries - keep but remove IDs
    if apollo_filters.get('industries'):
        industry = broaden_industries(apollo_filters['industries'])
        if industry:
            apify_payload['industry'] = industry

    # Company Size - keep as is (usually reasonable)
    if apollo_filters.get('company_size'):
        apify_payload['company_size'] = ','.join(apollo_filters['company_size'])

    # Revenue - keep as is
    if apollo_filters.get('revenue', {}).get('min'):
        apify_payload['min_revenue'] = apollo_filters['revenue']['min']
    if apollo_filters.get('revenue', {}).get('max'):
        apify_payload['max_revenue'] = apollo_filters['revenue']['max']

    # Funding - keep as is
    if apollo_filters.get('funding'):
        apify_payload['funding'] = ','.join(apollo_filters['funding'])

    # Email Status - default to validated
    apify_payload['email_status'] = 'validated'

    # Apply broadening level adjustments
    if broadening_level >= 2:
        # Level 2: Remove some restrictions
        if 'city' in apify_payload:
            del apify_payload['city']  # Remove city filter, keep only state/country

    if broadening_level >= 3:
        # Level 3: Very broad - keep only essential filters
        essential = {}
        if 'seniority' in apify_payload:
            essential['seniority'] = apify_payload['seniority']
        if 'location' in apify_payload:
            essential['location'] = apify_payload['location']
        if 'industry' in apify_payload:
            essential['industry'] = apify_payload['industry']
        essential['email_status'] = 'validated'
        apify_payload = essential

    return apify_payload


def main():
    parser = argparse.ArgumentParser(description='Map Apollo filters to Apify payload')
    parser.add_argument('--apollo-filters', required=True, help='JSON string of Apollo filters')
    parser.add_argument('--broadening-level', type=int, default=1, choices=[1, 2, 3],
                        help='Broadening level: 1=default, 2=more broad, 3=very broad')
    parser.add_argument('--output-format', choices=['json', 'text'], default='json', help='Output format')

    args = parser.parse_args()

    try:
        apollo_filters = json.loads(args.apollo_filters)
        apify_payload = map_apollo_to_apify(apollo_filters, args.broadening_level)

        if args.output_format == 'json':
            print(json.dumps(apify_payload, indent=2))
        else:
            print("=== APIFY PAYLOAD ===")
            for key, value in apify_payload.items():
                print(f"{key}: {value}")

        return 0

    except Exception as e:
        print(f"Error mapping filters: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
X_Guru Leads Scraper (x_guru/Leads-Scraper-apollo-zoominfo)

B2B Leads Scraper with 100M+ professional records.
LinkedIn URLs ~95%+ coverage, ~70% email coverage.
Up to 50k leads per run.

Features:
- Auto-derive filters from Apollo URL
- 25-lead validation test (80% match threshold)
- Full scrape only if validation passes
- Standardized lead output schema
"""

import os
import sys
import json
import argparse
import time
from datetime import datetime
from urllib.parse import parse_qs, urlparse, unquote
from apify_client import ApifyClient

# Import Apollo URL parser
sys.path.append(os.path.dirname(__file__))
from parse_apollo_filters import parse_apollo_url, extract_validation_keywords


def map_apollo_to_xguru(apollo_filters):
    """
    Map Apollo filters to x_guru/Leads-Scraper-apollo-zoominfo input schema.

    X_Guru ACTUAL input schema (verified via testing):
    {
        "job_titles": ["ceo"],  # Job titles (lowercase, snake_case)
        "person_location_country": ["Sweden"],  # Person country locations
        "industries": ["construction"],  # Industry names (text, not IDs)
        "employee_size": ["1-10", "11-50", "51-200"],  # Company size ranges
        "max_results": 100,  # Number of results (snake_case)
        "include_emails": true,  # Always get emails (snake_case)
        "include_phones": false  # Phone numbers (snake_case)
    }
    """

    xguru_input = {
        "include_emails": True,  # Always get emails
        "include_phones": False,  # Don't include phones by default
        "max_results": 25  # Will be overridden by caller
    }

    # Map titles (convert to lowercase for better matching)
    if apollo_filters.get('titles'):
        xguru_input['job_titles'] = [title.lower() for title in apollo_filters['titles']]

    # Map locations to person_location_country
    # Note: X_Guru expects country names only
    if apollo_filters.get('locations'):
        # Clean up locations (remove extra spaces, capitalize properly)
        cleaned_locations = []
        for loc in apollo_filters['locations']:
            loc_cleaned = loc.strip()
            # Capitalize first letter of each word for country names
            loc_cleaned = ' '.join(word.capitalize() for word in loc_cleaned.split())
            cleaned_locations.append(loc_cleaned)
        xguru_input['person_location_country'] = cleaned_locations

    # Map company size to employee_size
    if apollo_filters.get('company_size'):
        xguru_input['employee_size'] = apollo_filters['company_size']

    # Map industries - IMPORTANT: Use text names, not IDs
    # For now, we'll use keywords to search for industries since we don't have ID->name mapping
    # This is a limitation we'll need to address with proper industry mapping
    apollo_keywords = apollo_filters.get('keywords', [])

    # If we have keywords, try to extract industry names from them
    # Common industry keywords that can be passed as industries
    industry_keywords = [
        'construction', 'marketing', 'advertising', 'technology', 'software',
        'healthcare', 'finance', 'manufacturing', 'retail', 'education',
        'real estate', 'consulting', 'legal', 'accounting', 'architecture',
        'engineering', 'design', 'media', 'telecommunications', 'automotive',
        'aerospace', 'agriculture', 'energy', 'utilities', 'transportation',
        'hospitality', 'entertainment', 'insurance', 'banking', 'biotechnology'
    ]

    # Extract any industry-like keywords
    if apollo_keywords:
        industries = []
        for keyword in apollo_keywords:
            keyword_lower = keyword.lower()
            # Check if keyword matches known industry names
            for industry in industry_keywords:
                if industry in keyword_lower:
                    industries.append(industry)

        if industries:
            xguru_input['industries'] = list(set(industries))  # Deduplicate

    return xguru_input


def extract_org_keywords_from_url(apollo_url):
    """
    Extract organization keywords from Apollo URL.
    These are often in qOrganizationKeywordTags[] parameter.
    """
    try:
        parsed = urlparse(apollo_url)
        if '?' in parsed.fragment:
            query_string = parsed.fragment.split('?', 1)[1]
        else:
            query_string = parsed.query

        params = parse_qs(query_string)

        # Extract organization keywords
        org_keywords = []
        if 'qOrganizationKeywordTags[]' in params:
            org_keywords = [unquote(kw) for kw in params['qOrganizationKeywordTags[]']]

        return org_keywords
    except:
        return []


def normalize_lead_to_schema(lead):
    """
    Normalize x_guru lead output to standardized schema.
    """
    return {
        'first_name': lead.get('firstName', ''),
        'last_name': lead.get('lastName', ''),
        'name': lead.get('name') or f"{lead.get('firstName', '')} {lead.get('lastName', '')}".strip(),
        'organization_phone': lead.get('companyPhone', '') or lead.get('organizationPhone', ''),
        'linkedin_url': lead.get('linkedinUrl', '') or lead.get('linkedin', ''),
        'title': lead.get('title', '') or lead.get('jobTitle', ''),
        'email_status': lead.get('emailStatus', 'unknown'),
        'email': lead.get('email', ''),
        'city': lead.get('city', ''),
        'country': lead.get('country', ''),
        'org_name': lead.get('companyName', '') or lead.get('company', ''),
        'website_url': lead.get('companyWebsite', '') or lead.get('website', ''),
        'source': 'xguru_leads_scraper'
    }


def validate_leads_against_filters(leads, apollo_filters, validation_keywords):
    """
    Validate that scraped leads match Apollo filters.
    Returns (match_count, total_count, match_percentage).
    """
    if not leads:
        return 0, 0, 0.0

    match_count = 0
    total_count = len(leads)

    # Extract validation criteria
    title_keywords = [t.lower() for t in apollo_filters.get('titles', [])]
    seniority_keywords = [s.lower() for s in apollo_filters.get('seniority', [])]
    location_keywords = [loc.lower() for loc in apollo_filters.get('locations', [])]

    # Combine all validation keywords
    all_keywords = validation_keywords.lower().split(',') if validation_keywords else []
    all_keywords = [kw.strip() for kw in all_keywords if kw.strip()]

    for lead in leads:
        title = lead.get('title', '').lower()
        location = f"{lead.get('city', '')} {lead.get('country', '')}".lower()

        # Check if lead matches any of the filters
        matches = False

        # Title match
        if title_keywords and any(kw in title for kw in title_keywords):
            matches = True

        # Location match
        if location_keywords and any(kw in location for kw in location_keywords):
            matches = True

        # General keyword match
        lead_text = f"{title} {location} {lead.get('org_name', '')}".lower()
        if all_keywords and any(kw in lead_text for kw in all_keywords):
            matches = True

        # If no specific filters, count as match
        if not title_keywords and not location_keywords and not all_keywords:
            matches = True

        if matches:
            match_count += 1

    match_percentage = (match_count / total_count * 100) if total_count > 0 else 0
    return match_count, total_count, match_percentage


def run_xguru_scraper(apollo_url, max_leads, output_dir='.tmp/xguru', output_prefix='xguru_leads', test_only=False):
    """
    Run x_guru/Leads-Scraper-apollo-zoominfo with Apollo URL-derived filters.

    Args:
        apollo_url: Apollo.io search URL
        max_leads: Maximum leads to scrape
        output_dir: Output directory for results
        output_prefix: Output file prefix
        test_only: If True, only scrape 25 leads for validation

    Returns:
        tuple: (success: bool, output_file: str, match_percentage: float)
    """

    # Get API key
    apify_api_key = os.getenv('APIFY_API_KEY')
    if not apify_api_key:
        print("Error: APIFY_API_KEY not found in environment", file=sys.stderr)
        return False, None, 0.0

    try:
        # Parse Apollo URL to extract filters
        apollo_filters = parse_apollo_url(apollo_url)
        validation_keywords = extract_validation_keywords(apollo_filters)

        # Extract organization keywords from URL
        org_keywords = extract_org_keywords_from_url(apollo_url)
        if org_keywords and 'keywords' not in apollo_filters:
            apollo_filters['keywords'] = org_keywords
        elif org_keywords:
            apollo_filters['keywords'].extend(org_keywords)

        # Map to x_guru input schema
        xguru_input = map_apollo_to_xguru(apollo_filters)

        # Set result count
        target_leads = 25 if test_only else max_leads
        xguru_input['max_results'] = target_leads

        print(f"\n{'='*60}")
        print(f"X_GURU SCRAPER {'TEST' if test_only else 'FULL RUN'}")
        print(f"{'='*60}")
        print(f"Target leads: {target_leads}")
        print(f"Apollo filters extracted:")
        print(f"  Titles: {apollo_filters.get('titles', [])}")
        print(f"  Seniority: {apollo_filters.get('seniority', [])}")
        print(f"  Locations: {apollo_filters.get('locations', [])}")
        print(f"  Company Size: {apollo_filters.get('company_size', [])}")
        print(f"  Revenue: {apollo_filters.get('revenue', {})}")
        print(f"\nX_Guru input:")
        print(json.dumps(xguru_input, indent=2))

        # Initialize Apify client
        client = ApifyClient(apify_api_key)

        # Run the actor
        print(f"\nStarting Apify actor: x_guru/Leads-Scraper-apollo-zoominfo...")
        run = client.actor("x_guru/Leads-Scraper-apollo-zoominfo").call(run_input=xguru_input)

        print(f"Actor run ID: {run['id']}")
        print(f"Status: {run['status']}")

        # Check if run was successful
        if run['status'] != 'SUCCEEDED':
            print(f"Error: Actor run failed with status: {run['status']}", file=sys.stderr)
            if 'statusMessage' in run:
                print(f"Status message: {run['statusMessage']}", file=sys.stderr)
            return False, None, 0.0

        # Fetch results
        print("\nDownloading results...")
        dataset_items = list(client.dataset(run['defaultDatasetId']).iterate_items())

        if not dataset_items:
            print("Warning: No leads returned from x_guru scraper", file=sys.stderr)
            return False, None, 0.0

        print(f"Downloaded {len(dataset_items)} leads")

        # Normalize leads to standardized schema
        normalized_leads = [normalize_lead_to_schema(lead) for lead in dataset_items]

        # Validate leads against Apollo filters
        match_count, total_count, match_percentage = validate_leads_against_filters(
            normalized_leads, apollo_filters, validation_keywords
        )

        print(f"\n{'='*60}")
        print(f"VALIDATION RESULTS")
        print(f"{'='*60}")
        print(f"Total leads: {total_count}")
        print(f"Matching leads: {match_count}")
        print(f"Match percentage: {match_percentage:.1f}%")
        print(f"Threshold: 80%")

        if match_percentage < 80.0:
            print(f"[X] Match rate below 80% threshold")
            if test_only:
                print("[INFO] X_Guru scraper will NOT be used for full run")
                return False, None, match_percentage
        else:
            print(f"[OK] Match rate meets 80% threshold")
            if test_only:
                print("[INFO] X_Guru scraper validated - ready for full run")

        # Save results
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_suffix = "_test" if test_only else ""
        filename = f"{output_prefix}{test_suffix}_{timestamp}_{len(normalized_leads)}leads.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(normalized_leads, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {filepath}")

        return True, filepath, match_percentage

    except KeyboardInterrupt:
        print("\nScraping interrupted by user.", file=sys.stderr)
        return False, None, 0.0
    except Exception as e:
        print(f"Error running x_guru scraper: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False, None, 0.0


def main():
    parser = argparse.ArgumentParser(description='X_Guru Leads Scraper with Apollo URL input')
    parser.add_argument('--apollo-url', required=True, help='Apollo.io search URL')
    parser.add_argument('--max-leads', type=int, default=5000, help='Maximum leads to scrape (up to 50k)')
    parser.add_argument('--output-dir', default='.tmp/xguru', help='Output directory')
    parser.add_argument('--output-prefix', default='xguru_leads', help='Output file prefix')
    parser.add_argument('--test-only', action='store_true', help='Only scrape 25 leads for validation')

    args = parser.parse_args()

    success, output_file, match_percentage = run_xguru_scraper(
        apollo_url=args.apollo_url,
        max_leads=args.max_leads,
        output_dir=args.output_dir,
        output_prefix=args.output_prefix,
        test_only=args.test_only
    )

    if success:
        if output_file:
            print(output_file)  # Print filepath to stdout for caller to capture
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())

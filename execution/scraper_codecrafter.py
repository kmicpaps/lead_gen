# [CLI] — run via: py execution/scraper_codecrafter.py --help
"""
Code_Crafter Leads Scraper (code_crafter/leads-finder)

B2B Leads Scraper with Apollo URL filter extraction.
Supports: Job titles, Location, Industry, Revenue, Funding, Seniority, etc.

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
from datetime import datetime
from pathlib import Path
from apify_client import ApifyClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Apollo URL parser
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apollo_url_parser import parse_apollo_url, extract_validation_keywords


def map_apollo_to_codecrafter(apollo_filters):
    """
    Map Apollo filters to code_crafter/leads-finder input schema.

    Code_Crafter input schema:
    {
        "fetch_count": 25,
        "email_status": ["validated"],
        "contact_job_title": ["CEO", "Founder"],
        "contact_location": ["United States"],
        "seniority_level": ["Owner", "C-Level"],
        "company_industry": ["Marketing & Advertising"],
        "size": ["11-50", "51-200"],
        "min_revenue": "1000000",
        "max_revenue": "10000000",
        "funding": ["Series A", "Venture"]
    }
    """

    codecrafter_input = {
        "fetch_count": 25,  # Will be overridden by caller
        "email_status": ["validated"]  # Always get validated emails
    }

    # Map job titles
    if apollo_filters.get('titles'):
        codecrafter_input['contact_job_title'] = apollo_filters['titles']

    # Map locations - MUST BE LOWERCASE
    # Prefer org_locations over person locations if both exist
    if apollo_filters.get('org_locations'):
        # Organization locations - Code_Crafter treats these as company locations
        codecrafter_input['contact_location'] = [loc.lower() for loc in apollo_filters['org_locations']]
    elif apollo_filters.get('locations'):
        # Code_Crafter requires lowercase location names
        codecrafter_input['contact_location'] = [loc.lower() for loc in apollo_filters['locations']]

    # Map seniority
    if apollo_filters.get('seniority'):
        # Map Apollo seniority to Code_Crafter format (must be lowercase)
        seniority_map = {
            'founder': 'founder',
            'owner': 'owner',
            'c_suite': 'c_suite',
            'vp': 'vp',
            'director': 'director',
            'manager': 'manager',
            'head': 'head',
            'partner': 'partner',
            'senior': 'senior',
            'entry': 'entry',
            'trainee': 'trainee'
        }
        mapped_seniority = []
        for s in apollo_filters['seniority']:
            mapped = seniority_map.get(s.lower(), s.lower())
            if mapped not in mapped_seniority:
                mapped_seniority.append(mapped)

        codecrafter_input['seniority_level'] = mapped_seniority

    # Map company size
    if apollo_filters.get('company_size'):
        # Apollo uses broad ranges (e.g. "11,50", "51,200") that must be expanded
        # into CodeCrafter's granular buckets (e.g. "11-20", "21-50", "51-100", "101-200")
        size_map = {
            '1,10': '1-10',
            '11,20': '11-20',
            '11,50': ['11-20', '21-50'],
            '21,50': '21-50',
            '51,100': '51-100',
            '51,200': ['51-100', '101-200'],
            '101,200': '101-200',
            '201,500': '201-500',
            '501,1000': '501-1000',
            '1001,2000': '1001-2000',
            '1001,5000': ['1001-2000', '2001-5000'],
            '2001,5000': '2001-5000',
            '5001,10000': '5001-10000',
            '10001': ['10001-20000', '20001-50000', '50000+'],
            '10001+': ['10001-20000', '20001-50000', '50000+'],
        }
        mapped_sizes = []
        for size in apollo_filters['company_size']:
            mapped_size = size_map.get(size)
            if mapped_size is None:
                print(f"  WARNING: Unknown company size '{size}', skipping (valid Apollo sizes: 1,10 / 11,50 / 51,200 / 201,500 / etc.)", file=sys.stderr)
                continue
            # Handle cases where mapped_size is a list (like 10001+)
            if isinstance(mapped_size, list):
                for s in mapped_size:
                    if s not in mapped_sizes:
                        mapped_sizes.append(s)
            else:
                if mapped_size not in mapped_sizes:
                    mapped_sizes.append(mapped_size)

        codecrafter_input['size'] = mapped_sizes

    # Map resolved industry names to company_industry (CodeCrafter API requires lowercase)
    if apollo_filters.get('industries_resolved'):
        codecrafter_input['company_industry'] = [ind.lower() for ind in apollo_filters['industries_resolved']]
        if apollo_filters.get('industries_unresolved'):
            print(f"  WARNING: {len(apollo_filters['industries_unresolved'])} industry IDs unresolved. "
                  f"Scraping with {len(apollo_filters['industries_resolved'])} resolved: "
                  f"{apollo_filters['industries_resolved']}", file=sys.stderr)
    elif apollo_filters.get('industries'):
        # URL had industry hex IDs but NONE could be resolved
        unresolved = apollo_filters.get('industries_unresolved', apollo_filters['industries'])
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"INDUSTRY RESOLUTION FAILED", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        print(f"Apollo URL contains {len(apollo_filters['industries'])} industry hex ID(s)", file=sys.stderr)
        print(f"but NONE could be resolved to text names.", file=sys.stderr)
        print(f"Scraping without industry filter would return ALL industries.", file=sys.stderr)
        print(f"\nTo fix, add each mapping:", file=sys.stderr)
        for hid in unresolved:
            print(f"  py execution/apollo_industry_resolver.py --add {hid} \"INDUSTRY_NAME\"", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        return None

    # Map keywords to company_keywords
    if apollo_filters.get('keywords'):
        codecrafter_input['company_keywords'] = apollo_filters['keywords']

    # Map revenue
    if apollo_filters.get('revenue'):
        if apollo_filters['revenue'].get('min'):
            codecrafter_input['min_revenue'] = apollo_filters['revenue']['min']
        if apollo_filters['revenue'].get('max'):
            codecrafter_input['max_revenue'] = apollo_filters['revenue']['max']

    # Map funding
    if apollo_filters.get('funding'):
        codecrafter_input['funding'] = apollo_filters['funding']

    # Map functions/departments
    if apollo_filters.get('functions'):
        codecrafter_input['functional_level'] = apollo_filters['functions']

    return codecrafter_input


def extract_org_keywords_from_url(apollo_url):
    """
    Extract organization keywords from Apollo URL.
    These are often in qOrganizationKeywordTags[] parameter.
    """
    try:
        from urllib.parse import parse_qs, urlparse, unquote
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
    except Exception:
        return []


def normalize_lead_to_schema(lead):
    """
    Normalize Code_Crafter lead output to standardized schema.
    """
    from urllib.parse import urlparse

    # Extract company domain from website URL
    website_url = lead.get('company_website', '')
    company_domain = ''
    if website_url:
        try:
            parsed = urlparse(website_url if website_url.startswith('http') else f'http://{website_url}')
            company_domain = parsed.netloc.replace('www.', '')
        except Exception:
            company_domain = ''

    return {
        'first_name': lead.get('first_name', ''),
        'last_name': lead.get('last_name', ''),
        'name': lead.get('full_name') or f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
        'organization_phone': lead.get('company_phone', ''),
        'linkedin_url': lead.get('linkedin', ''),
        'title': lead.get('job_title', ''),
        'email_status': lead.get('email_status', 'unknown'),
        'email': lead.get('email', ''),
        'city': lead.get('city', ''),
        'country': lead.get('country', ''),
        'org_name': lead.get('company_name', ''),
        'website_url': website_url,
        'company_linkedin': lead.get('company_linkedin', ''),
        'company_domain': company_domain,
        'industry': lead.get('industry', ''),
        'source': 'codecrafter'
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


def run_codecrafter_scraper(apollo_url, max_leads, output_dir='.tmp/codecrafter', output_prefix='codecrafter_leads', test_only=False):
    """
    Run code_crafter/leads-finder with Apollo URL-derived filters.

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

        # Map to code_crafter input schema
        codecrafter_input = map_apollo_to_codecrafter(apollo_filters)

        if codecrafter_input is None:
            print("Aborting: Cannot scrape without industry filter. Resolve hex IDs first.", file=sys.stderr)
            sys.exit(3)

        # Set result count
        target_leads = 25 if test_only else max_leads
        codecrafter_input['fetch_count'] = target_leads

        print(f"\n{'='*60}")
        print(f"CODE_CRAFTER SCRAPER {'TEST' if test_only else 'FULL RUN'}")
        print(f"{'='*60}")
        print(f"Target leads: {target_leads}")
        print(f"Apollo filters extracted:")
        print(f"  Titles: {apollo_filters.get('titles', [])}")
        print(f"  Seniority: {apollo_filters.get('seniority', [])}")
        print(f"  Locations: {apollo_filters.get('locations', [])}")
        print(f"  Company Size: {apollo_filters.get('company_size', [])}")
        print(f"  Keywords: {apollo_filters.get('keywords', [])}")
        print(f"\nCode_Crafter input:")
        print(json.dumps(codecrafter_input, indent=2))

        # Initialize Apify client
        client = ApifyClient(apify_api_key)

        # Start the actor (non-blocking) so we can save run ID immediately
        print(f"\nStarting Apify actor: code_crafter/leads-finder...")
        started_run = client.actor("code_crafter/leads-finder").start(run_input=codecrafter_input)
        run_id = started_run['id']
        print(f"Actor run ID: {run_id}")

        # Save run ID for recovery (if local process is killed, Apify run continues)
        run_id_file = Path(output_dir) / '.active_run.json'
        run_id_file.parent.mkdir(parents=True, exist_ok=True)
        with open(run_id_file, 'w', encoding='utf-8') as _f:
            json.dump({'run_id': run_id, 'actor': 'code_crafter/leads-finder',
                       'started_at': datetime.now().isoformat()}, _f)

        # Wait for the actor to finish
        run = client.run(run_id).wait_for_finish()

        # Clean up run ID file
        run_id_file.unlink(missing_ok=True)

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
            print("Warning: No leads returned from code_crafter scraper", file=sys.stderr)
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
                print("[INFO] Code_Crafter scraper will NOT be used for full run")
                return False, None, match_percentage
        else:
            print(f"[OK] Match rate meets 80% threshold")
            if test_only:
                print("[INFO] Code_Crafter scraper validated - ready for full run")

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
        print(f"Error running code_crafter scraper: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False, None, 0.0


def main():
    parser = argparse.ArgumentParser(description='Code_Crafter Leads Scraper with Apollo URL input')
    parser.add_argument('--apollo-url', required=True, help='Apollo.io search URL')
    parser.add_argument('--max-leads', type=int, default=5000, help='Maximum leads to scrape')
    parser.add_argument('--output-dir', default='.tmp/codecrafter', help='Output directory')
    parser.add_argument('--output-prefix', default='codecrafter_leads', help='Output file prefix')
    parser.add_argument('--test-only', action='store_true', help='Only scrape 25 leads for validation')

    args = parser.parse_args()

    success, output_file, match_percentage = run_codecrafter_scraper(
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

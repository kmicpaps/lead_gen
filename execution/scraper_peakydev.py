# [CLI] — run via: py execution/scraper_peakydev.py --help
"""
Peakydev Leads Scraper (peakydev/leads-scraper-ppe)

Extract up to 30K leads per run with emails guaranteed.
Supports: Titles, Seniority, Industry, Keywords, Company/Person Location,
          Company Size, Revenue, Funding, Functions, Email Status

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
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Apollo URL parser
sys.path.append(os.path.dirname(__file__))
from apollo_url_parser import parse_apollo_url, extract_validation_keywords


def map_apollo_to_peakydev(apollo_filters):
    """
    Map Apollo filters to peakydev/leads-scraper-ppe input schema.

    Peakydev ACTUAL input schema (verified via Apify docs 2026-02-25):
    {
        "businessModel": ["Product"],                           # Business model filter
        "companyCountry": ["United Kingdom"],                   # Company HQ country
        "companyEmployeeSize": ["0 - 1", "11 - 50", "51 - 200"], # Employee ranges
        "contactEmailStatus": "verified",                       # Email verification status
        "functional": ["Fraud"],                                # Department/function
        "fundingFromDate": "2026-02-25",                        # Funding date range
        "fundingToDate": "2026-02-26",
        "fundingType": ["Venture Round"],                       # Funding type
        "includeEmails": true,                                  # Include email addresses
        "industry": ["Construction Hardware Manufacturing"],     # Industry text names (V2 taxonomy)
        "industryKeywords": ["construction"],                   # Keyword search
        "personCountry": ["Sweden"],                            # Person's home country
        "personTitle": ["ceo"],                                 # Job title filter (lowercase)
        "revenue": ["< 1M"],                                    # Revenue range
        "seniority": ["CEO", "Founder", "Director", ...],       # Seniority levels
        "totalResults": 1000
    }
    """

    peakydev_input = {
        "includeEmails": True,  # Always get emails
        "totalResults": 1000  # Will be overridden by caller
    }

    # Map company size to companyEmployeeSize (different format than Apollo)
    if apollo_filters.get('company_size'):
        # Apollo format: ["1,10", "11,20", "21,50"] -> Peakydev format: ["2 - 10", "11 - 50"]
        # Note: Peakydev has fewer size buckets, so we map granular Apollo sizes to broader Peakydev buckets
        size_map = {
            '1,10': '2 - 10',
            '11,20': '11 - 50',
            '11,50': '11 - 50',
            '21,50': '11 - 50',
            '51,200': '51 - 200',
            '201,500': '201 - 500',
            '501,1000': '501 - 1000',
            '1001,5000': '1001 - 5000',
            '5001,10000': '5001 - 10000',
            '10001+': '10000+'
        }
        mapped_sizes = []
        for size in apollo_filters['company_size']:
            mapped_size = size_map.get(size, None)
            if mapped_size and mapped_size not in mapped_sizes:
                mapped_sizes.append(mapped_size)

        # Add "0 - 1" if very small companies
        if any(s in ['1,10', '0,1'] for s in apollo_filters['company_size']):
            if '0 - 1' not in mapped_sizes:
                mapped_sizes.insert(0, '0 - 1')

        peakydev_input['companyEmployeeSize'] = mapped_sizes

    # Map locations to companyCountry (company HQ) or personCountry (person's location)
    # Prefer org_locations → companyCountry; fall back to person locations → personCountry
    org_locations = apollo_filters.get('org_locations')
    person_locations = apollo_filters.get('locations')

    def _clean_country_names(locations):
        """Title-case country names for PeakyDev API."""
        cleaned = []
        for loc in locations:
            loc_cleaned = loc.strip()
            loc_cleaned = ' '.join(word.capitalize() for word in loc_cleaned.split())
            cleaned.append(loc_cleaned)
        return cleaned

    if org_locations:
        peakydev_input['companyCountry'] = _clean_country_names(org_locations)
    if person_locations:
        peakydev_input['personCountry'] = _clean_country_names(person_locations)
    # If only person locations exist and no org locations, use personCountry (already set above)
    # If only org locations exist, we filter by company HQ — no person location filter

    # Map job titles to personTitle (lowercase)
    if apollo_filters.get('titles'):
        peakydev_input['personTitle'] = [t.lower() for t in apollo_filters['titles']]

    # Map seniority levels
    if apollo_filters.get('seniority'):
        # PeakyDev seniority values (from Apify schema)
        seniority_map = {
            'founder': 'Founder',
            'owner': 'Founder',      # Apollo "Owner" → PeakyDev "Founder"
            'c_suite': 'CXO',
            'vp': 'Vice President',
            'director': 'Director',
            'manager': 'Manager',
            'head': 'Head',
            'partner': 'Chairman',    # Closest match
            'senior': 'Senior',
            'entry': 'Entry Level',
            'trainee': 'Junior',
            'executive': 'Executive',
            'president': 'President',
        }
        mapped_seniority = []
        for s in apollo_filters['seniority']:
            mapped = seniority_map.get(s.lower(), s)
            if mapped not in mapped_seniority:
                mapped_seniority.append(mapped)
        peakydev_input['seniority'] = mapped_seniority

    # Map email status
    if apollo_filters.get('email_status'):
        # Apollo: ["verified"] → PeakyDev: "verified"
        if 'verified' in [s.lower() for s in apollo_filters['email_status']]:
            peakydev_input['contactEmailStatus'] = 'verified'

    # Map revenue (Apollo min/max → PeakyDev range strings)
    if apollo_filters.get('revenue'):
        revenue = apollo_filters['revenue']
        # PeakyDev uses range strings: "< 1M", "1M - 10M", "10M - 50M", etc.
        revenue_ranges = []
        min_rev = int(revenue.get('min', 0) or 0)
        max_rev = int(revenue.get('max', 0) or 0)

        # Map Apollo min/max to PeakyDev bucket strings
        buckets = [
            (0, 1000000, '< 1M'),
            (1000000, 10000000, '1M - 10M'),
            (10000000, 50000000, '10M - 50M'),
            (50000000, 100000000, '50M - 100M'),
            (100000000, 500000000, '100M - 500M'),
            (500000000, 1000000000, '500M - 1B'),
            (1000000000, float('inf'), '> 1B'),
        ]
        for low, high, label in buckets:
            # Include bucket if it overlaps with the min/max range
            if max_rev == 0:
                # No upper bound — include all buckets >= min_rev bucket
                if high > min_rev:
                    revenue_ranges.append(label)
            elif low < max_rev and high > min_rev:
                revenue_ranges.append(label)

        if revenue_ranges:
            peakydev_input['revenue'] = revenue_ranges

    # Map funding type
    if apollo_filters.get('funding'):
        # Apollo funding types map directly to PeakyDev (same names)
        peakydev_input['fundingType'] = apollo_filters['funding']

    # Map functions/departments
    if apollo_filters.get('functions'):
        peakydev_input['functional'] = apollo_filters['functions']

    # Map keywords to industryKeywords
    apollo_keywords = apollo_filters.get('keywords', [])
    if apollo_keywords:
        # Use keywords for industryKeywords field (deduplicate to avoid API error)
        peakydev_input['industryKeywords'] = list(set(apollo_keywords))

    # Map resolved industry names to industry field
    # PeakyDev uses LinkedIn V2 taxonomy which differs from Apollo's V1 taxonomy.
    # Mapping is maintained in the shared industry_taxonomy module.
    if apollo_filters.get('industries_resolved'):
        from industry_taxonomy import v1_to_v2
        peakydev_input['industry'] = v1_to_v2(apollo_filters['industries_resolved'])
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

    return peakydev_input


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
    Normalize peakydev lead output to standardized schema.
    """
    from urllib.parse import urlparse

    # Extract company domain from website URL
    website_url = lead.get('companyWebsite', '') or lead.get('organizationWebsite', '')
    company_domain = ''
    if website_url:
        try:
            parsed = urlparse(website_url if website_url.startswith('http') else f'http://{website_url}')
            company_domain = parsed.netloc.replace('www.', '')
        except:
            company_domain = ''

    return {
        'first_name': lead.get('firstName', ''),
        'last_name': lead.get('lastName', ''),
        'name': lead.get('name') or f"{lead.get('firstName', '')} {lead.get('lastName', '')}".strip(),
        'organization_phone': lead.get('companyPhone', '') or lead.get('organizationPhone', ''),
        'linkedin_url': lead.get('linkedInUrl', '') or lead.get('linkedinUrl', ''),
        'title': lead.get('title', '') or lead.get('position', ''),
        'email_status': lead.get('emailStatus', 'unknown'),
        'email': lead.get('email', ''),
        'city': lead.get('city', ''),
        'country': lead.get('country', ''),
        'org_name': lead.get('companyName', '') or lead.get('organizationName', ''),
        'website_url': website_url,
        'company_linkedin': lead.get('organizationLinkedinUrl', '') or lead.get('companyLinkedinUrl', ''),
        'company_domain': company_domain,
        'industry': lead.get('organizationIndustry', '') or lead.get('industry', ''),
        'source': 'peakydev_leads_scraper'
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
    locations_for_validation = apollo_filters.get('org_locations') or apollo_filters.get('locations', [])
    location_keywords = [loc.lower() for loc in locations_for_validation]

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


def run_peakydev_scraper(apollo_url, max_leads, output_dir='.tmp/peakydev', output_prefix='peakydev_leads', test_only=False):
    """
    Run peakydev/leads-scraper-ppe with Apollo URL-derived filters.

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

        # Map to peakydev input schema
        peakydev_input = map_apollo_to_peakydev(apollo_filters)

        if peakydev_input is None:
            print("Aborting: Cannot scrape without industry filter. Resolve hex IDs first.", file=sys.stderr)
            sys.exit(3)

        # Set result count
        # NOTE: Peakydev requires minimum 1000 leads - cannot do 25-lead test
        if test_only:
            # For test mode, use minimum 1000 leads (Peakydev requirement)
            target_leads = 1000
            print(f"\n{'='*60}")
            print(f"PEAKYDEV SCRAPER TEST (using 1000 leads - minimum required)")
            print(f"{'='*60}")
            print(f"WARNING: Peakydev requires minimum 1000 leads")
            print(f"Target leads: {target_leads} (minimum enforced)")
        else:
            target_leads = max(1000, max_leads)  # Ensure minimum 1000
            print(f"\n{'='*60}")
            print(f"PEAKYDEV SCRAPER FULL RUN")
            print(f"{'='*60}")
            print(f"Target leads: {target_leads}")

        peakydev_input['totalResults'] = target_leads
        print(f"Apollo filters extracted:")
        print(f"  Titles: {apollo_filters.get('titles', [])}")
        print(f"  Seniority: {apollo_filters.get('seniority', [])}")
        print(f"  Person Locations: {apollo_filters.get('locations', [])}")
        print(f"  Org Locations: {apollo_filters.get('org_locations', [])}")
        print(f"  Keywords: {apollo_filters.get('keywords', [])}")
        print(f"\nPeakydev input:")
        print(json.dumps(peakydev_input, indent=2))

        # Initialize Apify client
        client = ApifyClient(apify_api_key)

        # Run the actor
        print(f"\nStarting Apify actor: peakydev/leads-scraper-ppe...")
        run = client.actor("peakydev/leads-scraper-ppe").call(run_input=peakydev_input)

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
            print("Warning: No leads returned from peakydev scraper", file=sys.stderr)
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
            print(f"[FAIL] Match rate below 80% threshold")
            if test_only:
                print("[INFO] Peakydev scraper will NOT be used for full run")
                return False, None, match_percentage
        else:
            print(f"[PASS] Match rate meets 80% threshold")
            if test_only:
                print("[INFO] Peakydev scraper validated - ready for full run")

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
        print(f"Error running peakydev scraper: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False, None, 0.0


def main():
    parser = argparse.ArgumentParser(description='Peakydev Leads Scraper with Apollo URL input')
    parser.add_argument('--apollo-url', required=True, help='Apollo.io search URL')
    parser.add_argument('--max-leads', type=int, default=5000, help='Maximum leads to scrape')
    parser.add_argument('--output-dir', default='.tmp/peakydev', help='Output directory')
    parser.add_argument('--output-prefix', default='peakydev_leads', help='Output file prefix')
    parser.add_argument('--test-only', action='store_true', help='Only scrape 25 leads for validation')

    args = parser.parse_args()

    success, output_file, match_percentage = run_peakydev_scraper(
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

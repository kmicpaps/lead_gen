# [CLI] — run via: py execution/scraper_olympus_b2b_finder.py --help
"""
Apify B2B Leads Finder Scraper (olympus/b2b-leads-finder)

This scraper replaces the RapidAPI Apollo scraper with a more robust Apify-based solution.

Features:
- Automatic progress tracking (resumes from last page)
- Built-in email enrichment (~60% coverage)
- Single cookie array format (EditThisCookie export)
- $1/1k leads for paid Apify users

Usage:
    python execution/run_apify_b2b_leads_finder.py \
        --apollo-url "https://app.apollo.io/#/people?..." \
        --max-leads 2000 \
        --output-dir .tmp/b2b_finder \
        --output-prefix b2b_leads
"""

import os
import sys
import json
import argparse
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote
from apify_client import ApifyClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import save_json

# Note: We manually load env vars to avoid load_dotenv() parsing errors with multiline JSON cookie
# The APOLLO_COOKIE is manually parsed from .env file
# APIFY_API_KEY is accessed directly via os.getenv()

def detect_country_from_url(apollo_url):
    """
    Auto-detect country code from Apollo URL.
    B2B Finder requires country to match your Apollo account location.
    For Nordic/Baltic countries, we'll default to SE (Sweden) as it's a common Apollo account location.
    """
    try:
        parsed = urlparse(apollo_url)
        query_params = parse_qs(parsed.fragment.split('?')[1] if '?' in parsed.fragment else '')

        # Extract locations from personLocations parameter
        locations = query_params.get('personLocations[]', [])

        if not locations:
            return 'US'  # Default to US if no location specified

        # Decode URL-encoded locations
        locations = [unquote(loc).strip().lower() for loc in locations]

        # Country mapping for common Apollo searches
        country_map = {
            'united states': 'US',
            'usa': 'US',
            'us': 'US',
            'estonia': 'EE',
            'lithuania': 'LT',
            'latvia': 'LV',
            'finland': 'FI',
            'sweden': 'SE',
            'norway': 'NO',
            'denmark': 'DK',
            'poland': 'PL',
            'germany': 'DE',
            'united kingdom': 'GB',
            'uk': 'GB',
            'france': 'FR',
            'spain': 'ES',
            'italy': 'IT',
            'netherlands': 'NL',
        }

        # Check each location for a match
        for location in locations:
            for country_name, code in country_map.items():
                if country_name in location:
                    return code

        # If Nordic/Baltic countries mentioned but no exact match, default to SE
        nordic_baltic = ['sweden', 'norway', 'finland', 'denmark', 'estonia', 'lithuania', 'latvia']
        if any(nb in ' '.join(locations) for nb in nordic_baltic):
            return 'SE'

        return 'US'  # Final fallback
    except Exception:
        return 'US'

def normalize_apollo_url(apollo_url):
    """
    Normalize Apollo URL by cleaning up malformed parameters.
    Fixes issues like trailing spaces in URL parameters.
    """
    try:
        # URL-decode and re-encode to fix encoding issues
        parsed = urlparse(apollo_url)

        if '?' not in parsed.fragment:
            return apollo_url

        base, query = parsed.fragment.split('?', 1)
        query_params = parse_qs(query)

        # Clean up parameter values (remove trailing spaces, normalize)
        cleaned_params = {}
        for key, values in query_params.items():
            cleaned_values = [unquote(v).strip() for v in values]
            cleaned_params[key] = cleaned_values

        # Rebuild query string
        from urllib.parse import urlencode
        new_query = urlencode(cleaned_params, doseq=True)
        new_fragment = f"{base}?{new_query}"

        # Reconstruct URL
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}#{new_fragment}"
    except Exception:
        # If normalization fails, return original URL
        return apollo_url

def normalize_lead_to_schema(lead):
    """
    Normalize B2B Leads Finder output to standardized schema.
    Preserves organization data (industry, keywords, etc.) that Apollo provides.
    """
    org = lead.get('organization', {}) or {}
    industries = org.get('industries', []) or []
    keywords = org.get('keywords', []) or []

    return {
        'first_name': lead.get('first_name', ''),
        'last_name': lead.get('last_name', ''),
        'name': lead.get('name') or f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
        'organization_phone': lead.get('organization_phone') or lead.get('phone', '') or org.get('phone', ''),
        'linkedin_url': lead.get('linkedin_url', ''),
        'title': lead.get('title', ''),
        'email_status': lead.get('email_status', 'unknown'),
        'email': lead.get('email', ''),
        'city': lead.get('city', ''),
        'country': lead.get('country', ''),
        'org_name': lead.get('organization_name') or org.get('name', ''),
        'website_url': lead.get('website_url') or org.get('website_url', ''),
        'industry': industries[0].title() if industries else '',
        'org_keywords': keywords[:10] if keywords else [],
        'org_linkedin': org.get('linkedin_url', ''),
        'org_facebook': org.get('facebook_url', ''),
        'org_employee_count': org.get('estimated_num_employees'),
        'org_founded_year': org.get('founded_year'),
        'seniority': lead.get('seniority', ''),
        'departments': lead.get('departments', []),
        'headline': lead.get('headline', ''),
        'source': 'olympus'
    }


def main():
    parser = argparse.ArgumentParser(description='Apify B2B Leads Finder Scraper')
    parser.add_argument('--apollo-url', required=True, help='Apollo search URL')
    parser.add_argument('--max-leads', type=int, default=5000, help='Maximum leads to scrape')
    parser.add_argument('--output-dir', default='.tmp/b2b_finder', help='Output directory')
    parser.add_argument('--output-prefix', default='b2b_leads', help='Output file prefix')
    parser.add_argument('--country', default=None, help='Country code (ISO format, e.g., US, FI, EE). If not specified, auto-detected from Apollo URL.')

    args = parser.parse_args()

    # Manually load required env vars from .env file
    apify_api_key = None
    apollo_cookie = None

    try:
        with open('.env', 'r', encoding='utf-8') as f:
            env_content = f.read()

        # Parse simple key=value pairs for Apify API key
        import re
        for line in env_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                if line.startswith('APIFY_API_KEY='):
                    apify_api_key = line.split('=', 1)[1].strip()

        # Validate Apify API key
        if not apify_api_key:
            print("Error: APIFY_API_KEY not found in .env", file=sys.stderr)
            return 1

        # Find APOLLO_COOKIE=[...] in the file
        # Match from APOLLO_COOKIE=[ to the last ] on its own line
        match = re.search(r'(?:^|\n)APOLLO_COOKIE=(\[.*?\n\])', env_content, re.DOTALL | re.MULTILINE)
        if match:
            apollo_cookie_str = match.group(1)

            # Browser-exported cookies from EditThisCookie
            # Try standard JSON parsing first
            try:
                apollo_cookie = json.loads(apollo_cookie_str)
            except json.JSONDecodeError:
                # If standard parsing fails, try fixing common issues
                fixed_str = apollo_cookie_str.replace("'", '"')
                try:
                    apollo_cookie = json.loads(fixed_str)
                except json.JSONDecodeError as e:
                    # Try ast.literal_eval as fallback
                    import ast
                    try:
                        apollo_cookie = ast.literal_eval(apollo_cookie_str)
                    except Exception:
                        # Last resort: Try json5
                        try:
                            import json5
                            apollo_cookie = json5.loads(apollo_cookie_str)
                        except Exception:
                            print(f"Error: Could not parse APOLLO_COOKIE. JSON error: {e}", file=sys.stderr)
                            print(f"Cookie string length: {len(apollo_cookie_str)}", file=sys.stderr)
                            print(f"First 200 chars: {apollo_cookie_str[:200]}", file=sys.stderr)
                            print("Please ensure APOLLO_COOKIE is valid JSON array format.", file=sys.stderr)
                            return 1
        else:
            print("Error: APOLLO_COOKIE not found in .env", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error loading credentials from .env: {e}", file=sys.stderr)
        return 1

    try:
        # Auto-detect country if not specified
        country = args.country if args.country else detect_country_from_url(args.apollo_url)

        # Normalize URL (clean up malformed parameters)
        normalized_url = normalize_apollo_url(args.apollo_url)

        print(f"Starting Apify B2B Leads Finder Scraper...")
        print(f"Target leads: {args.max_leads}")
        print(f"Apollo URL: {normalized_url[:100]}..." if len(normalized_url) > 100 else normalized_url)
        print(f"Country: {country} (auto-detected)" if not args.country else f"Country: {country}")

        # Initialize Apify client
        client = ApifyClient(apify_api_key)

        # Prepare input for B2B Leads Finder
        run_input = {
            "searchUrl": normalized_url,  # Note: actor expects "searchUrl" not "url"
            "cookies": apollo_cookie,  # Single array, not double-nested
            "country": country,
            "maxResults": args.max_leads
        }

        print("\nStarting Apify actor run...")
        print(f"Actor: olympus/b2b-leads-finder")

        # Start the actor (non-blocking) so we can save run ID immediately
        started_run = client.actor("olympus/b2b-leads-finder").start(run_input=run_input)
        run_id = started_run['id']
        print(f"Actor run ID: {run_id}")

        # Save run ID for recovery (if local process is killed, Apify run continues)
        run_id_file = Path(args.output_dir) / '.active_run.json'
        run_id_file.parent.mkdir(parents=True, exist_ok=True)
        with open(run_id_file, 'w', encoding='utf-8') as _f:
            json.dump({'run_id': run_id, 'actor': 'olympus/b2b-leads-finder',
                       'started_at': datetime.now().isoformat()}, _f)
        print(f"Run ID saved to: {run_id_file}")

        # Wait for the actor to finish
        print("Waiting for actor to complete...")
        run = client.run(run_id).wait_for_finish()

        # Clean up run ID file
        run_id_file.unlink(missing_ok=True)

        print(f"Status: {run['status']}")

        # Check if run was successful
        if run['status'] != 'SUCCEEDED':
            print(f"Error: Actor run failed with status: {run['status']}", file=sys.stderr)
            if 'statusMessage' in run:
                print(f"Status message: {run['statusMessage']}", file=sys.stderr)
            return 1

        # Fetch results from the actor's dataset
        print("\nDownloading results...")
        dataset_items = list(client.dataset(run['defaultDatasetId']).iterate_items())

        if not dataset_items:
            print("Warning: No leads returned from B2B Leads Finder", file=sys.stderr)
            print("This could mean:")
            print("  - Filters are too restrictive")
            print("  - Cookie expired")
            print("  - Search URL returned no results")
            return 1

        # Check for session validation errors in dataset (cookie failures)
        cookie_validation_failed = False
        for item in dataset_items[:10]:  # Check first 10 items
            item_str = str(item).lower()
            if any(error in item_str for error in [
                'session validation failed',
                'resurrect the run',
                'cookie expired',
                'authentication failed',
                'login required',
                'please log in'
            ]):
                cookie_validation_failed = True
                break

        if cookie_validation_failed:
            print("\n" + "="*70, file=sys.stderr)
            print("🚫 COOKIE VALIDATION FAILED", file=sys.stderr)
            print("="*70, file=sys.stderr)
            print("", file=sys.stderr)
            print("The Apollo session cookie has expired.", file=sys.stderr)
            print("", file=sys.stderr)
            print("ACTION REQUIRED:", file=sys.stderr)
            print("1. Log into Apollo: https://app.apollo.io", file=sys.stderr)
            print("2. Export fresh cookies using EditThisCookie extension", file=sys.stderr)
            print("3. Update APOLLO_COOKIE in .env file", file=sys.stderr)
            print("4. Re-run the scraper", file=sys.stderr)
            print("", file=sys.stderr)
            print("="*70, file=sys.stderr)
            return 2  # Special exit code for cookie failures

        # Check for suspiciously low results (possible cookie issue)
        if len(dataset_items) < max(10, args.max_leads * 0.01):  # Less than 1% of requested (min 10)
            print(f"\n⚠️  Warning: Got only {len(dataset_items)} leads (requested {args.max_leads})", file=sys.stderr)
            print("This may indicate a cookie validation issue.", file=sys.stderr)
            print("If this persists, refresh your Apollo cookies.", file=sys.stderr)

        # Filter out status/notification messages from actor output
        junk_patterns = ['\U0001f440', '\u23f3', '\U0001f4c8', '\U0001f7e2', 'Actor speed', 'Scanning pages',
                         'enhance scraping', 'check the log', 'bear with us']
        real_leads = [item for item in dataset_items
                      if not any(p in str(item.get('name', '')) for p in junk_patterns)]
        if len(real_leads) < len(dataset_items):
            print(f"Filtered out {len(dataset_items) - len(real_leads)} status messages from actor output")
        print(f"Downloaded {len(real_leads)} leads")

        # Normalize leads to standardized schema
        normalized_leads = [normalize_lead_to_schema(lead) for lead in real_leads]

        # Save results
        os.makedirs(args.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{args.output_prefix}_{timestamp}_{len(normalized_leads)}leads.json"
        filepath = os.path.join(args.output_dir, filename)

        save_json(normalized_leads, filepath)

        print(f"Successfully scraped {len(normalized_leads)} leads from Apify B2B Leads Finder.")
        print(f"Note: Requested {args.max_leads}, got {len(normalized_leads)}")
        print(filepath)  # Print filepath to stdout for caller to capture

        return 0

    except KeyboardInterrupt:
        print("\nScraping interrupted by user.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error running Apify B2B Leads Finder: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

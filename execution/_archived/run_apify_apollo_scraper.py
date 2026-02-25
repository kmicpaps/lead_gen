"""
Apify Apollo scraper fallback using x_guru/Leads-Scraper-apollo-zoominfo.
This runs when RapidAPI Apollo scraper fails.
"""

import os
import sys
import json
import argparse
import time
from datetime import datetime
from dotenv import load_dotenv
from apify_client import ApifyClient

# Load environment variables
load_dotenv()

def normalize_lead_to_schema(lead):
    """
    Normalize Apify Apollo lead data to standardized schema.
    Output fields: first_name, last_name, name, organization_phone, linkedin_url,
                   title, email_status, email, city, country, org_name, website_url
    """
    return {
        'first_name': lead.get('firstName', ''),
        'last_name': lead.get('lastName', ''),
        'name': lead.get('name') or f"{lead.get('firstName', '')} {lead.get('lastName', '')}".strip(),
        'organization_phone': lead.get('companyPhone', ''),
        'linkedin_url': lead.get('linkedInUrl', ''),
        'title': lead.get('title', ''),
        'email_status': 'unknown',  # Will be updated by Lead Magic
        'email': lead.get('email', ''),
        'city': lead.get('city', ''),
        'country': lead.get('country', ''),
        'org_name': lead.get('companyName', ''),
        'website_url': lead.get('companyWebsite', ''),
        'source': 'apollo'
    }

def main():
    parser = argparse.ArgumentParser(description='Run Apify Apollo scraper (x_guru/Leads-Scraper-apollo-zoominfo)')
    parser.add_argument('--apollo-url', required=True, help='Apollo search URL')
    parser.add_argument('--max-leads', type=int, default=5000, help='Maximum leads to scrape')
    parser.add_argument('--output-dir', default='.tmp/apollo_run', help='Output directory')
    parser.add_argument('--output-prefix', default='apollo_leads', help='Output file prefix')

    args = parser.parse_args()

    # Get API credentials from environment
    apify_api_key = os.getenv('APIFY_API_KEY')

    if not apify_api_key:
        print("Error: APIFY_API_KEY not found in .env", file=sys.stderr)
        return 1

    # Load Apollo cookie from .env
    apollo_cookie = None
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            env_content = f.read()

        # Find APOLLO_COOKIE=[...] in the file
        import re
        match = re.search(r'APOLLO_COOKIE=(\[.*?\])', env_content, re.DOTALL)
        if match:
            apollo_cookie_str = match.group(1)
            apollo_cookie = json.loads(apollo_cookie_str)
        else:
            print("Error: APOLLO_COOKIE not found in .env", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error loading APOLLO_COOKIE from .env: {e}", file=sys.stderr)
        return 1

    try:
        print(f"Starting Apify Apollo scraper (x_guru/Leads-Scraper-apollo-zoominfo)...")
        print(f"Target leads: {args.max_leads} (actual count may vary based on filters)")
        print(f"Apollo URL: {args.apollo_url}")

        # Initialize Apify client
        client = ApifyClient(apify_api_key)

        # Prepare actor input for x_guru/Leads-Scraper-apollo-zoominfo
        run_input = {
            "startUrls": [{"url": args.apollo_url}],
            "maxItems": args.max_leads,
            "proxy": {
                "useApifyProxy": True
            }
        }

        print("Starting Apify actor run...")

        # Run the actor and wait for it to finish
        run = client.actor("x_guru/Leads-Scraper-apollo-zoominfo").call(run_input=run_input)

        # Get run status
        run_info = client.run(run["id"]).get()
        status = run_info.get("status")

        print(f"Actor run completed with status: {status}")

        if status != "SUCCEEDED":
            print(f"Error: Actor run failed with status: {status}", file=sys.stderr)
            return 1

        # Fetch results from the dataset
        print("Downloading results from dataset...")
        dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items

        if not dataset_items:
            print("Warning: No leads returned from Apify Apollo scraper", file=sys.stderr)
            print("This could mean:")
            print("  - Filters are too restrictive")
            print("  - Cookie expired")
            print("  - API issue")
            return 1

        # Normalize leads to standardized schema
        normalized_leads = [normalize_lead_to_schema(lead) for lead in dataset_items]

        # Save results
        os.makedirs(args.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{args.output_prefix}_{timestamp}_{len(normalized_leads)}leads.json"
        filepath = os.path.join(args.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(normalized_leads, f, indent=2, ensure_ascii=False)

        print(f"Successfully scraped {len(normalized_leads)} leads from Apollo via Apify.")
        print(f"Note: Requested {args.max_leads}, got {len(normalized_leads)} (filter compliance prioritized over quantity)")
        print(filepath)  # Print filepath to stdout for caller to capture

        return 0

    except Exception as e:
        print(f"Error running Apify Apollo scraper: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

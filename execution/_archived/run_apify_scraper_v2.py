"""
Enhanced Apify scraper for code_crafter/leads-finder with advanced filtering.
Supports: Job titles, Location, Industry, Revenue, Funding, Seniority, etc.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv
from apify_client import ApifyClient

# Load environment variables
load_dotenv()

def normalize_lead_to_schema(lead):
    """
    Normalize Apify lead data to standardized schema.
    Output fields: first_name, last_name, name, organization_phone, linkedin_url,
                   title, email_status, email, city, country, org_name, website_url
    """
    return {
        'first_name': lead.get('first_name', ''),
        'last_name': lead.get('last_name', ''),
        'name': lead.get('full_name') or f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
        'organization_phone': lead.get('company_phone', ''),
        'linkedin_url': lead.get('linkedin', ''),
        'title': lead.get('job_title', ''),
        'email_status': lead.get('email_status', 'unknown'), # Use provided status if available
        'email': lead.get('email', ''),
        'city': lead.get('city', ''),
        'country': lead.get('country', ''),
        'org_name': lead.get('company_name', ''),
        'website_url': lead.get('company_website', ''),
        'source': 'apify',
        # Extra fields that might be useful for debugging or custom logic
        'revenue': lead.get('company_annual_revenue', ''),
        'funding': lead.get('company_total_funding', ''),
        'industry': lead.get('industry', '')
    }

def main():
    parser = argparse.ArgumentParser(description='Run Apify leads-finder scraper with advanced filters')
    
    # General
    parser.add_argument('--fetch-count', type=int, default=2000, help='Max leads to fetch')
    
    # People Targeting
    parser.add_argument('--job-title', help='Include job titles (comma-separated)')
    parser.add_argument('--excluded-job-title', help='Exclude job titles (comma-separated)')
    parser.add_argument('--seniority', help='Seniority level (e.g., Owner, C-Level, VP, Director)')
    parser.add_argument('--functional-level', help='Functional level (e.g., Marketing, Sales, C-Level)')
    
    # Location
    parser.add_argument('--location', help='Region/Country/State (e.g., United States, California)')
    parser.add_argument('--city', help='Specific cities (comma-separated)')
    parser.add_argument('--excluded-location', help='Exclude Region/Country/State')
    parser.add_argument('--excluded-city', help='Exclude cities')
    
    # Company Targeting
    parser.add_argument('--industry', help='Include industries (comma-separated)')
    parser.add_argument('--excluded-industry', help='Exclude industries')
    parser.add_argument('--company-keywords', help='Include company keywords')
    parser.add_argument('--excluded-company-keywords', help='Exclude company keywords')
    parser.add_argument('--company-size', help='Company size range (e.g., 11-50, 51-200)')
    parser.add_argument('--company-domain', help='Specific company domains')
    parser.add_argument('--min-revenue', help='Min revenue (e.g., 1000000)')
    parser.add_argument('--max-revenue', help='Max revenue')
    parser.add_argument('--funding', help='Funding type (e.g., Series A, Venture)')
    
    # Email Quality
    parser.add_argument('--email-status', default='validated', help='Email status: validated, not_validated, unknown (default: validated)')
    
    # Output
    parser.add_argument('--output-dir', default='.tmp/apify_run', help='Output directory')
    parser.add_argument('--output-prefix', default='apify_leads', help='Output file prefix')

    args = parser.parse_args()

    api_key = os.getenv('APIFY_API_KEY')
    if not api_key:
        print("Error: APIFY_API_KEY not found in .env", file=sys.stderr)
        return 1

    try:
        # Initialize Apify Client
        client = ApifyClient(api_key)

        # Prepare actor input
        run_input = {
            "fetch_count": args.fetch_count,
            "email_status": [s.strip() for s in args.email_status.split(',')] if args.email_status else ["validated"],
        }

        # Helper to add list arguments
        def add_list_arg(key, value):
            if value:
                run_input[key] = [v.strip() for v in value.split(',')]

        # Helper to add string arguments
        def add_str_arg(key, value):
            if value:
                run_input[key] = value

        # Map arguments to actor input schema
        add_list_arg("contact_job_title", args.job_title)
        add_list_arg("contact_not_job_title", args.excluded_job_title)
        add_list_arg("seniority_level", args.seniority)
        add_list_arg("functional_level", args.functional_level)
        
        add_list_arg("contact_location", args.location)
        add_list_arg("contact_city", args.city)
        add_list_arg("contact_not_location", args.excluded_location)
        add_list_arg("contact_not_city", args.excluded_city)
        
        add_list_arg("company_industry", args.industry)
        add_list_arg("company_not_industry", args.excluded_industry)
        add_list_arg("company_keywords", args.company_keywords)
        add_list_arg("company_not_keywords", args.excluded_company_keywords)
        add_list_arg("size", args.company_size)
        add_list_arg("company_domain", args.company_domain)
        add_list_arg("funding", args.funding)
        
        add_str_arg("min_revenue", args.min_revenue)
        add_str_arg("max_revenue", args.max_revenue)

        print(f"Starting Apify run with input: {json.dumps(run_input, indent=2)}")
        print(f"Target leads: {args.fetch_count} (actual count may vary based on filters)")

        # Start the actor and wait for it to finish
        # Actor ID: code_crafter/leads-finder
        run = client.actor("code_crafter/leads-finder").call(run_input=run_input)

        if not run:
            print("Error: Apify run failed to start or returned no data.", file=sys.stderr)
            return 1

        print(f"Run finished. Dataset ID: {run['defaultDatasetId']}")

        # Fetch results
        dataset_items = client.dataset(run['defaultDatasetId']).list_items().items

        if not dataset_items:
            print("Warning: No leads returned from Apify scraper", file=sys.stderr)
            print("This could mean filters are too restrictive or no matching leads found")
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

        print(f"Successfully scraped {len(normalized_leads)} leads from Apify.")
        print(f"Note: Requested {args.fetch_count}, got {len(normalized_leads)} (filter compliance prioritized)")
        print(filepath)  # Print filepath to stdout for the caller to capture

        return 0

    except Exception as e:
        print(f"Error running Apify scraper: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

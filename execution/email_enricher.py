# [CLI] — run via: py execution/email_enricher.py --help
"""
Fast email enrichment using Lead Magic API with concurrent requests.
Find missing emails using Lead Magic API email finder.
Rate limit: 400 requests/minute (conservative, actual may be 1000)
Cost: Expensive (1 credit per lookup) - use sparingly

PERFORMANCE: Uses ThreadPoolExecutor for ~5x speed improvement
"""

import os
import sys
import json
import argparse
import requests
import time
from datetime import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import RateLimiter, load_leads, save_json

# Load environment variables
load_dotenv()

# Rate limiting: 400 req/min = ~6.67 req/second
# Use 6 req/second to be conservative
RATE_LIMIT = 6  # requests per second
MAX_WORKERS = 6  # concurrent threads

def find_single_email(lead, api_key, rate_limiter):
    """
    Find email for a single lead using Lead Magic email finder API.
    Returns: (updated lead, success status)
    """
    base_url = "https://api.leadmagic.io"
    headers = {
        'X-API-Key': api_key,
        'Content-Type': 'application/json'
    }

    # Prepare payload
    payload = {}

    if lead.get('first_name'):
        payload['first_name'] = lead['first_name']
    if lead.get('last_name'):
        payload['last_name'] = lead['last_name']
    if lead.get('website_url'):
        # Extract domain from URL
        domain = lead['website_url'].replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0]
        payload['domain'] = domain
    if lead.get('org_name'):
        payload['company_name'] = lead['org_name']

    # Need at least first_name to make a request
    if not payload.get('first_name'):
        return lead, False

    try:
        # Wait for rate limit
        rate_limiter.acquire()

        response = requests.post(
            f"{base_url}/email-finder",
            json=payload,
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            found_email = result.get('email')

            if found_email:
                lead['email'] = found_email
                lead['email_status'] = result.get('status', 'valid')
                lead['email_source'] = 'leadmagic_enrichment'
                lead['leadmagic_credits_used'] = lead.get('leadmagic_credits_used', 0) + result.get('credits_consumed', 1)
                return lead, True
            else:
                return lead, False

        elif response.status_code == 429:
            # Rate limit - wait and retry once
            print(f"Rate limit hit for {lead.get('name', 'Unknown')}, waiting...")
            time.sleep(10)
            response = requests.post(
                f"{base_url}/email-finder",
                json=payload,
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                found_email = result.get('email')
                if found_email:
                    lead['email'] = found_email
                    lead['email_status'] = result.get('status', 'valid')
                    lead['email_source'] = 'leadmagic_enrichment'
                    return lead, True
            return lead, False

        else:
            return lead, False

    except Exception as e:
        print(f"Error finding email for {lead.get('name', 'Unknown')}: {e}", file=sys.stderr)
        return lead, False

def enrich_missing_emails_concurrent(leads, api_key):
    """
    Find emails for leads that are missing emails or have invalid emails.
    Uses concurrent processing for speed.
    """
    # Filter leads that need enrichment
    leads_to_enrich = [
        lead for lead in leads
        if not lead.get('email') or lead.get('email_status') in ['missing', 'invalid', 'verification_failed']
    ]

    if not leads_to_enrich:
        print("No leads need email enrichment")
        return leads

    print(f"Enriching {len(leads_to_enrich)} leads with missing/invalid emails using {MAX_WORKERS} workers")
    print(f"Estimated cost: {len(leads_to_enrich)} credits")
    print(f"Estimated time: ~{len(leads_to_enrich) / RATE_LIMIT:.1f} seconds")

    enriched_count = 0
    failed_count = 0

    # Create a lookup map for quick updating
    leads_map = {id(lead): lead for lead in leads}

    rate_limiter = RateLimiter(RATE_LIMIT)
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all enrichment tasks
        future_to_lead = {
            executor.submit(find_single_email, lead, api_key, rate_limiter): id(lead)
            for lead in leads_to_enrich
        }

        # Process completed tasks
        processed = 0
        for future in as_completed(future_to_lead):
            processed += 1
            lead_id = future_to_lead[future]

            try:
                updated_lead, success = future.result()
                leads_map[lead_id] = updated_lead

                if success:
                    enriched_count += 1
                else:
                    failed_count += 1

                if processed % 25 == 0:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed
                    print(f"  Enriched {processed}/{len(leads_to_enrich)} | Found: {enriched_count} ({rate:.1f}/sec)")

            except Exception as e:
                print(f"Error in future: {e}", file=sys.stderr)
                failed_count += 1

    elapsed_time = time.time() - start_time
    actual_rate = len(leads_to_enrich) / elapsed_time if elapsed_time > 0 else 0

    print(f"\nEnrichment complete in {elapsed_time:.1f}s ({actual_rate:.1f} leads/sec):")
    print(f"  Attempted: {len(leads_to_enrich)}")
    print(f"  Emails found: {enriched_count} ({enriched_count/len(leads_to_enrich)*100:.1f}%)")
    print(f"  Not found: {failed_count}")

    return leads

def main():
    parser = argparse.ArgumentParser(description='Fast email enrichment using Lead Magic API')
    parser.add_argument('--input', required=True, help='Path to leads JSON file')
    parser.add_argument('--output-dir', default='.tmp/enriched', help='Output directory')
    parser.add_argument('--output-prefix', default='enriched_leads', help='Output file prefix')
    parser.add_argument('--skip-enrichment', action='store_true', help='Skip enrichment (for testing)')

    args = parser.parse_args()

    api_key = os.getenv('LeadMagic-X-API-Key')
    if not api_key:
        print("Error: LeadMagic-X-API-Key not found in .env", file=sys.stderr)
        return 1

    try:
        # Load leads
        leads = load_leads(args.input)

        if not leads:
            print("No leads to enrich", file=sys.stderr)
            return 1

        print(f"Loaded {len(leads)} leads")

        if args.skip_enrichment:
            print("Skipping enrichment (--skip-enrichment flag set)")
        else:
            # Enrich emails concurrently
            leads = enrich_missing_emails_concurrent(leads, api_key)

        # Save enriched leads
        os.makedirs(args.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{args.output_prefix}_{timestamp}_{len(leads)}leads.json"
        filepath = os.path.join(args.output_dir, filename)

        save_json(leads, filepath)

        print(f"\nEnriched leads saved to: {filepath}")
        print(filepath)  # Print filepath to stdout for caller

        return 0

    except Exception as e:
        print(f"Error enriching emails: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

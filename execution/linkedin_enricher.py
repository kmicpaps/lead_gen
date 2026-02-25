# [CLI] — run via: py execution/linkedin_enricher.py --help
"""
LinkedIn Profile Enrichment using Lead Magic Profile Search API.
Enriches leads with LinkedIn profile data: bio, experience, education, tenure, followers.

API: POST https://api.leadmagic.io/v1/people/profile-search
Cost: 1 credit per profile (0 if not found)
Rate limit: 500 requests/minute

PERFORMANCE: Uses ThreadPoolExecutor for concurrent processing
"""

import os
import sys
import json
import argparse
import requests
import time
import re
from datetime import datetime, timezone
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from utils import RateLimiter

# Load environment variables
load_dotenv()

# Rate limiting: 500 req/min = ~8.3 req/second
# Use 8 req/second to be conservative
RATE_LIMIT = 8  # requests per second
MAX_WORKERS = 10  # concurrent threads

# Progress tracking
progress_lock = Lock()
progress_data = {
    'processed': 0,
    'success': 0,
    'not_found': 0,
    'failed': 0,
    'credits': 0
}


def normalize_linkedin_url(url):
    """
    Normalize LinkedIn URL to format expected by API.
    Returns: normalized URL or None if invalid
    """
    if not url:
        return None

    url = url.strip()

    # Check if it's a LinkedIn URL
    if 'linkedin.com' not in url.lower():
        return None

    # Strip protocol and www
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^www\.', '', url)

    # Ensure it has linkedin.com prefix
    if not url.startswith('linkedin.com'):
        # Try to extract the path
        match = re.search(r'linkedin\.com(/.*)', url)
        if match:
            url = 'linkedin.com' + match.group(1)
        else:
            return None

    return url


def enrich_single_profile(lead, api_key, rate_limiter):
    """
    Enrich a single lead with LinkedIn profile data.
    Returns: (updated lead, status: 'success'|'not_found'|'error', credits_used)
    """
    global progress_data

    base_url = "https://api.leadmagic.io/v1/people/profile-search"
    headers = {
        'X-API-Key': api_key,
        'Content-Type': 'application/json'
    }

    # Normalize LinkedIn URL
    linkedin_url = normalize_linkedin_url(lead.get('linkedin_url'))

    if not linkedin_url:
        lead['linkedin_enrichment_error'] = 'invalid_url'
        return lead, 'error', 0

    payload = {
        'profile_url': linkedin_url,
        'extended_response': True
    }

    try:
        # Wait for rate limit
        rate_limiter.acquire()

        response = requests.post(
            base_url,
            json=payload,
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            credits = result.get('credits_consumed', 0)

            # Check if profile was found
            if result.get('message') == 'Profile not found.' or credits == 0:
                lead['linkedin_enrichment_error'] = 'not_found'
                return lead, 'not_found', 0

            # Map response to lead fields
            lead['linkedin_bio'] = result.get('bio') or ''
            lead['linkedin_headline'] = result.get('professional_title') or ''
            lead['linkedin_company'] = result.get('company_name') or ''
            lead['linkedin_industry'] = result.get('company_industry') or ''
            lead['linkedin_location'] = result.get('location') or ''
            lead['linkedin_tenure_years'] = result.get('total_tenure_years') or ''
            lead['linkedin_followers'] = result.get('followers_range') or ''

            # Map work experience
            work_exp = result.get('work_experience', [])
            if work_exp:
                lead['linkedin_experience'] = [
                    {
                        'title': exp.get('position_title', ''),
                        'company': exp.get('company_name', ''),
                        'period': exp.get('employment_period', '')
                    }
                    for exp in work_exp[:5]  # Keep top 5 positions
                ]

            # Map education
            education = result.get('education', [])
            if education:
                lead['linkedin_education'] = [
                    {
                        'school': edu.get('institution_name', ''),
                        'degree': edu.get('degree', ''),
                        'period': edu.get('attendance_period', '')
                    }
                    for edu in education[:3]  # Keep top 3
                ]

            # Metadata
            lead['linkedin_enriched_at'] = datetime.now(timezone.utc).isoformat() + 'Z'
            lead['linkedin_enrichment_credits'] = credits

            return lead, 'success', credits

        elif response.status_code == 429:
            # Rate limited - wait and retry once
            print(f"Rate limit hit, waiting 60s...")
            time.sleep(60)

            response = requests.post(
                base_url,
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                credits = result.get('credits_consumed', 0)

                if result.get('message') == 'Profile not found.' or credits == 0:
                    lead['linkedin_enrichment_error'] = 'not_found'
                    return lead, 'not_found', 0

                # Map response (same as above)
                lead['linkedin_bio'] = result.get('bio') or ''
                lead['linkedin_headline'] = result.get('professional_title') or ''
                lead['linkedin_company'] = result.get('company_name') or ''
                lead['linkedin_industry'] = result.get('company_industry') or ''
                lead['linkedin_location'] = result.get('location') or ''
                lead['linkedin_tenure_years'] = result.get('total_tenure_years') or ''
                lead['linkedin_followers'] = result.get('followers_range') or ''
                lead['linkedin_enriched_at'] = datetime.now(timezone.utc).isoformat() + 'Z'
                lead['linkedin_enrichment_credits'] = credits

                return lead, 'success', credits

            lead['linkedin_enrichment_error'] = 'rate_limited'
            return lead, 'error', 0

        elif response.status_code == 401:
            lead['linkedin_enrichment_error'] = 'invalid_api_key'
            return lead, 'error', 0

        else:
            lead['linkedin_enrichment_error'] = f'api_error_{response.status_code}'
            return lead, 'error', 0

    except requests.exceptions.Timeout:
        lead['linkedin_enrichment_error'] = 'timeout'
        return lead, 'error', 0

    except Exception as e:
        lead['linkedin_enrichment_error'] = f'error: {str(e)}'
        return lead, 'error', 0


def enrich_linkedin_profiles(leads, api_key, force_regenerate=False, limit=None):
    """
    Enrich multiple leads with LinkedIn profile data.
    Uses concurrent processing for speed.
    """
    global progress_data

    # Reset progress
    progress_data = {
        'processed': 0,
        'success': 0,
        'not_found': 0,
        'failed': 0,
        'credits': 0
    }

    # Filter leads that need enrichment
    leads_to_enrich = []
    for lead in leads:
        # Skip if no LinkedIn URL
        if not lead.get('linkedin_url'):
            continue

        # Skip if already enriched (unless force)
        if not force_regenerate and lead.get('linkedin_bio') is not None:
            continue

        leads_to_enrich.append(lead)

    # Apply limit if specified
    if limit and limit > 0:
        leads_to_enrich = leads_to_enrich[:limit]

    if not leads_to_enrich:
        print("No leads need LinkedIn enrichment")
        return leads

    print(f"Enriching {len(leads_to_enrich)} LinkedIn profiles using {MAX_WORKERS} workers")
    print(f"Estimated cost: ~{len(leads_to_enrich)} credits (max)")
    print(f"Estimated time: ~{len(leads_to_enrich) / RATE_LIMIT:.1f} seconds")
    print()

    # Create lookup map for quick updating
    lead_map = {id(lead): lead for lead in leads}

    rate_limiter = RateLimiter(RATE_LIMIT)
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all enrichment tasks
        future_to_lead = {
            executor.submit(enrich_single_profile, lead, api_key, rate_limiter): id(lead)
            for lead in leads_to_enrich
        }

        # Process completed tasks
        for future in as_completed(future_to_lead):
            lead_id = future_to_lead[future]

            try:
                updated_lead, status, credits = future.result()
                lead_map[lead_id] = updated_lead

                with progress_lock:
                    progress_data['processed'] += 1
                    progress_data['credits'] += credits

                    if status == 'success':
                        progress_data['success'] += 1
                    elif status == 'not_found':
                        progress_data['not_found'] += 1
                    else:
                        progress_data['failed'] += 1

                    # Progress update every 25 leads
                    if progress_data['processed'] % 25 == 0:
                        elapsed = time.time() - start_time
                        rate = progress_data['processed'] / elapsed
                        print(f"  Processed {progress_data['processed']}/{len(leads_to_enrich)} | "
                              f"Success: {progress_data['success']} | "
                              f"Not found: {progress_data['not_found']} | "
                              f"Credits: {progress_data['credits']} | "
                              f"({rate:.1f}/sec)")

            except Exception as e:
                print(f"Error in future: {e}", file=sys.stderr)
                with progress_lock:
                    progress_data['processed'] += 1
                    progress_data['failed'] += 1

    elapsed_time = time.time() - start_time
    actual_rate = len(leads_to_enrich) / elapsed_time if elapsed_time > 0 else 0

    print(f"\nLinkedIn enrichment complete in {elapsed_time:.1f}s ({actual_rate:.1f} leads/sec)")
    print(f"  Attempted: {len(leads_to_enrich)}")
    print(f"  Successful: {progress_data['success']} ({progress_data['success']/len(leads_to_enrich)*100:.1f}%)")
    print(f"  Not found: {progress_data['not_found']} ({progress_data['not_found']/len(leads_to_enrich)*100:.1f}%)")
    print(f"  Failed: {progress_data['failed']}")
    print(f"  Credits consumed: {progress_data['credits']}")

    return leads


def main():
    parser = argparse.ArgumentParser(description='LinkedIn Profile Enrichment using Lead Magic API')
    parser.add_argument('--input', required=True, help='Path to leads JSON file')
    parser.add_argument('--output-dir', default='.tmp/linkedin_enriched', help='Output directory')
    parser.add_argument('--output-prefix', default='linkedin_enriched', help='Output file prefix')
    parser.add_argument('--force-regenerate', action='store_true', help='Re-enrich already enriched leads')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of leads to enrich (0 = all)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be enriched without calling API')

    args = parser.parse_args()

    api_key = os.getenv('LeadMagic-X-API-Key')
    if not api_key:
        print("Error: LeadMagic-X-API-Key not found in .env", file=sys.stderr)
        return 1

    try:
        # Load leads
        print(f"Loading leads from: {args.input}")
        with open(args.input, 'r', encoding='utf-8') as f:
            leads = json.load(f)

        if not leads:
            print("No leads to enrich", file=sys.stderr)
            return 1

        print(f"Loaded {len(leads)} leads")

        # Count leads with LinkedIn URLs
        linkedin_count = sum(1 for lead in leads if lead.get('linkedin_url'))
        already_enriched = sum(1 for lead in leads if lead.get('linkedin_bio') is not None)

        print(f"  - With LinkedIn URL: {linkedin_count}")
        print(f"  - Already enriched: {already_enriched}")
        print()

        if args.dry_run:
            # Calculate what would be enriched
            to_enrich = [l for l in leads if l.get('linkedin_url') and (args.force_regenerate or l.get('linkedin_bio') is None)]
            if args.limit and args.limit > 0:
                to_enrich = to_enrich[:args.limit]
            print(f"DRY RUN: Would enrich {len(to_enrich)} leads")
            print(f"Estimated cost: ~{len(to_enrich)} credits")
            return 0

        # Enrich LinkedIn profiles
        leads = enrich_linkedin_profiles(
            leads,
            api_key,
            force_regenerate=args.force_regenerate,
            limit=args.limit if args.limit > 0 else None
        )

        # Save enriched leads
        os.makedirs(args.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{args.output_prefix}_{timestamp}_{len(leads)}leads.json"
        filepath = os.path.join(args.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(leads, f, indent=2, ensure_ascii=False)

        print(f"\nEnriched leads saved to: {filepath}")
        print(filepath)  # Print filepath to stdout for caller

        return 0

    except FileNotFoundError:
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"Error enriching LinkedIn profiles: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

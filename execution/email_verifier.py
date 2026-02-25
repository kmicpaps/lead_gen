# [CLI] — run via: py execution/email_verifier.py --help
"""
Fast email verification using Lead Magic API with concurrent requests.
Rate limit: 1000 requests/minute (16.67/second)
Cost: Cheap (token-based, verification is inexpensive)

PERFORMANCE: Uses ThreadPoolExecutor for ~10x speed improvement
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
from utils import RateLimiter

# Load environment variables
load_dotenv()

# Rate limiting: 1000 req/min = ~16 req/second
# Use 15 req/second to be conservative
RATE_LIMIT = 15  # requests per second
MAX_WORKERS = 10  # concurrent threads

def verify_single_email(lead, api_key, rate_limiter):
    """
    Verify a single email using Lead Magic API.
    Returns: updated lead with email_status
    """
    email = lead.get('email')

    if not email or not email.strip():
        lead['email_status'] = 'missing'
        return lead

    base_url = "https://api.leadmagic.io"
    headers = {
        'X-API-Key': api_key,
        'Content-Type': 'application/json'
    }

    try:
        # Wait for rate limit
        rate_limiter.acquire()

        payload = {
            'email': email,
            'first_name': lead.get('first_name', ''),
            'last_name': lead.get('last_name', '')
        }

        response = requests.post(
            f"{base_url}/email-validate",
            json=payload,
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            lead['email_status'] = result.get('email_status') or result.get('status', 'unknown')
            lead['leadmagic_credits_used'] = result.get('credits_consumed', 0)

            if result.get('is_domain_catch_all'):
                lead['is_catch_all'] = True

        elif response.status_code == 429:
            # Rate limit hit - wait and retry once
            print(f"Rate limit hit for {email}, waiting...")
            time.sleep(5)
            response = requests.post(
                f"{base_url}/email-validate",
                json=payload,
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                lead['email_status'] = result.get('email_status') or result.get('status', 'unknown')
            else:
                lead['email_status'] = 'verification_failed'
        else:
            lead['email_status'] = 'verification_failed'

    except Exception as e:
        print(f"Error verifying {email}: {e}", file=sys.stderr)
        lead['email_status'] = 'verification_error'

    return lead

def verify_emails_concurrent(leads, api_key):
    """
    Verify emails concurrently using ThreadPoolExecutor.
    Much faster than sequential processing.
    """
    emails_to_verify = [lead for lead in leads if lead.get('email')]

    if not emails_to_verify:
        print("No emails to verify")
        for lead in leads:
            lead['email_status'] = 'missing'
        return leads

    print(f"\nVerifying {len(emails_to_verify)} emails with {MAX_WORKERS} concurrent workers...")
    print(f"Estimated time: ~{len(emails_to_verify) / RATE_LIMIT:.1f} seconds")

    rate_limiter = RateLimiter(RATE_LIMIT)
    verified_count = 0

    # Create a mapping to preserve order
    email_to_lead = {id(lead): lead for lead in leads}

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all verification tasks
        future_to_lead = {
            executor.submit(verify_single_email, lead, api_key, rate_limiter): id(lead)
            for lead in emails_to_verify
        }

        # Process completed tasks
        for future in as_completed(future_to_lead):
            verified_count += 1
            lead_id = future_to_lead[future]

            try:
                updated_lead = future.result()
                email_to_lead[lead_id] = updated_lead

                if verified_count % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = verified_count / elapsed
                    print(f"  Verified {verified_count}/{len(emails_to_verify)} ({rate:.1f}/sec)")

            except Exception as e:
                print(f"Error in future: {e}", file=sys.stderr)

    elapsed_time = time.time() - start_time
    actual_rate = len(emails_to_verify) / elapsed_time
    print(f"\nCompleted in {elapsed_time:.1f}s ({actual_rate:.1f} emails/sec)")

    return leads

def main():
    parser = argparse.ArgumentParser(description='Fast email verification using Lead Magic API')
    parser.add_argument('--input', required=True, help='Path to leads JSON file')
    parser.add_argument('--output-dir', default='.tmp/verified', help='Output directory')
    parser.add_argument('--output-prefix', default='verified_leads', help='Output file prefix')

    args = parser.parse_args()

    api_key = os.getenv('LeadMagic-X-API-Key')
    if not api_key:
        print("Error: LeadMagic-X-API-Key not found in .env", file=sys.stderr)
        return 1

    try:
        # Load leads
        with open(args.input, 'r', encoding='utf-8') as f:
            leads = json.load(f)

        if not leads:
            print("No leads to verify", file=sys.stderr)
            return 1

        print(f"Loaded {len(leads)} leads")

        # Count how many have emails
        emails_count = len([lead for lead in leads if lead.get('email')])
        print(f"Emails to verify: {emails_count}")
        print(f"Leads without emails: {len(leads) - emails_count}")

        if emails_count == 0:
            print("No emails to verify. Skipping verification step.")
            for lead in leads:
                lead['email_status'] = 'missing'
        else:
            # Verify emails concurrently
            leads = verify_emails_concurrent(leads, api_key)

        # Count verification results
        status_counts = {}
        for lead in leads:
            status = lead.get('email_status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        print("\nVerification Results:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count} ({count/len(leads)*100:.1f}%)")

        # Save verified leads
        os.makedirs(args.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{args.output_prefix}_{timestamp}_{len(leads)}leads.json"
        filepath = os.path.join(args.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(leads, f, indent=2, ensure_ascii=False)

        print(f"\nVerified leads saved to: {filepath}")
        print(filepath)  # Print filepath to stdout for caller

        return 0

    except Exception as e:
        print(f"Error verifying emails: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

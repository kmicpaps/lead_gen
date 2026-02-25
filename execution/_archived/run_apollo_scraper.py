"""
Script to run RapidAPI Scraper (Apollo Data Source).
Accepts an Apollo search URL and APOLLO_COOKIE to scrape leads.
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def normalize_lead_to_schema(lead):
    """
    Normalize Apollo lead data to standardized schema.
    Output fields: first_name, last_name, name, organization_phone, linkedin_url,
                   title, email_status, email, city, country, org_name, website_url
    """
    return {
        'first_name': lead.get('first_name', ''),
        'last_name': lead.get('last_name', ''),
        'name': lead.get('name') or f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
        'organization_phone': lead.get('organization_phone') or lead.get('phone', ''),
        'linkedin_url': lead.get('linkedin_url', ''),
        'title': lead.get('title', ''),
        'email_status': lead.get('email_status', 'unknown'),  # Will be updated by Lead Magic
        'email': lead.get('email', ''),
        'city': lead.get('city', ''),
        'country': lead.get('country', ''),
        'org_name': lead.get('organization_name') or lead.get('organization', ''),
        'website_url': lead.get('website_url') or lead.get('organization_website_url', ''),
        'source': 'apollo'
    }

def main():
    parser = argparse.ArgumentParser(description='Run RapidAPI Scraper (Apollo Data Source)')
    parser.add_argument('--apollo-url', required=True, help='Apollo search URL')
    parser.add_argument('--max-leads', type=int, default=5000, help='Maximum leads to scrape (target, not guaranteed)')
    parser.add_argument('--output-dir', default='.tmp/apollo_run', help='Output directory')
    parser.add_argument('--output-prefix', default='apollo_leads', help='Output file prefix')

    args = parser.parse_args()

    # Get API credentials from environment
    rapidapi_key = os.getenv('x-rapidapi-key')
    rapidapi_host = os.getenv('x-rapidapi-host')

    if not rapidapi_key:
        print("Error: x-rapidapi-key not found in .env", file=sys.stderr)
        return 1
    if not rapidapi_host:
        print("Error: x-rapidapi-host not found in .env", file=sys.stderr)
        return 1

    # Load Apollo cookie from .env (it's in JSON format, not a simple key=value)
    # Read the .env file directly and extract the JSON cookie
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
        print(f"Starting RapidAPI Scraper (Apollo Data Source)...")
        print(f"Target leads: {args.max_leads} (actual count may vary based on filters)")
        print(f"Apollo URL: {args.apollo_url}")

        headers = {
            'x-rapidapi-key': rapidapi_key,
            'x-rapidapi-host': rapidapi_host,
            'Content-Type': 'application/json'
        }

        # Step 1: Start the scraping job
        print("Step 1: Starting scraping job...")
        start_url = f"https://{rapidapi_host}/start"

        payload = {
            'url': args.apollo_url,
            'totalResults': args.max_leads,
            'includeEmails': True,
            'cookies': [apollo_cookie]  # Nested array format required
        }

        response = requests.post(start_url, json=payload, headers=headers, timeout=60)

        if response.status_code != 200:
            print(f"Error: Failed to start job - status {response.status_code}", file=sys.stderr)
            print(f"Response: {response.text}", file=sys.stderr)
            return 1

        start_result = response.json()
        run_id = start_result.get('runId')

        if not run_id:
            print(f"Error: No runId in response: {start_result}", file=sys.stderr)
            return 1

        print(f"Job started with runId: {run_id}")

        # Step 2: Poll for completion
        print("Step 2: Waiting for scraping to complete...")
        status_url = f"https://{rapidapi_host}/status/{run_id}"
        max_polls = 40  # 20 minutes max (30 second intervals)
        poll_count = 0

        while poll_count < max_polls:
            import time
            time.sleep(30)  # Wait 30 seconds between checks (matching n8n workflow)

            status_response = requests.get(status_url, headers=headers, timeout=30)

            if status_response.status_code != 200:
                print(f"Warning: Status check failed: {status_response.status_code}")
                print(f"Response: {status_response.text}")
                poll_count += 1
                continue

            status_result = status_response.json()

            # Handle array response format
            if isinstance(status_result, list) and len(status_result) > 0:
                status_result = status_result[0]

            status = status_result.get('status')

            # Show progress data if available
            if 'data' in status_result:
                data = status_result['data']
                total_collected = data.get('total_collected', 0)
                total_duplicates = data.get('total_duplicates', 0)
                # Remove emojis and non-ASCII characters to avoid Windows encoding issues
                message = data.get('message', '').encode('ascii', errors='ignore').decode('ascii')
                extra_message = data.get('extraMessage', '').encode('ascii', errors='ignore').decode('ascii')
                print(f"  Status: {status} | Collected: {total_collected} | Duplicates: {total_duplicates} | {message}")
                if extra_message:
                    print(f"  Extra Info: {extra_message}")
            else:
                print(f"  Status: {status} ({poll_count * 30}s elapsed)")

            # Check for completion (lowercase 'completed' to match n8n workflow)
            if status == 'completed' or status == 'COMPLETED':
                print("Scraping completed successfully!")
                break
            elif status == 'FAILED' or status == 'failed':
                print(f"\n{'='*60}", file=sys.stderr)
                print("ERROR: RapidAPI Scraper job FAILED", file=sys.stderr)
                print(f"{'='*60}", file=sys.stderr)
                print(f"Full status response:", file=sys.stderr)
                print(json.dumps(status_result, indent=2), file=sys.stderr)
                print(f"{'='*60}", file=sys.stderr)
                return 1
            elif status == 'error':
                print(f"\n{'='*60}", file=sys.stderr)
                print("ERROR: RapidAPI Scraper encountered an error", file=sys.stderr)
                print(f"{'='*60}", file=sys.stderr)
                print(f"Full status response:", file=sys.stderr)
                print(json.dumps(status_result, indent=2), file=sys.stderr)
                print(f"{'='*60}", file=sys.stderr)
                return 1

            poll_count += 1

        if poll_count >= max_polls:
            print(f"\n{'='*60}", file=sys.stderr)
            print("ERROR: Scraping timed out after 20 minutes", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)
            print(f"Last status response:", file=sys.stderr)
            try:
                print(json.dumps(status_result, indent=2), file=sys.stderr)
            except:
                print("(no status available)", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)
            
            # Cancel the job on timeout
            cancel_job(run_id, headers, rapidapi_host)
            return 1

        # Step 3: Download results
        print("Step 3: Downloading results...")
        download_url = f"https://{rapidapi_host}/download/{run_id}"

        download_response = requests.get(download_url, headers=headers, timeout=120)

        if download_response.status_code != 200:
            print(f"Error: Failed to download results - status {download_response.status_code}", file=sys.stderr)
            print(f"Response: {download_response.text}", file=sys.stderr)
            return 1

        result = download_response.json()

        # Extract leads from response
        if 'leads' in result:
            leads = result['leads']
        elif 'data' in result:
            leads = result['data']
        elif isinstance(result, list):
            leads = result
        else:
            print(f"Unexpected response structure: {result.keys() if isinstance(result, dict) else type(result)}", file=sys.stderr)
            leads = []

        if not leads:
            print("Warning: No leads returned from RapidAPI Scraper", file=sys.stderr)
            print("This could mean:")
            print("  - Filters are too restrictive")
            print("  - Cookie expired")
            print("  - API issue")
            return 1

        # Normalize leads to standardized schema
        normalized_leads = [normalize_lead_to_schema(lead) for lead in leads]

        # Save results
        os.makedirs(args.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{args.output_prefix}_{timestamp}_{len(normalized_leads)}leads.json"
        filepath = os.path.join(args.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(normalized_leads, f, indent=2, ensure_ascii=False)

        print(f"Successfully scraped {len(normalized_leads)} leads from RapidAPI (Apollo Data).")
        print(f"Note: Requested {args.max_leads}, got {len(normalized_leads)} (filter compliance prioritized over quantity)")
        print(filepath)  # Print filepath to stdout for caller to capture

        return 0

    except KeyboardInterrupt:
        print("\nScraping interrupted by user.", file=sys.stderr)
        if 'run_id' in locals():
            cancel_job(run_id, headers, rapidapi_host)
        return 1
    except requests.Timeout:
        print("Error: Request timed out. Apollo scraping can take a while for large datasets.", file=sys.stderr)
        if 'run_id' in locals():
            cancel_job(run_id, headers, rapidapi_host)
        return 1
    except requests.RequestException as e:
        print(f"Error calling RapidAPI: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error running Apollo scraper: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

def cancel_job(run_id, headers, rapidapi_host):
    """
    Cancel a running scraping job.
    """
    print(f"Attempting to cancel job {run_id}...")
    cancel_url = f"https://{rapidapi_host}/cancel/{run_id}"
    try:
        response = requests.post(cancel_url, json={}, headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"Job {run_id} cancelled successfully.")
        else:
            print(f"Failed to cancel job {run_id}. Status: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error cancelling job: {e}")

if __name__ == "__main__":
    sys.exit(main())

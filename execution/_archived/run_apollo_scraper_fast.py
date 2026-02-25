"""
FAST RapidAPI Scraper (Apollo Data Source) with optimized polling strategy.
Changes from original:
- Reduced polling interval from 30s to 10s
- Adaptive polling: starts fast, slows down if job takes longer
- Better progress tracking

PERFORMANCE: ~3x faster for typical scraping jobs
"""

import os
import sys
import json
import argparse
import requests
import time
from datetime import datetime

# Note: We manually load env vars to avoid load_dotenv() parsing errors with multiline JSON cookie
# The APOLLO_COOKIE is manually parsed from .env file (see lines ~66-107)
# Other env vars are accessed directly via os.getenv() (they should be set in environment or .env)

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
    parser = argparse.ArgumentParser(description='FAST RapidAPI Scraper (Apollo Data Source) with optimized polling')
    parser.add_argument('--apollo-url', required=True, help='Apollo search URL')
    parser.add_argument('--max-leads', type=int, default=5000, help='Maximum leads to scrape (target, not guaranteed)')
    parser.add_argument('--output-dir', default='.tmp/apollo_run', help='Output directory')
    parser.add_argument('--output-prefix', default='apollo_leads', help='Output file prefix')

    args = parser.parse_args()

    # Manually load all required env vars from .env file
    # (Avoiding load_dotenv() to prevent parsing errors with multiline JSON cookie)
    rapidapi_key = None
    rapidapi_host = None
    apollo_cookie = None

    try:
        with open('.env', 'r', encoding='utf-8') as f:
            env_content = f.read()

        # Parse simple key=value pairs for RapidAPI credentials
        import re
        for line in env_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                if line.startswith('x-rapidapi-key='):
                    rapidapi_key = line.split('=', 1)[1].strip()
                elif line.startswith('x-rapidapi-host='):
                    rapidapi_host = line.split('=', 1)[1].strip()

        # Validate required credentials
        if not rapidapi_key:
            print("Error: x-rapidapi-key not found in .env", file=sys.stderr)
            return 1
        if not rapidapi_host:
            print("Error: x-rapidapi-host not found in .env", file=sys.stderr)
            return 1

        # Find APOLLO_COOKIE=[...] in the file
        # Need to match the complete JSON array, not just to the first ]
        # Match from APOLLO_COOKIE=[ to the last ] on its own line
        # Use (?:^|\n) to ensure we match start of line
        match = re.search(r'(?:^|\n)APOLLO_COOKIE=(\[.*?\n\])', env_content, re.DOTALL | re.MULTILINE)
        if match:
            apollo_cookie_str = match.group(1)

            # Browser-exported cookies may have formatting variations
            # Try standard JSON parsing first
            try:
                apollo_cookie = json.loads(apollo_cookie_str)
            except json.JSONDecodeError:
                # If standard parsing fails, try fixing common issues:
                # 1. Replace single quotes with double quotes
                # 2. Handle potential whitespace/newline issues
                fixed_str = apollo_cookie_str.replace("'", '"')
                try:
                    apollo_cookie = json.loads(fixed_str)
                except json.JSONDecodeError as e:
                    # If still failing, try ast.literal_eval as fallback for Python literals
                    import ast
                    try:
                        apollo_cookie = ast.literal_eval(apollo_cookie_str)
                    except Exception:
                        # Last resort: Try json5 or relaxed JSON parsing
                        # This handles trailing commas, comments, etc.
                        try:
                            import json5
                            apollo_cookie = json5.loads(apollo_cookie_str)
                        except:
                            print(f"Error: Could not parse APOLLO_COOKIE. JSON error: {e}", file=sys.stderr)
                            print(f"Cookie string length: {len(apollo_cookie_str)}", file=sys.stderr)
                            print(f"First 200 chars: {apollo_cookie_str[:200]}", file=sys.stderr)
                            print("Please ensure APOLLO_COOKIE is valid JSON array format.", file=sys.stderr)
                            return 1
        else:
            print("Error: APOLLO_COOKIE not found in .env", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error loading APOLLO_COOKIE from .env: {e}", file=sys.stderr)
        return 1

    try:
        print(f"Starting FAST RapidAPI Scraper (Apollo Data Source)...")
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
            'cookies': [apollo_cookie]  # apollo_cookie is already an array, wrap it once more
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

        # Step 2: Adaptive polling for completion
        print("Step 2: Waiting for scraping to complete (adaptive polling)...")
        status_url = f"https://{rapidapi_host}/status/{run_id}"

        # Adaptive polling strategy:
        # - First 5 polls: 10 seconds (fast for small jobs)
        # - Next 10 polls: 15 seconds (medium for typical jobs)
        # - Remaining polls: 30 seconds (conservative for large jobs)
        max_polls = 60  # 30 minutes max total
        poll_count = 0
        start_time = time.time()

        while poll_count < max_polls:
            # Adaptive interval
            if poll_count < 5:
                interval = 10  # Fast start
            elif poll_count < 15:
                interval = 15  # Medium
            else:
                interval = 30  # Conservative for long jobs

            time.sleep(interval)

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
            elapsed = time.time() - start_time
            if 'data' in status_result:
                data = status_result['data']
                total_collected = data.get('total_collected', 0)
                total_duplicates = data.get('total_duplicates', 0)
                # Remove emojis and non-ASCII characters to avoid Windows encoding issues
                message = data.get('message', '').encode('ascii', errors='ignore').decode('ascii')
                extra_message = data.get('extraMessage', '').encode('ascii', errors='ignore').decode('ascii')
                print(f"  [{int(elapsed)}s] Status: {status} | Collected: {total_collected} | Duplicates: {total_duplicates} | {message}")
                if extra_message:
                    print(f"  Extra Info: {extra_message}")
            else:
                print(f"  [{int(elapsed)}s] Status: {status} (poll #{poll_count + 1})")

            # Check for completion (lowercase 'completed' to match n8n workflow)
            if status == 'completed' or status == 'COMPLETED':
                print(f"Scraping completed successfully in {int(elapsed)}s!")
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
            print("ERROR: Scraping timed out after 30 minutes", file=sys.stderr)
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

        total_time = time.time() - start_time
        print(f"Successfully scraped {len(normalized_leads)} leads from RapidAPI (Apollo Data) in {int(total_time)}s.")
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

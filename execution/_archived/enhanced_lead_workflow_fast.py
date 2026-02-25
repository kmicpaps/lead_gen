"""
Enhanced Multi-Source Lead Generation Workflow with PARALLEL SCRAPING
Orchestrates the entire lead generation pipeline:
1. Scrape from Apollo AND Apify IN PARALLEL - tries RapidAPI Apollo with FAST polling
2. Merge and deduplicate
3. Verify all emails (FAST concurrent version)
4. Enrich missing emails (FAST concurrent version)
5. Export to Google Sheets
6. Generate quality report

PERFORMANCE: Scraping runs in parallel for ~2x speed improvement
"""

import os
import sys
import subprocess
import argparse
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Determine Python executable
PYTHON_EXE = sys.executable

def run_command(cmd, step_name):
    """Run a command and return the output file path (last line of stdout)."""
    print(f"\n{'='*60}")
    print(f"STEP: {step_name}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR in {step_name}:")
        print(result.stderr)
        return None

    # Extract file path from last line of stdout
    output_lines = result.stdout.strip().split('\n')
    filepath = output_lines[-1] if output_lines else None

    return filepath

def run_rapidapi_scraper(rapidapi_url, rapidapi_max):
    """Run RapidAPI scraper (Apollo data source) in a separate thread."""
    print(f"\n[PARALLEL] Starting RapidAPI scraper...")

    # Try FAST RapidAPI Apollo scraper first
    cmd = [
        PYTHON_EXE, "execution/run_apollo_scraper_fast.py",
        "--apollo-url", rapidapi_url,
        "--max-leads", str(rapidapi_max)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[PARALLEL] RapidAPI scraper (FAST) failed. Trying Apify Apollo scraper fallback...")

        # Fallback to Apify Apollo scraper
        cmd = [
            PYTHON_EXE, "execution/run_apify_apollo_scraper.py",
            "--apollo-url", rapidapi_url,
            "--max-leads", str(rapidapi_max)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"[PARALLEL] Both RapidAPI/Apollo scrapers failed.")
            return None

    # Extract file path from last line of stdout
    output_lines = result.stdout.strip().split('\n')
    filepath = output_lines[-1] if output_lines else None

    if filepath:
        print(f"[PARALLEL] RapidAPI scraper completed: {filepath}")

    return filepath

def validate_leads(leads_file, keywords, threshold=0.8):
    """
    Validate that leads match target criteria.
    Returns: (is_valid, match_percentage, details_str)
    """
    if not leads_file or not os.path.exists(leads_file):
        return False, 0.0, "File not found"

    try:
        with open(leads_file, 'r', encoding='utf-8') as f:
            leads = json.load(f)
    except Exception as e:
        return False, 0.0, f"Error reading file: {e}"

    if not leads:
        return False, 0.0, "No leads to validate"

    if not keywords:
        return True, 1.0, "No validation keywords provided"

    keyword_list = [k.strip().lower() for k in keywords.split(',')]
    matches = 0
    total = len(leads)

    for lead in leads:
        # Check fields: title, org_name, industry (if available)
        # Note: Standard schema uses 'title', 'org_name'. 
        # Raw Apify/Apollo data might have different fields, but we check what we can.
        
        text_to_check = []
        if lead.get('title'): text_to_check.append(str(lead.get('title')))
        if lead.get('org_name'): text_to_check.append(str(lead.get('org_name')))
        if lead.get('industry'): text_to_check.append(str(lead.get('industry')))
        if lead.get('keywords'): text_to_check.append(str(lead.get('keywords'))) # Apollo sometimes has keywords
        
        combined_text = " ".join(text_to_check).lower()
        
        if any(k in combined_text for k in keyword_list):
            matches += 1

    match_rate = matches / total if total > 0 else 0
    is_valid = match_rate >= threshold
    
    details = f"{matches}/{total} leads matched keywords ({match_rate*100:.1f}%)"
    return is_valid, match_rate, details

def run_apify_scraper(apify_max, apify_args):
    """Run Apify scraper in a separate thread."""
    print(f"\n[PARALLEL] Starting Apify scraper...")

    cmd = [
        PYTHON_EXE, "execution/run_apify_scraper_v2.py",
        "--fetch-count", str(apify_max)
    ]
    
    # Add optional arguments if present in the dictionary
    arg_mapping = {
        'industry': '--industry',
        'job_titles': '--job-title',
        'excluded_job_titles': '--excluded-job-title',
        'seniority': '--seniority',
        'functional_level': '--functional-level',
        'location': '--location',
        'city': '--city',
        'excluded_location': '--excluded-location',
        'excluded_city': '--excluded-city',
        'excluded_industry': '--excluded-industry',
        'company_keywords': '--company-keywords',
        'excluded_company_keywords': '--excluded-company-keywords',
        'company_size': '--company-size',
        'company_domain': '--company-domain',
        'min_revenue': '--min-revenue',
        'max_revenue': '--max-revenue',
        'funding': '--funding',
        'email_status': '--email-status'
    }

    for key, flag in arg_mapping.items():
        if apify_args.get(key):
            cmd.extend([flag, apify_args[key]])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[PARALLEL] Apify scraper failed.")
        print(result.stderr)
        return None

    # Extract file path from last line of stdout
    output_lines = result.stdout.strip().split('\n')
    filepath = output_lines[-1] if output_lines else None

    if filepath:
        print(f"[PARALLEL] Apify scraper completed: {filepath}")

    return filepath

# ... (rest of file) ...

def main():
    parser = argparse.ArgumentParser(description='Enhanced Lead Generation Workflow with PARALLEL SCRAPING')
    
    # RapidAPI Args
    parser.add_argument('--rapidapi-url', help='RapidAPI (Apollo) search URL')
    parser.add_argument('--rapidapi-max', type=int, help='RapidAPI target leads (REQUIRED if using RapidAPI)')
    
    # Apify Args
    parser.add_argument('--apify-max', type=int, help='Apify target leads (REQUIRED if using Apify)')
    parser.add_argument('--apify-industry', help='Include industries (comma-separated)')
    parser.add_argument('--apify-excluded-industry', help='Exclude industries')
    parser.add_argument('--apify-job-titles', help='Include job titles (comma-separated)')
    parser.add_argument('--apify-excluded-job-titles', help='Exclude job titles')
    parser.add_argument('--apify-seniority', help='Seniority level (e.g., Owner, C-Level)')
    parser.add_argument('--apify-functional-level', help='Functional level (e.g., Marketing, Sales)')
    parser.add_argument('--apify-location', help='Region/Country/State')
    parser.add_argument('--apify-city', help='Specific cities')
    parser.add_argument('--apify-excluded-location', help='Exclude Region/Country/State')
    parser.add_argument('--apify-excluded-city', help='Exclude cities')
    parser.add_argument('--apify-company-keywords', help='Include company keywords')
    parser.add_argument('--apify-excluded-company-keywords', help='Exclude company keywords')
    parser.add_argument('--apify-company-size', help='Company size range')
    parser.add_argument('--apify-company-domain', help='Specific company domains')
    parser.add_argument('--apify-min-revenue', help='Min revenue')
    parser.add_argument('--apify-max-revenue', help='Max revenue')
    parser.add_argument('--apify-funding', help='Funding type')
    parser.add_argument('--apify-email-status', help='Email status (default: validated)')

    # General Args
    parser.add_argument('--skip-rapidapi', action='store_true', help='Skip RapidAPI scraping')
    parser.add_argument('--skip-apify', action='store_true', help='Skip Apify scraping')
    parser.add_argument('--skip-enrichment', action='store_true', help='Skip email enrichment (saves credits)')
    parser.add_argument('--validation-keywords', help='Comma-separated keywords for validation')
    parser.add_argument('--validation-threshold', type=float, default=0.8, help='Validation threshold (0.0-1.0)')
    parser.add_argument('--sheet-title', help='Custom Google Sheet title')

    args = parser.parse_args()

    # Validate required arguments
    if not args.skip_rapidapi and not args.rapidapi_max:
        print("Error: --rapidapi-max is required unless --skip-rapidapi is set", file=sys.stderr)
        return 1
    if not args.skip_apify and not args.apify_max:
        print("Error: --apify-max is required unless --skip-apify is set", file=sys.stderr)
        return 1

    apollo_file = None
    apify_file = None

    # Collect Apify args into a dictionary
    apify_args = {
        'industry': args.apify_industry,
        'excluded_industry': args.apify_excluded_industry,
        'job_titles': args.apify_job_titles,
        'excluded_job_titles': args.apify_excluded_job_titles,
        'seniority': args.apify_seniority,
        'functional_level': args.apify_functional_level,
        'location': args.apify_location,
        'city': args.apify_city,
        'excluded_location': args.apify_excluded_location,
        'excluded_city': args.apify_excluded_city,
        'company_keywords': args.apify_company_keywords,
        'excluded_company_keywords': args.apify_excluded_company_keywords,
        'company_size': args.apify_company_size,
        'company_domain': args.apify_company_domain,
        'min_revenue': args.apify_min_revenue,
        'max_revenue': args.apify_max_revenue,
        'funding': args.apify_funding,
        'email_status': args.apify_email_status
    }

    # --- STEP 1: TEST RUN & VALIDATION ---
    if args.validation_keywords:
        print(f"\n{'='*60}")
        print("STEP: TEST RUN & VALIDATION")
        print(f"{'='*60}")
        print(f"Validation Keywords: {args.validation_keywords}")
        print(f"Threshold: {args.validation_threshold*100}%")

        test_leads_count = 25
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            
            if not args.skip_rapidapi:
                print("Starting Test Scrape: RapidAPI...")
                futures.append(('rapidapi', executor.submit(run_rapidapi_scraper, args.rapidapi_url, test_leads_count)))
            
            if not args.skip_apify:
                print("Starting Test Scrape: Apify...")
                futures.append(('apify', executor.submit(
                    run_apify_scraper, test_leads_count, apify_args
                )))
            
            # Check results
            validation_passed = True
            for name, future in futures:
                try:
                    test_file = future.result()
                    if test_file:
                        is_valid, rate, details = validate_leads(test_file, args.validation_keywords, args.validation_threshold)
                        print(f"[{name.upper()}] Validation: {details}")
                        if not is_valid:
                            print(f"❌ [{name.upper()}] FAILED validation (<{args.validation_threshold*100}%)")
                            validation_passed = False
                        else:
                            print(f"✅ [{name.upper()}] PASSED validation")
                    else:
                        print(f"⚠️ [{name.upper()}] Test scrape returned no file")
                except Exception as e:
                    print(f"Error in test run for {name}: {e}")
            
            if not validation_passed:
                print("\n❌ VALIDATION FAILED. Aborting full run to save credits.")
                print("Please adjust your filters or keywords and try again.")
                return 1
            
            print("\n✅ VALIDATION SUCCESSFUL. Proceeding to full run...")

    # --- STEP 2: FULL PARALLEL SCRAPING ---
    print(f"\n{'='*60}")
    print("STEP: FULL PARALLEL SCRAPING")
    print(f"{'='*60}")

    start_time = datetime.now()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []

        # Submit RapidAPI scraper if not skipped
        if not args.skip_rapidapi:
            if not args.rapidapi_url:
                print("Error: --rapidapi-url required unless --skip-rapidapi is set", file=sys.stderr)
                return 1

            apollo_future = executor.submit(run_rapidapi_scraper, args.rapidapi_url, args.rapidapi_max)
            futures.append(('apollo', apollo_future))

        # Submit Apify scraper if not skipped
        if not args.skip_apify:
            apify_future = executor.submit(
                run_apify_scraper,
                args.apify_max,
                apify_args
            )
            futures.append(('apify', apify_future))

        # Wait for all scrapers to complete
        for name, future in futures:
            try:
                result = future.result()
                if name == 'apollo':
                    apollo_file = result
                elif name == 'apify':
                    apify_file = result
            except Exception as e:
                print(f"Error in {name} scraper: {e}", file=sys.stderr)

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    print(f"\n{'='*60}")
    print(f"PARALLEL SCRAPING COMPLETED in {int(elapsed)}s")
    print(f"{'='*60}")
    print(f"RapidAPI: {'SUCCESS' if apollo_file else 'FAILED'}")
    print(f"Apify:    {'SUCCESS' if apify_file else 'FAILED'}")

    # Ensure we have at least one source
    if not apollo_file and not apify_file:
        print("ERROR: No leads scraped from any source.", file=sys.stderr)
        return 1

    # Step 3: Merge & Deduplicate
    cmd = [PYTHON_EXE, "execution/merge_deduplicate_leads.py"]
    if apollo_file:
        cmd.extend(["--apollo-file", apollo_file])
    if apify_file:
        cmd.extend(["--apify-file", apify_file])

    merged_file = run_command(cmd, "Merge & Deduplicate")
    if not merged_file:
        print("ERROR: Merge failed.", file=sys.stderr)
        return 1

    # Step 4: Verify Emails (FAST version with concurrent processing)
    cmd = [
        PYTHON_EXE, "execution/verify_emails_leadmagic_fast.py",
        "--input", merged_file
    ]
    verified_file = run_command(cmd, "Email Verification (Lead Magic - FAST)")
    if not verified_file:
        print("ERROR: Email verification failed.", file=sys.stderr)
        return 1

    # Step 5: Enrich Missing Emails (FAST version with concurrent processing)
    cmd = [
        PYTHON_EXE, "execution/enrich_emails_leadmagic_fast.py",
        "--input", verified_file
    ]
    if args.skip_enrichment:
        cmd.append("--skip-enrichment")

    enriched_file = run_command(cmd, "Email Enrichment (Lead Magic - FAST)")
    if not enriched_file:
        print("ERROR: Email enrichment failed.", file=sys.stderr)
        return 1

    # Step 6: Export to Google Sheets
    if not args.sheet_title:
        timestamp = datetime.now().strftime("%Y-%m-%d")
        args.sheet_title = f"Enhanced Lead Generation - {timestamp}"

    cmd = [
        PYTHON_EXE, "execution/upload_to_google_sheet.py",
        "--input", enriched_file,
        "--sheet-title", args.sheet_title
    ]
    print(f"\n{'='*60}")
    print("STEP: Export to Google Sheets")
    print(f"{'='*60}")
    subprocess.run(cmd)

    # Step 7: Generate Quality Report
    generate_quality_report(apollo_file, apify_file, merged_file, verified_file, enriched_file, enriched_file)

    print(f"\n{'='*60}")
    print("WORKFLOW COMPLETE!")
    print(f"{'='*60}")
    print(f"\nFinal output: {enriched_file}")
    print("Check Google Sheets link above for your deliverable.")

    return 0

if __name__ == "__main__":
    sys.exit(main())

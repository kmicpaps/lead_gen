"""
Enhanced Multi-Source Lead Generation Workflow
Orchestrates the entire lead generation pipeline:
1. Scrape from Apollo (5000 target) - tries RapidAPI first, falls back to Apify Apollo scraper
2. Scrape from Apify leads-finder (2000 target) - always runs to supplement Apollo
3. Merge and deduplicate
4. Verify all emails
5. Enrich missing emails
6. Export to Google Sheets
7. Generate quality report
"""

import os
import sys
import subprocess
import argparse
import json
from datetime import datetime

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
        text_to_check = []
        if lead.get('title'): text_to_check.append(str(lead.get('title')))
        if lead.get('org_name'): text_to_check.append(str(lead.get('org_name')))
        if lead.get('industry'): text_to_check.append(str(lead.get('industry')))
        if lead.get('keywords'): text_to_check.append(str(lead.get('keywords')))
        
        combined_text = " ".join(text_to_check).lower()
        
        if any(k in combined_text for k in keyword_list):
            matches += 1

    match_rate = matches / total if total > 0 else 0
    is_valid = match_rate >= threshold
    
    details = f"{matches}/{total} leads matched keywords ({match_rate*100:.1f}%)"
    return is_valid, match_rate, details

def generate_quality_report(apollo_file, apify_file, merged_file, verified_file, enriched_file, final_file):
    """Generate a comprehensive quality report."""
    print(f"\n{'='*60}")
    print("QUALITY REPORT")
    print(f"{'='*60}\n")

    try:
        # Load data from each stage
        apollo_leads = json.load(open(apollo_file, 'r', encoding='utf-8')) if apollo_file and os.path.exists(apollo_file) else []
        apify_leads = json.load(open(apify_file, 'r', encoding='utf-8')) if apify_file and os.path.exists(apify_file) else []
        merged_leads = json.load(open(merged_file, 'r', encoding='utf-8')) if merged_file and os.path.exists(merged_file) else []
        final_leads = json.load(open(final_file, 'r', encoding='utf-8')) if final_file and os.path.exists(final_file) else []

        # Calculate statistics
        total_raw = len(apollo_leads) + len(apify_leads)
        duplicates = total_raw - len(merged_leads)

        # Email status breakdown
        email_status_counts = {}
        for lead in final_leads:
            status = lead.get('email_status', 'unknown')
            email_status_counts[status] = email_status_counts.get(status, 0) + 1

        # Enrichment statistics
        enriched_count = sum(1 for lead in final_leads if lead.get('email_source') == 'leadmagic_enrichment')

        # Valid emails (deliverable)
        valid_statuses = ['valid', 'verified']
        valid_email_count = sum(email_status_counts.get(status, 0) for status in valid_statuses)

        # Source breakdown
        apollo_only = sum(1 for lead in final_leads if lead.get('source') == 'apollo')
        apify_only = sum(1 for lead in final_leads if lead.get('source') == 'apify')
        both_sources = sum(1 for lead in final_leads if ',' in lead.get('source', ''))

        # Print report
        print("LEAD ACQUISITION:")
        print(f"  Apollo leads:           {len(apollo_leads):>6}")
        print(f"  Apify leads:            {len(apify_leads):>6}")
        print(f"  Raw total:              {total_raw:>6}")
        print()
        print("DEDUPLICATION:")
        print(f"  Duplicates removed:     {duplicates:>6} ({duplicates/total_raw*100 if total_raw > 0 else 0:.1f}%)")
        print(f"  Unique leads:           {len(merged_leads):>6}")
        print()
        print("EMAIL QUALITY:")
        for status, count in sorted(email_status_counts.items()):
            print(f"  {status.capitalize():<20} {count:>6} ({count/len(final_leads)*100:.1f}%)")
        print()
        print("EMAIL ENRICHMENT:")
        print(f"  Emails found:           {enriched_count:>6}")
        print()
        print("FINAL OUTPUT:")
        print(f"  Total deliverable:      {valid_email_count:>6} leads with valid emails")
        print(f"  Apollo only:            {apollo_only:>6}")
        print(f"  Apify only:             {apify_only:>6}")
        print(f"  Both sources:           {both_sources:>6}")
        print()

        # Save report to file
        report_path = os.path.join(".tmp", f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(report_path, 'w') as f:
            f.write(f"Lead Generation Quality Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*60}\n\n")
            f.write(f"Apollo leads: {len(apollo_leads)}\n")
            f.write(f"Apify leads: {len(apify_leads)}\n")
            f.write(f"Duplicates removed: {duplicates}\n")
            f.write(f"Unique leads: {len(merged_leads)}\n")
            f.write(f"Valid emails: {valid_email_count}\n")
            f.write(f"Enriched emails: {enriched_count}\n")

        print(f"Report saved to: {report_path}\n")

    except Exception as e:
        print(f"Error generating report: {e}")

def main():
    parser = argparse.ArgumentParser(description='Enhanced Lead Generation Workflow')
    
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

    # Helper to build Apify command
    def build_apify_cmd(fetch_count):
        cmd = [
            PYTHON_EXE, "execution/run_apify_scraper_v2.py",
            "--fetch-count", str(fetch_count)
        ]
        
        arg_mapping = {
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
        
        flag_mapping = {
            'industry': '--industry',
            'excluded_industry': '--excluded-industry',
            'job_titles': '--job-title',
            'excluded_job_titles': '--excluded-job-title',
            'seniority': '--seniority',
            'functional_level': '--functional-level',
            'location': '--location',
            'city': '--city',
            'excluded_location': '--excluded-location',
            'excluded_city': '--excluded-city',
            'company_keywords': '--company-keywords',
            'excluded_company_keywords': '--excluded-company-keywords',
            'company_size': '--company-size',
            'company_domain': '--company-domain',
            'min_revenue': '--min-revenue',
            'max_revenue': '--max-revenue',
            'funding': '--funding',
            'email_status': '--email-status'
        }

        for key, value in arg_mapping.items():
            if value:
                cmd.extend([flag_mapping[key], value])
        
        return cmd

    # --- STEP 1: TEST RUN & VALIDATION ---
    if args.validation_keywords:
        print(f"\n{'='*60}")
        print("STEP: TEST RUN & VALIDATION")
        print(f"{'='*60}")
        print(f"Validation Keywords: {args.validation_keywords}")
        print(f"Threshold: {args.validation_threshold*100}%")

        test_leads_count = 25
        validation_passed = True
        
        # Test RapidAPI
        if not args.skip_rapidapi:
            print("Starting Test Scrape: RapidAPI...")
            cmd = [
                PYTHON_EXE, "execution/run_apollo_scraper.py",
                "--apollo-url", args.rapidapi_url,
                "--max-leads", str(test_leads_count)
            ]
            test_file = run_command(cmd, "Test RapidAPI Scrape")
            
            if test_file:
                is_valid, rate, details = validate_leads(test_file, args.validation_keywords, args.validation_threshold)
                print(f"[RAPIDAPI] Validation: {details}")
                if not is_valid:
                    print(f"❌ [RAPIDAPI] FAILED validation (<{args.validation_threshold*100}%)")
                    validation_passed = False
                else:
                    print(f"✅ [RAPIDAPI] PASSED validation")
            else:
                print(f"⚠️ [RAPIDAPI] Test scrape returned no file")

        # Test Apify
        if not args.skip_apify:
            print("Starting Test Scrape: Apify...")
            cmd = build_apify_cmd(test_leads_count)
            
            test_file = run_command(cmd, "Test Apify Scrape")
            
            if test_file:
                is_valid, rate, details = validate_leads(test_file, args.validation_keywords, args.validation_threshold)
                print(f"[APIFY] Validation: {details}")
                if not is_valid:
                    print(f"❌ [APIFY] FAILED validation (<{args.validation_threshold*100}%)")
                    validation_passed = False
                else:
                    print(f"✅ [APIFY] PASSED validation")
            else:
                print(f"⚠️ [APIFY] Test scrape returned no file")
        
        if not validation_passed:
            print("\n❌ VALIDATION FAILED. Aborting full run to save credits.")
            print("Please adjust your filters or keywords and try again.")
            return 1
        
        print("\n✅ VALIDATION SUCCESSFUL. Proceeding to full run...")

    # --- STEP 2: FULL SCRAPING ---
    
    # RapidAPI Scraper (with fallback)
    if not args.skip_rapidapi:
        if not args.rapidapi_url:
            print("Error: --rapidapi-url required unless --skip-rapidapi is set", file=sys.stderr)
            return 1

        # Try RapidAPI Apollo scraper first
        cmd = [
            PYTHON_EXE, "execution/run_apollo_scraper.py",
            "--apollo-url", args.rapidapi_url,
            "--max-leads", str(args.rapidapi_max)
        ]
        apollo_file = run_command(cmd, "RapidAPI Scraper (Apollo Data)")

        # If RapidAPI failed, try Apify Apollo scraper as fallback
        if not apollo_file:
            print("RapidAPI scraper failed. Trying Apify Apollo scraper fallback...")
            cmd = [
                PYTHON_EXE, "execution/run_apify_apollo_scraper.py",
                "--apollo-url", args.rapidapi_url,
                "--max-leads", str(args.rapidapi_max)
            ]
            apollo_file = run_command(cmd, "Apollo Scraper (Apify Fallback)")

            if not apollo_file:
                print("Both RapidAPI/Apollo scrapers failed. Continuing with leads-finder only...")

    # Apify Scraper
    if not args.skip_apify:
        cmd = build_apify_cmd(args.apify_max)

        apify_file = run_command(cmd, "Apify Scraper")
        if not apify_file:
            print("Apify scraping failed.")
            if not apollo_file:
                print("ERROR: Both scrapers failed. Exiting.")
                return 1

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

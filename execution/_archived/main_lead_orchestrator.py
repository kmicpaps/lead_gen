"""
Enhanced Multi-Source Lead Generation Workflow V2
MAJOR CHANGES:
- Simplified inputs: Only Apollo URL + target lead count
- Auto-derives Apify filters from Apollo URL
- Intelligent pre-validation with auto-troubleshooting
- Smart enrichment cost gate (500 lead threshold)
- User-friendly error messages

User provides:
1. Apollo URL (contains all filters)
2. Target lead count

Workflow:
1. Parse Apollo URL -> derive Apify filters
2. Pre-validation (25 leads from each source)
   - B2B Finder: Test + validate -> auto-troubleshoot if fails
   - Apify: Test + validate -> auto-optimize filters if <80% match
3. Full run (both scrapers target user's lead count)
4. Merge & deduplicate
5. Verify emails
6. Enrich emails (if <500 leads need it, auto-run; if >=500, ask user)
7. Export to Google Sheets
8. Generate quality report
"""

import os
import sys
import subprocess
import argparse
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Add execution directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from apollo_url_parser import parse_apollo_url, extract_validation_keywords
from apollo_to_apify_mapper import map_apollo_to_apify
from error_handler import (
    parse_apify_error,
    format_error_message, suggest_next_steps
)
from scraper_peakydev import run_peakydev_scraper

PYTHON_EXE = sys.executable


def run_command(cmd, step_name, capture_output=True):
    """Run a command and return the output file path (last line of stdout)."""
    print(f"\n{'='*60}")
    print(f"STEP: {step_name}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, capture_output=capture_output, text=True)

    if result.returncode != 0:
        print(f"ERROR in {step_name}:")
        if capture_output:
            print(result.stderr)
        return None, result

    # Extract file path from last line of stdout
    if capture_output:
        output_lines = result.stdout.strip().split('\n')
        filepath = output_lines[-1] if output_lines else None
    else:
        filepath = None

    return filepath, result


def validate_leads(leads_file, keywords, threshold=0.8):
    """
    Validate that leads match target criteria.
    Returns: (is_valid, match_percentage, details_str, mismatch_info)
    """
    if not leads_file or not os.path.exists(leads_file):
        return False, 0.0, "File not found", {}

    try:
        with open(leads_file, 'r', encoding='utf-8') as f:
            leads = json.load(f)
    except Exception as e:
        return False, 0.0, f"Error reading file: {e}", {}

    if not leads:
        return False, 0.0, "No leads to validate", {}

    if not keywords:
        return True, 1.0, "No validation keywords provided", {}

    keyword_list = [k.strip().lower() for k in keywords.split(',')]
    matches = 0
    total = len(leads)
    mismatch_examples = []

    for lead in leads:
        text_to_check = []
        if lead.get('title'): text_to_check.append(str(lead.get('title')))
        if lead.get('org_name'): text_to_check.append(str(lead.get('org_name')))
        if lead.get('industry'): text_to_check.append(str(lead.get('industry')))
        if lead.get('keywords'): text_to_check.append(str(lead.get('keywords')))

        combined_text = " ".join(text_to_check).lower()

        if any(k in combined_text for k in keyword_list):
            matches += 1
        elif len(mismatch_examples) < 3:
            # Keep a few examples of mismatches for debugging
            mismatch_examples.append({
                'title': lead.get('title'),
                'org_name': lead.get('org_name'),
                'industry': lead.get('industry')
            })

    match_rate = matches / total if total > 0 else 0
    is_valid = match_rate >= threshold

    details = f"{matches}/{total} leads matched keywords ({match_rate*100:.1f}%)"
    mismatch_info = {'examples': mismatch_examples, 'keyword_list': keyword_list}

    return is_valid, match_rate, details, mismatch_info


def run_b2b_finder_test(apollo_url, validation_keywords, max_attempts=3):
    """
    Run Apify B2B Leads Finder test scrape with auto-troubleshooting.
    Returns: (success, filepath, error_info)
    """
    print(f"\n{'='*60}")
    print("APIFY B2B LEADS FINDER TEST SCRAPE (25 leads)")
    print(f"{'='*60}")

    for attempt in range(1, max_attempts + 1):
        print(f"\nAttempt {attempt}/{max_attempts}...")

        cmd = [
            PYTHON_EXE, "execution/run_apify_b2b_leads_finder.py",
            "--apollo-url", apollo_url,
            "--max-leads", "25"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            # Extract file path
            output_lines = result.stdout.strip().split('\n')
            filepath = output_lines[-1] if output_lines else None

            if filepath and os.path.exists(filepath):
                print(f"[OK] B2B Leads Finder test scrape successful: {filepath}")

                # Validate leads
                is_valid, match_rate, details, mismatch_info = validate_leads(
                    filepath, validation_keywords, threshold=0.8
                )

                print(f"Validation: {details}")

                if is_valid:
                    print("[OK] B2B Leads Finder validation PASSED")
                    return True, filepath, None
                else:
                    print(f"[WARNING] B2B Leads Finder validation FAILED (attempt {attempt}/{max_attempts})")
                    print(f"Match rate: {match_rate*100:.1f}% (need >=80%)")

                    if attempt < max_attempts:
                        print("This suggests the scraper may not be extracting data correctly.")
                        print("Retrying...")
            else:
                print(f"[WARNING] No file returned from scraper (attempt {attempt}/{max_attempts})")
        else:
            print(f"[WARNING] B2B Leads Finder scraper failed (attempt {attempt}/{max_attempts})")
            print(f"Error: {result.stderr}")

            if attempt < max_attempts:
                wait_time = 10  # Apify handles retries internally, shorter wait
                print(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                print("Retrying...")

    # All attempts failed
    print(f"\n[FAIL] B2B Leads Finder scraper failed after {max_attempts} attempts")

    # Parse error for user-friendly message
    error_info = {'type': 'scraper_failure', 'details': result.stderr if 'result' in locals() else 'Unknown error'}
    print(format_error_message(error_info))

    return False, None, error_info


def run_apify_test(apify_payload, validation_keywords, max_attempts=5):
    """
    Run Apify test scrape with auto-optimization of filters.
    Returns: (success, filepath, final_payload)
    """
    print(f"\n{'='*60}")
    print("APIFY TEST SCRAPE (25 leads)")
    print(f"{'='*60}")

    current_payload = apify_payload.copy()
    broadening_level = 1

    for attempt in range(1, max_attempts + 1):
        print(f"\nAttempt {attempt}/{max_attempts} (Broadening level: {broadening_level})...")
        print(f"Current filters: {json.dumps(current_payload, indent=2)}")

        cmd = [
            PYTHON_EXE, "execution/run_apify_scraper_v2.py",
            "--fetch-count", "25"
        ]

        # Add payload arguments
        arg_mapping = {
            'industry': '--industry',
            'job_titles': '--job-title',
            'seniority': '--seniority',
            'functional_level': '--functional-level',
            'location': '--location',
            'city': '--city',
            'company_size': '--company-size',
            'min_revenue': '--min-revenue',
            'max_revenue': '--max-revenue',
            'funding': '--funding',
            'email_status': '--email-status'
        }

        for key, flag in arg_mapping.items():
            if current_payload.get(key):
                cmd.extend([flag, current_payload[key]])

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            # Extract file path
            output_lines = result.stdout.strip().split('\n')
            filepath = output_lines[-1] if output_lines else None

            if filepath and os.path.exists(filepath):
                print(f"[OK] Apify test scrape successful: {filepath}")

                # Validate leads
                is_valid, match_rate, details, mismatch_info = validate_leads(
                    filepath, validation_keywords, threshold=0.8
                )

                print(f"Validation: {details}")

                if is_valid:
                    print("[OK] Apify validation PASSED")
                    return True, filepath, current_payload
                else:
                    print(f"[WARNING] Match rate: {match_rate*100:.1f}% (need >=80%)")
                    print("Auto-optimizing filters...")

                    # Show mismatch examples
                    if mismatch_info.get('examples'):
                        print("\nExample mismatches:")
                        for ex in mismatch_info['examples'][:2]:
                            print(f"  - {ex.get('title')} at {ex.get('org_name')}")

                    # Broaden filters for next attempt
                    if attempt < max_attempts:
                        broadening_level += 1
                        # Re-map with higher broadening level
                        # For now, we'll manually broaden by removing restrictive filters
                        if 'city' in current_payload:
                            print("  -> Removing city filter")
                            del current_payload['city']
                        elif 'job_titles' in current_payload:
                            print("  -> Removing specific job titles, keeping seniority")
                            del current_payload['job_titles']
                        elif 'company_size' in current_payload:
                            print("  -> Removing company size filter")
                            del current_payload['company_size']
                        else:
                            print("  -> Cannot broaden further")
                            break
            else:
                print(f"[WARNING] No file returned from scraper")
        else:
            print(f"[WARNING] Apify scraper failed: {result.stderr}")

    # All attempts failed
    print(f"\n[WARNING] Could not optimize Apify filters after {max_attempts} attempts")
    print("Proceeding with B2B Finder only...")

    return False, None, current_payload


def run_full_scrape(apollo_url, target_leads, apify_payload):
    """
    Run full scrape from both sources in parallel.
    Both scrapers target the full lead count.
    """
    print(f"\n{'='*60}")
    print(f"FULL SCRAPE - TARGET: {target_leads} leads from EACH source")
    print(f"{'='*60}")

    apollo_file = None
    apify_file = None

    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit B2B Leads Finder scraper
        print("Starting Apify B2B Leads Finder scraper...")
        apollo_future = executor.submit(run_b2b_finder_scraper_full, apollo_url, target_leads)

        # Submit Apify scraper
        print("Starting Apify scraper...")
        apify_future = executor.submit(run_apify_scraper_full, target_leads, apify_payload)

        # Wait for results
        apollo_file = apollo_future.result()
        apify_file = apify_future.result()

    print(f"\n{'='*60}")
    print("SCRAPING COMPLETE")
    print(f"{'='*60}")
    print(f"B2B Finder: {'[OK] ' + apollo_file if apollo_file else '[FAIL] FAILED'}")
    print(f"Apify:      {'[OK] ' + apify_file if apify_file else '[FAIL] FAILED'}")

    return apollo_file, apify_file


def run_b2b_finder_scraper_full(apollo_url, target_leads):
    """Run full Apify B2B Leads Finder scrape."""
    # B2B Finder requires minimum 1000 leads
    actual_leads = max(target_leads, 1000)

    if actual_leads > target_leads:
        print(f"[INFO] B2B Finder requires minimum 1000 leads (requested: {target_leads})")
        print(f"[INFO] Scraping {actual_leads} leads, will use first {target_leads} after dedup")

    cmd = [
        PYTHON_EXE, "execution/run_apify_b2b_leads_finder.py",
        "--apollo-url", apollo_url,
        "--max-leads", str(actual_leads)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        output_lines = result.stdout.strip().split('\n')
        return output_lines[-1] if output_lines else None

    return None


def run_apify_scraper_full(target_leads, apify_payload):
    """Run full Apify scrape."""
    cmd = [
        PYTHON_EXE, "execution/run_apify_scraper_v2.py",
        "--fetch-count", str(target_leads)
    ]

    arg_mapping = {
        'industry': '--industry',
        'job_titles': '--job-title',
        'seniority': '--seniority',
        'functional_level': '--functional-level',
        'location': '--location',
        'city': '--city',
        'company_size': '--company-size',
        'min_revenue': '--min-revenue',
        'max_revenue': '--max-revenue',
        'funding': '--funding',
        'email_status': '--email-status'
    }

    for key, flag in arg_mapping.items():
        if apify_payload.get(key):
            cmd.extend([flag, apify_payload[key]])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        output_lines = result.stdout.strip().split('\n')
        return output_lines[-1] if output_lines else None

    return None


def count_leads_needing_enrichment(verified_file):
    """Count leads with missing or invalid emails."""
    try:
        with open(verified_file, 'r', encoding='utf-8') as f:
            leads = json.load(f)

        count = sum(1 for lead in leads
                   if lead.get('email_status') in ['missing', 'invalid', 'unknown', ''])

        return count
    except Exception as e:
        print(f"Error counting leads: {e}")
        return 0


def generate_quality_report(scraper_files, merged_file, verified_file, enriched_file):
    """Generate quality report with multi-source breakdown."""
    try:
        report_path = f".tmp/quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        # Load data from all scraper sources
        source_counts = {}
        total_raw = 0
        source_breakdown_by_type = {}

        for scraper_name, filepath in scraper_files.items():
            if filepath and os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    leads = json.load(f)
                    count = len(leads)
                    source_counts[scraper_name] = count
                    total_raw += count

                    # Track sources by type in merged leads
                    for lead in leads:
                        source = lead.get('source', scraper_name.lower())
                        source_breakdown_by_type[source] = source_breakdown_by_type.get(source, 0) + 1
            else:
                source_counts[scraper_name] = 0

        merged_leads = []
        if merged_file and os.path.exists(merged_file):
            with open(merged_file, 'r', encoding='utf-8') as f:
                merged_leads = json.load(f)

        verified_leads = []
        if verified_file and os.path.exists(verified_file):
            with open(verified_file, 'r', encoding='utf-8') as f:
                verified_leads = json.load(f)

        enriched_leads = []
        if enriched_file and os.path.exists(enriched_file):
            with open(enriched_file, 'r', encoding='utf-8') as f:
                enriched_leads = json.load(f)

        # Calculate stats
        duplicates_removed = total_raw - len(merged_leads)

        email_stats = {
            'valid': 0,
            'invalid': 0,
            'risky': 0,
            'missing': 0,
            'unknown': 0
        }

        for lead in verified_leads:
            status = lead.get('email_status', 'unknown')
            if status in email_stats:
                email_stats[status] += 1
            else:
                email_stats['unknown'] += 1

        # Generate report
        report_lines = [
            "="*60,
            f"QUALITY REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "="*60,
            "",
            "LEAD ACQUISITION (by scraper):"
        ]

        for scraper_name, count in source_counts.items():
            report_lines.append(f"  {scraper_name}: {count:,}")

        report_lines.extend([
            f"  Total Raw Leads: {total_raw:,}",
            "",
            "DEDUPLICATION:",
            f"  After Deduplication: {len(merged_leads):,}",
            f"  Duplicates Removed: {duplicates_removed:,} ({duplicates_removed/total_raw*100:.1f}%)" if total_raw > 0 else "  Duplicates Removed: 0",
            "",
            "EMAIL VERIFICATION:",
            f"  Valid: {email_stats['valid']:,} ({email_stats['valid']/len(verified_leads)*100:.1f}%)" if verified_leads else "  Valid: 0",
            f"  Invalid: {email_stats['invalid']:,} ({email_stats['invalid']/len(verified_leads)*100:.1f}%)" if verified_leads else "  Invalid: 0",
            f"  Risky: {email_stats['risky']:,} ({email_stats['risky']/len(verified_leads)*100:.1f}%)" if verified_leads else "  Risky: 0",
            f"  Missing: {email_stats['missing']:,} ({email_stats['missing']/len(verified_leads)*100:.1f}%)" if verified_leads else "  Missing: 0",
            f"  Unknown: {email_stats['unknown']:,} ({email_stats['unknown']/len(verified_leads)*100:.1f}%)" if verified_leads else "  Unknown: 0",
            "",
            "FINAL DELIVERABLE:",
            f"  Total Leads: {len(enriched_leads):,}",
            f"  Scrapers Used: {len([c for c in source_counts.values() if c > 0])}",
            "",
            "="*60
        ])

        report = "\n".join(report_lines) + "\n"

        # Write report
        os.makedirs('.tmp', exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(report)
        print(f"Report saved to: {report_path}")

    except Exception as e:
        print(f"Error generating quality report: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Enhanced Lead Generation Workflow V2 - Simplified Inputs'
    )

    # Required inputs
    parser.add_argument('--apollo-url', required=True, help='Apollo.io search URL with filters')
    parser.add_argument('--target-leads', type=int, required=True,
                       help='Target number of leads (scraped from EACH source)')

    # Optional overrides
    parser.add_argument('--skip-enrichment', action='store_true',
                       help='Skip email enrichment entirely')
    parser.add_argument('--force-enrichment', action='store_true',
                       help='Force enrichment even for >500 leads (no prompt)')
    parser.add_argument('--sheet-title', help='Custom Google Sheet title')
    parser.add_argument('--validation-threshold', type=float, default=0.8,
                       help='Validation threshold (default: 0.8)')

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("ENHANCED LEAD GENERATION WORKFLOW V2")
    print(f"{'='*60}")
    print(f"Apollo URL: {args.apollo_url}")
    print(f"Target Leads: {args.target_leads} from EACH source")
    print(f"{'='*60}\n")

    # STEP 1: Parse Apollo URL and derive Apify filters
    print(f"\n{'='*60}")
    print("STEP 1: PARSE APOLLO URL & DERIVE APIFY FILTERS")
    print(f"{'='*60}")

    try:
        apollo_filters = parse_apollo_url(args.apollo_url)
        print("Apollo Filters:")
        print(json.dumps(apollo_filters, indent=2))

        validation_keywords = extract_validation_keywords(apollo_filters)
        print(f"\nValidation Keywords: {validation_keywords}")

        apify_payload = map_apollo_to_apify(apollo_filters, broadening_level=1)
        print("\nApify Payload (Initial):")
        print(json.dumps(apify_payload, indent=2))

    except Exception as e:
        print(f"[FAIL] Error parsing Apollo URL: {e}")
        return 1

    # STEP 2: Pre-validation (Parallel Testing)
    print(f"\n{'='*60}")
    print("STEP 2: PRE-VALIDATION - PARALLEL SCRAPER TESTING")
    print(f"{'='*60}")
    print("Testing 3 scrapers in parallel with 25 leads each...")
    print("Only scrapers passing 80% threshold will be used for full run\n")

    # Track validation results
    validation_results = {}

    def test_scraper(scraper_name, test_func):
        """Test a single scraper and return results."""
        try:
            print(f"[{scraper_name}] Starting pre-validation...")
            success, filepath, match_percentage = test_func()
            validation_results[scraper_name] = {
                'success': success,
                'filepath': filepath,
                'match_percentage': match_percentage
            }
            if success:
                print(f"[{scraper_name}] [PASS] ({match_percentage:.1f}%)")
            else:
                print(f"[{scraper_name}] [FAIL] ({match_percentage:.1f}%)")
            return success, filepath, match_percentage
        except Exception as e:
            print(f"[{scraper_name}] ERROR: {e}")
            validation_results[scraper_name] = {
                'success': False,
                'filepath': None,
                'match_percentage': 0.0,
                'error': str(e)
            }
            return False, None, 0.0

    # Run all scrapers in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Peakydev test
        peakydev_future = executor.submit(
            test_scraper,
            "Peakydev",
            lambda: run_peakydev_scraper(args.apollo_url, 25, test_only=True)
        )

        # B2B Finder test
        b2b_finder_future = executor.submit(
            test_scraper,
            "B2B_Finder",
            lambda: run_b2b_finder_test(args.apollo_url, validation_keywords)
        )

        # Wait for completion
        peakydev_success, _, peakydev_match = peakydev_future.result()
        b2b_finder_success, _, b2b_finder_match = b2b_finder_future.result()

    # Run Apify separately (it has complex retry logic)
    apify_success, apify_test_file, apify_final_payload = run_apify_test(
        apify_payload, validation_keywords
    )
    apify_match = 100.0 if apify_success else 0.0

    # Print validation summary
    print(f"\n{'='*60}")
    print("PRE-VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"B2B_Finder: {'[OK] PASSED' if b2b_finder_success else '[X] FAILED'} ({b2b_finder_match:.1f}%)")
    print(f"Apify_v2:   {'[OK] PASSED' if apify_success else '[X] FAILED'} ({apify_match:.1f}%)")
    print(f"Peakydev:   {'[OK] PASSED' if peakydev_success else '[X] FAILED'} ({peakydev_match:.1f}%)")
    print(f"{'='*60}")

    # Count passing scrapers
    passing_scrapers = sum([b2b_finder_success, apify_success, peakydev_success])
    print(f"\nScrapers passing validation: {passing_scrapers}/3")

    if passing_scrapers == 0:
        print("\n[WARNING] No scrapers passed validation!")
        print("[INFO] Cannot proceed - no validated scrapers available.")
        return 1

    print(f"\n[OK] {passing_scrapers} scraper(s) ready for full run")

    # STEP 3: Full scrape (parallel execution of validated scrapers)
    print(f"\n{'='*60}")
    print(f"STEP 3: FULL SCRAPE - {passing_scrapers} validated scraper(s)")
    print(f"{'='*60}")
    print(f"Target leads per scraper: {args.target_leads}")

    scraper_files = {}

    def run_full_scraper(scraper_name, scrape_func):
        """Run a full scrape for a single scraper."""
        try:
            print(f"[{scraper_name}] Starting full scrape...")
            success, filepath, _ = scrape_func()
            scraper_files[scraper_name] = filepath if success else None
            if success:
                print(f"[{scraper_name}] ✅ Completed: {filepath}")
            else:
                print(f"[{scraper_name}] ❌ Failed")
            return filepath
        except Exception as e:
            print(f"[{scraper_name}] ERROR: {e}")
            scraper_files[scraper_name] = None
            return None

    # Run validated scrapers in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []

        if b2b_finder_success:
            futures.append(executor.submit(
                run_full_scraper,
                "B2B_Finder",
                lambda: (True, run_b2b_finder_scraper_full(args.apollo_url, args.target_leads), 0.0)
            ))

        if apify_success:
            futures.append(executor.submit(
                run_full_scraper,
                "Apify_v2",
                lambda: (True, run_apify_scraper_full(args.target_leads, apify_final_payload), 0.0)
            ))

        if peakydev_success:
            futures.append(executor.submit(
                run_full_scraper,
                "Peakydev",
                lambda: run_peakydev_scraper(args.apollo_url, args.target_leads, test_only=False)
            ))

        # Wait for all to complete
        for future in futures:
            future.result()

    print(f"\n{'='*60}")
    print("SCRAPING COMPLETE")
    print(f"{'='*60}")
    for scraper_name, filepath in scraper_files.items():
        status = f"[OK] {filepath}" if filepath else "[FAIL] FAILED"
        print(f"{scraper_name}: {status}")

    # Check if we got any results
    successful_files = [f for f in scraper_files.values() if f]
    if not successful_files:
        print("\n[FAIL] All scrapers failed during full run. Aborting.")
        return 1

    print(f"\n[OK] {len(successful_files)} scraper(s) completed successfully")

    # STEP 4: Merge & Deduplicate (Multi-source)
    print(f"\n{'='*60}")
    print("STEP 4: MERGE & DEDUPLICATE")
    print(f"{'='*60}")
    print(f"Merging {len(successful_files)} source files...")

    cmd = [PYTHON_EXE, "execution/merge_deduplicate_leads.py"]

    # Add all successful scraper files
    for scraper_name, filepath in scraper_files.items():
        if filepath:
            # Use generic --source-file flag for all scrapers
            cmd.extend(["--source-file", filepath])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("[FAIL] Merge failed")
        print(result.stderr)
        return 1

    # Extract merged file path from output
    output_lines = result.stdout.strip().split('\n')
    merged_file = output_lines[-1] if output_lines else None

    if not merged_file or not os.path.exists(merged_file):
        print("[FAIL] Merge output file not found")
        return 1

    print(f"[OK] Merged file: {merged_file}")

    # STEP 5: Verify Emails
    cmd = [
        PYTHON_EXE, "execution/verify_emails_leadmagic_fast.py",
        "--input", merged_file
    ]
    verified_file, _ = run_command(cmd, "Email Verification")
    if not verified_file:
        print("[FAIL] Email verification failed")
        return 1

    # STEP 6: Email Enrichment (with cost gate)
    enriched_file = verified_file

    if not args.skip_enrichment:
        leads_needing_enrichment = count_leads_needing_enrichment(verified_file)

        print(f"\n{'='*60}")
        print(f"EMAIL ENRICHMENT DECISION")
        print(f"{'='*60}")
        print(f"Leads needing enrichment: {leads_needing_enrichment}")

        run_enrichment = False

        if leads_needing_enrichment < 500:
            print("[OK] Under 500 leads - running enrichment automatically")
            run_enrichment = True
        elif args.force_enrichment:
            print("[OK] Force enrichment flag set - running enrichment")
            run_enrichment = True
        else:
            estimated_cost = leads_needing_enrichment * 0.10
            print(f"[WARNING] Estimated cost: ${estimated_cost:.2f}")
            response = input("Proceed with enrichment? (y/n): ")
            run_enrichment = response.lower() == 'y'

        if run_enrichment:
            cmd = [
                PYTHON_EXE, "execution/enrich_emails_leadmagic_fast.py",
                "--input", verified_file
            ]
            enriched_file, _ = run_command(cmd, "Email Enrichment")
            if not enriched_file:
                print("[WARNING] Email enrichment failed, using verified file")
                enriched_file = verified_file
        else:
            print("[SKIP] Skipping enrichment")
    else:
        print("\n[SKIP] Enrichment skipped by user")

    # STEP 7: Export to Google Sheets
    if not args.sheet_title:
        timestamp = datetime.now().strftime("%Y-%m-%d")
        args.sheet_title = f"Lead Generation - {timestamp}"

    cmd = [
        PYTHON_EXE, "execution/upload_to_google_sheet.py",
        "--input", enriched_file,
        "--sheet-title", args.sheet_title
    ]
    run_command(cmd, "Export to Google Sheets", capture_output=False)

    # STEP 8: Generate Quality Report
    generate_quality_report(scraper_files, merged_file, verified_file, enriched_file)

    print(f"\n{'='*60}")
    print("[OK] WORKFLOW COMPLETE!")
    print(f"{'='*60}")
    print(f"Final output: {enriched_file}")
    print(f"Scrapers used: {', '.join([k for k, v in scraper_files.items() if v])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

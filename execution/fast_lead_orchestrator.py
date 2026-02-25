# [ORCHESTRATOR] — pipeline controller, calls other scripts via subprocess
"""
Fast Lead Generation Orchestrator (V8 — Parallel-First)

Automated pipeline from Apollo URL to clean Google Sheet with quality gates.
User picks scrapers upfront; all selected scrapers run in parallel.

Steps:
0. Pre-flight: parse Apollo URL, show filter/cost/time per scraper
1. Run ALL selected scrapers in parallel
2. Merge & internal deduplication
3. Cross-campaign deduplication
3.5. Reference CSV deduplication (if --reference-csv)
4. Country verification (if --country, skip with --skip-country-verify)
4.5. Auto-derived quality filtering (skip with --skip-quality-filter)
5. Optional AI enrichment (if --enrich)
6. Google Sheets export (create/append/replace)
7. Update client.json

Usage:
    # Pre-flight only — see filter mappings + cost + time without scraping
    py execution/fast_lead_orchestrator.py \
      --client-id example_client \
      --campaign-name "Latvia Industries" \
      --apollo-url "https://app.apollo.io/#/people?..." \
      --target-leads 5000 \
      --country LV \
      --pre-flight-only

    # All scrapers (default)
    py execution/fast_lead_orchestrator.py \
      --client-id example_client \
      --campaign-name "Latvia Industries" \
      --apollo-url "https://app.apollo.io/#/people?..." \
      --target-leads 5000 \
      --country LV

    # Pick specific scrapers
    py execution/fast_lead_orchestrator.py \
      --client-id example_client \
      --campaign-name "Latvia Industries" \
      --apollo-url "https://app.apollo.io/#/people?..." \
      --target-leads 5000 \
      --country LV \
      --scrapers codecrafter,peakydev

    # With reference CSV dedup and existing sheet update
    py execution/fast_lead_orchestrator.py \
      --client-id example_client \
      --campaign-name "Latvia Industries" \
      --apollo-url "https://app.apollo.io/#/people?..." \
      --target-leads 5000 \
      --country LV \
      --scrapers codecrafter \
      --reference-csv "existing_leads.csv" \
      --sheet-id 1mw6Zu... \
      --sheet-mode replace
"""

import os
import sys
import argparse
import subprocess
import time
import shutil
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_registry import (
    SCRAPER_REGISTRY, VALID_SCRAPER_NAMES, ALL_SCRAPERS,
    build_scraper_command, get_default_target, estimate_time, estimate_cost
)
from utils import load_json, save_json, load_leads


def try_recover_apify_run(scraper_name, config, campaign_folder):
    """
    Attempt to recover results from an Apify run that completed despite local timeout.

    Each scraper saves its Apify run ID to .active_run.json immediately after starting.
    If the local subprocess is killed (timeout), the Apify run continues remotely.
    This function checks the run status and downloads results if available.

    Returns:
        (scraper_name, lead_file_path, lead_count) on success, or None on failure.
    """
    run_id_file = Path(config["output_dir"]) / '.active_run.json'
    if not run_id_file.exists():
        return None

    try:
        run_info = load_json(str(run_id_file))
        run_id = run_info['run_id']
        actor_name = run_info.get('actor', 'unknown')
        print(f"\n[RECOVERY] {scraper_name}: Found saved run ID {run_id} ({actor_name})")
        print(f"  Checking Apify run status...")

        from apify_client import ApifyClient
        from dotenv import load_dotenv
        load_dotenv()
        apify_key = os.getenv('APIFY_API_TOKEN') or os.getenv('APIFY_TOKEN')
        if not apify_key:
            print(f"  [RECOVERY FAILED] No Apify API token found")
            return None

        client = ApifyClient(apify_key)
        run = client.run(run_id).get()

        if not run:
            print(f"  [RECOVERY FAILED] Run {run_id} not found")
            return None

        status = run.get('status', 'UNKNOWN')
        print(f"  Run status: {status}")

        if status == 'RUNNING':
            print(f"  Run is still in progress — waiting for completion...")
            run = client.run(run_id).wait_for_finish()
            status = run.get('status', 'UNKNOWN')
            print(f"  Final status: {status}")

        if status != 'SUCCEEDED':
            print(f"  [RECOVERY FAILED] Run ended with status: {status}")
            run_id_file.unlink(missing_ok=True)
            return None

        # Download results
        print(f"  Downloading results from recovered run...")
        dataset_id = run.get('defaultDatasetId')
        if not dataset_id:
            print(f"  [RECOVERY FAILED] No dataset ID in run")
            return None

        dataset_items = list(client.dataset(dataset_id).iterate_items())
        if not dataset_items:
            print(f"  [RECOVERY FAILED] Dataset is empty")
            return None

        lead_count = len(dataset_items)
        print(f"  Downloaded {lead_count} leads from recovered run")

        # Normalize and save (import the right normalizer)
        if scraper_name == 'olympus':
            from scraper_olympus_b2b_finder import normalize_lead_to_schema
        elif scraper_name == 'codecrafter':
            from scraper_codecrafter import normalize_lead_to_schema
        elif scraper_name == 'peakydev':
            from scraper_peakydev import normalize_lead_to_schema
        else:
            print(f"  [RECOVERY FAILED] Unknown scraper: {scraper_name}")
            return None

        normalized = [normalize_lead_to_schema(item) for item in dataset_items]

        # Save to output dir
        output_dir = Path(config["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{config['output_prefix']}_{timestamp}_{lead_count}leads.json"
        output_path = output_dir / filename
        save_json(normalized, str(output_path))

        # Copy to campaign folder
        import shutil as _shutil
        _shutil.copy2(output_path, campaign_folder / config["campaign_filename"])

        # Clean up
        run_id_file.unlink(missing_ok=True)

        print(f"  [RECOVERY SUCCESS] {lead_count} leads saved to {output_path}")
        return (scraper_name, output_path, lead_count)

    except Exception as e:
        print(f"  [RECOVERY FAILED] Error: {e}")
        return None


def run_command(cmd, description, timeout=600, tag=None):
    """Run a shell command and return success status, exit code, and output.

    Args:
        tag: Optional prefix for log lines (e.g. scraper name). When set,
             all print output is prefixed with [TAG] so parallel output
             can be attributed to the right scraper.
    """
    prefix = f"[{tag}] " if tag else ""

    print(f"\n{'='*70}")
    print(f"{prefix}[STEP] {description}")
    print(f"{'='*70}")

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        elapsed = time.time() - start_time

        if result.returncode == 0:
            print(f"{prefix}[SUCCESS] Completed in {elapsed:.1f}s")
            if result.stdout:
                # Prefix each line so parallel output stays attributable
                if tag:
                    for line in result.stdout.rstrip('\n').split('\n'):
                        print(f"{prefix}{line}")
                else:
                    print(result.stdout)
            return True, result.returncode, result.stdout
        else:
            print(f"{prefix}[FAILED] Exit code {result.returncode}")
            if result.stderr:
                if tag:
                    for line in result.stderr.rstrip('\n').split('\n'):
                        print(f"{prefix}{line}")
                else:
                    print(result.stderr)
            # Combine stdout and stderr for cookie detection
            combined_output = result.stdout + "\n" + result.stderr
            return False, result.returncode, combined_output

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"{prefix}[TIMEOUT] Command exceeded {timeout}s timeout")
        return False, -1, "Timeout"
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"{prefix}[ERROR] {str(e)}")
        return False, -1, str(e)


def get_lead_count_from_output(output):
    """Extract lead count from scraper output."""
    import re

    # Look for patterns like "Downloaded 1006 leads" or "1006 leads"
    patterns = [
        r'Downloaded\s+(\d+)\s+leads',
        r'Successfully scraped\s+(\d+)\s+leads',
        r'Total leads:\s+(\d+)',
        r'(\d+)\s+leads'
    ]

    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return int(match.group(1))

    return 0


def find_latest_lead_file(directory, prefix=""):
    """Find the most recent lead file in a directory."""
    path = Path(directory)
    if not path.exists():
        return None

    files = list(path.glob(f"{prefix}*.json"))
    if not files:
        return None

    return max(files, key=lambda p: p.stat().st_mtime)


def run_scraper_parallel(scrapers):
    """Run multiple scrapers in parallel."""
    print(f"\n{'='*70}")
    print(f"[PARALLEL] Running {len(scrapers)} scrapers simultaneously")
    print(f"{'='*70}")

    results = {}

    with ThreadPoolExecutor(max_workers=len(scrapers)) as executor:
        futures = {}

        for scraper_name, cmd, timeout in scrapers:
            future = executor.submit(
                run_command, cmd, f"Running {scraper_name}", timeout,
                tag=scraper_name.upper()
            )
            futures[future] = scraper_name

        for future in as_completed(futures):
            scraper_name = futures[future]
            success, exit_code, output = future.result()
            results[scraper_name] = {
                'success': success,
                'output': output,
                'lead_count': get_lead_count_from_output(output) if success else 0
            }

            if success:
                print(f"[{scraper_name}] Completed - {results[scraper_name]['lead_count']} leads")
            else:
                print(f"[{scraper_name}] Failed")

    return results


def pre_flight(apollo_url, country_code, selected_scrapers=None, target_leads=None):
    """
    Parse Apollo URL and show how filters map to each scraper (registry-driven).
    Returns the parsed apollo_filters dict.
    """
    from apollo_url_parser import parse_apollo_url
    from industry_taxonomy import v1_to_v2

    apollo_filters = parse_apollo_url(apollo_url)

    print(f"\n{'='*70}")
    print(f"PRE-FLIGHT: Apollo URL Filter Mapping")
    print(f"{'='*70}")

    # --- Apollo URL filters ---
    print(f"\n  APOLLO URL FILTERS:")
    if apollo_filters.get('industries_resolved'):
        print(f"    Industries ({len(apollo_filters['industries_resolved'])}):")
        for ind in apollo_filters['industries_resolved']:
            print(f"      - {ind}")
    if apollo_filters.get('industries_unresolved'):
        print(f"    UNRESOLVED industry IDs ({len(apollo_filters['industries_unresolved'])}):")
        for hid in apollo_filters['industries_unresolved']:
            print(f"      - {hid}")
    locs = apollo_filters.get('org_locations') or apollo_filters.get('locations') or []
    if locs:
        print(f"    Locations: {', '.join(locs)}")
    if apollo_filters.get('titles'):
        print(f"    Titles: {', '.join(apollo_filters['titles'])}")
    if apollo_filters.get('seniority'):
        print(f"    Seniority: {', '.join(apollo_filters['seniority'])}")
    if apollo_filters.get('company_size'):
        print(f"    Company size: {', '.join(apollo_filters['company_size'])}")
    if apollo_filters.get('keywords'):
        print(f"    Keywords: {', '.join(apollo_filters['keywords'])}")

    # --- Per-scraper mapping (driven by registry) ---
    scrapers_to_show = selected_scrapers or set(SCRAPER_REGISTRY.keys())

    for name, config in SCRAPER_REGISTRY.items():
        if name not in scrapers_to_show:
            continue

        label = config["display_name"]
        cookie_note = " (needs cookies)" if config["needs_cookies"] else " (no cookies needed)"

        print(f"\n  {'-'*60}")
        print(f"  {label.upper()}{cookie_note}:")

        # Pre-flight notes
        for note in config["preflight_notes"]:
            print(f"    {note}")

        # Location display
        if locs and config["location_transform"]:
            transform = config["location_transform"]
            if transform == "lowercase":
                display_locs = [l.lower() for l in locs]
            elif transform == "title_case":
                display_locs = [l.title() for l in locs]
            else:
                display_locs = locs
            print(f"    Location sent: {', '.join(display_locs)}")

        # Industry display (skip apollo_native — already in preflight_notes)
        if apollo_filters.get('industries_resolved'):
            tax = config["industry_taxonomy"]
            if tax == "v1":
                inds = apollo_filters['industries_resolved']
                ind_transform = config.get("industry_transform", "")
                print(f"    Industries ({len(inds)}): V1 names, {ind_transform}")
                for ind in inds[:5]:
                    display = ind.lower() if ind_transform == "lowercase" else ind
                    print(f"      - {display}")
                if len(inds) > 5:
                    print(f"      ... +{len(inds)-5} more")
            elif tax == "v2":
                v2_inds = v1_to_v2(apollo_filters['industries_resolved'])
                print(f"    Industries ({len(v2_inds)}): V2 taxonomy (mapped from V1)")
                for ind in v2_inds[:5]:
                    print(f"      - {ind}")
                if len(v2_inds) > 5:
                    print(f"      ... +{len(v2_inds)-5} more")

        # Titles/seniority
        has_titles = "titles" in config["supported_filters"]
        has_seniority = "seniority" in config["supported_filters"]
        if apollo_filters.get('titles') and has_titles:
            print(f"    Titles: {', '.join(apollo_filters['titles'])}")
        elif not has_titles and apollo_filters.get('titles'):
            pass  # Shown in warnings below
        elif has_titles and not apollo_filters.get('titles'):
            print(f"    Titles: (none in Apollo URL)")
        if apollo_filters.get('seniority') and has_seniority:
            print(f"    Seniority: {', '.join(apollo_filters['seniority'])}")
        elif has_seniority and not apollo_filters.get('seniority'):
            print(f"    Seniority: (none in Apollo URL)")

        # Pre-flight warnings
        for warning in config["preflight_warnings"]:
            print(f"    {warning}")

    # --- Quality gate summary ---
    print(f"\n  {'-'*60}")
    print(f"  POST-SCRAPE QUALITY GATES:")
    if country_code:
        print(f"    Country verification: {country_code} (domain TLD + phone + Lead Magic)")
    print(f"    Industry whitelist: V1 + V2 names combined")
    print(f"    Require: email, website/domain")
    if country_code:
        print(f"    Remove: foreign TLDs, phone/country discrepancies")

    # --- Cost & time estimates ---
    print(f"\n  {'-'*60}")
    print(f"  ESTIMATED COST & TIME:")
    total_cost = 0.0
    max_time = 0
    leads_for_estimate = target_leads if target_leads else 1000
    for name, config in SCRAPER_REGISTRY.items():
        if name not in scrapers_to_show:
            continue
        label = config["display_name"]
        est_cost = estimate_cost(name, leads_for_estimate)
        est_mins = estimate_time(name, leads_for_estimate)
        total_cost += est_cost
        max_time = max(max_time, est_mins)
        notes = []
        if config["needs_cookies"]:
            notes.append("needs cookies")
        min_leads = config.get("min_leads")
        if min_leads and leads_for_estimate < min_leads:
            notes.append(f"min {min_leads} leads")
        notes_str = f"  ({', '.join(notes)})" if notes else ""
        print(f"    {label:15s} ~${est_cost:.2f}   ~{est_mins} min{notes_str}")
    if target_leads:
        print(f"    {'-'*45}")
        print(f"    {'Total cost':15s} ~${total_cost:.2f} (before dedup overlap)")
        print(f"    {'Parallel time':15s} ~{max_time} min (= slowest scraper)")
    print(f"{'='*70}")

    return apollo_filters


def main():
    parser = argparse.ArgumentParser(description='Fast lead generation orchestrator')
    parser.add_argument('--client-id', required=True, help='Client identifier')
    parser.add_argument('--campaign-name', required=True, help='Campaign name')
    parser.add_argument('--apollo-url', required=True, help='Apollo search URL')
    parser.add_argument('--target-leads', type=int, required=True, help='Target number of leads')
    parser.add_argument('--country', default=None, help='Country code for verification (e.g. LT, LV, IT). If omitted, country verification is skipped.')
    parser.add_argument('--enrich', action='store_true', help='Enable AI enrichment (slower)')
    parser.add_argument('--scrapers', type=str,
                        help='Comma-separated scrapers to run: olympus,codecrafter,peakydev (default: all)')
    parser.add_argument('--pre-flight-only', action='store_true',
                        help='Show filter mapping and exit without scraping')
    parser.add_argument('--reference-csv', type=str,
                        help='CSV file to dedup against (e.g. existing client leads)')
    parser.add_argument('--sheet-id', type=str,
                        help='Existing Google Sheet ID to update instead of creating new')
    parser.add_argument('--sheet-mode', choices=['create', 'append', 'replace'], default='create',
                        help='Sheet mode: create (new), append (add rows), replace (clear+rewrite)')
    parser.add_argument('--skip-quality-filter', action='store_true',
                        help='Skip auto-derived quality filtering')
    parser.add_argument('--skip-country-verify', action='store_true',
                        help='Skip country verification step')
    parser.add_argument('--max-leads-mode', choices=['target', 'maximum'], default='target',
                        help='target: match --target-leads. maximum: request max from each scraper')

    args = parser.parse_args()

    # Generate campaign ID
    campaign_id = args.campaign_name.lower().replace(' ', '_') + '_' + datetime.now().strftime('%Y%m%d')
    campaign_folder = Path(f'campaigns/{args.client_id}/apollo_lists/{campaign_id}')

    # Create campaign folder
    campaign_folder.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"FAST LEAD GENERATION ORCHESTRATOR")
    print(f"{'='*70}")
    # Parse --scrapers flag into a set (default: all scrapers)
    if args.scrapers:
        selected_scrapers = {s.strip().lower() for s in args.scrapers.split(',')}
        invalid = selected_scrapers - VALID_SCRAPER_NAMES
        if invalid:
            print(f"ERROR: Unknown scraper(s): {', '.join(invalid)}")
            print(f"Valid scrapers: {', '.join(sorted(VALID_SCRAPER_NAMES))}")
            return 1
    else:
        selected_scrapers = set(ALL_SCRAPERS)

    print(f"Client: {args.client_id}")
    print(f"Campaign: {args.campaign_name}")
    print(f"Target leads: {args.target_leads}")
    print(f"Country: {args.country}")
    print(f"Scrapers: {', '.join(sorted(selected_scrapers))}")
    print(f"Max leads mode: {args.max_leads_mode}")
    print(f"Country verification: {'Disabled' if args.skip_country_verify else 'Enabled'}")
    print(f"Quality filtering: {'Disabled' if args.skip_quality_filter else 'Auto-derived'}")
    print(f"Reference CSV: {args.reference_csv or 'None'}")
    print(f"Sheet mode: {args.sheet_mode}" + (f" (ID: {args.sheet_id})" if args.sheet_id else ""))
    print(f"AI enrichment: {'Enabled' if args.enrich else 'Disabled (fast-track)'}")
    print(f"")

    # STEP 0: Pre-flight — show filter mapping per scraper
    try:
        apollo_filters = pre_flight(args.apollo_url, args.country, selected_scrapers, args.target_leads)
    except Exception as e:
        print(f"[WARNING] Pre-flight failed: {e}")
        apollo_filters = None

    if args.pre_flight_only:
        print("\n[PRE-FLIGHT ONLY] Exiting without scraping.")
        return 0

    workflow_start = time.time()

    # STEP 1: Run ALL selected scrapers in parallel
    lead_sources = []

    # Build commands for all selected scrapers
    scrapers_to_run = []
    for name in ALL_SCRAPERS:
        if name not in selected_scrapers:
            continue
        config = SCRAPER_REGISTRY[name]
        target = get_default_target(name, args.target_leads, args.max_leads_mode)
        cmd = build_scraper_command(name, args.apollo_url, target, args.country)
        est_mins = estimate_time(name, target)
        print(f"  {config['display_name']:15s} requesting {target:,} leads (~{est_mins} min)")
        scrapers_to_run.append((name, cmd, config["timeout"]))

    print(f"\n  Monitor progress at: https://console.apify.com/actors/runs")

    if len(scrapers_to_run) == 1:
        # Single scraper — run directly (no parallel overhead)
        name, cmd, timeout = scrapers_to_run[0]
        config = SCRAPER_REGISTRY[name]
        success, exit_code, output = run_command(
            cmd, f"Step 1: {config['display_name']} scraper", timeout=timeout
        )

        # Cookie failure handling
        if config["needs_cookies"] and (
            exit_code == config.get("cookie_exit_code")
            or 'COOKIE VALIDATION FAILED' in output
        ):
            print(f"\n[CRITICAL] {config['display_name']}: Cookie validation failed")
            print(f"  Apollo session cookie has expired.")
            print(f"  1. Log into Apollo: https://app.apollo.io")
            print(f"  2. Export cookies using EditThisCookie extension")
            print(f"  3. Update APOLLO_COOKIE in .env file")
            return 1

        lead_count = get_lead_count_from_output(output) if success else 0
        lead_file = find_latest_lead_file(config["output_dir"], config["output_prefix"])
        if lead_file and success:
            shutil.copy2(lead_file, campaign_folder / config["campaign_filename"])
            lead_sources.append((name, lead_file, lead_count))
    else:
        # Multiple scrapers — run all in parallel
        scraper_results = run_scraper_parallel(scrapers_to_run)

        # Collect results + handle cookie failures
        for name in ALL_SCRAPERS:
            if name not in selected_scrapers:
                continue
            config = SCRAPER_REGISTRY[name]
            result = scraper_results.get(name, {})

            # Cookie failure warning (doesn't block other scrapers since they ran in parallel)
            if config["needs_cookies"] and not result.get('success'):
                output = result.get('output', '')
                if 'COOKIE VALIDATION FAILED' in output or 'cookie expired' in output.lower():
                    print(f"\n[WARNING] {config['display_name']}: Cookie validation failed")
                    print(f"  Apollo session cookie has expired — {config['display_name']} returned 0 leads.")
                    print(f"  Other scrapers continued normally.")

            lead_file = find_latest_lead_file(config["output_dir"], config["output_prefix"])
            if lead_file and result.get('success'):
                shutil.copy2(lead_file, campaign_folder / config["campaign_filename"])
                lead_sources.append((name, lead_file, result['lead_count']))
            elif not result.get('success'):
                # Attempt recovery: check if Apify run completed despite local timeout
                recovered = try_recover_apify_run(name, config, campaign_folder)
                if recovered:
                    rec_name, rec_file, rec_count = recovered
                    lead_sources.append((rec_name, rec_file, rec_count))

    # STEP 2: Merge & deduplicate (if multiple sources)
    if len(lead_sources) > 1:
        source_args = ' '.join([f'--source-file "{path}"' for name, path, count in lead_sources])
        merge_cmd = f'py execution/leads_deduplicator.py {source_args} --output-dir "{campaign_folder}" --output-prefix "raw_leads"'
        merge_success, _, _ = run_command(merge_cmd, "Step 2: Merge & deduplicate sources", timeout=300)

        if merge_success:
            raw_file = find_latest_lead_file(campaign_folder, 'raw_leads_')
        else:
            print("[WARNING] Merge failed, using first source file only")
            raw_file = lead_sources[0][1] if lead_sources else None
    else:
        # Single source - just copy it
        raw_file = lead_sources[0][1] if lead_sources else None
        if raw_file:
            shutil.copy2(raw_file, campaign_folder / f'raw_leads_{datetime.now().strftime("%Y%m%d_%H%M%S")}_{lead_sources[0][2]}leads.json')
            raw_file = find_latest_lead_file(campaign_folder, 'raw_leads_')

    if not raw_file:
        print("[ERROR] No leads available - exiting")
        return 1

    # STEP 3: Cross-campaign deduplication
    dedup_cmd = f'py execution/cross_campaign_deduplicator.py --client-id "{args.client_id}"'
    _, _, _ = run_command(dedup_cmd, "Step 3: Cross-campaign deduplication", timeout=300)

    # Refresh raw file path after deduplication
    raw_file = find_latest_lead_file(campaign_folder, 'raw_leads_')
    if not raw_file:
        print("[ERROR] raw_leads file not found after cross-campaign dedup - exiting")
        return 1

    # STEP 3.5: Reference CSV deduplication (if --reference-csv provided)
    if args.reference_csv and raw_file:
        import csv
        print(f"\n{'='*70}")
        print(f"[STEP] Step 3.5: Reference CSV deduplication")
        print(f"{'='*70}")
        try:
            # Load reference emails
            ref_emails = set()
            with open(args.reference_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = (row.get('Email') or row.get('email') or row.get('EMAIL') or '').strip().lower()
                    if email:
                        ref_emails.add(email)

            # Load current leads
            current_leads = load_leads(str(raw_file))

            before_count = len(current_leads)
            current_leads = [l for l in current_leads if (l.get('email') or '').strip().lower() not in ref_emails]
            removed = before_count - len(current_leads)

            # Save filtered leads
            ref_dedup_path = campaign_folder / f'ref_deduped_{datetime.now().strftime("%Y%m%d_%H%M%S")}_{len(current_leads)}leads.json'
            save_json(current_leads, str(ref_dedup_path))

            raw_file = ref_dedup_path
            print(f"[SUCCESS] Reference CSV dedup: {before_count} → {len(current_leads)} (removed {removed}, ref had {len(ref_emails)} emails)")
        except Exception as e:
            print(f"[WARNING] Reference CSV dedup failed: {e}")
            print(f"[CONTINUING] Proceeding without reference dedup")

    # STEP 4: Country verification (if --country and not --skip-country-verify)
    if not args.skip_country_verify and args.country and raw_file:
        verify_cmd = f'py execution/verify_country.py --input "{raw_file}" --country {args.country} --output-dir "{campaign_folder}" --output-prefix "verified"'
        verify_success, _, verify_output = run_command(verify_cmd, "Step 4: Country verification", timeout=600)

        if verify_success:
            verified_file = find_latest_lead_file(campaign_folder, 'verified_')
            if verified_file:
                raw_file = verified_file
                print(f"[OK] Using verified leads: {verified_file}")
            else:
                print(f"[WARNING] No verified file found, continuing with unverified leads")
        else:
            print(f"[WARNING] Country verification failed, continuing with unverified leads")

    # STEP 4.5: Auto-derived quality filtering (if not --skip-quality-filter)
    if not args.skip_quality_filter and raw_file:
        filter_args_list = ['--require-email', '--require-website']

        # Auto-derive industry whitelist from Apollo URL
        try:
            from apollo_url_parser import parse_apollo_url
            from industry_taxonomy import build_combined_whitelist

            apollo_filters = parse_apollo_url(args.apollo_url)
            if apollo_filters.get('industries_resolved'):
                combined = build_combined_whitelist(apollo_filters['industries_resolved'])
                if combined:
                    filter_args_list.extend(['--include-industries', f'"{",".join(combined)}"'])
        except Exception as e:
            print(f"[WARNING] Could not auto-derive industry whitelist: {e}")

        # Country-specific filters
        if args.country:
            filter_args_list.append('--remove-phone-discrepancies')
            filter_args_list.extend(['--remove-foreign-tld', args.country])

        filter_cmd = f'py execution/lead_filter.py --input "{raw_file}" --output-dir "{campaign_folder}" --output-prefix "filtered" {" ".join(filter_args_list)}'
        filter_success, _, _ = run_command(filter_cmd, "Step 4.5: Quality filtering", timeout=120)

        if filter_success:
            filtered_file = find_latest_lead_file(campaign_folder, 'filtered_')
            if filtered_file:
                raw_file = filtered_file
                print(f"[OK] Using filtered leads: {filtered_file}")
        else:
            print(f"[WARNING] Quality filtering failed, continuing with unfiltered leads")

    # STEP 5: Optional AI enrichment
    if args.enrich:
        print(f"\n[ENRICHMENT] Running AI enrichment (adds ~30-40 min)")

        # Casual names — output to campaign folder with known filename
        casual_output = campaign_folder / 'enriched_casual.json'
        casual_cmd = f'py execution/ai_casual_name_generator.py --input "{raw_file}" --ai-provider openai --output-dir "{campaign_folder}" --output-prefix "enriched_casual"'
        casual_success, _, casual_stdout = run_command(casual_cmd, "Step 5a: AI casual names", timeout=900)

        if casual_success:
            # Scripts print the output filepath on the last line of stdout
            casual_file = find_latest_lead_file(campaign_folder, 'enriched_casual')
            if casual_file:
                raw_file = casual_file

        # Icebreakers — output to campaign folder with known filename
        icebreaker_cmd = f'py execution/ai_icebreaker_generator.py --input "{raw_file}" --ai-provider openai --output-dir "{campaign_folder}" --output-prefix "enriched_icebreaker"'
        icebreaker_success, _, _ = run_command(icebreaker_cmd, "Step 5b: AI icebreakers", timeout=1800)

        if icebreaker_success:
            icebreaker_file = find_latest_lead_file(campaign_folder, 'enriched_icebreaker')
            if icebreaker_file:
                raw_file = icebreaker_file

        # Fallback enrichment — supports --output for explicit path
        fallback_output = campaign_folder / 'enriched_fallback.json'
        fallback_cmd = f'py execution/ai_fallback_enricher.py --input "{raw_file}" --output "{fallback_output}"'
        fallback_success, _, _ = run_command(fallback_cmd, "Step 5c: AI fallback enrichment", timeout=600)

        if fallback_success and fallback_output.exists():
            raw_file = fallback_output
    else:
        print(f"\n[FAST-TRACK] Skipping AI enrichment (Saved ~30-40 minutes)")

    # STEP 6: Upload to Google Sheets
    sheet_args = f'--input "{raw_file}"'
    if args.sheet_id:
        sheet_args += f' --sheet-id {args.sheet_id} --mode {args.sheet_mode}'
    else:
        sheet_title = f"{args.client_id.title()} - {args.campaign_name}"
        sheet_args += f' --sheet-title "{sheet_title}"'
    upload_cmd = f'py execution/google_sheets_exporter.py {sheet_args}'
    upload_success, _, upload_output = run_command(upload_cmd, "Step 6: Upload to Google Sheets", timeout=300)

    # Extract sheet URL
    sheet_url = None
    if upload_success:
        import re
        match = re.search(r'https://docs\.google\.com/spreadsheets/d/[^\s]+', upload_output)
        if match:
            sheet_url = match.group(0)

            # Save to campaign folder
            with open(campaign_folder / 'sheet_url.txt', 'w', encoding='utf-8') as f:
                f.write(sheet_url)

    # STEP 7: Update client.json
    # Count final leads (before the conditional so final_count is always defined)
    final_leads = load_leads(str(raw_file))
    final_count = len(final_leads)

    client_file = Path(f'campaigns/{args.client_id}/client.json')
    if client_file.exists():
        client_data = load_json(str(client_file))

        # Add campaign
        campaign_entry = {
            'campaign_id': campaign_id,
            'campaign_name': args.campaign_name,
            'type': 'apollo',
            'created_at': datetime.now(timezone.utc).isoformat() + 'Z',
            'lead_count': final_count,
            'sheet_url': sheet_url or '',
            'sources': {name: count for name, _, count in lead_sources},
            'notes': f'Generated with fast orchestrator - {"with AI enrichment" if args.enrich else "fast-track"}'
        }

        client_data.setdefault('campaigns', []).append(campaign_entry)
        client_data['updated_at'] = datetime.now(timezone.utc).isoformat() + 'Z'

        save_json(client_data, str(client_file))

        print(f"[OK] Updated client.json")

    # Final report
    workflow_time = time.time() - workflow_start

    print(f"\n{'='*70}")
    print(f"WORKFLOW COMPLETE")
    print(f"{'='*70}")
    print(f"Campaign: {args.campaign_name}")
    print(f"Final lead count: {final_count}")
    print(f"Lead sources: {', '.join([name for name, _, _ in lead_sources])}")
    print(f"Total time: {workflow_time / 60:.1f} minutes")
    print(f"Google Sheet: {sheet_url or 'N/A'}")
    print(f"Campaign folder: {campaign_folder}")
    print(f"")

    if workflow_time < 600:  # Under 10 minutes
        print(f"[FAST-TRACK] Completed in {workflow_time / 60:.1f} min (vs ~45 min for full pipeline)")

    return 0


if __name__ == '__main__':
    sys.exit(main())

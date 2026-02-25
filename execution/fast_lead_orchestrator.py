# [ORCHESTRATOR] — pipeline controller, calls other scripts via subprocess
"""
Fast Lead Generation Orchestrator (V7)

Automated pipeline from Apollo URL to clean Google Sheet with quality gates.

Steps:
0. Pre-flight: parse Apollo URL, show filter mapping per scraper
1. Olympus scraper (skip with --skip-olympus or --scrapers)
2. Backup scrapers in parallel (user picks via --scrapers)
3. Merge & internal deduplication
4. Cross-campaign deduplication
4.5. Reference CSV deduplication (if --reference-csv)
5. Country verification (if --country, skip with --skip-country-verify)
5.5. Auto-derived quality filtering (skip with --skip-quality-filter)
6. Optional AI enrichment (if --enrich)
7. Google Sheets export (create/append/replace)
8. Update client.json

Usage:
    # Pre-flight only — see filter mappings without scraping
    py execution/fast_lead_orchestrator.py \
      --client-id example_client \
      --campaign-name "Latvia Industries" \
      --apollo-url "https://app.apollo.io/#/people?..." \
      --target-leads 5000 \
      --country LV \
      --pre-flight-only

    # Pick specific scrapers (CodeCrafter only)
    py execution/fast_lead_orchestrator.py \
      --client-id example_client \
      --campaign-name "Latvia Industries" \
      --apollo-url "https://app.apollo.io/#/people?..." \
      --target-leads 5000 \
      --country LV \
      --scrapers codecrafter \
      --max-leads-mode maximum

    # Both backup scrapers
    py execution/fast_lead_orchestrator.py \
      --client-id example_client \
      --campaign-name "Latvia Industries" \
      --apollo-url "https://app.apollo.io/#/people?..." \
      --target-leads 5000 \
      --country LV \
      --scrapers codecrafter,peakydev \
      --max-leads-mode maximum

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
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_registry import (
    SCRAPER_REGISTRY, VALID_SCRAPER_NAMES, PRIMARY_SCRAPERS,
    BACKUP_SCRAPERS, build_scraper_command, get_default_target
)
from utils import load_json, save_json, load_leads

def run_command(cmd, description, timeout=600):
    """Run a shell command and return success status, exit code, and output."""
    print(f"\n{'='*70}")
    print(f"[STEP] {description}")
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
            print(f"[SUCCESS] Completed in {elapsed:.1f}s")
            if result.stdout:
                print(result.stdout)
            return True, result.returncode, result.stdout
        else:
            print(f"[FAILED] Exit code {result.returncode}")
            if result.stderr:
                print(result.stderr)
            # Combine stdout and stderr for cookie detection
            combined_output = result.stdout + "\n" + result.stderr
            return False, result.returncode, combined_output

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"[TIMEOUT] Command exceeded {timeout}s timeout")
        return False, -1, "Timeout"
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[ERROR] {str(e)}")
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
            future = executor.submit(run_command, cmd, f"Running {scraper_name}", timeout)
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

    # --- Cost estimates ---
    print(f"\n  {'-'*60}")
    print(f"  ESTIMATED COSTS:")
    total_cost = 0.0
    for name, config in SCRAPER_REGISTRY.items():
        if name not in scrapers_to_show:
            continue
        pricing = config.get("pricing", {})
        cost_per_1k = pricing.get("cost_per_1k", 0)
        label = config["display_name"]
        leads_for_estimate = target_leads if target_leads else 1000
        est = cost_per_1k * leads_for_estimate / 1000
        total_cost += est
        print(f"    {label:15s} ${cost_per_1k:.2f}/1k leads   (~${est:.2f} for {leads_for_estimate:,} leads)")
    if target_leads:
        print(f"    {'─'*45}")
        print(f"    {'Total estimate':15s} ~${total_cost:.2f} (before dedup overlap)")
    print(f"{'='*70}")

    return apollo_filters


def main():
    parser = argparse.ArgumentParser(description='Fast lead generation orchestrator')
    parser.add_argument('--client-id', required=True, help='Client identifier')
    parser.add_argument('--campaign-name', required=True, help='Campaign name')
    parser.add_argument('--apollo-url', required=True, help='Apollo search URL')
    parser.add_argument('--target-leads', type=int, required=True, help='Target number of leads')
    parser.add_argument('--country', default='NZ', help='Country code for Olympus scraper')
    parser.add_argument('--enrich', action='store_true', help='Enable AI enrichment (slower)')
    parser.add_argument('--force-multi-source', action='store_true', help='Force running all scrapers')
    parser.add_argument('--skip-olympus', action='store_true',
                        help='Skip Olympus, go straight to backup scrapers (CC + PeakyDev)')
    parser.add_argument('--scrapers', type=str,
                        help='Comma-separated scrapers to use: olympus,codecrafter,peakydev (overrides auto-selection)')
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
    # Parse --scrapers flag into a set
    selected_scrapers = None  # None = auto-select
    if args.scrapers:
        selected_scrapers = {s.strip().lower() for s in args.scrapers.split(',')}
        invalid = selected_scrapers - VALID_SCRAPER_NAMES
        if invalid:
            print(f"ERROR: Unknown scraper(s): {', '.join(invalid)}")
            print(f"Valid scrapers: {', '.join(sorted(VALID_SCRAPER_NAMES))}")
            return 1
        # --scrapers overrides --skip-olympus if no primary scrapers selected
        if not selected_scrapers & set(PRIMARY_SCRAPERS):
            args.skip_olympus = True

    print(f"Client: {args.client_id}")
    print(f"Campaign: {args.campaign_name}")
    print(f"Target leads: {args.target_leads}")
    print(f"Country: {args.country}")
    print(f"Scrapers: {', '.join(sorted(selected_scrapers)) if selected_scrapers else 'auto'}")
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

    # STEP 1: Run primary scraper(s)
    lead_sources = []
    primary_lead_count = 0

    # Determine which primary scrapers to run
    if selected_scrapers:
        run_primary = [s for s in PRIMARY_SCRAPERS if s in selected_scrapers]
    else:
        run_primary = PRIMARY_SCRAPERS[:]

    if args.skip_olympus:
        run_primary = []
        print(f"\n{'='*70}")
        print(f"[SKIP-PRIMARY] Going straight to backup scrapers")
        print(f"{'='*70}")

    for name in run_primary:
        config = SCRAPER_REGISTRY[name]
        cmd = build_scraper_command(name, args.apollo_url, args.target_leads, args.country)
        success, exit_code, output = run_command(
            cmd, f"Step 1: {config['display_name']} scraper (primary)", timeout=config["timeout"]
        )

        # Cookie failure handling (for scrapers that need cookies)
        if config["needs_cookies"] and (
            exit_code == config.get("cookie_exit_code")
            or 'COOKIE VALIDATION FAILED' in output
        ):
            print(f"\n{'='*70}")
            print(f"[CRITICAL] {config['display_name']}: Cookie validation failed")
            print(f"{'='*70}")
            print("")
            print("Apollo session cookie has expired.")
            print("")
            print("ACTION REQUIRED:")
            print("1. Log into Apollo: https://app.apollo.io")
            print("2. Export cookies using EditThisCookie extension")
            print("3. Update APOLLO_COOKIE in .env file")
            print("4. Run the orchestrator again")
            print("")
            print(f"{'='*70}")
            print("")
            backup_names = ', '.join(BACKUP_SCRAPERS)
            user_choice = input(f"Continue with backup scrapers ({backup_names})? [y/N]: ").strip().lower()

            if user_choice != 'y':
                print("\n[STOPPED] Exiting to allow cookie refresh.")
                return 1

            print(f"\n[CONTINUING] Using backup scrapers without {config['display_name']}...")
            success = False

        lead_count = get_lead_count_from_output(output) if success else 0
        lead_file = find_latest_lead_file(config["output_dir"], config["output_prefix"])

        if lead_file and success:
            shutil.copy2(lead_file, campaign_folder / config["campaign_filename"])
            lead_sources.append((name, lead_file, lead_count))
            primary_lead_count += lead_count

    # Decision: Do we need backup scrapers?
    has_explicit_backups = selected_scrapers and (selected_scrapers & set(BACKUP_SCRAPERS))
    need_more = has_explicit_backups or args.force_multi_source or (primary_lead_count < args.target_leads)

    if not need_more and primary_lead_count > 0:
        print(f"\n{'='*70}")
        print(f"[FAST-TRACK] Primary got {primary_lead_count} leads (target: {args.target_leads})")
        print(f"[FAST-TRACK] Skipping additional scrapers (Saved ~10 minutes)")
        print(f"{'='*70}")
    else:
        # STEP 2: Run backup scrapers in parallel
        remaining = args.target_leads - primary_lead_count
        print(f"\n[DECISION] Need {remaining} more leads - running backup scrapers")

        # Determine which backup scrapers to run
        if selected_scrapers:
            backups_to_run = [s for s in BACKUP_SCRAPERS if s in selected_scrapers]
        else:
            # Auto-select: skip scrapers whose min_leads exceeds remaining (unless maximum mode)
            backups_to_run = []
            for name in BACKUP_SCRAPERS:
                cfg = SCRAPER_REGISTRY[name]
                min_leads = cfg.get("min_leads") or 0
                if min_leads > remaining and args.max_leads_mode != 'maximum':
                    continue
                backups_to_run.append(name)

        # Build commands using registry
        scrapers_to_run = []
        for name in backups_to_run:
            config = SCRAPER_REGISTRY[name]
            target = get_default_target(name, remaining, args.max_leads_mode)
            cmd = build_scraper_command(name, args.apollo_url, target, args.country)
            scrapers_to_run.append((name, cmd, config["timeout"]))

        if args.max_leads_mode == 'maximum':
            targets_str = ', '.join(
                f"{SCRAPER_REGISTRY[n]['display_name']}: {get_default_target(n, remaining, 'maximum')}"
                for n in backups_to_run
            )
            print(f"[MAX-MODE] Requesting maximum from each scraper ({targets_str})")

        # Run scrapers in parallel
        scraper_results = run_scraper_parallel(scrapers_to_run)

        # Collect results — registry-driven loop
        for name in backups_to_run:
            config = SCRAPER_REGISTRY[name]
            lead_file = find_latest_lead_file(config["output_dir"], config["output_prefix"])
            if lead_file and scraper_results.get(name, {}).get('success'):
                shutil.copy2(lead_file, campaign_folder / config["campaign_filename"])
                lead_sources.append((name, lead_file, scraper_results[name]['lead_count']))

    # STEP 3: Merge & deduplicate (if multiple sources)
    if len(lead_sources) > 1:
        source_args = ' '.join([f'--source-file "{path}"' for name, path, count in lead_sources])
        merge_cmd = f'py execution/leads_deduplicator.py {source_args} --output-dir "{campaign_folder}" --output-prefix "raw_leads"'
        merge_success, _, _ = run_command(merge_cmd, "Step 3: Merge & deduplicate sources", timeout=300)

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

    # STEP 4: Cross-campaign deduplication
    dedup_cmd = f'py execution/cross_campaign_deduplicator.py --client-id {args.client_id}'
    _, _, _ = run_command(dedup_cmd, "Step 4: Cross-campaign deduplication", timeout=300)

    # Refresh raw file path after deduplication
    raw_file = find_latest_lead_file(campaign_folder, 'raw_leads_')

    # STEP 4.5: Reference CSV deduplication (if --reference-csv provided)
    if args.reference_csv and raw_file:
        import csv
        print(f"\n{'='*70}")
        print(f"[STEP] Step 4.5: Reference CSV deduplication")
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

    # STEP 5: Country verification (if --country and not --skip-country-verify)
    if not args.skip_country_verify and args.country and raw_file:
        verify_cmd = f'py execution/verify_country.py --input "{raw_file}" --country {args.country} --output-dir "{campaign_folder}" --output-prefix "verified"'
        verify_success, _, verify_output = run_command(verify_cmd, "Step 5: Country verification", timeout=600)

        if verify_success:
            verified_file = find_latest_lead_file(campaign_folder, 'verified_')
            if verified_file:
                raw_file = verified_file
                print(f"[OK] Using verified leads: {verified_file}")
            else:
                print(f"[WARNING] No verified file found, continuing with unverified leads")
        else:
            print(f"[WARNING] Country verification failed, continuing with unverified leads")

    # STEP 5.5: Auto-derived quality filtering (if not --skip-quality-filter)
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
                    filter_args_list.extend(['--include-industries', ','.join(combined)])
        except Exception as e:
            print(f"[WARNING] Could not auto-derive industry whitelist: {e}")

        # Country-specific filters
        if args.country:
            filter_args_list.append('--remove-phone-discrepancies')
            filter_args_list.extend(['--remove-foreign-tld', args.country])

        filter_cmd = f'py execution/lead_filter.py --input "{raw_file}" --output-dir "{campaign_folder}" --output-prefix "filtered" {" ".join(filter_args_list)}'
        filter_success, _, _ = run_command(filter_cmd, "Step 5.5: Quality filtering", timeout=120)

        if filter_success:
            filtered_file = find_latest_lead_file(campaign_folder, 'filtered_')
            if filtered_file:
                raw_file = filtered_file
                print(f"[OK] Using filtered leads: {filtered_file}")
        else:
            print(f"[WARNING] Quality filtering failed, continuing with unfiltered leads")

    # STEP 6: Optional AI enrichment
    if args.enrich:
        print(f"\n[ENRICHMENT] Running AI enrichment (adds ~30-40 min)")

        # Casual names
        casual_cmd = f'py execution/ai_casual_name_generator.py --input "{raw_file}" --ai-provider openai'
        casual_success, _, _ = run_command(casual_cmd, "Step 6a: AI casual names", timeout=900)

        if casual_success:
            casual_file = str(raw_file).replace('.json', '_casual.json')
            if Path(casual_file).exists():
                raw_file = Path(casual_file)

        # Icebreakers
        icebreaker_cmd = f'py execution/ai_icebreaker_generator.py --input "{raw_file}" --ai-provider openai'
        icebreaker_success, _, _ = run_command(icebreaker_cmd, "Step 6b: AI icebreakers", timeout=1800)

        if icebreaker_success:
            icebreaker_file = str(raw_file).replace('.json', '_icebreakers.json')
            if Path(icebreaker_file).exists():
                raw_file = Path(icebreaker_file)

        # Fallback enrichment
        fallback_cmd = f'py execution/ai_fallback_enricher.py --input "{raw_file}"'
        _, _, _ = run_command(fallback_cmd, "Step 6c: AI fallback enrichment", timeout=600)

        # Update file path
        fallback_file = str(raw_file).replace('.json', '_fallback.json')
        if Path(fallback_file).exists():
            raw_file = Path(fallback_file)
    else:
        print(f"\n[FAST-TRACK] Skipping AI enrichment (Saved ~30-40 minutes)")

    # STEP 7: Upload to Google Sheets
    sheet_args = f'--input "{raw_file}"'
    if args.sheet_id:
        sheet_args += f' --sheet-id {args.sheet_id} --mode {args.sheet_mode}'
    else:
        sheet_title = f"{args.client_id.title()} - {args.campaign_name}"
        sheet_args += f' --sheet-title "{sheet_title}"'
    upload_cmd = f'py execution/google_sheets_exporter.py {sheet_args}'
    upload_success, _, upload_output = run_command(upload_cmd, "Step 7: Upload to Google Sheets", timeout=300)

    # Extract sheet URL
    sheet_url = None
    if upload_success:
        import re
        match = re.search(r'https://docs\.google\.com/spreadsheets/d/[^\s]+', upload_output)
        if match:
            sheet_url = match.group(0)

            # Save to campaign folder
            with open(campaign_folder / 'sheet_url.txt', 'w') as f:
                f.write(sheet_url)

    # STEP 8: Update client.json
    client_file = Path(f'campaigns/{args.client_id}/client.json')
    if client_file.exists():
        client_data = load_json(str(client_file))

        # Count final leads
        final_leads = load_leads(str(raw_file))
        final_count = len(final_leads)

        # Add campaign
        campaign_entry = {
            'campaign_id': campaign_id,
            'campaign_name': args.campaign_name,
            'type': 'apollo',
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'lead_count': final_count,
            'sheet_url': sheet_url or '',
            'sources': {name: count for name, _, count in lead_sources},
            'notes': f'Generated with fast orchestrator - {"with AI enrichment" if args.enrich else "fast-track"}'
        }

        client_data['campaigns'].append(campaign_entry)
        client_data['updated_at'] = datetime.utcnow().isoformat() + 'Z'

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

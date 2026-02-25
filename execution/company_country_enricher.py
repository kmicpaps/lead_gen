# [CLI] — run via: py execution/company_country_enricher.py --help
"""
Company Country Enrichment using Lead Magic Company Search API.
Looks up company_country for leads missing it, using company_domain.

Key optimization: deduplicates domains first — calls API once per unique domain,
then maps the result (headquarter country) back to ALL leads sharing that domain.

API: POST https://api.leadmagic.io/v1/companies/company-search
Cost: 1 credit per company found, FREE if not found
Rate limit: 500 requests/minute

Usage:
    py execution/company_country_enricher.py \
        --input .tmp/merged/example_client_latvia_final.json \
        --output-dir .tmp/enriched
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
from threading import Lock

load_dotenv()

# Rate limiting: 500 req/min = ~8.3 req/sec — use 7 to be safe
RATE_LIMIT = 7
MAX_WORKERS = 7

progress_lock = Lock()
progress = {
    'processed': 0,
    'found': 0,
    'found_with_country': 0,
    'not_found': 0,
    'errors': 0,
    'credits': 0,
}


def search_company(domain, api_key):
    """
    Look up a single domain via Lead Magic Company Search.
    Returns: (domain, result_dict) where result_dict has 'country', 'company_name', etc.
    """
    headers = {
        'X-API-Key': api_key,
        'Content-Type': 'application/json'
    }

    try:
        # Small delay for rate limiting (smoothing)
        time.sleep(1.0 / RATE_LIMIT)

        resp = requests.post(
            'https://api.leadmagic.io/v1/companies/company-search',
            json={'company_domain': domain},
            headers=headers,
            timeout=30
        )

        data = resp.json()
        credits = data.get('credits_consumed', 0)

        result = {
            'credits': credits,
            'found': credits > 0,
            'country': None,
            'hq_city': None,
            'company_name_api': data.get('companyName'),
            'industry_api': data.get('industry'),
            'employee_count': data.get('employeeCount'),
        }

        if credits > 0:
            # Extract country from headquarter first, then locations
            hq = data.get('headquarter') or {}
            if hq.get('country'):
                result['country'] = hq['country']
                result['hq_city'] = hq.get('city')
            else:
                # Fallback: check locations array for any with headquarter=True
                locations = data.get('locations') or []
                for loc in locations:
                    if loc.get('headquarter') and loc.get('country'):
                        result['country'] = loc['country']
                        result['hq_city'] = loc.get('city')
                        break
                # If still nothing, take first location with country
                if not result['country']:
                    for loc in locations:
                        if loc.get('country'):
                            result['country'] = loc['country']
                            result['hq_city'] = loc.get('city')
                            break

        return domain, result

    except requests.exceptions.Timeout:
        return domain, {'found': False, 'credits': 0, 'country': None, 'error': 'timeout'}
    except Exception as e:
        return domain, {'found': False, 'credits': 0, 'country': None, 'error': str(e)}


def enrich_domains(domains, api_key):
    """
    Look up all domains concurrently, return {domain: result} map.
    """
    global progress

    results = {}
    total = len(domains)
    start_time = time.time()

    print(f"Looking up {total} unique domains ({MAX_WORKERS} workers, {RATE_LIMIT}/sec)...")
    print(f"Estimated time: ~{total / RATE_LIMIT:.0f} seconds")
    print()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(search_company, domain, api_key): domain
            for domain in domains
        }

        for future in as_completed(futures):
            domain = futures[future]
            try:
                dom, result = future.result()
                results[dom] = result

                with progress_lock:
                    progress['processed'] += 1
                    progress['credits'] += result.get('credits', 0)

                    if result.get('error'):
                        progress['errors'] += 1
                    elif result['found']:
                        progress['found'] += 1
                        if result.get('country'):
                            progress['found_with_country'] += 1
                    else:
                        progress['not_found'] += 1

                    if progress['processed'] % 50 == 0:
                        elapsed = time.time() - start_time
                        rate = progress['processed'] / elapsed
                        pct = progress['processed'] / total * 100
                        print(f"  [{progress['processed']}/{total}] ({pct:.0f}%) "
                              f"found={progress['found']} "
                              f"w/country={progress['found_with_country']} "
                              f"not_found={progress['not_found']} "
                              f"credits={progress['credits']} "
                              f"({rate:.1f}/sec)")

            except Exception as e:
                results[domain] = {'found': False, 'credits': 0, 'country': None, 'error': str(e)}
                with progress_lock:
                    progress['processed'] += 1
                    progress['errors'] += 1

    elapsed = time.time() - start_time
    print(f"\nDomain lookup complete in {elapsed:.0f}s ({total / elapsed:.1f}/sec)")
    print(f"  Found: {progress['found']}/{total} ({progress['found']/total*100:.0f}%)")
    print(f"  Found w/ country: {progress['found_with_country']}/{total} ({progress['found_with_country']/total*100:.0f}%)")
    print(f"  Not found: {progress['not_found']}/{total}")
    print(f"  Errors: {progress['errors']}/{total}")
    print(f"  Credits consumed: {progress['credits']}")

    return results


def apply_to_leads(leads, domain_results):
    """
    Map domain lookup results back to leads. Only fills company_country if it was empty.
    Returns: (updated_leads, stats)
    """
    enriched = 0
    already_had = 0
    no_domain = 0
    no_result = 0

    country_counts = {}

    for lead in leads:
        if lead.get('company_country'):
            already_had += 1
            continue

        domain = lead.get('company_domain')
        if not domain:
            no_domain += 1
            continue

        result = domain_results.get(domain)
        if not result or not result.get('country'):
            no_result += 1
            continue

        country = result['country']
        lead['company_country'] = country
        lead['company_country_source'] = 'leadmagic_company_search'
        enriched += 1

        country_counts[country] = country_counts.get(country, 0) + 1

    stats = {
        'enriched': enriched,
        'already_had': already_had,
        'no_domain': no_domain,
        'no_result': no_result,
        'country_distribution': dict(sorted(country_counts.items(), key=lambda x: -x[1])),
    }

    return leads, stats


def main():
    parser = argparse.ArgumentParser(description='Enrich leads with company country via Lead Magic')
    parser.add_argument('--input', required=True, help='Path to leads JSON file')
    parser.add_argument('--output-dir', default='.tmp/enriched', help='Output directory')
    parser.add_argument('--output-prefix', default='country_enriched', help='Output filename prefix')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without calling API')

    args = parser.parse_args()

    api_key = os.getenv('LeadMagic-X-API-Key')
    if not api_key:
        print("Error: LeadMagic-X-API-Key not found in .env", file=sys.stderr)
        return 1

    # Fix Windows encoding for Latvian characters
    sys.stdout.reconfigure(encoding='utf-8')

    # Load leads
    print(f"Loading leads from: {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        leads = json.load(f)
    print(f"Loaded {len(leads)} leads")

    # Find leads needing enrichment
    needs_country = [l for l in leads if not l.get('company_country') and l.get('company_domain')]
    already_has = sum(1 for l in leads if l.get('company_country'))
    no_domain = sum(1 for l in leads if not l.get('company_country') and not l.get('company_domain'))

    print(f"  Already have company_country: {already_has}")
    print(f"  Need enrichment (have domain): {len(needs_country)}")
    print(f"  No domain available: {no_domain}")

    # Get unique domains
    unique_domains = list(set(l['company_domain'] for l in needs_country))
    print(f"  Unique domains to look up: {len(unique_domains)}")
    print(f"  Estimated max credits: ~{len(unique_domains)} (1 per found, free if not)")
    print()

    if args.dry_run:
        print("DRY RUN: Would look up the above domains. No API calls made.")
        return 0

    # Check credits first
    headers = {'X-API-Key': api_key, 'Content-Type': 'application/json'}
    try:
        resp = requests.post('https://api.leadmagic.io/credits', headers=headers, timeout=15)
        credits_data = resp.json()
        current_credits = credits_data.get('credits', 0)
        print(f"Current credit balance: {current_credits:.0f}")
        if current_credits < len(unique_domains):
            print(f"WARNING: May not have enough credits ({current_credits:.0f} < {len(unique_domains)} domains)")
        print()
    except Exception:
        pass

    # Run domain lookups
    domain_results = enrich_domains(unique_domains, api_key)

    # Apply results to leads
    print("\nApplying results to leads...")
    leads, stats = apply_to_leads(leads, domain_results)

    print(f"\n{'='*60}")
    print("ENRICHMENT RESULTS")
    print(f"{'='*60}")
    print(f"  Leads enriched with new country: {stats['enriched']}")
    print(f"  Already had country: {stats['already_had']}")
    print(f"  No domain to look up: {stats['no_domain']}")
    print(f"  Domain lookup returned no country: {stats['no_result']}")
    print(f"\n  Total with company_country now: {stats['already_had'] + stats['enriched']}/{len(leads)}")

    if stats['country_distribution']:
        print(f"\n  New countries added:")
        for country, count in stats['country_distribution'].items():
            print(f"    {country}: {count}")

    # Save
    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{args.output_prefix}_{ts}_{len(leads)}leads.json"
    filepath = os.path.join(args.output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)

    print(f"\nEnriched leads saved: {filepath}")
    print(filepath)

    # Also save the domain results map for reference
    domain_map_path = os.path.join(args.output_dir, f"domain_country_map_{ts}.json")
    with open(domain_map_path, 'w', encoding='utf-8') as f:
        json.dump(domain_results, f, indent=2, ensure_ascii=False)
    print(f"Domain map saved: {domain_map_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

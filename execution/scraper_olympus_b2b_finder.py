# [CLI] : run via: py execution/scraper_olympus_b2b_finder.py --help
"""
Apify B2B Leads Finder Scraper (olympus/b2b-leads-finder)

Since ~Sep 2026 the actor is "[NO COOKIES]": it NO LONGER accepts an Apollo
searchUrl or cookies. Any searchUrl sent is silently ignored and the actor
scrapes its whole database (~133M leads). It now takes structured filters
(seniority, companyCountry, industry, webKeywords, ...), same shape as PeakyDev.

This script parses the Apollo URL, maps it to those fields, and validates every
value against the actor's LIVE input schema before starting a run. If any value
doesn't map, or no real filter survives, it refuses to run (exit 3) rather than
scrape unfiltered.

Emails: the actor has no email-status filter. Output emails equal the
`emailPatternGuess` field, i.e. pattern-guessed, NOT Apollo-verified.
Normalized leads get email_status='guessed' so downstream steps know.

Old version (searchUrl + cookies): execution/_archived/scraper_olympus_b2b_finder_v1_searchurl.py

Usage:
    py execution/scraper_olympus_b2b_finder.py --apollo-url "..." --max-leads 1000 --dry-run
    py execution/scraper_olympus_b2b_finder.py --apollo-url "..." --max-leads 1000 \
        --output-dir .tmp/b2b_finder --output-prefix b2b_leads
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path
from apify_client import ApifyClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import save_json
from apollo_url_parser import parse_apollo_url

ACTOR_ID = "olympus/b2b-leads-finder"
MIN_RESULTS = 100  # actor rejects maxResults < 100


def load_apify_key():
    """Read APIFY_API_KEY from .env manually (load_dotenv chokes on multiline APOLLO_COOKIE)."""
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('APIFY_API_KEY='):
                    return line.split('=', 1)[1].strip()
    except FileNotFoundError:
        pass
    return os.getenv('APIFY_API_KEY')


def fetch_input_schema(api_key):
    """Fetch the actor's current input schema (free API call) -> properties dict."""
    base = "https://api.apify.com/v2"
    act = requests.get(f"{base}/acts/{ACTOR_ID.replace('/', '~')}",
                       params={'token': api_key}, timeout=30).json()['data']
    build_id = act['taggedBuilds']['latest']['buildId']
    build = requests.get(f"{base}/actor-builds/{build_id}",
                         params={'token': api_key}, timeout=30).json()['data']
    schema = build.get('inputSchema') or build.get('actorDefinition', {}).get('input')
    if isinstance(schema, str):
        schema = json.loads(schema)
    return schema['properties']


def enum_for(props, field):
    """Allowed values for an array/select field, or None for free-text fields."""
    p = props.get(field, {})
    items = p.get('items') if isinstance(p.get('items'), dict) else {}
    return p.get('enum') or items.get('enum')


def match_enum(values, allowed, field, errors):
    """Case-insensitive match of values to the schema enum. Unmatched -> errors."""
    lookup = {a.lower(): a for a in allowed}
    out = []
    for v in values:
        hit = lookup.get(v.strip().lower())
        if hit:
            if hit not in out:
                out.append(hit)
        else:
            errors.append(f"{field}: '{v}' is not an accepted value")
    return out


def map_company_size(apollo_sizes, allowed, errors):
    """Apollo '11,50' / '10001,' -> actor '11 - 50' / '10001+'."""
    out = []
    for s in apollo_sizes:
        lo, _, hi = s.partition(',')
        label = f"{lo.strip()}+" if not hi.strip() else f"{lo.strip()} - {hi.strip()}"
        if label in allowed:
            if label not in out:
                out.append(label)
        else:
            errors.append(f"companyEmployeeSize: Apollo range '{s}' has no exact match in {allowed}")
    return out


def build_run_input(apollo_filters, max_leads, props):
    """Map parsed Apollo filters to actor input. Returns (run_input, errors, warnings)."""
    errors, warnings = [], []
    run_input = {'maxResults': max(MIN_RESULTS, max_leads)}

    if apollo_filters.get('seniority'):
        run_input['seniority'] = match_enum(apollo_filters['seniority'],
                                            enum_for(props, 'seniority'), 'seniority', errors)
    if apollo_filters.get('org_locations'):
        run_input['companyCountry'] = match_enum(apollo_filters['org_locations'],
                                                 enum_for(props, 'companyCountry'), 'companyCountry', errors)
    if apollo_filters.get('locations'):
        run_input['personCountry'] = match_enum(apollo_filters['locations'],
                                                enum_for(props, 'personCountry'), 'personCountry', errors)
    if apollo_filters.get('industries'):
        if apollo_filters.get('industries_unresolved'):
            errors.append(f"industry: unresolved Apollo IDs {apollo_filters['industries_unresolved']} "
                          f"(add with apollo_industry_resolver.py --add)")
        run_input['industry'] = match_enum(apollo_filters.get('industries_resolved', []),
                                           enum_for(props, 'industry'), 'industry', errors)
    if apollo_filters.get('keywords'):
        # Dedup case-insensitively, keep first spelling
        seen, kws = set(), []
        for k in apollo_filters['keywords']:
            if k.strip().lower() not in seen:
                seen.add(k.strip().lower())
                kws.append(k.strip())
        run_input['webKeywords'] = kws[:100]
    if apollo_filters.get('titles'):
        run_input['personTitle'] = [t.strip() for t in apollo_filters['titles']][:100]
    if apollo_filters.get('company_size'):
        run_input['companyEmployeeSize'] = map_company_size(apollo_filters['company_size'],
                                                            enum_for(props, 'companyEmployeeSize'), errors)

    # Filters the actor cannot apply
    if apollo_filters.get('email_status'):
        warnings.append(f"email status {apollo_filters['email_status']} NOT supported: "
                        f"output emails are pattern guesses, not verified")
    if apollo_filters.get('revenue'):
        warnings.append("revenue filter not mapped (actor uses fixed buckets), dropped")
    if apollo_filters.get('functions'):
        warnings.append("department/function filter not mapped, dropped")

    # Any field the schema doesn't know means the actor changed again
    for field in run_input:
        if field not in props:
            errors.append(f"field '{field}' no longer exists in actor schema")

    # Safety: never scrape with location as the only filter
    narrowing = [f for f in ('seniority', 'industry', 'webKeywords', 'personTitle', 'companyEmployeeSize')
                 if run_input.get(f)]
    if not narrowing:
        errors.append("no narrowing filter survived mapping (only location/none), refusing to scrape")

    return run_input, errors, warnings


def normalize_lead_to_schema(lead):
    """Normalize new-format (camelCase, organization*) actor output to standard schema."""
    first = lead.get('firstName') or ''
    last = lead.get('lastName') or ''
    email = lead.get('email') or ''
    guess = lead.get('emailPatternGuess') or ''
    website = lead.get('organizationWebsite') or ''
    if website and not website.startswith('http'):
        website = f"https://{website}"
    keywords = lead.get('organizationKeywords') or []
    return {
        'first_name': first,
        'last_name': last,
        'name': f"{first} {last}".strip(),
        'organization_phone': lead.get('organizationPhone') or lead.get('phone') or '',
        'linkedin_url': lead.get('linkedinUrl') or '',
        'title': lead.get('title') or '',
        'email_status': 'guessed' if email and email == guess else ('unknown' if email else ''),
        'email': email,
        'city': lead.get('city') or '',
        'state': lead.get('state') or '',
        'country': lead.get('country') or '',
        'org_name': lead.get('organizationName') or '',
        'company_name': lead.get('organizationName') or '',
        'website_url': website,
        'company_domain': (lead.get('organizationWebsite') or '').replace('https://', '').replace('http://', '').strip('/'),
        'industry': lead.get('organizationIndustry') or '',
        'org_keywords': keywords[:10],
        'org_linkedin': lead.get('organizationLinkedinUrl') or '',
        'company_linkedin': lead.get('organizationLinkedinUrl') or '',
        'org_employee_count': lead.get('organizationSize'),
        'org_employee_range': lead.get('organizationEmployeeRange') or '',
        'org_founded_year': lead.get('organizationFoundedYear'),
        'company_city': lead.get('organizationCity') or '',
        'company_country': lead.get('organizationCountry') or '',
        'company_revenue': lead.get('organizationRevenue') or '',
        'seniority': lead.get('seniority') or '',
        'departments': [lead['department']] if lead.get('department') else [],
        'headline': '',
        'source': 'olympus'
    }


def main():
    parser = argparse.ArgumentParser(description='Apify B2B Leads Finder Scraper (structured filters)')
    parser.add_argument('--apollo-url', required=True, help='Apollo search URL (parsed into filters)')
    parser.add_argument('--max-leads', type=int, default=5000, help=f'Maximum leads (actor minimum {MIN_RESULTS})')
    parser.add_argument('--output-dir', default='.tmp/b2b_finder', help='Output directory')
    parser.add_argument('--output-prefix', default='b2b_leads', help='Output file prefix')
    parser.add_argument('--country', default=None, help='Ignored (kept for orchestrator compatibility)')
    parser.add_argument('--dry-run', action='store_true', help='Print the exact actor input and exit (no cost)')
    args = parser.parse_args()

    apify_api_key = load_apify_key()
    if not apify_api_key:
        print("Error: APIFY_API_KEY not found in .env", file=sys.stderr)
        return 1

    apollo_filters = parse_apollo_url(args.apollo_url)
    try:
        props = fetch_input_schema(apify_api_key)
    except Exception as e:
        print(f"Error: could not fetch actor input schema ({e}), refusing to run blind", file=sys.stderr)
        return 1

    run_input, errors, warnings = build_run_input(apollo_filters, args.max_leads, props)

    print("Olympus actor input (validated against live schema):")
    print(json.dumps(run_input, indent=2, ensure_ascii=False))
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    if errors:
        print("\nFILTER MAPPING FAILED, not starting a run:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 3
    if args.dry_run:
        print("\n[DRY RUN] Input valid. No run started.")
        return 0

    try:
        client = ApifyClient(apify_api_key)
        print(f"\nStarting Apify actor run: {ACTOR_ID} (maxResults={run_input['maxResults']})")
        started_run = client.actor(ACTOR_ID).start(run_input=run_input)
        run_id = started_run['id']
        print(f"Actor run ID: {run_id}")

        # Save run ID for recovery (if local process is killed, Apify run continues)
        run_id_file = Path(args.output_dir) / '.active_run.json'
        save_json({'run_id': run_id, 'actor': ACTOR_ID,
                   'started_at': datetime.now().isoformat()}, str(run_id_file), mkdir=True)

        print("Waiting for actor to complete...")
        run = client.run(run_id).wait_for_finish()
        run_id_file.unlink(missing_ok=True)
        print(f"Status: {run['status']}")
        if run['status'] != 'SUCCEEDED':
            print(f"Error: Actor run ended with status {run['status']}: {run.get('statusMessage', '')}",
                  file=sys.stderr)
            # Keep partial data if the run was cut short (e.g. budget cap), fail otherwise
            if run['status'] not in ('ABORTED', 'TIMED-OUT'):
                return 1

        dataset_items = list(client.dataset(run['defaultDatasetId']).iterate_items())
        # Drop status/notification rows (e.g. {"firstName": "Check the log ..."})
        real_leads = [i for i in dataset_items if i.get('employee_id') or i.get('email') or i.get('organizationName')]
        if len(real_leads) < len(dataset_items):
            print(f"Filtered out {len(dataset_items) - len(real_leads)} status messages from actor output")
        if not real_leads:
            print("Warning: No leads returned (filters too narrow?)", file=sys.stderr)
            return 1

        normalized_leads = [normalize_lead_to_schema(lead) for lead in real_leads]

        os.makedirs(args.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(args.output_dir,
                                f"{args.output_prefix}_{timestamp}_{len(normalized_leads)}leads.json")
        save_json(normalized_leads, filepath)

        print(f"Successfully scraped {len(normalized_leads)} leads (requested {run_input['maxResults']}).")
        print(filepath)  # Last stdout line = filepath, captured by the orchestrator
        return 0

    except KeyboardInterrupt:
        print("\nInterrupted locally. The Apify run continues; see .active_run.json for its ID.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error running {ACTOR_ID}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

# [CLI] — run via: py execution/apollo_industry_fetcher.py --help
"""
Apollo Industry Tag Fetcher

Fetches the complete industry hex ID → name mapping from Apollo's internal API
using session cookies. Falls back to parsing a manually captured DevTools response.

Usage:
    # Auto-fetch from Apollo API (requires valid cookies in .env)
    py execution/apollo_industry_fetcher.py --fetch

    # Parse a saved JSON response from browser DevTools
    py execution/apollo_industry_fetcher.py --parse-response response.json

    # Dry run (show what would be saved without writing)
    py execution/apollo_industry_fetcher.py --fetch --dry-run
"""

import os
import sys
import json
import re
import argparse
import time

# Add parent dir for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_json, save_json

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_LEARNED_MAPPINGS_FILE = os.path.join(_SCRIPT_DIR, "apollo_industry_learned_mappings.json")
_ENV_FILE = os.path.join(_SCRIPT_DIR, "..", ".env")


def load_apollo_cookies():
    """Load Apollo session cookies from .env file.
    Returns dict of {cookie_name: cookie_value} for use in requests.
    """
    try:
        with open(_ENV_FILE, 'r', encoding='utf-8') as f:
            env_content = f.read()
    except FileNotFoundError:
        print("Error: .env file not found", file=sys.stderr)
        return None

    match = re.search(r'(?:^|\n)APOLLO_COOKIE=(\[.*?\n\])', env_content, re.DOTALL | re.MULTILINE)
    if not match:
        print("Error: APOLLO_COOKIE not found in .env", file=sys.stderr)
        return None

    try:
        cookies_list = json.loads(match.group(1))
    except json.JSONDecodeError:
        try:
            cookies_list = json.loads(match.group(1).replace("'", '"'))
        except json.JSONDecodeError as e:
            print(f"Error: Could not parse APOLLO_COOKIE: {e}", file=sys.stderr)
            return None

    # Convert to {name: value} dict for requests
    cookies = {}
    for c in cookies_list:
        name = c.get('name', '')
        value = c.get('value', '')
        if name and value:
            cookies[name] = value

    return cookies


def load_existing_mappings():
    """Load existing learned mappings from JSON file."""
    if os.path.isfile(_LEARNED_MAPPINGS_FILE):
        try:
            return load_json(_LEARNED_MAPPINGS_FILE)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_mappings(mappings, dry_run=False):
    """Save mappings to the learned mappings JSON file."""
    if dry_run:
        print(f"\n[DRY RUN] Would save {len(mappings)} mappings to {_LEARNED_MAPPINGS_FILE}")
        return

    save_json(mappings, _LEARNED_MAPPINGS_FILE)
    print(f"\nSaved {len(mappings)} mappings to {os.path.basename(_LEARNED_MAPPINGS_FILE)}")


def get_linkedin_industries():
    """Import the LinkedIn industries set from apollo_industry_resolver."""
    try:
        from apollo_industry_resolver import LINKEDIN_INDUSTRIES
        return LINKEDIN_INDUSTRIES
    except ImportError:
        print("Warning: Could not import LINKEDIN_INDUSTRIES for validation", file=sys.stderr)
        return set()


def extract_mappings_from_tags(tags_data):
    """Extract {hex_id: industry_name} from Apollo tag search response.

    Apollo's tag search can return different shapes:
    - {"tags": [{"_id": "...", "name": "..."}, ...]}
    - [{"_id": "...", "name": "..."}, ...]
    - {"results": [{"_id": "...", "name": "..."}, ...]}
    - {"data": {"tags": [...]}}
    """
    mappings = {}

    # Normalize: find the array of tag objects
    tag_list = None
    if isinstance(tags_data, list):
        tag_list = tags_data
    elif isinstance(tags_data, dict):
        # Try common response shapes
        for key in ['tags', 'results', 'data', 'industry_tags', 'items',
                     'organization_industry_tag_ids']:
            if key in tags_data:
                val = tags_data[key]
                if isinstance(val, list):
                    tag_list = val
                    break
                elif isinstance(val, dict):
                    # Nested: data -> tags
                    for subkey in ['tags', 'results', 'items']:
                        if subkey in val and isinstance(val[subkey], list):
                            tag_list = val[subkey]
                            break
                    if tag_list:
                        break

        # Maybe the dict itself is {hex_id: name} already
        if tag_list is None:
            # Check if keys look like hex IDs
            hex_keys = [k for k in tags_data.keys() if re.match(r'^[0-9a-f]{24}$', k)]
            if hex_keys:
                for k in hex_keys:
                    if isinstance(tags_data[k], str):
                        mappings[k] = tags_data[k]
                return mappings

    if tag_list is None:
        return mappings

    # Extract from array of objects
    for tag in tag_list:
        if not isinstance(tag, dict):
            continue

        hex_id = tag.get('_id') or tag.get('id') or tag.get('tag_id') or tag.get('hex_id')
        name = tag.get('name') or tag.get('cleaned_name') or tag.get('label') or tag.get('display_name')

        if hex_id and name and re.match(r'^[0-9a-f]{24}$', str(hex_id)):
            # Title-case the name to match LinkedIn taxonomy
            mappings[str(hex_id)] = name.title() if name == name.lower() else name

    return mappings


def fetch_from_apollo(cookies, dry_run=False):
    """Try to fetch industry tags from Apollo's internal API.
    Tries multiple known endpoint patterns.
    """
    try:
        import requests
    except ImportError:
        print("Error: 'requests' package required. Install with: pip install requests",
              file=sys.stderr)
        return None

    # Build request headers mimicking browser
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Origin': 'https://app.apollo.io',
        'Referer': 'https://app.apollo.io/',
        'X-Requested-With': 'XMLHttpRequest',
    }

    # Extract CSRF token if present in cookies
    csrf_token = cookies.get('X-CSRF-TOKEN') or cookies.get('_csrf_token')
    if csrf_token:
        headers['X-CSRF-TOKEN'] = csrf_token

    # Build cookie header string
    cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())
    headers['Cookie'] = cookie_str

    session = requests.Session()
    session.headers.update(headers)

    # Endpoints to try, in order of likelihood
    endpoints = [
        # Tag search (most likely — what the industry dropdown calls)
        {
            'method': 'POST',
            'url': 'https://app.apollo.io/api/v1/tags/search',
            'json': {
                'q_tag_type': 'industry',
                'display_mode': 'explorer_mode',
                'per_page': 300,
                'page': 1,
            },
            'desc': 'POST /api/v1/tags/search (industry type)',
        },
        # Tag search with kind param
        {
            'method': 'POST',
            'url': 'https://app.apollo.io/api/v1/tags/search',
            'json': {
                'kind': 'industry',
                'per_page': 300,
                'page': 1,
            },
            'desc': 'POST /api/v1/tags/search (kind=industry)',
        },
        # Direct tag listing
        {
            'method': 'GET',
            'url': 'https://app.apollo.io/api/v1/tags',
            'params': {'type': 'industry', 'per_page': 300},
            'desc': 'GET /api/v1/tags?type=industry',
        },
        # Label/filter search
        {
            'method': 'POST',
            'url': 'https://app.apollo.io/api/v1/labels/search',
            'json': {
                'label_type': 'industry',
                'per_page': 300,
            },
            'desc': 'POST /api/v1/labels/search',
        },
        # Mixed search facets
        {
            'method': 'POST',
            'url': 'https://app.apollo.io/api/v1/mixed_people/search',
            'json': {
                'per_page': 1,
                'page': 1,
                'display_mode': 'explorer_mode',
                'finder_view_id': 'table',
                'prospected_by_current_team[]': ['no'],
            },
            'desc': 'POST /api/v1/mixed_people/search (for facets)',
        },
        # Organization industry tags
        {
            'method': 'POST',
            'url': 'https://app.apollo.io/api/v1/organization_industry_tag_ids/search',
            'json': {
                'per_page': 300,
            },
            'desc': 'POST /api/v1/organization_industry_tag_ids/search',
        },
        # Typeahead / autocomplete
        {
            'method': 'POST',
            'url': 'https://app.apollo.io/api/v1/typeaheads/search',
            'json': {
                'type': 'organization_industry_tag_id',
                'q': '',
                'per_page': 300,
            },
            'desc': 'POST /api/v1/typeaheads/search (industry)',
        },
        # Typeahead with different type name
        {
            'method': 'POST',
            'url': 'https://app.apollo.io/api/v1/typeaheads/search',
            'json': {
                'type': 'industry_tag',
                'q': '',
                'per_page': 300,
            },
            'desc': 'POST /api/v1/typeaheads/search (industry_tag)',
        },
    ]

    all_mappings = {}

    for ep in endpoints:
        desc = ep.pop('desc')
        method = ep.pop('method')
        url = ep.pop('url')

        print(f"\nTrying: {desc}")
        try:
            if method == 'POST':
                resp = session.request(method, url, timeout=15, **ep)
            else:
                resp = session.request(method, url, timeout=15, **ep)

            print(f"  Status: {resp.status_code}")

            if resp.status_code == 401 or resp.status_code == 403:
                print("  -> Authentication failed. Cookies may be expired.", file=sys.stderr)
                continue

            if resp.status_code == 404:
                print("  -> Endpoint not found.")
                continue

            if resp.status_code == 422:
                print("  -> Unprocessable entity (wrong parameters).")
                # Show error body for debugging
                try:
                    err = resp.json()
                    print(f"  -> Error: {json.dumps(err, indent=2)[:500]}")
                except Exception:
                    pass
                continue

            if resp.status_code != 200:
                print(f"  -> Unexpected status.")
                continue

            # Parse response
            try:
                data = resp.json()
            except json.JSONDecodeError:
                print("  -> Response is not JSON.")
                continue

            # Show response shape for debugging
            if isinstance(data, dict):
                keys = list(data.keys())[:10]
                print(f"  Response keys: {keys}")

                # Check for pagination info
                total = data.get('pagination', {}).get('total_entries') or data.get('total') or data.get('num_results')
                if total:
                    print(f"  Total entries: {total}")

            # Try to extract mappings
            mappings = extract_mappings_from_tags(data)
            if mappings:
                print(f"  Found {len(mappings)} industry mappings!")
                all_mappings.update(mappings)

                # If we got a good number, we can check for pagination
                if isinstance(data, dict):
                    total = data.get('pagination', {}).get('total_entries') or data.get('total')
                    if total and int(total) > len(mappings):
                        print(f"  Paginating: {len(mappings)} of {total}...")
                        page = 2
                        while len(all_mappings) < int(total) and page < 10:
                            time.sleep(0.5)
                            if method == 'POST':
                                body = ep.get('json', {}).copy()
                                body['page'] = page
                                resp2 = session.post(url, json=body, timeout=15)
                            else:
                                params = ep.get('params', {}).copy()
                                params['page'] = page
                                resp2 = session.get(url, params=params, timeout=15)

                            if resp2.status_code != 200:
                                break
                            data2 = resp2.json()
                            more = extract_mappings_from_tags(data2)
                            if not more:
                                break
                            all_mappings.update(more)
                            print(f"  Page {page}: +{len(more)} (total: {len(all_mappings)})")
                            page += 1

                # If we got 100+ mappings, that's likely the full set
                if len(all_mappings) >= 100:
                    print(f"\n  Got {len(all_mappings)} mappings — likely complete!")
                    return all_mappings
            else:
                # Show snippet of response for debugging
                snippet = json.dumps(data, indent=2)[:800]
                print(f"  No mappings extracted. Response snippet:\n{snippet}")

        except requests.exceptions.Timeout:
            print("  -> Request timed out.")
        except requests.exceptions.ConnectionError as e:
            print(f"  -> Connection error: {e}")
        except Exception as e:
            print(f"  -> Error: {e}")

    # Return whatever we found (might be partial or empty)
    if all_mappings:
        print(f"\nCollected {len(all_mappings)} mappings across endpoints (may be partial).")
    return all_mappings if all_mappings else None


def parse_response_file(filepath):
    """Parse a saved JSON response from browser DevTools.

    The user captures the network response when Apollo's industry filter
    dropdown loads. The response might be in various formats depending
    on the exact endpoint captured.
    """
    try:
        data = load_json(filepath)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return None

    mappings = extract_mappings_from_tags(data)
    if not mappings:
        print(f"Could not extract mappings from {filepath}.", file=sys.stderr)
        print("Expected format: array of objects with '_id' and 'name' fields,", file=sys.stderr)
        print("or a dict with 'tags'/'results' key containing such an array.", file=sys.stderr)

        # Show structure hint
        if isinstance(data, dict):
            print(f"\nFound keys: {list(data.keys())[:15]}", file=sys.stderr)
            for k, v in data.items():
                if isinstance(v, list) and v:
                    print(f"  '{k}' is a list of {len(v)} items. First item keys: "
                          f"{list(v[0].keys()) if isinstance(v[0], dict) else type(v[0]).__name__}",
                          file=sys.stderr)
        elif isinstance(data, list):
            print(f"\nFound array of {len(data)} items.", file=sys.stderr)
            if data and isinstance(data[0], dict):
                print(f"First item keys: {list(data[0].keys())}", file=sys.stderr)

    return mappings


def parse_checklist_file(filepath):
    """Parse the industry_id_checklist.md file where the user pasted hex IDs.

    Expected format per line:
        - [ ] Industry Name: 5567xxxxxxxxxxxxxxxxxxxx
    or:
        - [ ] Industry Name: 5567xxxxxxxxxxxxxxxxxxxx (with optional trailing text)

    Lines without a hex ID (24 hex chars) are skipped.
    Already-mapped lines (- [x]) are also skipped.
    """
    mappings = {}
    skipped = 0

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except IOError as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return None

    for line in lines:
        line = line.strip()

        # Skip already-mapped lines
        if line.startswith('- [x]'):
            continue

        # Match: - [ ] Industry Name: HEX_ID
        match = re.match(r'^- \[ \] (.+?):\s*([0-9a-f]{24})', line)
        if match:
            name = match.group(1).strip()
            hex_id = match.group(2).strip()
            mappings[hex_id] = name

        # Also match lines where user might have pasted without the checkbox
        elif ':' in line and not line.startswith('#') and not line.startswith('-'):
            parts = line.split(':', 1)
            if len(parts) == 2:
                hex_match = re.search(r'([0-9a-f]{24})', parts[1])
                if hex_match:
                    mappings[hex_match.group(1)] = parts[0].strip()

    if not mappings:
        print(f"No hex IDs found in {filepath}.", file=sys.stderr)
        print("Paste the hex ID after the colon for each industry, e.g.:", file=sys.stderr)
        print("  - [ ] Accounting: 5567cd4773696439b1370000", file=sys.stderr)
        return None

    print(f"Parsed {len(mappings)} industry mappings from checklist.")
    return mappings


def merge_and_report(new_mappings, dry_run=False):
    """Merge new mappings with existing ones and report results."""
    existing = load_existing_mappings()
    linkedin = get_linkedin_industries()

    added = 0
    updated = 0
    skipped = 0
    conflicts = []
    unvalidated = []

    merged = dict(existing)  # Start from existing

    for hex_id, name in new_mappings.items():
        # Normalize name
        if name == name.lower():
            name = name.title()
        # Fix common Apollo vs LinkedIn naming
        name = name.replace(' And ', ' & ')

        if hex_id in merged:
            if merged[hex_id] == name:
                skipped += 1
            else:
                conflicts.append((hex_id, merged[hex_id], name))
                skipped += 1  # Don't overwrite
        else:
            merged[hex_id] = name
            added += 1

        # Validate against LinkedIn taxonomy
        if linkedin and name not in linkedin:
            # Try common variations
            alt = name.replace(' & ', ' And ')
            if alt not in linkedin:
                unvalidated.append(name)

    # Report
    print(f"\n{'='*50}")
    print(f"MAPPING RESULTS")
    print(f"{'='*50}")
    print(f"  New fetched:     {len(new_mappings)}")
    print(f"  Already known:   {skipped}")
    print(f"  New to add:      {added}")
    print(f"  Total after merge: {len(merged)}")
    print(f"  LinkedIn taxonomy: {len(linkedin)} industries")

    if conflicts:
        print(f"\n  CONFLICTS ({len(conflicts)}):")
        for hex_id, old_name, new_name in conflicts:
            print(f"    {hex_id}: '{old_name}' vs '{new_name}' (keeping existing)")

    if unvalidated:
        print(f"\n  NOT IN LINKEDIN TAXONOMY ({len(unvalidated)}):")
        for name in sorted(unvalidated)[:20]:
            print(f"    - {name}")
        if len(unvalidated) > 20:
            print(f"    ... and {len(unvalidated) - 20} more")

    coverage = len(merged) / len(linkedin) * 100 if linkedin else 0
    print(f"\n  Coverage: {len(merged)}/{len(linkedin)} ({coverage:.0f}%)")
    print(f"{'='*50}")

    # Save
    save_mappings(merged, dry_run=dry_run)

    return merged


def main():
    parser = argparse.ArgumentParser(
        description='Fetch complete Apollo industry hex ID → name mapping'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--fetch', action='store_true',
                       help='Auto-fetch from Apollo API using cookies from .env')
    group.add_argument('--parse-response', metavar='FILE',
                       help='Parse a saved JSON response from browser DevTools')
    group.add_argument('--parse-checklist', metavar='FILE',
                       help='Parse the industry_id_checklist.md with pasted hex IDs')

    parser.add_argument('--dry-run', action='store_true',
                        help='Show results without saving to disk')

    args = parser.parse_args()

    if args.fetch:
        cookies = load_apollo_cookies()
        if not cookies:
            print("\nCannot proceed without Apollo cookies.", file=sys.stderr)
            print("Either fix cookies in .env or use --parse-response instead.", file=sys.stderr)
            return 1

        print(f"Loaded {len(cookies)} cookies from .env")
        print("Attempting to fetch industry tags from Apollo API...")

        new_mappings = fetch_from_apollo(cookies, dry_run=args.dry_run)

        if not new_mappings:
            print("\n" + "="*50, file=sys.stderr)
            print("AUTO-FETCH FAILED", file=sys.stderr)
            print("="*50, file=sys.stderr)
            print("\nFallback: Capture the response manually from browser DevTools:", file=sys.stderr)
            print("  1. Open https://app.apollo.io/#/people in Chrome", file=sys.stderr)
            print("  2. Open DevTools (F12) → Network tab → filter 'XHR/Fetch'", file=sys.stderr)
            print("  3. Click the 'Industry' filter in the sidebar", file=sys.stderr)
            print("  4. Look for a request to /tags/search or /typeaheads/search", file=sys.stderr)
            print("  5. Right-click → Copy → Copy Response", file=sys.stderr)
            print("  6. Save to a .json file", file=sys.stderr)
            print(f"  7. Run: py execution/apollo_industry_fetcher.py --parse-response FILE.json",
                  file=sys.stderr)
            return 1

        merge_and_report(new_mappings, dry_run=args.dry_run)
        return 0

    elif args.parse_response:
        new_mappings = parse_response_file(args.parse_response)
        if not new_mappings:
            return 1

        merge_and_report(new_mappings, dry_run=args.dry_run)
        return 0

    elif args.parse_checklist:
        new_mappings = parse_checklist_file(args.parse_checklist)
        if not new_mappings:
            return 1

        merge_and_report(new_mappings, dry_run=args.dry_run)
        return 0


if __name__ == '__main__':
    sys.exit(main())

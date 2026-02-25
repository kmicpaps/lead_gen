# [CLI] — run via: py execution/apollo_url_builder.py --help
"""
Apollo URL Builder

Constructs Apollo.io search URLs from structured filter parameters.
The inverse of apollo_url_parser.py — takes filters in, produces a URL.

Supports two input modes:
  1. CLI flags (--titles, --industries, etc.)
  2. JSON file (--from-json) using the same schema as apollo_url_parser output

Industries are specified by name (e.g., "Construction") and automatically
converted to Apollo hex IDs using apollo_industry_resolver.

Usage:
    # CLI flags
    py execution/apollo_url_builder.py \
        --titles "CEO,CFO,Managing Director" \
        --seniority "c_suite,vp,director" \
        --industries "Construction,Building Materials,Civil Engineering" \
        --org-locations "Latvia" \
        --company-size "11,50" "51,200" \
        --keywords "HVAC,prefab"

    # From JSON
    py execution/apollo_url_builder.py --from-json .tmp/url_draft.json

    # Round-trip validation (build then parse back)
    py execution/apollo_url_builder.py --from-json filters.json --validate
"""

import sys
import os
import json
import argparse
from urllib.parse import quote

# Add execution/ to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apollo_industry_resolver import resolve_industry_names_to_hex, LINKEDIN_INDUSTRIES

APOLLO_BASE_URL = "https://app.apollo.io/#/people"


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------

def build_apollo_url(filters: dict) -> tuple:
    """
    Build an Apollo search URL from a filter dictionary.

    Accepts filter dict with keys:
        titles: list[str]               - Job titles
        seniority: list[str]            - Seniority levels (c_suite, vp, director, etc.)
        industries: list[str]           - Industry NAMES (auto-converted to hex IDs)
        industries_resolved: list[str]  - Alias for industries (same behavior)
        keywords: list[str]             - Organization keyword tags
        locations: list[str]            - Person locations
        org_locations: list[str]        - Organization locations
        company_size: list[str]         - Size ranges (e.g., "11,50" or "51,200")
        email_status: list[str]         - Email status (e.g., "verified")
        functions: list[str]            - Person departments/functions
        revenue: dict                   - {"min": "X", "max": "Y"}
        funding: list[str]              - Funding types

    Returns: (url: str, warnings: list[str])
    """
    params = []
    warnings = []

    # --- Titles ---
    for title in filters.get("titles", []):
        params.append(f"personTitles[]={_encode(title)}")

    # --- Seniority ---
    for s in filters.get("seniority", []):
        params.append(f"personSeniorities[]={_encode(s)}")

    # --- Industries (name -> hex ID conversion) ---
    industry_names = filters.get("industries_resolved", []) or filters.get("industries", [])
    if industry_names:
        # Check if these look like hex IDs already (24-char hex strings)
        if all(_is_hex_id(name) for name in industry_names):
            # Already hex IDs, use directly
            for hex_id in industry_names:
                params.append(f"organizationIndustryTagIds[]={hex_id}")
        else:
            # Names — convert to hex IDs
            resolved, unresolved = resolve_industry_names_to_hex(industry_names)
            for name, hex_id in resolved.items():
                params.append(f"organizationIndustryTagIds[]={hex_id}")
            if unresolved:
                warnings.append(f"Could not resolve industries to hex IDs: {', '.join(unresolved)}")
                warnings.append("These industries will be MISSING from the URL.")

    # --- Keywords ---
    for kw in filters.get("keywords", []):
        params.append(f"qOrganizationKeywordTags[]={_encode(kw)}")

    # --- Person Locations ---
    for loc in filters.get("locations", []):
        params.append(f"personLocations[]={_encode(loc)}")

    # --- Org Locations ---
    for loc in filters.get("org_locations", []):
        params.append(f"organizationLocations[]={_encode(loc)}")

    # --- Company Size ---
    for size in filters.get("company_size", []):
        params.append(f"organizationNumEmployeesRanges[]={_encode(size)}")

    # --- Email Status ---
    for status in filters.get("email_status", []):
        params.append(f"contactEmailStatusV2[]={_encode(status)}")

    # --- Functions/Departments ---
    for func in filters.get("functions", []):
        params.append(f"personDepartments[]={_encode(func)}")

    # --- Revenue ---
    revenue = filters.get("revenue", {})
    if revenue.get("min"):
        params.append(f"organizationMinRevenue={revenue['min']}")
    if revenue.get("max"):
        params.append(f"organizationMaxRevenue={revenue['max']}")

    # --- Funding ---
    for fund in filters.get("funding", []):
        params.append(f"organizationFundingTypes[]={_encode(fund)}")

    # Build URL
    if params:
        url = f"{APOLLO_BASE_URL}?{'&'.join(params)}"
    else:
        url = APOLLO_BASE_URL
        warnings.append("No filters specified — URL will show all people.")

    return url, warnings


def _encode(value: str) -> str:
    """URL-encode a parameter value."""
    return quote(str(value), safe="")


def _is_hex_id(value: str) -> bool:
    """Check if a string looks like a 24-character hex ID."""
    import re
    return bool(re.match(r'^[0-9a-f]{24}$', value))


# ---------------------------------------------------------------------------
# Round-trip validation
# ---------------------------------------------------------------------------

def validate_round_trip(filters: dict) -> dict:
    """
    Build a URL from filters, then parse it back and compare.
    Returns dict with match status per filter key.
    """
    from apollo_url_parser import parse_apollo_url

    url, warnings = build_apollo_url(filters)
    parsed = parse_apollo_url(url)

    results = {}
    # Compare each filter category
    for key in ["titles", "seniority", "keywords", "locations", "org_locations",
                "company_size", "email_status", "functions", "funding"]:
        original = set(filters.get(key, []))
        parsed_val = set(parsed.get(key, []))
        if not original and not parsed_val:
            continue
        results[key] = {
            "match": original == parsed_val,
            "original": sorted(original),
            "parsed": sorted(parsed_val)
        }

    # Industries (compare resolved names)
    industry_names = set(filters.get("industries_resolved", []) or filters.get("industries", []))
    parsed_industries = set(parsed.get("industries_resolved", []))
    if industry_names or parsed_industries:
        # Filter out hex IDs from original (if user passed hex IDs)
        industry_names_clean = {n for n in industry_names if not _is_hex_id(n)}
        results["industries"] = {
            "match": industry_names_clean == parsed_industries or industry_names == parsed_industries,
            "original": sorted(industry_names),
            "parsed_resolved": sorted(parsed_industries)
        }

    # Revenue
    orig_rev = filters.get("revenue", {})
    parsed_rev = parsed.get("revenue", {})
    if orig_rev or parsed_rev:
        results["revenue"] = {
            "match": orig_rev == parsed_rev,
            "original": orig_rev,
            "parsed": parsed_rev
        }

    return results


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_summary(filters: dict, url: str, warnings: list):
    """Print a human-readable summary of the built URL."""
    from filter_gap_analyzer import FILTER_DISPLAY_NAMES

    print("\n=== APOLLO URL BUILDER ===\n")

    # Show filters
    filter_keys = ["titles", "seniority", "industries_resolved", "industries",
                   "keywords", "locations", "org_locations", "company_size",
                   "email_status", "functions", "revenue", "funding"]

    for key in filter_keys:
        val = filters.get(key, [])
        if not val:
            continue
        # Skip industries if industries_resolved is present
        if key == "industries" and filters.get("industries_resolved"):
            continue
        display_key = key.replace("industries_resolved", "industries")
        display_name = FILTER_DISPLAY_NAMES.get(display_key, display_key.replace("_", " ").title())
        if isinstance(val, dict):
            parts = [f"{k}={v}" for k, v in val.items() if v]
            print(f"  {display_name}: {', '.join(parts)}")
        elif isinstance(val, list):
            print(f"  {display_name}: {', '.join(str(v) for v in val)}")

    # Show warnings
    if warnings:
        print()
        for w in warnings:
            print(f"  WARNING: {w}")

    # Show URL
    print(f"\n  URL:\n  {url}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Build Apollo.io search URLs from filter parameters')
    parser.add_argument('--from-json', help='Path to JSON file with filter parameters')
    parser.add_argument('--titles', help='Comma-separated job titles')
    parser.add_argument('--seniority', help='Comma-separated seniority levels (c_suite,vp,director,manager,owner,founder,head,partner,senior,entry)')
    parser.add_argument('--industries', help='Comma-separated industry names (from LinkedIn taxonomy)')
    parser.add_argument('--keywords', help='Comma-separated organization keywords')
    parser.add_argument('--locations', help='Comma-separated person locations')
    parser.add_argument('--org-locations', help='Comma-separated organization locations')
    parser.add_argument('--company-size', nargs='+', help='Company size ranges (e.g., "1,10" "11,50" "51,200")')
    parser.add_argument('--email-status', help='Comma-separated email statuses (e.g., verified)')
    parser.add_argument('--functions', help='Comma-separated department/function names')
    parser.add_argument('--revenue-min', help='Minimum revenue')
    parser.add_argument('--revenue-max', help='Maximum revenue')
    parser.add_argument('--funding', help='Comma-separated funding types')
    parser.add_argument('--validate', action='store_true', help='Run round-trip validation (build then parse back)')
    parser.add_argument('--json', action='store_true', help='Output URL as JSON')
    parser.add_argument('--list-industries', action='store_true', help='List all available LinkedIn industries')

    args = parser.parse_args()

    # List industries mode
    if args.list_industries:
        print(f"LinkedIn V1 Industry Taxonomy ({len(LINKEDIN_INDUSTRIES)} industries):\n")
        for name in sorted(LINKEDIN_INDUSTRIES):
            print(f"  {name}")
        return 0

    # Build filters dict
    if args.from_json:
        with open(args.from_json, 'r', encoding='utf-8') as f:
            filters = json.load(f)
    else:
        filters = {}
        if args.titles:
            filters["titles"] = [t.strip() for t in args.titles.split(",")]
        if args.seniority:
            filters["seniority"] = [s.strip() for s in args.seniority.split(",")]
        if args.industries:
            filters["industries"] = [i.strip() for i in args.industries.split(",")]
        if args.keywords:
            filters["keywords"] = [k.strip() for k in args.keywords.split(",")]
        if args.locations:
            filters["locations"] = [l.strip() for l in args.locations.split(",")]
        if args.org_locations:
            filters["org_locations"] = [l.strip() for l in args.org_locations.split(",")]
        if args.company_size:
            filters["company_size"] = args.company_size
        if args.email_status:
            filters["email_status"] = [s.strip() for s in args.email_status.split(",")]
        if args.functions:
            filters["functions"] = [f.strip() for f in args.functions.split(",")]
        if args.revenue_min or args.revenue_max:
            filters["revenue"] = {}
            if args.revenue_min:
                filters["revenue"]["min"] = args.revenue_min
            if args.revenue_max:
                filters["revenue"]["max"] = args.revenue_max
        if args.funding:
            filters["funding"] = [f.strip() for f in args.funding.split(",")]

    if not filters:
        parser.print_help()
        return 1

    # Build URL
    url, warnings = build_apollo_url(filters)

    if args.json:
        print(json.dumps({"url": url, "warnings": warnings}, indent=2))
    else:
        print_summary(filters, url, warnings)

    # Round-trip validation
    if args.validate:
        print("=== ROUND-TRIP VALIDATION ===\n")
        results = validate_round_trip(filters)
        all_match = True
        for key, info in results.items():
            status = "OK" if info.get("match") else "MISMATCH"
            if not info.get("match"):
                all_match = False
            print(f"  {key}: {status}")
            if not info.get("match"):
                print(f"    Original: {info.get('original', info.get('original', '?'))}")
                parsed_key = 'parsed_resolved' if 'parsed_resolved' in info else 'parsed'
                print(f"    Parsed:   {info.get(parsed_key, '?')}")
        print()
        if all_match:
            print("  All filters round-trip correctly!")
        else:
            print("  WARNING: Some filters did not round-trip correctly.")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

# [CLI] — run via: py execution/filter_gap_analyzer.py --help
"""
Filter Gap Analyzer

Analyzes an Apollo URL and reports which filters each scraper supports vs drops.
Run BEFORE spending money on scrapers to understand data quality trade-offs.

Also calculates oversample multipliers: if a scraper drops title filters (which
typically remove 40-60% of leads), you should request 2-2.5x more leads and
post-filter them afterward.

Usage:
    py execution/filter_gap_analyzer.py --apollo-url "https://app.apollo.io/#/people?..."
    py execution/filter_gap_analyzer.py --apollo-url "URL" --json

Output:
    Table showing filter support per scraper, plus oversample recommendations.
"""

import sys
import os
import json
import argparse

# Add execution/ to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apollo_url_parser import parse_apollo_url
from scraper_registry import SCRAPER_SUPPORT

# Which dropped filters can be enforced post-scrape (matching against normalized lead fields)
POST_ENFORCEABLE = {
    "titles",       # match against lead.title (substring)
    "seniority",    # infer from lead.title (regex patterns)
    "locations",    # match against lead.country / lead.city
    "org_locations", # match against lead.company_country / lead.country
    "industries",   # match against lead.industry (already in lead_filter.py)
}

# Filters that CANNOT be enforced post-scrape (no data in normalized leads)
NOT_ENFORCEABLE = {
    "revenue",      # backup scrapers don't return company revenue
    "funding",      # backup scrapers don't return funding info
    "functions",    # PeakyDev doesn't return department data
    "email_status", # scrapers hardcode "validated" anyway
}

# Expected keep rates when post-filtering (conservative estimates)
FILTER_KEEP_RATES = {
    "titles": 0.45,       # Title filter typically keeps 35-55% of leads
    "seniority": 0.70,    # Seniority filter keeps ~60-80%
    "locations": 0.80,    # Location filter keeps ~70-90% (already partially filtered by org_location)
    "org_locations": 0.85, # Org location usually partially handled
}


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_filters(apollo_url: str) -> dict:
    """
    Analyze an Apollo URL and return filter gap analysis per scraper.

    Returns dict:
    {
        "active_filters": {"titles": [...], "seniority": [...], ...},
        "scrapers": {
            "olympus": { "supported": [...], "dropped_enforceable": [...], ... },
            "codecrafter": { ... },
            "peakydev": { ... }
        }
    }
    """
    filters = parse_apollo_url(apollo_url)

    # Determine which filter categories are active (non-empty) in this URL
    active_filters = {}
    filter_keys = ["titles", "seniority", "industries", "keywords", "locations",
                   "org_locations", "company_size", "email_status", "functions",
                   "revenue", "funding"]

    for key in filter_keys:
        val = filters.get(key, [])
        if key == "revenue":
            if val:  # revenue is a dict, truthy if has keys
                active_filters[key] = val
        elif val:
            active_filters[key] = val

    # Analyze each scraper
    result = {
        "active_filters": active_filters,
        "parsed_filters": filters,
        "scrapers": {}
    }

    for scraper_name, supported_set in SCRAPER_SUPPORT.items():
        supported = []
        dropped_enforceable = []
        dropped_not_enforceable = []

        for filter_key in active_filters:
            if filter_key in supported_set:
                supported.append(filter_key)
            elif filter_key in POST_ENFORCEABLE:
                dropped_enforceable.append(filter_key)
            else:
                dropped_not_enforceable.append(filter_key)

        # Calculate oversample multiplier
        multiplier = 1.0
        for dropped_filter in dropped_enforceable:
            keep_rate = FILTER_KEEP_RATES.get(dropped_filter, 0.70)
            multiplier /= keep_rate
        # Cap at 4x to avoid excessive costs
        multiplier = min(round(multiplier, 1), 4.0)

        result["scrapers"][scraper_name] = {
            "supported": supported,
            "dropped_enforceable": dropped_enforceable,
            "dropped_not_enforceable": dropped_not_enforceable,
            "oversample_multiplier": multiplier
        }

    return result


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

FILTER_DISPLAY_NAMES = {
    "titles": "Titles",
    "seniority": "Seniority",
    "industries": "Industries",
    "keywords": "Keywords",
    "locations": "Person Location",
    "org_locations": "Org Location",
    "company_size": "Company Size",
    "email_status": "Email Status",
    "functions": "Functions/Dept",
    "revenue": "Revenue Range",
    "funding": "Funding Type",
}


def print_table(analysis: dict):
    """Print a formatted table of filter support by scraper."""
    active = analysis["active_filters"]
    scrapers = analysis["scrapers"]

    if not active:
        print("No active filters found in the Apollo URL.")
        return

    print("\n=== FILTER GAP ANALYSIS ===\n")

    # Header
    header = f"  {'Filter':<20} {'Olympus':<12} {'CodeCrafter':<14} {'PeakyDev':<14}"
    print(header)
    print("  " + "-" * 58)

    for filter_key, values in active.items():
        display = FILTER_DISPLAY_NAMES.get(filter_key, filter_key)
        count = len(values) if isinstance(values, list) else 1
        label = f"{display} ({count})" if count > 1 else display

        cells = []
        for scraper_name in ["olympus", "codecrafter", "peakydev"]:
            info = scrapers[scraper_name]
            if filter_key in info["supported"]:
                cells.append("OK")
            elif filter_key in info["dropped_enforceable"]:
                cells.append("POST-FILTER")
            else:
                cells.append("DROPPED")

        print(f"  {label:<20} {cells[0]:<12} {cells[1]:<14} {cells[2]:<14}")

    print()

    # Summary per scraper
    for scraper_name in ["codecrafter", "peakydev"]:
        info = scrapers[scraper_name]
        if info["dropped_enforceable"] or info["dropped_not_enforceable"]:
            print(f"  {scraper_name}:")
            if info["dropped_enforceable"]:
                names = [FILTER_DISPLAY_NAMES.get(f, f) for f in info["dropped_enforceable"]]
                print(f"    Post-filterable: {', '.join(names)}")
            if info["dropped_not_enforceable"]:
                names = [FILTER_DISPLAY_NAMES.get(f, f) for f in info["dropped_not_enforceable"]]
                print(f"    NOT enforceable: {', '.join(names)}")
            if info["oversample_multiplier"] > 1.0:
                print(f"    Recommended oversample: {info['oversample_multiplier']}x")
            print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Analyze Apollo URL filter gaps per scraper')
    parser.add_argument('--apollo-url', required=True, help='Apollo.io search URL')
    parser.add_argument('--json', action='store_true', help='Output as JSON instead of table')
    args = parser.parse_args()

    analysis = analyze_filters(args.apollo_url)

    if args.json:
        # Remove parsed_filters from JSON output to keep it clean
        output = {
            "active_filters": {k: v for k, v in analysis["active_filters"].items()},
            "scrapers": analysis["scrapers"]
        }
        print(json.dumps(output, indent=2))
    else:
        print_table(analysis)

    return 0


if __name__ == "__main__":
    sys.exit(main())

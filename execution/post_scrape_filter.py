# [CLI] — run via: py execution/post_scrape_filter.py --help
"""
Post-Scrape Filter Enforcer

Applies Apollo URL filters that backup scrapers (CodeCrafter/PeakyDev) couldn't
handle during scraping. This compensates for filter gaps by removing leads that
don't match the original search intent.

Enforceable filters (match against normalized lead fields):
  - Titles: substring match on lead.title
  - Seniority: regex inference from lead.title
  - Person Location: substring match on lead.country / lead.city
  - Org Location: substring match on lead.company_country / lead.country
  - Industries: substring match on lead.industry using resolved industry names

NOT enforceable (data not available in normalized leads from backup scrapers):
  - Revenue, Funding, Functions/Departments

Usage:
    py execution/post_scrape_filter.py \
        --input .tmp/peakydev/peakydev_leads_*.json \
        --apollo-url "https://app.apollo.io/#/people?..." \
        --scraper peakydev \
        --output-dir .tmp/peakydev/

    py execution/post_scrape_filter.py \
        --input leads.json \
        --apollo-url "URL" \
        --scraper codecrafter
"""

import sys
import os
import json
import re
import argparse
import glob
from datetime import datetime

# Add execution/ to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apollo_url_parser import parse_apollo_url
from filter_gap_analyzer import analyze_filters
from scraper_registry import SCRAPER_SUPPORT
from utils import load_json, save_json


# ---------------------------------------------------------------------------
# Seniority inference from job titles
# ---------------------------------------------------------------------------

SENIORITY_TITLE_PATTERNS = {
    "owner": [r"\bowner\b", r"\bco-owner\b", r"\bco owner\b"],
    "founder": [r"\bfounder\b", r"\bco-founder\b", r"\bco founder\b"],
    "c_suite": [
        r"\bceo\b", r"\bcto\b", r"\bcfo\b", r"\bcoo\b", r"\bcmo\b", r"\bcio\b",
        r"\bchief\b", r"\bc\.e\.o\b", r"\bc\.t\.o\b",
    ],
    "vp": [r"\bvp\b", r"\bvice president\b", r"\bvice-president\b"],
    "director": [r"\bdirector\b"],
    "head": [r"\bhead of\b", r"\bhead,\b", r"\bhead\s"],
    "manager": [r"\bmanager\b", r"\bmanaging\b"],
    "partner": [r"\bpartner\b"],
    "senior": [r"\bsenior\b", r"\bsr\.\b", r"\bsr\s", r"\blead\b"],
    "entry": [r"\bjunior\b", r"\bintern\b", r"\btrainee\b", r"\bassistant\b(?!.*director|.*manager)"],
}


def infer_seniority(title: str) -> list:
    """
    Infer seniority level(s) from a job title using regex patterns.
    Returns list of matching seniority keys (e.g., ["c_suite", "founder"]).
    """
    if not title:
        return []
    title_lower = title.lower()
    matches = []
    for seniority_key, patterns in SENIORITY_TITLE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, title_lower):
                matches.append(seniority_key)
                break  # One match per seniority level is enough
    return matches


# ---------------------------------------------------------------------------
# Filter functions
# ---------------------------------------------------------------------------

def filter_by_titles(leads: list, required_titles: list) -> list:
    """Keep leads whose title contains any of the required title strings (case-insensitive)."""
    if not required_titles:
        return leads
    required_lower = [t.lower() for t in required_titles]
    kept = []
    for lead in leads:
        title = (lead.get("title") or "").lower()
        if not title:
            kept.append(lead)  # No title = can't verify, keep
            continue
        if any(req in title for req in required_lower):
            kept.append(lead)
    return kept


def filter_by_seniority(leads: list, required_seniorities: list) -> list:
    """Keep leads whose title implies one of the required seniority levels."""
    if not required_seniorities:
        return leads
    required_set = set(s.lower() for s in required_seniorities)
    kept = []
    for lead in leads:
        title = lead.get("title") or ""
        if not title:
            kept.append(lead)  # Keep leads with no title — can't determine seniority
            continue
        inferred = infer_seniority(title)
        if any(s in required_set for s in inferred):
            kept.append(lead)
    return kept


def filter_by_person_location(leads: list, required_locations: list) -> list:
    """Keep leads whose country/city matches any required location (substring, case-insensitive)."""
    if not required_locations:
        return leads
    required_lower = [loc.lower() for loc in required_locations]
    kept = []
    for lead in leads:
        country = (lead.get("country") or "").lower()
        city = (lead.get("city") or "").lower()
        combined = f"{city} {country}"
        if any(req in combined for req in required_lower):
            kept.append(lead)
    return kept


def filter_by_org_location(leads: list, required_locations: list) -> list:
    """Keep leads whose company country matches any required org location (substring, case-insensitive)."""
    if not required_locations:
        return leads
    required_lower = [loc.lower() for loc in required_locations]
    kept = []
    for lead in leads:
        company_country = (lead.get("company_country") or "").lower()
        country = (lead.get("country") or "").lower()
        combined = f"{company_country} {country}"
        if any(req in combined for req in required_lower):
            kept.append(lead)
    return kept


def filter_by_industry(leads: list, required_industries: list) -> list:
    """Keep leads whose industry matches any required industry keyword (substring, case-insensitive).

    Uses industries_resolved (human-readable names) from the parsed Apollo URL.
    Falls back to raw hex IDs if resolved names aren't available, but those
    won't match anything meaningful — the caller should ensure resolution.
    """
    if not required_industries:
        return leads
    required_lower = [ind.lower() for ind in required_industries]
    kept = []
    for lead in leads:
        industry = (lead.get("industry") or "").lower()
        if not industry:
            kept.append(lead)  # No industry data = can't verify, keep
            continue
        if any(req in industry for req in required_lower):
            kept.append(lead)
    return kept


# ---------------------------------------------------------------------------
# Main enforcement logic
# ---------------------------------------------------------------------------

def enforce_filters(leads: list, apollo_url: str, scraper: str) -> dict:
    """
    Apply enforceable filters that the specified scraper dropped.

    Returns dict with:
        - leads: filtered lead list
        - stages: list of {filter, before, after, kept_pct} for each stage
        - total_before: original count
        - total_after: final count
    """
    filters = parse_apollo_url(apollo_url)
    analysis = analyze_filters(apollo_url)
    scraper_info = analysis["scrapers"].get(scraper, {})
    dropped_enforceable = scraper_info.get("dropped_enforceable", [])

    stages = []
    current = leads[:]

    # Apply each enforceable filter that was dropped
    for filter_key in dropped_enforceable:
        before_count = len(current)

        if filter_key == "titles" and filters.get("titles"):
            current = filter_by_titles(current, filters["titles"])
        elif filter_key == "seniority" and filters.get("seniority"):
            current = filter_by_seniority(current, filters["seniority"])
        elif filter_key == "locations" and filters.get("locations"):
            current = filter_by_person_location(current, filters["locations"])
        elif filter_key == "org_locations" and filters.get("org_locations"):
            current = filter_by_org_location(current, filters["org_locations"])
        elif filter_key == "industries" and filters.get("industries_resolved"):
            # Use resolved human-readable names for substring matching
            current = filter_by_industry(current, filters["industries_resolved"])
        else:
            continue  # No values for this filter in the URL

        after_count = len(current)
        kept_pct = (after_count / before_count * 100) if before_count > 0 else 0
        stages.append({
            "filter": filter_key,
            "before": before_count,
            "after": after_count,
            "kept_pct": round(kept_pct, 1)
        })

    return {
        "leads": current,
        "stages": stages,
        "total_before": len(leads),
        "total_after": len(current),
        "dropped_not_enforceable": scraper_info.get("dropped_not_enforceable", [])
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Post-scrape filter enforcement')
    parser.add_argument('--input', required=True, help='Input leads JSON file (supports glob patterns)')
    parser.add_argument('--apollo-url', required=True, help='Original Apollo search URL')
    parser.add_argument('--scraper', required=True, choices=['codecrafter', 'peakydev'],
                        help='Which scraper produced the input (determines which filters were dropped)')
    parser.add_argument('--output-dir', help='Output directory (default: same as input)')
    parser.add_argument('--json', action='store_true', help='Output stats as JSON')

    args = parser.parse_args()

    # Resolve input file (support glob patterns)
    input_files = glob.glob(args.input)
    if not input_files:
        print(f"ERROR: No files matching '{args.input}'", file=sys.stderr)
        return 1

    # Load leads from all matching files
    all_leads = []
    for fpath in input_files:
        data = load_json(fpath)
        if isinstance(data, list):
            all_leads.extend(data)
        elif isinstance(data, dict) and 'leads' in data:
            all_leads.extend(data['leads'])
        else:
            print(f"WARNING: Unexpected format in {fpath}, skipping", file=sys.stderr)

    if not all_leads:
        print("ERROR: No leads loaded from input file(s)", file=sys.stderr)
        return 1

    # Run enforcement
    result = enforce_filters(all_leads, args.apollo_url, args.scraper)

    # Output
    if args.json:
        stats = {
            "scraper": args.scraper,
            "total_before": result["total_before"],
            "total_after": result["total_after"],
            "stages": result["stages"],
            "dropped_not_enforceable": result["dropped_not_enforceable"]
        }
        print(json.dumps(stats, indent=2))
    else:
        print(f"\nPost-scrape filter applied to {result['total_before']} {args.scraper} leads:")
        for stage in result["stages"]:
            print(f"  {stage['filter']}: {stage['before']} -> {stage['after']} (kept {stage['kept_pct']}%)")
        if not result["stages"]:
            print("  No enforceable filters to apply (scraper handled all active filters)")
        print(f"\n  Final: {result['total_after']} leads ({round(result['total_after'] / result['total_before'] * 100, 1) if result['total_before'] > 0 else 0}% of original)")

        if result["dropped_not_enforceable"]:
            from filter_gap_analyzer import FILTER_DISPLAY_NAMES
            names = [FILTER_DISPLAY_NAMES.get(f, f) for f in result["dropped_not_enforceable"]]
            print(f"\n  WARNING: These filters could NOT be enforced: {', '.join(names)}")
            print("  Leads may not match these criteria. Consider using Olympus for full filter fidelity.")

    # Save filtered leads
    output_dir = args.output_dir or os.path.dirname(input_files[0]) or '.'
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f"{args.scraper}_leads_postfiltered_{timestamp}.json")
    save_json(result["leads"], output_file)

    print(f"\n  Saved to: {output_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

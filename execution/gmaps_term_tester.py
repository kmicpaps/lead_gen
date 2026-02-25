# [CLI] — run via: py execution/gmaps_term_tester.py --help
#!/usr/bin/env python3
"""
Google Maps Search Term Tester

Tests multiple search terms against Google Maps to find which terms
yield the most results (with and without websites) for a given location.

Usage:
    py execution/gmaps_term_tester.py --terms-file .tmp/term_test/candidate_terms.json --location "Latvia" --country lv --limit 200
"""

import os
import sys
import argparse
import time
from datetime import datetime

# Fix Windows console encoding for Latvian diacritics
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from execution.scrape_google_maps import scrape_google_maps
from execution.utils import load_json, save_json


def test_term(term: str, location: str, country: str, limit: int) -> dict:
    """Test a single search term and return stats."""
    search_query = f"{term} in {location}"
    start_time = time.time()

    try:
        businesses = scrape_google_maps(
            search_query=search_query,
            limit=limit,
            country=country
        )
    except Exception as e:
        return {
            "term": term,
            "query": search_query,
            "total": 0,
            "with_website": 0,
            "no_website": 0,
            "no_website_pct": 0,
            "with_phone": 0,
            "error": str(e),
            "duration_sec": round(time.time() - start_time, 1),
            "businesses": []
        }

    with_website = sum(1 for b in businesses if b.get("website"))
    no_website = sum(1 for b in businesses if not b.get("website"))
    with_phone = sum(1 for b in businesses if b.get("phone"))
    total = len(businesses)

    return {
        "term": term,
        "query": search_query,
        "total": total,
        "with_website": with_website,
        "no_website": no_website,
        "no_website_pct": round(no_website / total * 100, 1) if total > 0 else 0,
        "with_phone": with_phone,
        "error": None,
        "duration_sec": round(time.time() - start_time, 1),
        "businesses": businesses
    }


def print_summary_table(results: list):
    """Print a formatted summary table of all test results."""
    # Sort by no_website count descending
    sorted_results = sorted(results, key=lambda r: r["no_website"], reverse=True)

    print("\n" + "=" * 90)
    print("SEARCH TERM TEST RESULTS")
    print("=" * 90)
    print(f"{'Niche':<12} {'Term':<25} {'Total':>6} {'Website':>8} {'No Web':>7} {'% NoWeb':>8} {'Phone':>6} {'Time':>6}")
    print("-" * 90)

    total_all = 0
    total_no_web = 0

    for r in sorted_results:
        niche = r.get("niche", "")
        status = "ERR" if r["error"] else ""
        print(
            f"{niche:<12} {r['term']:<25} {r['total']:>6} {r['with_website']:>8} "
            f"{r['no_website']:>7} {r['no_website_pct']:>7.1f}% {r['with_phone']:>6} "
            f"{r['duration_sec']:>5.0f}s {status}"
        )
        total_all += r["total"]
        total_no_web += r["no_website"]

    print("-" * 90)
    print(f"{'TOTALS':<12} {'(before dedup)':<25} {total_all:>6} {'':>8} {total_no_web:>7}")
    print("=" * 90)
    print("\nNote: totals include duplicates across terms. Actual unique leads will be lower.")


def main():
    parser = argparse.ArgumentParser(description="Test Google Maps search terms for lead yield")
    parser.add_argument("--terms-file", required=True, help="JSON file with {niche: [terms]} structure")
    parser.add_argument("--location", required=True, help="Location for search (e.g., 'Latvia')")
    parser.add_argument("--country", default="lv", help="Country code (default: lv)")
    parser.add_argument("--limit", type=int, default=200, help="Max results per term (default: 200)")
    parser.add_argument("--output-dir", default=".tmp/term_test", help="Directory for results (default: .tmp/term_test)")
    parser.add_argument("--niches", nargs="*", help="Only test specific niches (default: all)")
    args = parser.parse_args()

    # Load terms
    terms_by_niche = load_json(args.terms_file)

    # Filter niches if specified
    if args.niches:
        terms_by_niche = {k: v for k, v in terms_by_niche.items() if k in args.niches}

    # Count total terms
    total_terms = sum(len(terms) for terms in terms_by_niche.values())
    print(f"\nTesting {total_terms} search terms across {len(terms_by_niche)} niches")
    print(f"Location: {args.location} | Country: {args.country} | Limit: {args.limit}/term")
    print(f"Estimated time: {total_terms * 5}-{total_terms * 10} minutes\n")

    # Test each term
    all_results = []
    term_count = 0

    for niche, terms in terms_by_niche.items():
        print(f"\n{'='*60}")
        print(f"NICHE: {niche} ({len(terms)} terms)")
        print(f"{'='*60}")

        for term in terms:
            term_count += 1
            print(f"\n[{term_count}/{total_terms}] Testing: '{term}' ...")

            result = test_term(term, args.location, args.country, args.limit)
            result["niche"] = niche
            all_results.append(result)

            # Quick status
            if result["error"]:
                print(f"  ERROR: {result['error']}")
            else:
                print(f"  -> {result['total']} total, {result['no_website']} no-website ({result['no_website_pct']}%), {result['duration_sec']}s")

    # Print summary
    print_summary_table(all_results)

    # Save results (without full business data for the summary)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Summary file (without business details)
    summary = [{k: v for k, v in r.items() if k != "businesses"} for r in all_results]
    summary_path = os.path.join(args.output_dir, f"summary_{timestamp}.json")
    save_json(summary, summary_path, mkdir=True)
    print(f"\nSummary saved to: {summary_path}")

    # Full results with business data (for later use)
    full_path = os.path.join(args.output_dir, f"full_results_{timestamp}.json")
    save_json(all_results, full_path)
    print(f"Full results saved to: {full_path}")


if __name__ == "__main__":
    main()

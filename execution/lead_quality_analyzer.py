# [CLI] — run via: py execution/lead_quality_analyzer.py --help
"""
Lead Quality Analyzer
Parses an Apollo URL to understand what filters were applied, then analyzes
a scraped lead file against those filters. Produces a quality report with
breakdowns and recommendations that the AI agent presents to the user so
they can choose which filters to apply.

Usage:
    py execution/lead_quality_analyzer.py \
        --apollo-url "https://app.apollo.io/#/people?..." \
        --leads path/to/leads.json \
        [--output-dir path/to/dir]

Output:
    - Prints a human-readable quality report to stdout
    - Optionally saves a JSON report to output-dir
"""

import sys
import os
import re
import argparse
from collections import Counter
from datetime import datetime

# Add parent dir so we can import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_leads, save_json
from apollo_url_parser import parse_apollo_url
try:
    from lead_filter import COUNTRY_PHONE_CODES
    _KNOWN_PHONE_PREFIXES = set(COUNTRY_PHONE_CODES.values())
except ImportError:
    _KNOWN_PHONE_PREFIXES = set()


# ---------------------------------------------------------------------------
# Apollo industry ID -> human-readable name: use authoritative resolver (146 verified mappings)
# ---------------------------------------------------------------------------
try:
    from apollo_industry_resolver import resolve_industry_ids
except ImportError:
    def resolve_industry_ids(industry_ids):
        """Fallback: return all IDs as unresolved if resolver unavailable."""
        return [], list(industry_ids)


def describe_apollo_filters(filters):
    """
    Produce a human-readable description of what the Apollo URL was filtering for.
    Returns a list of description lines.
    """
    lines = []

    # Titles
    if filters.get("titles"):
        lines.append(f"  Titles: {', '.join(filters['titles'])}")

    # Seniority
    if filters.get("seniority"):
        lines.append(f"  Seniority: {', '.join(filters['seniority'])}")

    # Functions / Departments
    if filters.get("functions"):
        lines.append(f"  Departments: {', '.join(filters['functions'])}")

    # Person locations
    if filters.get("locations"):
        lines.append(f"  Person locations: {', '.join(filters['locations'])}")

    # Org locations
    if filters.get("org_locations"):
        lines.append(f"  Org locations: {', '.join(filters['org_locations'])}")

    # Industries — prefer pre-resolved names, fall back to local resolver
    if filters.get("industries_resolved"):
        lines.append(f"  Industries: {', '.join(filters['industries_resolved'])}")
    elif filters.get("industries"):
        resolved, unresolved = resolve_industry_ids(filters["industries"])
        if resolved:
            lines.append(f"  Industries: {', '.join(resolved)}")
        if unresolved:
            lines.append(f"  Industry IDs (unmapped): {', '.join(unresolved)}")

    # Company size
    if filters.get("company_size"):
        lines.append(f"  Company size: {', '.join(filters['company_size'])}")

    # Revenue
    if filters.get("revenue"):
        rev = filters["revenue"]
        parts = []
        if "min" in rev:
            parts.append(f"min ${int(rev['min']):,}")
        if "max" in rev:
            parts.append(f"max ${int(rev['max']):,}")
        lines.append(f"  Revenue: {', '.join(parts)}")

    # Keywords
    if filters.get("keywords"):
        lines.append(f"  Org keywords: {', '.join(filters['keywords'])}")

    # Email status
    if filters.get("email_status"):
        lines.append(f"  Email status: {', '.join(filters['email_status'])}")

    return lines


def analyze_leads(leads, filters):
    """
    Analyze lead data quality against what Apollo was filtering for.
    Returns a dict with all analysis results.
    """
    total = len(leads)
    if total == 0:
        return {"total": 0, "error": "No leads to analyze"}

    analysis = {"total": total}

    # --- Email coverage ---
    has_email = [l for l in leads if l.get("email")]
    analysis["email"] = {
        "has_email": len(has_email),
        "no_email": total - len(has_email),
        "pct": round(len(has_email) / total * 100, 1),
    }

    # --- Phone coverage & country codes ---
    has_phone = [l for l in leads if l.get("company_phone") or l.get("phone") or l.get("organization_phone")]
    phone_codes = Counter()
    for l in leads:
        phone = l.get("company_phone") or l.get("phone") or l.get("organization_phone") or ""
        phone = str(phone).strip()
        if phone.startswith("+"):
            # Extract country code using known-prefix longest match
            digits = phone[1:]
            matched = None
            if _KNOWN_PHONE_PREFIXES:
                for plen in (3, 2, 1):
                    if len(digits) >= plen:
                        candidate = f"+{digits[:plen]}"
                        if candidate in _KNOWN_PHONE_PREFIXES:
                            matched = candidate
                            break
            if not matched:
                # Fallback: take first 2 digits (most common code length)
                matched = f"+{digits[:min(2, len(digits))]}" if digits else "other"
            phone_codes[matched] += 1
        elif phone:
            phone_codes["no_code"] += 1

    analysis["phone"] = {
        "has_phone": len(has_phone),
        "no_phone": total - len(has_phone),
        "pct": round(len(has_phone) / total * 100, 1),
        "country_codes": dict(phone_codes.most_common(10)),
    }

    # --- Location analysis ---
    countries = Counter(l.get("country", "") or "EMPTY" for l in leads)
    cities = Counter(l.get("city", "") or "EMPTY" for l in leads)
    analysis["locations"] = {
        "countries": dict(countries.most_common(10)),
        "top_cities": dict(cities.most_common(15)),
    }

    # Detect expected country from Apollo filters
    # Use word-boundary-safe matching to avoid "nz" matching "Linz", "uk" matching "Vanusku"
    import re
    def _country_word_match(pattern, text):
        """Match country abbreviation as a whole word or after comma/space."""
        return bool(re.search(r'(?:^|[\s,])' + pattern + r'(?:$|[\s,])', text))

    expected_countries = []
    for loc in filters.get("locations", []) + filters.get("org_locations", []):
        loc_lower = loc.lower()
        if "latvia" in loc_lower:
            expected_countries.append(("Latvia", "+371"))
        elif "lithuania" in loc_lower:
            expected_countries.append(("Lithuania", "+370"))
        elif "estonia" in loc_lower:
            expected_countries.append(("Estonia", "+372"))
        elif "finland" in loc_lower:
            expected_countries.append(("Finland", "+358"))
        elif "germany" in loc_lower:
            expected_countries.append(("Germany", "+49"))
        elif "austria" in loc_lower:
            expected_countries.append(("Austria", "+43"))
        elif "new zealand" in loc_lower or _country_word_match("nz", loc_lower):
            expected_countries.append(("New Zealand", "+64"))
        elif "united states" in loc_lower or _country_word_match("usa?", loc_lower):
            expected_countries.append(("United States", "+1"))
        elif "united kingdom" in loc_lower or _country_word_match("uk", loc_lower):
            expected_countries.append(("United Kingdom", "+44"))
    analysis["expected_countries"] = expected_countries

    # --- Title analysis ---
    titles = Counter(l.get("title", "") or "EMPTY" for l in leads)
    analysis["titles"] = {
        "unique_count": len(titles),
        "top_25": dict(titles.most_common(25)),
    }

    # Classify titles into categories
    title_categories = {
        "C-Level": r"\b(ceo|cfo|cto|coo|cmo|cio|cpo|chief)\b",
        "VP / SVP": r"\b(vp|vice president|svp)\b",
        "Director": r"\bdirector\b",
        "Head of": r"\bhead of\b|\bhead\b",
        "Manager": r"\bmanager\b|\bmanaging\b",
        "Owner / Founder": r"\b(owner|founder|co-founder|partner|principal)\b",
        "Board / Chair": r"\b(board|chairman|chairwoman|chairperson|member of the board)\b",
        "Specialist / Expert": r"\b(specialist|expert|advisor|consultant)\b",
        "Coordinator": r"\bcoordinator\b",
        "Analyst": r"\banalyst\b",
        "Engineer / Developer": r"\b(engineer|developer|programmer|devops|architect)\b",
        "Other IC": r".",  # Catch-all
    }
    category_counts = {}
    categorized_leads = {cat: [] for cat in title_categories}
    for l in leads:
        t = (l.get("title") or "").lower().strip()
        if not t:
            category_counts["No title"] = category_counts.get("No title", 0) + 1
            continue
        matched = False
        for cat, pat in title_categories.items():
            if cat == "Other IC":
                continue
            if re.search(pat, t):
                category_counts[cat] = category_counts.get(cat, 0) + 1
                categorized_leads[cat].append(l.get("title", ""))
                matched = True
                break
        if not matched:
            category_counts["Other IC"] = category_counts.get("Other IC", 0) + 1
            categorized_leads["Other IC"].append(l.get("title", ""))

    analysis["title_categories"] = category_counts

    # Sample titles for "Other IC" so user can see what's there
    other_ic = categorized_leads.get("Other IC", [])
    if other_ic:
        analysis["other_ic_sample"] = dict(Counter(other_ic).most_common(15))

    # --- Industry analysis ---
    industries = Counter(l.get("industry", "") or "EMPTY" for l in leads)
    analysis["industries"] = {
        "unique_count": len(industries),
        "breakdown": dict(industries.most_common()),
    }

    # --- LinkedIn coverage ---
    has_linkedin = sum(1 for l in leads if l.get("linkedin_url"))
    analysis["linkedin"] = {
        "has_linkedin": has_linkedin,
        "pct": round(has_linkedin / total * 100, 1),
    }

    # --- Organization analysis ---
    orgs = Counter(str(l.get("company_name") or l.get("organization_name") or l.get("org_name") or "EMPTY") for l in leads)
    analysis["organizations"] = {
        "unique_count": len(orgs),
        "top_10": dict(orgs.most_common(10)),
    }

    return analysis


def format_report(filters, analysis, apollo_url=None):
    """Format the analysis into a human-readable report string."""
    lines = []
    lines.append("=" * 70)
    lines.append("LEAD QUALITY ANALYSIS REPORT")
    lines.append("=" * 70)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Total leads analyzed: {analysis['total']}")

    # --- Apollo filter description ---
    lines.append("")
    lines.append("-" * 70)
    lines.append("APOLLO FILTER DESCRIPTION (what we were looking for)")
    lines.append("-" * 70)
    filter_desc = describe_apollo_filters(filters)
    if filter_desc:
        lines.extend(filter_desc)
    else:
        lines.append("  No filters detected (very broad search)")

    # --- Email coverage ---
    lines.append("")
    lines.append("-" * 70)
    lines.append("EMAIL COVERAGE")
    lines.append("-" * 70)
    e = analysis["email"]
    lines.append(f"  Has email:  {e['has_email']} ({e['pct']}%)")
    lines.append(f"  No email:   {e['no_email']} ({100 - e['pct']}%)")
    if e["pct"] < 100:
        lines.append(f"  >> RECOMMENDATION: Filter out {e['no_email']} leads without email")

    # --- Phone coverage ---
    lines.append("")
    lines.append("-" * 70)
    lines.append("PHONE COVERAGE")
    lines.append("-" * 70)
    p = analysis["phone"]
    lines.append(f"  Has phone:  {p['has_phone']} ({p['pct']}%)")
    lines.append(f"  No phone:   {p['no_phone']} ({round(100 - p['pct'], 1)}%)")
    if p["country_codes"]:
        lines.append("  Country codes:")
        for code, cnt in sorted(p["country_codes"].items(), key=lambda x: -x[1]):
            pct = round(cnt / analysis["total"] * 100, 1)
            lines.append(f"    {code}: {cnt} ({pct}%)")

    # Recommend phone filter if we know the target country
    expected = analysis.get("expected_countries", [])
    if expected:
        expected_codes = [c[1] for c in expected]
        expected_names = [c[0] for c in expected]
        matching = sum(p["country_codes"].get(c, 0) for c in expected_codes)
        lines.append(f"  >> Target country: {', '.join(expected_names)} ({', '.join(expected_codes)})")
        lines.append(f"  >> Leads with target phone code: {matching}")
        if matching < p["has_phone"]:
            lines.append(f"  >> RECOMMENDATION: Filter to {', '.join(expected_codes)} phone codes only")

    # --- Location ---
    lines.append("")
    lines.append("-" * 70)
    lines.append("LOCATION BREAKDOWN")
    lines.append("-" * 70)
    loc = analysis["locations"]
    lines.append("  Countries:")
    for country, cnt in sorted(loc["countries"].items(), key=lambda x: -x[1]):
        pct = round(cnt / analysis["total"] * 100, 1)
        lines.append(f"    {country}: {cnt} ({pct}%)")
    lines.append("  Top cities:")
    for city, cnt in list(sorted(loc["top_cities"].items(), key=lambda x: -x[1]))[:10]:
        lines.append(f"    {city}: {cnt}")

    # --- Title categories ---
    lines.append("")
    lines.append("-" * 70)
    lines.append("TITLE SENIORITY BREAKDOWN")
    lines.append("-" * 70)
    cats = analysis.get("title_categories", {})
    for cat in [
        "C-Level", "VP / SVP", "Director", "Head of", "Board / Chair",
        "Owner / Founder", "Manager", "Specialist / Expert", "Coordinator",
        "Analyst", "Engineer / Developer", "Other IC", "No title"
    ]:
        cnt = cats.get(cat, 0)
        if cnt > 0:
            pct = round(cnt / analysis["total"] * 100, 1)
            lines.append(f"    {cat}: {cnt} ({pct}%)")

    # Show "Other IC" examples if any
    other_sample = analysis.get("other_ic_sample")
    if other_sample:
        lines.append("  'Other IC' sample titles:")
        for t, cnt in list(other_sample.items())[:10]:
            lines.append(f"    [{cnt}] {t}")

    lines.append("")
    lines.append("  Top 25 individual titles:")
    for t, cnt in list(analysis["titles"]["top_25"].items()):
        lines.append(f"    [{cnt:3d}] {t}")

    # --- Industry breakdown ---
    lines.append("")
    lines.append("-" * 70)
    lines.append(f"INDUSTRY BREAKDOWN ({analysis['industries']['unique_count']} unique)")
    lines.append("-" * 70)
    for ind, cnt in analysis["industries"]["breakdown"].items():
        pct = round(cnt / analysis["total"] * 100, 1)
        lines.append(f"    [{cnt:3d}] ({pct:5.1f}%) {ind}")

    # --- Organization concentration ---
    lines.append("")
    lines.append("-" * 70)
    lines.append(f"ORGANIZATION CONCENTRATION ({analysis['organizations']['unique_count']} unique orgs)")
    lines.append("-" * 70)
    for org, cnt in analysis["organizations"]["top_10"].items():
        lines.append(f"    [{cnt:3d}] {org}")

    # --- LinkedIn ---
    lines.append("")
    lines.append("-" * 70)
    lines.append("LINKEDIN COVERAGE")
    lines.append("-" * 70)
    li = analysis["linkedin"]
    lines.append(f"  Has LinkedIn: {li['has_linkedin']} ({li['pct']}%)")

    # --- Summary recommendations ---
    lines.append("")
    lines.append("=" * 70)
    lines.append("RECOMMENDED FILTERS (choose which to apply)")
    lines.append("=" * 70)
    recs = []
    if e["no_email"] > 0:
        recs.append(f"1. REQUIRE EMAIL - removes {e['no_email']} leads without email")
    if expected:
        expected_codes = [c[1] for c in expected]
        matching = sum(p["country_codes"].get(c, 0) for c in expected_codes)
        non_matching = analysis["total"] - matching
        if non_matching > 0:
            code_str = "/".join(expected_codes)
            recs.append(f"2. REQUIRE {code_str} PHONE - removes {non_matching} leads without target country phone")
    ic_count = cats.get("Specialist / Expert", 0) + cats.get("Coordinator", 0) + \
               cats.get("Analyst", 0) + cats.get("Engineer / Developer", 0) + \
               cats.get("Other IC", 0) + cats.get("No title", 0)
    if ic_count > 0:
        recs.append(f"3. EXCLUDE IC TITLES - removes ~{ic_count} individual contributors / irrelevant roles")
    recs.append("4. EXCLUDE INDUSTRIES - choose specific industries to remove (see breakdown above)")

    if recs:
        for r in recs:
            lines.append(f"  {r}")
    else:
        lines.append("  No filtering recommended - data looks clean.")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze lead quality against Apollo URL filters"
    )
    parser.add_argument("--apollo-url", required=True, help="Apollo.io search URL")
    parser.add_argument("--leads", required=True, help="Path to leads JSON file")
    parser.add_argument("--output-dir", help="Directory to save JSON report (optional)")
    args = parser.parse_args()

    # Parse Apollo URL
    filters = parse_apollo_url(args.apollo_url)

    # Load leads (validates data is a list)
    leads = load_leads(args.leads)

    # Analyze
    analysis = analyze_leads(leads, filters)

    # Print human-readable report
    report = format_report(filters, analysis, args.apollo_url)
    print(report)

    # Save JSON report if output dir specified
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(args.output_dir, f"quality_report_{ts}.json")
        report_data = {
            "generated": datetime.now().isoformat(),
            "apollo_filters": filters,
            "filter_description": describe_apollo_filters(filters),
            "analysis": analysis,
        }
        save_json(report_data, report_path)
        print(f"\nJSON report saved: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

# [CLI] — run via: py execution/lead_filter.py --help
"""
Lead Filter
Applies user-chosen quality filters to a lead list.
Designed to be called by the AI agent after presenting the quality report
and getting the user's filter choices.

Filters available:
  --require-email         Remove leads without email
  --require-phone CODE    Remove leads without a phone matching country code (e.g. +371)
  --require-country NAME  Keep only leads matching this country (e.g. Italy)
  --remove-phone-discrepancies  Remove leads where phone prefix doesn't match country
  --exclude-titles FILE   JSON file with title exclusion regex patterns
  --exclude-industries LIST  Comma-separated industry names to exclude
  --include-industries LIST  Comma-separated industry whitelist (keep only matching)
  --exclude-titles-builtin   Use built-in IC exclusion patterns (default set)

Usage:
    py execution/lead_filter.py \
        --input path/to/leads.json \
        --output-dir path/to/dir \
        --require-email \
        --require-phone +371 \
        --exclude-titles-builtin \
        --exclude-industries "Farming,Gambling & Casinos" \
        --include-industries "Retail,Construction,Plastics"

Output:
    Saves filtered leads JSON + prints summary of what was removed at each stage.
"""

import sys
import os
import re
import argparse
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_json, save_json


# ---------------------------------------------------------------------------
# Built-in title exclusion patterns
# Exclude individual contributors and clearly irrelevant roles.
# Keep all manager-level people, project managers, department heads, etc.
# ---------------------------------------------------------------------------
BUILTIN_TITLE_EXCLUDE_PATTERNS = [
    # Individual contributors - technical
    r"\bsoftware\b",
    r"\bengineer\b",
    r"\bdeveloper\b",
    r"\bprogrammer\b",
    r"\bdevops\b",
    r"\bdata scientist\b",
    r"\bdata engineer\b",
    r"\bqa\b",
    r"\btester\b",
    r"\btest engineer\b",
    r"\bdesigner\b(?!.*director)",
    r"\barchitect\b(?!.*chief)",
    r"\bfrontend\b",
    r"\bbackend\b",
    r"\bfull.?stack\b",
    r"\bsysadmin\b",
    r"\bsystem administrator\b",
    r"\bdba\b",
    r"\bdatabase administrator\b",
    # Individual contributors - business
    r"\bconsultant\b(?!.*senior|.*managing|.*principal)",
    r"\bsenior consultant\b",
    r"\banalyst\b(?!.*lead|.*head|.*chief|.*director)",
    r"\bspecialist\b(?!.*lead|.*head|.*chief)",
    r"\bcoordinator\b",
    r"\bexpert\b(?!.*chief|.*lead|.*head)",
    r"\bsenior expert\b",
    r"\bresearcher\b",
    r"\bsenior researcher\b",
    r"\bjunior\b",
    r"\bintern\b",
    r"\btrainee\b",
    r"\bassistant\b(?!.*director|.*manager)",
    # Admin / clerical
    r"\badministrator\b(?!.*director|.*manager)",
    r"\bsecretary\b",
    r"\breceptionist\b",
    r"\bclerk\b",
    # Finance individual contributors
    r"\baccountant\b(?!.*chief|.*head)",
    r"\bauditor\b(?!.*chief|.*head|.*lead)",
    r"\bbookkeeper\b",
    # Legal individual contributors
    r"\blawyer\b(?!.*managing|.*senior partner)",
    r"\bsenior lawyer\b",
    r"\blegal advisor\b",
    r"\blegal counsel\b(?!.*general|.*chief)",
    # Irrelevant manager roles (too niche / technical)
    r"\bit manager\b",
    r"\bsystem.* manager\b",
    r"\bnetwork manager\b",
    r"\bdatabase manager\b",
    r"\bwarehouse manager\b",
    r"\bwarehouse\b.*\bsupervisor\b",
    # Recruitment ICs
    r"\bsenior recruitment specialist\b",
    r"\brecruitment specialist\b",
    r"\brecruiter\b(?!.*head|.*director|.*manager)",
]


def title_passes(title, patterns):
    """Return True if the title should be KEPT (not excluded)."""
    if not title:
        return False
    t = title.lower().strip()
    for pat in patterns:
        if re.search(pat, t):
            return False
    return True


# ---------------------------------------------------------------------------
# Country → phone prefix mapping (for phone discrepancy detection)
# Covers countries commonly seen in lead gen campaigns.
# ---------------------------------------------------------------------------
COUNTRY_PHONE_CODES = {
    "albania": "+355", "australia": "+61", "austria": "+43",
    "belgium": "+32", "bosnia and herzegovina": "+387", "brazil": "+55",
    "bulgaria": "+359", "canada": "+1", "croatia": "+385",
    "czech republic": "+420", "czechia": "+420",
    "denmark": "+45", "estonia": "+372",
    "finland": "+358", "france": "+33", "germany": "+49",
    "greece": "+30", "hungary": "+36", "iceland": "+354",
    "india": "+91", "ireland": "+353", "israel": "+972",
    "italy": "+39", "japan": "+81", "latvia": "+371",
    "lithuania": "+370", "luxembourg": "+352",
    "mexico": "+52", "netherlands": "+31", "new zealand": "+64",
    "norway": "+47", "poland": "+48", "portugal": "+351",
    "romania": "+40", "serbia": "+381", "singapore": "+65",
    "slovakia": "+421", "slovenia": "+386",
    "south korea": "+82", "spain": "+34", "sweden": "+46",
    "switzerland": "+41", "turkey": "+90",
    "ukraine": "+380", "united arab emirates": "+971",
    "united kingdom": "+44", "united states": "+1",
}


def _get_lead_country(lead):
    """Get country from lead, checking both person and company country fields."""
    return (lead.get("country", "") or lead.get("company_country", "") or "").strip()


def _get_any_phone(lead):
    """Get first non-empty phone from lead."""
    for field in ("phone", "organization_phone", "personal_phone", "company_phone"):
        val = str(lead.get(field, "") or "").strip()
        if val:
            return val
    return ""


def _phone_matches_country(phone, country):
    """Check if a phone number's prefix matches the expected country code."""
    if not phone or not country:
        return True  # Can't check, assume OK
    expected_code = COUNTRY_PHONE_CODES.get(country.lower())
    if not expected_code:
        return True  # Unknown country, can't check
    # Strip non-digit chars after the + for comparison
    return phone.startswith(expected_code)


def _normalize_industry(name):
    """Normalize industry name for comparison: lowercase, 'and' -> '&', strip."""
    return (name or "").lower().strip().replace(" and ", " & ")


def _get_lead_industry(lead):
    """Get industry string from a lead, checking both field names."""
    return lead.get("industry", "") or lead.get("company_industry", "") or ""


def phone_matches_code(lead, required_code):
    """Check if any phone field on the lead matches the required country code."""
    phones = [
        lead.get("phone", ""),
        lead.get("organization_phone", ""),
        lead.get("personal_phone", ""),
        lead.get("company_phone", ""),
    ]
    for phone in phones:
        phone = str(phone or "").strip()
        if phone.startswith(required_code):
            return True
    return False


def apply_filters(leads, args):
    """
    Apply filters in sequence, tracking removals at each stage.
    Returns (filtered_leads, stages_report).
    """
    stages = []
    current = leads
    initial_count = len(current)

    # Stage 1: Require email
    if args.require_email:
        before = len(current)
        current = [l for l in current if l.get("email")]
        removed = before - len(current)
        stages.append({
            "name": "Require email",
            "before": before,
            "removed": removed,
            "after": len(current),
        })

    # Stage 2: Require phone country code
    if args.require_phone:
        code = args.require_phone if args.require_phone.startswith("+") else f"+{args.require_phone}"
        before = len(current)
        current = [l for l in current if phone_matches_code(l, code)]
        removed = before - len(current)
        stages.append({
            "name": f"Require {code} phone",
            "before": before,
            "removed": removed,
            "after": len(current),
        })

    # Stage 3: Title exclusion
    title_patterns = []
    if args.exclude_titles_builtin:
        title_patterns = BUILTIN_TITLE_EXCLUDE_PATTERNS[:]
    if args.exclude_titles:
        custom_patterns = load_json(args.exclude_titles)
        title_patterns.extend(custom_patterns)

    if title_patterns:
        before = len(current)
        passed = [l for l in current if title_passes(l.get("title", ""), title_patterns)]
        failed = [l for l in current if not title_passes(l.get("title", ""), title_patterns)]

        # Collect removed titles for transparency
        removed_titles = Counter(l.get("title", "") for l in failed)

        current = passed
        stages.append({
            "name": "Title exclusion",
            "before": before,
            "removed": before - len(current),
            "after": len(current),
            "removed_titles_top15": dict(removed_titles.most_common(15)),
        })

    # Stage 4: Industry inclusion whitelist
    if args.include_industries:
        include_set = {_normalize_industry(ind) for ind in args.include_industries.split(",")}
        before = len(current)
        passed = []
        failed = []
        for l in current:
            industry = _get_lead_industry(l)
            if not industry:
                passed.append(l)  # Keep leads with no industry (can't filter)
            elif _normalize_industry(industry) in include_set:
                passed.append(l)
            else:
                failed.append(l)
        removed_industries = Counter(_get_lead_industry(l) for l in failed)
        current = passed
        stages.append({
            "name": "Industry inclusion whitelist",
            "before": before,
            "removed": before - len(current),
            "after": len(current),
            "kept_no_industry": sum(1 for l in passed if not _get_lead_industry(l)),
            "removed_industries_top15": dict(removed_industries.most_common(15)),
        })

    # Stage 5: Industry exclusion
    if args.exclude_industries:
        exclude_set = {_normalize_industry(ind) for ind in args.exclude_industries.split(",")}
        before = len(current)
        passed = [
            l for l in current
            if _normalize_industry(_get_lead_industry(l)) not in exclude_set
        ]
        failed = [
            l for l in current
            if _normalize_industry(_get_lead_industry(l)) in exclude_set
        ]
        removed_industries = Counter(_get_lead_industry(l) for l in failed)
        current = passed
        stages.append({
            "name": "Industry exclusion",
            "before": before,
            "removed": before - len(current),
            "after": len(current),
            "removed_industries": dict(removed_industries.most_common()),
        })

    # Stage 6: Require country
    if args.require_country:
        target_country = args.require_country.strip().lower()
        before = len(current)
        passed = [l for l in current if _get_lead_country(l).lower() == target_country]
        failed_countries = Counter(_get_lead_country(l) for l in current if _get_lead_country(l).lower() != target_country)
        current = passed
        stages.append({
            "name": f"Require country: {args.require_country}",
            "before": before,
            "removed": before - len(current),
            "after": len(current),
            "removed_countries_top10": dict(Counter(dict(failed_countries.most_common(10))).items()),
        })

    # Stage 7: Require website
    if args.require_website:
        before = len(current)
        current = [l for l in current if
                   (l.get('website_url') or l.get('company_website') or
                    l.get('company_domain') or '').strip()]
        removed = before - len(current)
        stages.append({
            "name": "Require website/domain",
            "before": before,
            "removed": removed,
            "after": len(current),
        })

    # Stage 8: Remove foreign domain TLDs
    if args.remove_foreign_tld:
        try:
            from verify_country import COUNTRY_CONFIG, get_domain_tld
        except ImportError:
            from execution.verify_country import COUNTRY_CONFIG, get_domain_tld
        config = COUNTRY_CONFIG.get(args.remove_foreign_tld.upper(), {})
        foreign_tlds = set(config.get('foreign_tlds', []))
        if foreign_tlds:
            before = len(current)
            passed = []
            failed = []
            for l in current:
                domain = (l.get('company_domain') or '').lower().strip()
                tld = get_domain_tld(domain)
                if tld and tld in foreign_tlds:
                    failed.append(l)
                else:
                    passed.append(l)
            from collections import Counter as _Counter
            removed_tlds = _Counter(get_domain_tld((l.get('company_domain') or '').lower()) for l in failed)
            current = passed
            stages.append({
                "name": f"Foreign TLD filter ({args.remove_foreign_tld.upper()})",
                "before": before,
                "removed": before - len(current),
                "after": len(current),
                "removed_tlds_top10": dict(removed_tlds.most_common(10)),
            })

    # Stage 9: Remove phone/country discrepancies
    if args.remove_phone_discrepancies:
        before = len(current)
        passed = []
        failed = []
        for l in current:
            phone = _get_any_phone(l)
            country = _get_lead_country(l)
            if not phone:
                passed.append(l)  # No phone → no discrepancy possible
            elif _phone_matches_country(phone, country):
                passed.append(l)
            else:
                failed.append(l)
        discrepancy_details = Counter(
            f"{_get_lead_country(l)} but phone {_get_any_phone(l)[:6]}..." for l in failed
        )
        current = passed
        stages.append({
            "name": "Remove phone/country discrepancies",
            "before": before,
            "removed": before - len(current),
            "after": len(current),
            "discrepancies_top10": dict(discrepancy_details.most_common(10)),
        })

    return current, stages, initial_count


def format_filter_report(stages, initial_count, final_count):
    """Format filter results into a readable report."""
    lines = []
    lines.append("=" * 60)
    lines.append("FILTER RESULTS")
    lines.append("=" * 60)
    lines.append(f"Starting leads: {initial_count}")
    lines.append("")

    for i, stage in enumerate(stages, 1):
        lines.append(f"  Stage {i}: {stage['name']}")
        lines.append(f"    Before: {stage['before']} -> After: {stage['after']} (removed {stage['removed']})")

        # Show removed titles if available
        if "removed_titles_top15" in stage and stage["removed_titles_top15"]:
            lines.append("    Removed titles (top 15):")
            for t, cnt in stage["removed_titles_top15"].items():
                lines.append(f"      [{cnt}] {t}")

        # Show kept-no-industry count for inclusion whitelist
        if "kept_no_industry" in stage and stage["kept_no_industry"]:
            lines.append(f"    (kept {stage['kept_no_industry']} leads with no industry field)")

        # Show removed industries from whitelist (top 15)
        if "removed_industries_top15" in stage and stage["removed_industries_top15"]:
            lines.append("    Removed industries (top 15):")
            for ind, cnt in stage["removed_industries_top15"].items():
                lines.append(f"      [{cnt}] {ind}")

        # Show removed industries if available
        if "removed_industries" in stage and stage["removed_industries"]:
            lines.append("    Removed industries:")
            for ind, cnt in stage["removed_industries"].items():
                lines.append(f"      [{cnt}] {ind}")

        # Show removed countries (top 10)
        if "removed_countries_top10" in stage and stage["removed_countries_top10"]:
            lines.append("    Removed countries (top 10):")
            for c, cnt in stage["removed_countries_top10"].items():
                lines.append(f"      [{cnt}] {c}")

        # Show phone/country discrepancies
        if "discrepancies_top10" in stage and stage["discrepancies_top10"]:
            lines.append("    Discrepancies (top 10):")
            for d, cnt in stage["discrepancies_top10"].items():
                lines.append(f"      [{cnt}] {d}")

        # Show removed TLDs
        if "removed_tlds_top10" in stage and stage["removed_tlds_top10"]:
            lines.append("    Removed TLDs (top 10):")
            for tld, cnt in stage["removed_tlds_top10"].items():
                lines.append(f"      [{cnt}] {tld}")

        lines.append("")

    lines.append(f"  FINAL: {initial_count} -> {final_count} ({round(final_count / max(initial_count, 1) * 100)}% kept)")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Filter leads by quality criteria")
    parser.add_argument("--input", required=True, help="Path to leads JSON file")
    parser.add_argument("--output-dir", required=True, help="Output directory for filtered file")
    parser.add_argument("--require-email", action="store_true", help="Remove leads without email")
    parser.add_argument("--require-phone", type=str, help="Require phone with country code (e.g. +371)")
    parser.add_argument("--exclude-titles-builtin", action="store_true",
                        help="Exclude individual contributors using built-in patterns")
    parser.add_argument("--exclude-titles", type=str,
                        help="Path to JSON file with custom title exclusion regex patterns")
    parser.add_argument("--include-industries", type=str,
                        help="Comma-separated industry whitelist (keep only matching; leads with no industry are kept)")
    parser.add_argument("--exclude-industries", type=str,
                        help="Comma-separated industry names to exclude")
    parser.add_argument("--require-country", type=str,
                        help="Keep only leads matching this country (e.g. Italy)")
    parser.add_argument("--remove-phone-discrepancies", action="store_true",
                        help="Remove leads where phone prefix doesn't match lead country")
    parser.add_argument("--require-website", action="store_true",
                        help="Remove leads without a company website or domain")
    parser.add_argument("--remove-foreign-tld", type=str,
                        help="Country code — removes leads with foreign domain TLDs (e.g. LV removes .fi,.ee,.de leads)")
    parser.add_argument("--output-prefix", type=str, default="filtered",
                        help="Prefix for output filename (default: 'filtered')")

    args = parser.parse_args()

    # Load leads
    leads = load_json(args.input)
    print(f"Loaded {len(leads)} leads from {args.input}")

    # Check that at least one filter is specified
    if not any([args.require_email, args.require_phone,
                args.exclude_titles_builtin, args.exclude_titles,
                args.include_industries, args.exclude_industries,
                args.require_country, args.remove_phone_discrepancies,
                args.require_website, args.remove_foreign_tld]):
        print("WARNING: No filters specified. Output will be identical to input.", file=sys.stderr)

    # Apply filters
    filtered, stages, initial_count = apply_filters(leads, args)

    # Print report
    report = format_filter_report(stages, initial_count, len(filtered))
    print(report)

    # Save
    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{args.output_prefix}_{ts}_{len(filtered)}leads.json"
    filepath = os.path.join(args.output_dir, filename)
    save_json(filtered, filepath)

    print(f"\nFiltered leads saved: {filepath}")
    # Print just the path on last line for easy parsing
    print(filepath)

    return 0


if __name__ == "__main__":
    sys.exit(main())

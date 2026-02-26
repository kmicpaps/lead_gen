# [CLI] — run via: py execution/cold_email_exporter.py --help
#!/usr/bin/env python3
"""
Cold Email Exporter for Instantly

Exports segmented lead data as Instantly-compatible CSV with merge fields.
The email copy (templates) lives in Instantly -- this CSV provides only
the per-lead personalization data (icebreaker, company name, etc.).

Includes --qa flag for icebreaker quality checks.

Usage:
    python execution/cold_email_exporter.py \
        --input .tmp/gmaps_pipeline/cold_email_segmented.json \
        --output campaigns/techstart/instantly/website_build_20260220.csv

    # QA mode (check icebreakers before export):
    python execution/cold_email_exporter.py \
        --input .tmp/gmaps_pipeline/cold_email_segmented.json \
        --output campaigns/techstart/instantly/website_build_20260220.csv \
        --qa
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List


# ── QA Checks ─────────────────────────────────────────────────────────

def qa_check_lead(lead: dict) -> List[str]:
    """Check a single lead's icebreaker for quality issues."""
    warnings = []
    insight = lead.get("insight_lv", "")

    # Insight too long
    word_count = len(insight.split())
    if word_count > 15:
        warnings.append(f"icebreaker is {word_count} words (max 15)")

    # Em-dash in icebreaker
    if "\u2014" in insight:
        warnings.append("icebreaker contains em-dash")

    # Empty icebreaker
    if not insight.strip():
        warnings.append("icebreaker is empty")

    return warnings


def print_qa_summary(total_leads: int, all_warnings: Dict[str, List[str]]):
    """Print QA results summary."""
    print("\n" + "=" * 50)
    print("QA CHECK RESULTS")
    print("=" * 50)

    total_warnings = sum(len(w) for w in all_warnings.values())
    leads_with_warnings = sum(1 for w in all_warnings.values() if w)

    if total_warnings == 0:
        print("[PASS] All icebreakers look good")
    else:
        print(f"[WARN] {total_warnings} issues across {leads_with_warnings}/{total_leads} leads")
        print()
        shown = 0
        for biz, warnings in all_warnings.items():
            if warnings and shown < 5:
                print(f"  {biz}:")
                for w in warnings:
                    print(f"    - {w}")
                shown += 1


def main():
    parser = argparse.ArgumentParser(description="Export segmented leads to Instantly CSV (merge fields only)")
    parser.add_argument("--input", required=True, help="Path to segmented leads JSON")
    parser.add_argument("--output", required=True, help="Path to write Instantly CSV")
    parser.add_argument("--qa", action="store_true", help="Run icebreaker QA checks before export")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        sys.exit(1)

    # Load leads
    with open(input_path, "r", encoding="utf-8") as f:
        leads = json.load(f)
    print(f"[INFO] Loaded {len(leads)} segmented leads")

    # Build CSV rows -- merge fields only, no email bodies
    rows = []
    qa_warnings = {}

    for lead in leads:
        email = (lead.get("emails") or [None])[0] if isinstance(lead.get("emails"), list) else lead.get("email_1", "")
        if not email:
            continue

        rows.append({
            "email": email,
            "company_name": lead.get("business_name", ""),
            "casual_name": lead.get("casual_name", lead.get("business_name", "")),
            "icebreaker": lead.get("insight_lv", ""),
            "niche": lead.get("niche", ""),
            "city": lead.get("city", ""),
            "score": str(lead.get("overall_score", "")),
            "segment": lead.get("segment_id", ""),
            "website": lead.get("website", ""),
            "phone": lead.get("phone", ""),
        })

        if args.qa:
            biz = lead.get("business_name", "unknown")
            warnings = qa_check_lead(lead)
            if warnings:
                qa_warnings[biz] = warnings

    # QA summary
    if args.qa:
        print_qa_summary(len(rows), qa_warnings)

    # Write CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "email", "company_name", "casual_name", "icebreaker",
        "niche", "city", "score", "segment",
        "website", "phone",
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[OK] Exported {len(rows)} leads to {output_path}")

    # Segment breakdown
    seg_counts = {}
    for row in rows:
        seg = row["segment"]
        seg_counts[seg] = seg_counts.get(seg, 0) + 1
    print("\nPer-segment breakdown:")
    for seg, count in sorted(seg_counts.items()):
        print(f"  {seg}: {count}")


if __name__ == "__main__":
    main()

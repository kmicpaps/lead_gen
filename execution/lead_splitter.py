# [CLI] — run via: py execution/lead_splitter.py --help
#!/usr/bin/env python3
"""
Lead Splitter — Routes scraped leads into actionable streams.

Stream A (cold_calling): has phone, no email → phone outreach
Stream B (cold_email):   has email → website evaluation + scored email outreach
Stream C (no_contact):   no phone, no email → discard
"""

import os
import sys
import argparse
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_leads, save_json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def split_leads(leads: List[Dict], output_dir: str = ".tmp/split") -> Dict:
    """
    Split leads into cold_calling, cold_email, and no_contact streams.

    Args:
        leads: list of lead dicts (from scrape_gmaps_contact.py output)
        output_dir: directory to save split files

    Returns:
        Summary dict with counts and file paths
    """
    cold_calling = []
    cold_email = []
    no_contact = []

    for lead in leads:
        has_phone = bool(lead.get("phone"))
        has_email = bool(lead.get("emails")) and len(lead.get("emails", [])) > 0
        has_website = bool(lead.get("website"))

        if has_email:
            cold_email.append(lead)
        elif has_phone:
            # Has phone but no email — cold calling candidate
            cold_calling.append(lead)
        else:
            no_contact.append(lead)

    # Save files
    files = {}
    for name, data in [("cold_calling", cold_calling), ("cold_email", cold_email), ("no_contact", no_contact)]:
        path = os.path.join(output_dir, f"{name}.json")
        save_json(data, path, mkdir=True)
        files[name] = path

    summary = {
        "total": len(leads),
        "cold_calling": {"count": len(cold_calling), "file": files["cold_calling"]},
        "cold_email": {"count": len(cold_email), "file": files["cold_email"]},
        "no_contact": {"count": len(no_contact), "file": files["no_contact"]},
    }

    # Print summary
    print(f"\n{'='*50}")
    print("LEAD SPLIT RESULTS")
    print(f"{'='*50}")
    print(f"Total leads:       {summary['total']}")
    print(f"Cold calling:      {len(cold_calling)} (phone, no email)")
    print(f"Cold email:        {len(cold_email)} (has email)")
    print(f"No contact:        {len(no_contact)} (discarded)")
    print()

    # Breakdown of cold_calling: with vs without website
    cc_no_web = sum(1 for l in cold_calling if not l.get("website"))
    cc_has_web = sum(1 for l in cold_calling if l.get("website"))
    print(f"Cold calling detail:")
    print(f"  No website:      {cc_no_web}")
    print(f"  Has website:     {cc_has_web} (has site but no email found)")

    # Cold email: with vs without website
    ce_has_web = sum(1 for l in cold_email if l.get("website"))
    ce_no_web = sum(1 for l in cold_email if not l.get("website"))
    print(f"Cold email detail:")
    print(f"  Has website:     {ce_has_web} (evaluate these)")
    print(f"  No website:      {ce_no_web} (email only, skip eval)")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Split leads into cold calling and cold email streams")
    parser.add_argument("--input", required=True, help="Input JSON file with leads")
    parser.add_argument("--output-dir", default=".tmp/split", help="Output directory (default: .tmp/split)")

    args = parser.parse_args()

    leads = load_leads(args.input)

    print(f"Loaded {len(leads)} leads from {args.input}")
    summary = split_leads(leads, args.output_dir)

    # Save summary
    summary_path = os.path.join(args.output_dir, "split_summary.json")
    save_json(summary, summary_path)
    print(f"\n[OK] Summary saved to {summary_path}")


if __name__ == "__main__":
    main()

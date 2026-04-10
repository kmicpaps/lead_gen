# [CLI] -- run via: py execution/gmaps_dedup.py --help
#!/usr/bin/env python3
"""
GMaps Lead Deduplicator -- Remove duplicate businesses from scraped GMaps leads.

Dedup strategy:
  1. Primary key: place_id (Apify's unique Google Maps identifier)
  2. Fallback: MD5 hash of business_name|address (case-insensitive)

Usage:
    py execution/gmaps_dedup.py --input .tmp/gmaps/scraped.json --output .tmp/gmaps/deduped.json
"""

import os
import sys
import hashlib
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_json, save_json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def generate_lead_id(business_name: str, address: str) -> str:
    """Generate unique ID from business name + address."""
    key = f"{business_name}|{address}".lower().strip()
    return hashlib.md5(key.encode()).hexdigest()


def dedup_leads(leads: list) -> list:
    """Deduplicate leads by place_id, then by name|address hash.

    Args:
        leads: list of GMaps lead dicts

    Returns:
        Deduplicated list (preserves first occurrence)
    """
    seen_ids = set()
    unique = []
    for lead in leads:
        lid = lead.get("place_id") or generate_lead_id(
            lead.get("business_name", ""), lead.get("address", "")
        )
        if lid not in seen_ids:
            seen_ids.add(lid)
            unique.append(lead)
    return unique


def main():
    parser = argparse.ArgumentParser(description="Deduplicate GMaps leads by place_id + name|address")
    parser.add_argument("--input", required=True, help="Input JSON file with GMaps leads")
    parser.add_argument("--output", help="Output JSON file (default: input with _deduped suffix)")

    args = parser.parse_args()

    leads = load_json(args.input)
    before = len(leads)

    unique = dedup_leads(leads)
    after = len(unique)
    removed = before - after

    print(f"Dedup: {before} -> {after} ({removed} duplicates removed)")

    output_path = args.output or args.input.replace(".json", "_deduped.json")
    save_json(unique, output_path, mkdir=True)
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()

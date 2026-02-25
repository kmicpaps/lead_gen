# [CLI] — run via: py execution/merge_lead_lists.py --help
"""
Merge two lead lists without deduplication.
Simple concatenation of two JSON lists.
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_leads, save_leads

def main():
    parser = argparse.ArgumentParser(description='Merge two lead lists')
    parser.add_argument('--list1', required=True, help='Path to first leads JSON file')
    parser.add_argument('--list2', required=True, help='Path to second leads JSON file')
    parser.add_argument('--output-dir', required=True, help='Output directory')

    args = parser.parse_args()

    try:
        list1 = load_leads(args.list1)
        print(f"Loaded {len(list1)} leads from list 1")

        list2 = load_leads(args.list2)
        print(f"Loaded {len(list2)} leads from list 2")

        combined = list1 + list2
        print(f"\nCombined total: {len(combined)} leads")

        filepath = save_leads(combined, args.output_dir, "combined_leads")
        print(f"\nCombined leads saved to: {filepath}")
        print(filepath)

        return 0

    except Exception as e:
        print(f"Error merging lists: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

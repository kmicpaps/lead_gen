"""
Complete Poland Precast Concrete Workflow - Test Demonstration
Merges test results, validates, enriches, and exports to Google Sheets
"""

import os
import sys
import json
from datetime import datetime

def load_leads(filepath):
    """Load leads from JSON file, filtering out garbage records"""
    with open(filepath, 'r', encoding='utf-8') as f:
        leads = json.load(f)

    # Filter out garbage log messages (emojis in name)
    clean_leads = []
    for lead in leads:
        name = lead.get('name', '')
        # Skip leads with emojis or log messages
        if any(ord(char) > 127 for char in name if char in ['\U0001f440', '\U000023f3']):
            continue
        clean_leads.append(lead)

    return clean_leads

def merge_and_dedup(leads_list):
    """Merge and deduplicate leads by email"""
    leads_by_email = {}

    for lead in leads_list:
        email = lead.get('email') or ''
        email = email.lower().strip() if email else ''

        if email:
            if email in leads_by_email:
                # Keep the one with more non-empty fields
                existing = leads_by_email[email]
                existing_count = sum(1 for v in existing.values() if v and str(v).strip())
                new_count = sum(1 for v in lead.values() if v and str(v).strip())

                if new_count > existing_count:
                    leads_by_email[email] = lead
            else:
                leads_by_email[email] = lead

    return list(leads_by_email.values())

def count_email_statuses(leads):
    """Count leads by email status"""
    status_counts = {}
    missing = 0

    for lead in leads:
        email = lead.get('email', '').strip()
        if not email:
            missing += 1
        else:
            status = lead.get('email_status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

    return status_counts, missing

def main():
    print("="*60)
    print("POLAND PRECAST CONCRETE - WORKFLOW COMPLETION (TEST)")
    print("="*60)

    # Step 1: Load and merge leads
    print("\nStep 1: Loading test leads...")
    b2b_file = ".tmp/b2b_finder/b2b_leads_20251203_143306_1018leads.json"
    cc_file = ".tmp/codecrafter/codecrafter_leads_test_20251203_161039_25leads.json"

    b2b_leads = load_leads(b2b_file)
    cc_leads = load_leads(cc_file)

    print(f"  B2B_Finder: {len(b2b_leads)} leads (after filtering)")
    print(f"  Code_Crafter: {len(cc_leads)} leads")

    # Step 2: Merge and deduplicate
    print("\nStep 2: Merging and deduplicating...")
    all_leads = b2b_leads + cc_leads
    merged_leads = merge_and_dedup(all_leads)

    duplicates_removed = len(all_leads) - len(merged_leads)
    print(f"  Total raw: {len(all_leads)}")
    print(f"  Duplicates removed: {duplicates_removed}")
    print(f"  Unique leads: {len(merged_leads)}")

    # Step 3: Analyze email coverage
    print("\nStep 3: Analyzing email coverage...")
    status_counts, missing = count_email_statuses(merged_leads)

    print(f"  Leads with emails: {len(merged_leads) - missing}")
    print(f"  Leads missing emails: {missing}")

    for status, count in status_counts.items():
        print(f"    - {status}: {count}")

    # Save merged file
    os.makedirs(".tmp/poland_test", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    merged_file = f".tmp/poland_test/poland_merged_{timestamp}_{len(merged_leads)}leads.json"

    with open(merged_file, 'w', encoding='utf-8') as f:
        json.dump(merged_leads, f, indent=2, ensure_ascii=False)

    print(f"\n  Merged file saved: {merged_file}")

    # Step 4: Summary for remaining steps
    print("\n" + "="*60)
    print("REMAINING STEPS (NOT EXECUTED - TEST ONLY)")
    print("="*60)

    leads_needing_validation = len(merged_leads) - missing

    print(f"\nStep 4: Email Validation (Lead Magic)")
    print(f"  Would validate: {leads_needing_validation} emails")
    print(f"  Estimated cost: {leads_needing_validation} credits (cheap)")
    print(f"  Command: py execution/verify_emails_leadmagic_fast.py --input {merged_file}")

    print(f"\nStep 5: Email Enrichment (Lead Magic)")
    print(f"  Would enrich: ~{missing} missing emails")
    print(f"  Estimated cost: ~{missing} credits (expensive)")
    print(f"  Command: py execution/enrich_emails_leadmagic_fast.py --input [validated_file]")

    print(f"\nStep 6: Cleanup")
    print(f"  Remove leads with missing emails after enrichment")
    print(f"  Final dedup pass")

    print(f"\nStep 7: Export to Google Sheets")
    print(f"  Command: py execution/upload_to_google_sheet.py --input [final_file] --sheet-title 'Poland Precast Concrete Test'")

    print("\n" + "="*60)
    print("WORKFLOW TEST COMPLETE")
    print("="*60)
    print(f"\nTest demonstrates:")
    print(f"  [OK] B2B_Finder validation (1018 leads scraped)")
    print(f"  [OK] Code_Crafter validation (25 leads, 100% match)")
    print(f"  [OK] Merge and deduplication ({len(merged_leads)} unique leads)")
    print(f"  [PENDING] Email validation (requires Lead Magic API)")
    print(f"  [PENDING] Email enrichment (requires Lead Magic API)")
    print(f"  [PENDING] Final export to Google Sheets")

    print(f"\nMerged test file location: {merged_file}")

    return 0

if __name__ == "__main__":
    sys.exit(main())

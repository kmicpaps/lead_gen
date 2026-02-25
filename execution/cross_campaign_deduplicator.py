# [CLI] — run via: py execution/cross_campaign_deduplicator.py --help
"""
Cross-Campaign Deduplicator

Removes duplicate leads across multiple campaigns for the same client.
Preserves the first occurrence (oldest campaign) and removes duplicates from newer campaigns.

Usage:
    python cross_campaign_deduplicator.py --client-id acme_corp
    python cross_campaign_deduplicator.py --client-id acme_corp --dry-run
"""

import os
import sys
import argparse
import shutil
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_json, save_json

def normalize_key(text):
    """Normalize text for matching (lowercase, strip whitespace)."""
    if not text:
        return ''
    return str(text).lower().strip()


def get_lead_keys(lead):
    """
    Extract unique identifiers from a lead for deduplication.
    Returns: (email_key, linkedin_key, name_org_key)
    """
    email_key = normalize_key(lead.get('email', ''))
    linkedin_key = normalize_key(lead.get('linkedin_url', ''))

    # Fallback: name + organization
    name = normalize_key(lead.get('name', ''))
    org = normalize_key(lead.get('organization_name', ''))
    name_org_key = f"{name}|{org}" if name and org else ''

    return email_key, linkedin_key, name_org_key


def load_campaign_leads(campaign_folder):
    """
    Load leads from a campaign folder.
    Looks for raw_leads_*.json or the latest lead file.
    """
    campaign_path = Path(campaign_folder)

    # Try to find raw_leads file
    raw_files = list(campaign_path.glob('raw_leads_*.json'))
    if raw_files:
        # Get the most recent raw_leads file
        latest_file = max(raw_files, key=lambda p: p.stat().st_mtime)
        return load_json(str(latest_file)), latest_file

    # Fallback: look for any JSON file with leads
    json_files = [f for f in campaign_path.glob('*.json') if 'client.json' not in str(f)]
    if json_files:
        latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
        return load_json(str(latest_file)), latest_file

    return [], None


def save_campaign_leads(leads, original_file, backup=True):
    """Save deduplicated leads to file, optionally creating backup."""
    if backup and original_file.exists():
        backup_file = original_file.with_suffix('.backup.json')
        shutil.copy2(original_file, backup_file)
        print(f"  Created backup: {backup_file.name}")

    save_json(leads, str(original_file))

    print(f"  Saved deduplicated leads to: {original_file.name}")


def update_google_sheet(leads, sheet_url, campaign_name):
    """Update Google Sheet with deduplicated leads."""
    try:
        # Import here to avoid circular dependency
        from google_sheets_exporter import upload_leads_to_sheet

        # Extract sheet ID from URL
        if '/d/' in sheet_url:
            sheet_id = sheet_url.split('/d/')[1].split('/')[0]
        else:
            print(f"  Warning: Invalid Google Sheets URL: {sheet_url}")
            return False

        print(f"  Updating Google Sheet...")
        upload_leads_to_sheet(leads, sheet_id, campaign_name)
        print(f"  [OK] Google Sheet updated successfully")
        return True
    except Exception as e:
        print(f"  Warning: Failed to update Google Sheet: {e}")
        return False


def deduplicate_campaigns(client_id, dry_run=False, campaigns_filter=None):
    """
    Deduplicate leads across all campaigns for a client.

    Args:
        client_id: Client identifier
        dry_run: If True, only report what would be changed
        campaigns_filter: Optional list of campaign IDs to process
    """
    # Load client data
    client_file = Path(f'campaigns/{client_id}/client.json')
    if not client_file.exists():
        print(f"Error: Client file not found: {client_file}")
        return 1

    client_data = load_json(str(client_file))

    campaigns = client_data.get('campaigns', [])
    if not campaigns:
        print(f"No campaigns found for client: {client_id}")
        return 0

    # Filter campaigns if specified
    if campaigns_filter:
        campaigns = [c for c in campaigns if c['campaign_id'] in campaigns_filter]

    # Sort campaigns by creation date (oldest first)
    campaigns = sorted(campaigns, key=lambda c: c.get('created_at', ''))

    print(f"\n{'='*70}")
    print(f"Cross-Campaign Deduplication Report")
    print(f"{'='*70}")
    print(f"Client: {client_data['company_name']} ({client_id})")
    print(f"Total Campaigns: {len(campaigns)}")
    print(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'LIVE (will update files and sheets)'}")
    print(f"\n")

    # Track seen leads across campaigns
    seen_emails = set()
    seen_linkedin = set()
    seen_name_org = set()

    # Track statistics
    total_original = 0
    total_removed = 0
    total_final = 0

    # Process each campaign
    for idx, campaign in enumerate(campaigns, 1):
        campaign_id = campaign['campaign_id']
        campaign_name = campaign['campaign_name']
        created_at = campaign.get('created_at', 'Unknown')
        original_count = campaign.get('lead_count', 0)

        print(f"Campaign {idx}: {campaign_name} ({created_at[:10]})")
        print(f"  Original leads: {original_count:,}")

        # Find campaign folder
        campaign_folder = Path(f'campaigns/{client_id}/apollo_lists/{campaign_id}')
        if not campaign_folder.exists():
            campaign_folder = Path(f'campaigns/{client_id}/google_maps_lists/{campaign_id}')

        if not campaign_folder.exists():
            print(f"  Warning: Campaign folder not found: {campaign_id}")
            print(f"")
            continue

        # Load campaign leads
        leads, lead_file = load_campaign_leads(campaign_folder)
        if not leads:
            print(f"  Warning: No leads found in campaign folder")
            print(f"")
            continue

        current_count = len(leads)
        total_original += current_count

        # First campaign is baseline - just add to seen sets
        if idx == 1:
            for lead in leads:
                email_key, linkedin_key, name_org_key = get_lead_keys(lead)
                if email_key:
                    seen_emails.add(email_key)
                if linkedin_key:
                    seen_linkedin.add(linkedin_key)
                if name_org_key:
                    seen_name_org.add(name_org_key)

            total_final += current_count
            print(f"  Duplicates removed: 0 (baseline campaign)")
            print(f"  Final leads: {current_count:,}")
            print(f"  Status: [OK] Unchanged (baseline)")
            print(f"")
            continue

        # Deduplicate this campaign against previous campaigns
        deduplicated_leads = []
        removed_by_email = 0
        removed_by_linkedin = 0
        removed_by_name_org = 0

        for lead in leads:
            email_key, linkedin_key, name_org_key = get_lead_keys(lead)

            # Check if duplicate
            is_duplicate = False

            if email_key and email_key in seen_emails:
                removed_by_email += 1
                is_duplicate = True
            elif linkedin_key and linkedin_key in seen_linkedin:
                removed_by_linkedin += 1
                is_duplicate = True
            elif name_org_key and name_org_key in seen_name_org:
                removed_by_name_org += 1
                is_duplicate = True

            if not is_duplicate:
                deduplicated_leads.append(lead)
                # Add to seen sets
                if email_key:
                    seen_emails.add(email_key)
                if linkedin_key:
                    seen_linkedin.add(linkedin_key)
                if name_org_key:
                    seen_name_org.add(name_org_key)

        # Calculate statistics
        duplicates_removed = current_count - len(deduplicated_leads)
        total_removed += duplicates_removed
        total_final += len(deduplicated_leads)

        print(f"  Duplicates removed: {duplicates_removed:,}")
        if duplicates_removed > 0:
            print(f"    - {removed_by_email} duplicate emails from previous campaigns")
            print(f"    - {removed_by_linkedin} duplicate LinkedIn URLs from previous campaigns")
            print(f"    - {removed_by_name_org} duplicate name+org from previous campaigns")
        print(f"  Final leads: {len(deduplicated_leads):,}")

        # Save changes (if not dry run)
        if not dry_run and duplicates_removed > 0:
            # Save deduplicated leads
            save_campaign_leads(deduplicated_leads, lead_file, backup=True)

            # Update Google Sheet
            sheet_url = campaign.get('sheet_url', '')
            if sheet_url:
                update_google_sheet(deduplicated_leads, sheet_url, campaign_name)

            # Update campaign lead count in client.json
            campaign['lead_count'] = len(deduplicated_leads)

            print(f"  Status: [UPDATED] Removed {duplicates_removed} duplicates")
        else:
            if dry_run and duplicates_removed > 0:
                print(f"  Status: [DRY-RUN] Would remove {duplicates_removed} duplicates")
            else:
                print(f"  Status: [OK] No changes needed")

        print(f"")

    # Update client.json with new lead counts
    if not dry_run:
        client_data['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        save_json(client_data, str(client_file))
        print(f"[OK] Updated client.json with new lead counts")
        print(f"")

    # Print summary
    print(f"{'='*70}")
    print(f"Summary")
    print(f"{'='*70}")
    print(f"Total leads before: {total_original:,}")
    print(f"Total duplicates removed: {total_removed:,}")
    print(f"Total unique leads: {total_final:,}")
    print(f"Deduplication rate: {(total_removed / total_original * 100) if total_original > 0 else 0:.1f}%")

    if dry_run:
        print(f"\n[WARNING] This was a DRY RUN. No changes were made.")
        print(f"Run without --dry-run to apply changes.")
    else:
        print(f"\n[SUCCESS] Deduplication complete!")

    print(f"")

    return 0


def main():
    parser = argparse.ArgumentParser(description='Deduplicate leads across campaigns for a client')
    parser.add_argument('--client-id', required=True, help='Client identifier')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--campaigns', help='Comma-separated list of campaign IDs to process (default: all)')

    args = parser.parse_args()

    campaigns_filter = None
    if args.campaigns:
        campaigns_filter = [c.strip() for c in args.campaigns.split(',')]

    return deduplicate_campaigns(args.client_id, args.dry_run, campaigns_filter)


if __name__ == '__main__':
    sys.exit(main())

# Cross-Campaign Deduplication

**Purpose:** Remove duplicate leads across multiple campaigns for the same client to prevent sending duplicate outreach.

**Status:** Active directive
**Created:** December 5, 2025

## Problem Statement

When running multiple campaigns for the same client, leads may appear in multiple campaigns. For example:
- Campaign 1: "NZ Concrete Auckland" - 1,444 leads
- Campaign 2: "NZ Auckland Woodworking" - 1,006 leads

Some construction companies might appear in both campaigns (concrete manufacturers who also do woodworking). Without deduplication, the client would reach out to the same person multiple times.

## Solution

Deduplicate leads across all campaigns for a client, keeping only the **first occurrence** (oldest campaign) and removing duplicates from newer campaigns.

## Deduplication Strategy

### Primary Keys (in order of priority):
1. **Email** (case-insensitive) - Most reliable unique identifier
2. **LinkedIn URL** - Alternative unique identifier
3. **Name + Organization** - Fallback for leads without email/LinkedIn

### Campaign Ordering
- Campaigns are processed in **chronological order** (oldest to newest)
- **First campaign is never modified** - it serves as the baseline
- Newer campaigns have duplicates removed

### Update Process
1. Identify duplicates across campaigns
2. Remove duplicates from newer campaign files
3. Update Google Sheets with deduplicated data
4. Update `client.json` with new lead counts
5. Generate deduplication report

## Execution Script

**File:** [cross_campaign_deduplicator.py](../execution/cross_campaign_deduplicator.py)

**Usage:**
```bash
# Deduplicate all campaigns for a client
py execution/cross_campaign_deduplicator.py --client-id acme_corp

# Dry run (show what would be removed without making changes)
py execution/cross_campaign_deduplicator.py --client-id acme_corp --dry-run

# Deduplicate specific campaigns only
py execution/cross_campaign_deduplicator.py --client-id acme_corp --campaigns campaign1,campaign2
```

## Output

The script generates:
1. **Updated lead files** - Deduplicated JSON files for each campaign
2. **Updated Google Sheets** - Re-uploads with deduplicated data
3. **Deduplication Report** - Shows:
   - Number of duplicates found per campaign
   - Which campaigns they came from
   - Updated lead counts
   - Links to updated sheets

Example report:
```
Cross-Campaign Deduplication Report
===================================
Client: acme_corp
Total Campaigns: 2

Campaign 1: NZ Concrete Auckland (2025-12-05)
  Original leads: 1,444
  Duplicates removed: 0 (baseline campaign)
  Final leads: 1,444
  Status: ✓ Unchanged (baseline)

Campaign 2: NZ Auckland Woodworking (2025-12-05)
  Original leads: 1,006
  Duplicates removed: 47
    - 35 duplicate emails from Campaign 1
    - 8 duplicate LinkedIn URLs from Campaign 1
    - 4 duplicate name+org from Campaign 1
  Final leads: 959
  Status: ✓ Updated (removed 47 duplicates)

Summary
-------
Total leads before: 2,450
Total duplicates removed: 47
Total unique leads: 2,403
```

## When to Run

Run cross-campaign deduplication:
1. **After creating a new campaign** for an existing client
2. **Before starting outreach** on a new campaign
3. **Periodically** if campaigns are added over time

## Integration with Lead Generation Workflow

Update the lead generation workflow to include deduplication as a final step when the client already has existing campaigns:

```
14-Step Workflow (Updated):
1-13: [Existing steps...]
14. Upload to Google Sheets + report
15. Cross-campaign deduplication (if client has multiple campaigns)
16. Update client.json with final lead counts
```

## Important Notes

1. **First campaign is sacred** - Never modify the baseline campaign
2. **Chronological order matters** - Always process oldest to newest
3. **Google Sheets are updated** - No manual intervention needed
4. **Backup is automatic** - Original files are renamed with `.backup` suffix
5. **Dry-run first** - Always test with `--dry-run` before applying changes

## Edge Cases

### What if campaigns were created simultaneously?
- Use `created_at` timestamp to determine order
- If timestamps are identical, use `campaign_id` alphabetically

### What if a lead's email changes between campaigns?
- Deduplication uses the email at time of scraping
- LinkedIn URL can catch these cases
- Consider running periodic re-deduplication

### What if I want to keep duplicates for a specific campaign?
- Use `--exclude-campaigns` flag to skip specific campaigns
- Example: `--exclude-campaigns special_vip_campaign`

## Error Handling

The script handles:
- Missing campaign files gracefully
- Invalid Google Sheets URLs (skips update)
- Corrupted JSON files (backs up and continues)
- API rate limits (retries with exponential backoff)

## Future Enhancements

Potential improvements:
1. **Fuzzy matching** - Catch similar but not identical names
2. **Domain-based deduplication** - Remove leads from same company domain
3. **Time-based deduplication** - Only dedupe within X months
4. **Priority campaigns** - Mark certain campaigns as "always keep"

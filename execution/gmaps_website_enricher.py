# [CLI] -- run via: py execution/gmaps_website_enricher.py --help
#!/usr/bin/env python3
"""
GMaps Website Enricher -- Batch website contact extraction for GMaps leads.

For each lead with a website, scrapes the website + contact pages and uses
Claude Haiku to extract additional emails, phone numbers, owner info, etc.
Merges newly-found emails into the lead's existing `emails` list.

Run BEFORE lead_splitter.py so phone-only leads can move to cold_email
if their website yields an email.

Usage:
    py execution/gmaps_website_enricher.py \\
        --input .tmp/gmaps/deduped.json \\
        --output .tmp/gmaps/enriched.json \\
        --workers 5
"""

import os
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_json, save_json, log_ok, log_error, log_warn, log_info
from extract_website_contacts import extract_website_contacts

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def merge_enrichment(lead: Dict, enrichment: Dict) -> Dict:
    """Merge extracted contact data into a lead, deduping emails/phones.

    Args:
        lead: Original GMaps lead
        enrichment: Result from extract_website_contacts()

    Returns:
        Updated lead with enriched fields
    """
    if enrichment.get("enrichment_status") != "success":
        lead["website_enrichment_status"] = enrichment.get("enrichment_status", "unknown")
        return lead

    extracted = enrichment.get("extracted_data", {})

    # Merge emails (dedupe, case-insensitive)
    existing_emails = lead.get("emails") or []
    if isinstance(existing_emails, str):
        existing_emails = [existing_emails] if existing_emails else []

    new_emails = extracted.get("emails") or []
    seen_lower = {e.lower() for e in existing_emails if e}
    for email in new_emails:
        if email and email.lower() not in seen_lower:
            existing_emails.append(email)
            seen_lower.add(email.lower())

    # Add owner email if not already present
    owner = extracted.get("owner_info") or {}
    owner_email = owner.get("email")
    if owner_email and owner_email.lower() not in seen_lower:
        existing_emails.append(owner_email)
        seen_lower.add(owner_email.lower())

    # Add team member emails
    for member in extracted.get("team_members") or []:
        member_email = member.get("email") if isinstance(member, dict) else None
        if member_email and member_email.lower() not in seen_lower:
            existing_emails.append(member_email)
            seen_lower.add(member_email.lower())

    lead["emails"] = existing_emails

    # Merge phone numbers (only fill if missing)
    if not lead.get("phone"):
        new_phones = extracted.get("phone_numbers") or []
        if new_phones:
            lead["phone"] = new_phones[0]

    # Add owner info as new fields
    if owner.get("name"):
        lead["owner_name"] = owner.get("name")
        lead["owner_title"] = owner.get("title") or ""
        lead["owner_email"] = owner.get("email") or ""
        lead["owner_phone"] = owner.get("phone") or ""
        lead["owner_linkedin"] = owner.get("linkedin") or ""

    # Add social media (only fill missing)
    social = extracted.get("social_media") or {}
    for platform in ["facebook", "instagram", "linkedin", "twitter", "youtube", "tiktok"]:
        if not lead.get(platform) and social.get(platform):
            lead[platform] = social.get(platform)

    # Metadata
    lead["website_enrichment_status"] = "success"
    lead["website_pages_scraped"] = enrichment.get("pages_scraped", 0)

    return lead


def enrich_one(lead: Dict) -> Dict:
    """Enrich a single lead. Catches all errors so batch keeps running."""
    website = lead.get("website") or ""
    business_name = lead.get("business_name") or "Unknown"

    if not website:
        lead["website_enrichment_status"] = "no_website"
        return lead

    try:
        enrichment = extract_website_contacts(website, business_name)
        return merge_enrichment(lead, enrichment)
    except Exception as e:
        log_error(f"Enrichment failed for {business_name}: {str(e)[:100]}")
        lead["website_enrichment_status"] = f"error: {str(e)[:100]}"
        return lead


def enrich_batch(leads: List[Dict], max_workers: int = 5) -> List[Dict]:
    """Enrich all leads in parallel.

    Args:
        leads: list of GMaps leads
        max_workers: parallel threads (default 5, keep low to avoid AI rate limits)

    Returns:
        Enriched leads in original order
    """
    with_website = sum(1 for l in leads if l.get("website"))
    without_website = len(leads) - with_website

    log_info(f"Enriching {with_website} leads with websites ({without_website} skipped)")

    enriched = [None] * len(leads)
    completed = 0
    emails_before = sum(
        len(l.get("emails") or []) if isinstance(l.get("emails"), list) else (1 if l.get("emails") else 0)
        for l in leads
    )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {executor.submit(enrich_one, lead): i for i, lead in enumerate(leads)}
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                enriched[idx] = future.result()
            except Exception as e:
                log_error(f"Worker crashed: {e}")
                enriched[idx] = leads[idx]
            completed += 1
            if completed % 10 == 0 or completed == len(leads):
                print(f"  Progress: {completed}/{len(leads)}")

    emails_after = sum(
        len(l.get("emails") or []) if isinstance(l.get("emails"), list) else (1 if l.get("emails") else 0)
        for l in enriched
    )

    leads_with_email_before = sum(
        1 for l in leads
        if (isinstance(l.get("emails"), list) and len(l.get("emails")) > 0)
    )
    leads_with_email_after = sum(
        1 for l in enriched
        if (isinstance(l.get("emails"), list) and len(l.get("emails")) > 0)
    )

    print()
    log_ok(f"Enrichment complete")
    print(f"  Total emails:  {emails_before} -> {emails_after} (+{emails_after - emails_before})")
    print(f"  Leads with email: {leads_with_email_before} -> {leads_with_email_after} (+{leads_with_email_after - leads_with_email_before})")

    return enriched


def main():
    parser = argparse.ArgumentParser(description="Batch enrich GMaps leads with website contact extraction")
    parser.add_argument("--input", required=True, help="Input JSON file with GMaps leads")
    parser.add_argument("--output", help="Output JSON file (default: input with _enriched suffix)")
    parser.add_argument("--workers", type=int, default=5, help="Parallel workers (default: 5)")
    parser.add_argument("--limit", type=int, help="Only process first N leads (for testing)")

    args = parser.parse_args()

    leads = load_json(args.input)
    if args.limit:
        leads = leads[:args.limit]
        log_info(f"Limiting to first {args.limit} leads")

    enriched = enrich_batch(leads, max_workers=args.workers)

    output_path = args.output or args.input.replace(".json", "_enriched.json")
    save_json(enriched, output_path, mkdir=True)
    log_ok(f"Saved to {output_path}")


if __name__ == "__main__":
    main()

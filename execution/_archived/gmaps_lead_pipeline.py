# [CLI] — run via: py execution/gmaps_lead_pipeline.py --help
#!/usr/bin/env python3
"""
Google Maps Lead Generation Pipeline
Scrapes businesses from Google Maps, enriches with website contacts, saves to Google Sheets
"""

import os
import sys
import json
import argparse
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import gspread
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# Add execution/ to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our scraping modules
from scrape_google_maps import scrape_google_maps
from extract_website_contacts import extract_website_contacts

# Load environment variables
load_dotenv()

# Google Sheets scopes
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']

# Output schema - 34 columns (lead_id and place_id excluded from export)
HEADERS = [
    "scraped_at", "search_query", "business_name", "category",
    "address", "city", "state", "zip_code", "country", "phone", "website",
    "google_maps_url", "rating", "review_count", "price_level",
    "emails", "additional_phones", "business_hours", "facebook", "twitter",
    "linkedin", "instagram", "youtube", "tiktok", "owner_name", "owner_title",
    "owner_email", "owner_phone", "owner_linkedin", "team_contacts",
    "additional_contact_methods", "pages_scraped", "search_enriched",
    "enrichment_status"
]


def generate_lead_id(business_name: str, address: str) -> str:
    """Generate unique lead ID from business name and address"""
    name = business_name or ''
    addr = address or ''
    if not name and not addr:
        # Both empty — use random suffix to avoid hash collisions
        import uuid
        return hashlib.md5(f"unknown|{uuid.uuid4().hex[:8]}".encode()).hexdigest()
    key = f"{name}|{addr}".lower().strip()
    return hashlib.md5(key.encode()).hexdigest()


def authenticate_google_sheets() -> gspread.Client:
    """Authenticate with Google Sheets using OAuth"""
    creds = None

    # Try to load existing token
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # Refresh or create new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "credentials.json not found. Please set up Google OAuth credentials."
                )
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return gspread.authorize(creds)


def get_or_create_sheet(gc: gspread.Client, sheet_url: Optional[str] = None) -> tuple:
    """
    Get existing sheet or create new one
    Returns (spreadsheet, worksheet, existing_lead_ids)
    """
    if sheet_url:
        # Open existing sheet
        try:
            spreadsheet = gc.open_by_url(sheet_url)
            worksheet = spreadsheet.sheet1

            # Get existing lead IDs for deduplication
            all_values = worksheet.get_all_values()
            if len(all_values) > 1:  # Has data beyond headers
                # Regenerate lead_ids from business_name (col 2) and address (col 4)
                existing_lead_ids = set()
                for row in all_values[1:]:  # Skip header row
                    if len(row) > 4 and row[2] and row[4]:  # Has business_name and address
                        lead_id = generate_lead_id(row[2], row[4])
                        existing_lead_ids.add(lead_id)
            else:
                existing_lead_ids = set()

            print(f"[OK] Opened existing sheet: {spreadsheet.title}")
            print(f"     Found {len(existing_lead_ids)} existing leads")

            return spreadsheet, worksheet, existing_lead_ids

        except Exception as e:
            print(f"[ERROR] Could not open sheet: {e}")
            sys.exit(1)
    else:
        # Create new sheet
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        sheet_title = f"GMaps Leads - {timestamp}"

        spreadsheet = gc.create(sheet_title)
        worksheet = spreadsheet.sheet1

        # Set headers
        worksheet.append_row(HEADERS)

        # Format headers (34 columns = A1:AH1)
        worksheet.format('A1:AH1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })

        print(f"[OK] Created new sheet: {sheet_title}")
        print(f"     URL: {spreadsheet.url}")

        return spreadsheet, worksheet, set()


def enrich_lead(business: Dict, search_query: str) -> Dict:
    """
    Enrich a single business lead with website contact extraction
    """
    lead = {
        "lead_id": generate_lead_id(business.get("business_name", ""), business.get("address", "")),
        "scraped_at": datetime.now().isoformat(),
        "search_query": search_query,
        "business_name": business.get("business_name", ""),
        "category": business.get("category", ""),
        "address": business.get("address", ""),
        "city": business.get("city", ""),
        "state": business.get("state", ""),
        "zip_code": business.get("zip_code", ""),
        "country": business.get("country", ""),
        "phone": business.get("phone", ""),
        "website": business.get("website", ""),
        "google_maps_url": business.get("google_maps_url", ""),
        "place_id": business.get("place_id", ""),
        "rating": business.get("rating", ""),
        "review_count": business.get("review_count", ""),
        "price_level": business.get("price_level", ""),
        "emails": "",
        "additional_phones": "",
        "business_hours": business.get("business_hours", ""),
        "facebook": "",
        "twitter": "",
        "linkedin": "",
        "instagram": "",
        "youtube": "",
        "tiktok": "",
        "owner_name": "",
        "owner_title": "",
        "owner_email": "",
        "owner_phone": "",
        "owner_linkedin": "",
        "team_contacts": "",
        "additional_contact_methods": "",
        "pages_scraped": 0,
        "search_enriched": False,
        "enrichment_status": "no_website"
    }

    # Try to enrich if website exists
    if business.get("website"):
        try:
            enrichment = extract_website_contacts(
                business["website"],
                business["business_name"]
            )

            # Update with enrichment data
            lead["enrichment_status"] = enrichment["enrichment_status"]
            lead["pages_scraped"] = enrichment["pages_scraped"]
            lead["search_enriched"] = enrichment["search_enriched"]

            if enrichment.get("extracted_data"):
                data = enrichment["extracted_data"]

                # Basic contact info
                lead["emails"] = ", ".join(data.get("emails", []) or [])
                lead["additional_phones"] = ", ".join(data.get("phone_numbers", []) or [])
                lead["business_hours"] = data.get("business_hours") or ""

                # Social media (handle None values)
                social = data.get("social_media") or {}
                lead["facebook"] = social.get("facebook") or ""
                lead["twitter"] = social.get("twitter") or ""
                lead["linkedin"] = social.get("linkedin") or ""
                lead["instagram"] = social.get("instagram") or ""
                lead["youtube"] = social.get("youtube") or ""
                lead["tiktok"] = social.get("tiktok") or ""

                # Owner info (handle None values)
                owner = data.get("owner_info") or {}
                lead["owner_name"] = owner.get("name") or ""
                lead["owner_title"] = owner.get("title") or ""
                lead["owner_email"] = owner.get("email") or ""
                lead["owner_phone"] = owner.get("phone") or ""
                lead["owner_linkedin"] = owner.get("linkedin") or ""

                # Team members (serialize to JSON)
                team = data.get("team_members", [])
                if team:
                    lead["team_contacts"] = json.dumps(team)

                # Additional contacts
                additional = data.get("additional_contacts", [])
                if additional:
                    lead["additional_contact_methods"] = ", ".join(additional)

        except Exception as e:
            print(f"  [ERROR] Failed to enrich {business['business_name']}: {str(e)[:100]}")
            lead["enrichment_status"] = f"error: {str(e)[:50]}"

    return lead


def lead_to_row(lead: Dict) -> List:
    """Convert lead dict to row list matching HEADERS order"""
    return [str(lead.get(h, "") or "") for h in HEADERS]


def main():
    parser = argparse.ArgumentParser(
        description="Google Maps Lead Generation Pipeline"
    )
    parser.add_argument(
        "--search",
        required=True,
        help='Search query (e.g., "plumbers in Austin TX")'
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of results to scrape (default: 10)"
    )
    parser.add_argument(
        "--sheet-url",
        help="Existing Google Sheet URL to append to (optional)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of parallel workers for enrichment (default: 10)"
    )
    parser.add_argument(
        "--skip-enrichment",
        action="store_true",
        help="Skip website enrichment (GMaps data only)"
    )
    parser.add_argument(
        "--country",
        default="us",
        help="Country code for search (default: us, must be lowercase)"
    )

    args = parser.parse_args()

    print("="*70)
    print("GOOGLE MAPS LEAD GENERATION PIPELINE")
    print("="*70)
    print(f"Search query: {args.search}")
    print(f"Limit: {args.limit}")
    print(f"Workers: {args.workers}")
    print(f"Skip enrichment: {args.skip_enrichment}")
    print()

    # Step 1: Scrape Google Maps
    print("[1/4] Scraping Google Maps...")
    businesses = scrape_google_maps(args.search, limit=args.limit, country=args.country)

    if not businesses:
        print("[ERROR] No businesses found")
        return 1

    print(f"[OK] Found {len(businesses)} businesses")
    print()

    # Step 2: Enrich with website contacts
    print("[2/4] Enriching with website contacts...")
    leads = []

    if args.skip_enrichment:
        # Quick mode - no enrichment
        for business in businesses:
            lead = {
                "lead_id": generate_lead_id(business["business_name"], business["address"]),
                "scraped_at": datetime.now().isoformat(),
                "search_query": args.search,
                **business,
                "enrichment_status": "skipped"
            }
            leads.append(lead)
        print("[OK] Skipped enrichment (--skip-enrichment)")
    else:
        # Parallel enrichment
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_business = {
                executor.submit(enrich_lead, business, args.search): business
                for business in businesses
            }

            for future in as_completed(future_to_business):
                business = future_to_business[future]
                try:
                    lead = future.result()
                    leads.append(lead)
                    status = lead["enrichment_status"]
                    try:
                        print(f"  [{len(leads)}/{len(businesses)}] {business['business_name']}: {status}")
                    except UnicodeEncodeError:
                        print(f"  [{len(leads)}/{len(businesses)}] [Unicode encoding error]: {status}")
                except Exception as e:
                    try:
                        print(f"  [ERROR] {business['business_name']}: {str(e)[:100]}")
                    except UnicodeEncodeError:
                        print(f"  [ERROR] [Unicode encoding error]: {str(e)[:100]}")

    print(f"[OK] Enriched {len(leads)} leads")
    print()

    # Step 3: Authenticate with Google Sheets
    print("[3/4] Connecting to Google Sheets...")
    try:
        gc = authenticate_google_sheets()
        spreadsheet, worksheet, existing_lead_ids = get_or_create_sheet(gc, args.sheet_url)
    except Exception as e:
        print(f"[ERROR] Google Sheets authentication failed: {e}")
        return 1

    print()

    # Step 4: Save to Google Sheets with deduplication
    print("[4/4] Saving to Google Sheets...")

    new_leads = []
    duplicate_count = 0

    for lead in leads:
        if lead["lead_id"] in existing_lead_ids:
            duplicate_count += 1
        else:
            new_leads.append(lead)

    if not new_leads:
        print(f"[OK] No new leads to add (all {duplicate_count} duplicates)")
        print(f"\nSheet URL: {spreadsheet.url}")
        return 0

    # Append new leads
    rows = [lead_to_row(lead) for lead in new_leads]
    worksheet.append_rows(rows)

    print(f"[OK] Added {len(new_leads)} new leads")
    if duplicate_count > 0:
        print(f"     Skipped {duplicate_count} duplicates")

    print()
    print("="*70)
    print("PIPELINE COMPLETE")
    print("="*70)
    print(f"Total scraped: {len(businesses)}")
    print(f"New leads added: {len(new_leads)}")
    print(f"Duplicates skipped: {duplicate_count}")
    print(f"\nSheet URL: {spreadsheet.url}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

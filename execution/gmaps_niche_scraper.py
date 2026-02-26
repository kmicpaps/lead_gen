# [CLI] — run via: py execution/gmaps_niche_scraper.py --help
#!/usr/bin/env python3
"""
Google Maps Niche-by-Niche Lead Scraper
Interactive pipeline that scrapes businesses by niche, filters for those without websites,
and saves each niche to a separate tab in Google Sheets.
"""

import os
import sys
import argparse

# Fix Windows console encoding for Latvian diacritics
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import hashlib
from datetime import datetime
from typing import List, Dict, Set, Optional
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# Add execution/ to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Google Maps scraper
from scrape_google_maps import scrape_google_maps

# Load environment variables
load_dotenv()

# Google Sheets scopes
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']

# Simplified output schema for no-website leads
HEADERS = [
    "scraped_at", "niche", "business_name", "category",
    "address", "city", "phone", "google_maps_url",
    "rating", "review_count"
]


def generate_lead_id(business_name: str, address: str) -> str:
    """Generate unique lead ID from business name and address"""
    key = f"{business_name}|{address}".lower().strip()
    return hashlib.md5(key.encode()).hexdigest()


def authenticate_google_sheets() -> gspread.Client:
    """Authenticate with Google Sheets using OAuth"""
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

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

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return gspread.authorize(creds)


def create_spreadsheet(gc: gspread.Client, location: str) -> gspread.Spreadsheet:
    """Create a new Google Sheet for the scraping session"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet_title = f"GMaps No-Website Leads - {location} - {timestamp}"

    spreadsheet = gc.create(sheet_title)
    print(f"[OK] Created spreadsheet: {sheet_title}")
    print(f"     URL: {spreadsheet.url}")

    return spreadsheet


def get_or_create_worksheet(
    spreadsheet: gspread.Spreadsheet,
    niche: str,
    existing_worksheets: Dict[str, gspread.Worksheet]
) -> tuple:
    """
    Get existing worksheet for niche or create new one.
    Returns (worksheet, existing_lead_ids)
    """
    # Sanitize niche name for tab (max 100 chars, no special chars)
    tab_name = niche[:100].replace("/", "-").replace("\\", "-")

    if tab_name in existing_worksheets:
        worksheet = existing_worksheets[tab_name]
        # Get existing lead IDs for deduplication
        all_values = worksheet.get_all_values()
        existing_ids = set()
        if len(all_values) > 1:
            for row in all_values[1:]:
                if len(row) > 4 and row[2] and row[4]:  # business_name and address
                    lead_id = generate_lead_id(row[2], row[4])
                    existing_ids.add(lead_id)
        return worksheet, existing_ids

    # Create new worksheet
    try:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=len(HEADERS))
    except Exception:
        # If first sheet exists but is empty (Sheet1), rename it
        if len(spreadsheet.worksheets()) == 1:
            worksheet = spreadsheet.sheet1
            worksheet.update_title(tab_name)
        else:
            raise

    # Set headers
    worksheet.append_row(HEADERS)
    worksheet.format('A1:J1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
    })

    existing_worksheets[tab_name] = worksheet
    return worksheet, set()


def scrape_niche(
    niche: str,
    location: str,
    limit: int,
    country: str,
    no_website_only: bool
) -> List[Dict]:
    """
    Scrape a single niche from Google Maps.
    Returns list of business dicts, filtered if no_website_only is True.
    """
    search_query = f"{niche} in {location}"
    print(f"\n[SCRAPING] '{search_query}' (limit: {limit})")

    businesses = scrape_google_maps(
        search_query=search_query,
        limit=limit,
        country=country
    )

    if no_website_only:
        original_count = len(businesses)
        businesses = [b for b in businesses if not b.get("website")]
        filtered_count = len(businesses)
        print(f"[FILTER] {filtered_count}/{original_count} businesses have no website")

    return businesses


def business_to_row(business: Dict, niche: str) -> List[str]:
    """Convert business dict to row matching HEADERS"""
    return [
        datetime.now().isoformat(),
        niche,
        str(business.get("business_name") or ""),
        str(business.get("category") or ""),
        str(business.get("address") or ""),
        str(business.get("city") or ""),
        str(business.get("phone") or ""),
        str(business.get("google_maps_url") or ""),
        str(business.get("rating") or ""),
        str(business.get("review_count") or ""),
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Interactive niche-by-niche Google Maps scraper"
    )
    parser.add_argument(
        "--location",
        required=True,
        help='Location to search (e.g., "Riga Latvia")'
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max results per niche (default: 50)"
    )
    parser.add_argument(
        "--country",
        default="lv",
        help="Country code (default: lv for Latvia)"
    )
    parser.add_argument(
        "--no-website",
        action="store_true",
        help="Only keep businesses without a website"
    )
    parser.add_argument(
        "--sheet-url",
        help="Existing Google Sheet URL to append to (optional)"
    )
    parser.add_argument(
        "--niches",
        nargs="+",
        help="List of niches to scrape (non-interactive mode)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("GOOGLE MAPS NICHE-BY-NICHE SCRAPER")
    print("=" * 70)
    print(f"Location: {args.location}")
    print(f"Limit per niche: {args.limit}")
    print(f"No-website filter: {args.no_website}")
    print()

    # Authenticate with Google Sheets
    print("[AUTH] Connecting to Google Sheets...")
    try:
        gc = authenticate_google_sheets()
    except Exception as e:
        print(f"[ERROR] Google Sheets auth failed: {e}")
        return 1

    # Create or open spreadsheet
    if args.sheet_url:
        try:
            spreadsheet = gc.open_by_url(args.sheet_url)
            print(f"[OK] Opened existing sheet: {spreadsheet.title}")
        except Exception as e:
            print(f"[ERROR] Could not open sheet: {e}")
            return 1
    else:
        spreadsheet = create_spreadsheet(gc, args.location)

    existing_worksheets: Dict[str, gspread.Worksheet] = {}
    total_leads = 0
    niches_scraped = []

    # Build niche list from CLI args or interactive mode
    if args.niches:
        niche_queue = list(args.niches)
        print(f"\nBatch mode: {len(niche_queue)} niches queued")
        for i, n in enumerate(niche_queue, 1):
            print(f"  {i}. {n}")
        print()
    else:
        niche_queue = None
        print()
        print("-" * 70)
        print("INTERACTIVE MODE")
        print("Enter niches one at a time. Type 'done' when finished.")
        print("-" * 70)

    niche_index = 0
    while True:
        if niche_queue:
            if niche_index >= len(niche_queue):
                break
            niche = niche_queue[niche_index]
            niche_index += 1
            print(f"\n[{niche_index}/{len(niche_queue)}] Next niche: '{niche}'")
        else:
            print()
            niche = input("Enter niche to scrape (or 'done'): ").strip()
            if niche.lower() == 'done':
                break
            if not niche:
                print("[SKIP] Empty input, try again")
                continue

        try:
            # Scrape the niche
            businesses = scrape_niche(
                niche=niche,
                location=args.location,
                limit=args.limit,
                country=args.country,
                no_website_only=args.no_website
            )

            if not businesses:
                print(f"[WARN] No businesses found for '{niche}'")
                continue

            # Get or create worksheet for this niche
            worksheet, existing_ids = get_or_create_worksheet(
                spreadsheet, niche, existing_worksheets
            )

            # Deduplicate and prepare rows
            new_rows = []
            duplicates = 0
            for business in businesses:
                lead_id = generate_lead_id(
                    business.get("business_name", ""),
                    business.get("address", "")
                )
                if lead_id in existing_ids:
                    duplicates += 1
                else:
                    existing_ids.add(lead_id)
                    new_rows.append(business_to_row(business, niche))

            # Append to sheet
            if new_rows:
                worksheet.append_rows(new_rows)
                print(f"[OK] Added {len(new_rows)} leads to '{niche}' tab")
                if duplicates:
                    print(f"     Skipped {duplicates} duplicates")
                total_leads += len(new_rows)
                niches_scraped.append(niche)
            else:
                print(f"[WARN] All {duplicates} leads were duplicates")

        except Exception as e:
            print(f"[ERROR] Failed to scrape '{niche}': {e}")
            continue

    # Summary
    print()
    print("=" * 70)
    print("SCRAPING COMPLETE")
    print("=" * 70)
    print(f"Niches scraped: {len(niches_scraped)}")
    for niche in niches_scraped:
        print(f"  - {niche}")
    print(f"Total leads added: {total_leads}")
    print(f"\nSheet URL: {spreadsheet.url}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

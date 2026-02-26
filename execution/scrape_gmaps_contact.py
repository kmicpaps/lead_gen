# [CLI] — run via: py execution/scrape_gmaps_contact.py --help
#!/usr/bin/env python3
"""
Google Maps Scraper with Contact Details
Uses lukaskrivka/google-maps-with-contact-details actor to scrape businesses
including emails, phone numbers, and social media links.
"""

import os
import sys
import json
import argparse
import urllib.parse
from typing import List, Dict
from apify_client import ApifyClient
from dotenv import load_dotenv

# Fix Windows console encoding for Latvian diacritics
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

# Actor ID
ACTOR_ID = "lukaskrivka/google-maps-with-contact-details"

# Domains that are NOT business websites — news sites, directories, etc.
# Emails from these domains should be discarded (they belong to the site, not the business)
BLOCKED_DOMAINS = {
    # Latvian news/media
    "db.lv", "delfi.lv", "apollo.lv", "tvnet.lv", "lsm.lv", "la.lv",
    "nra.lv", "diena.lv", "kas.lv", "jauns.lv", "leta.lv",
    # Directories/listings
    "firmas.lv", "zl.lv", "1188.lv", "infolapa.zl.lv", "pasts.lv",
    "lursoft.lv", "company.lursoft.lv", "yellowpages.lv",
    # Global directories/review sites
    "yelp.com", "tripadvisor.com", "trustpilot.com", "glassdoor.com",
    "booking.com", "airbnb.com",
}


def scrape_gmaps_with_contacts(
    search_query: str,
    limit: int = 500,
    language: str = "en",
    country: str = "lv",
    dump_raw: bool = False,
    output_dir: str = ".tmp/gmaps_contact"
) -> List[Dict]:
    """
    Scrape businesses from Google Maps with contact details (emails, social).

    Args:
        search_query: Search term (e.g., "frizieris")
        limit: Max results per search
        language: Language code
        country: Country code (lowercase)
        dump_raw: Save first raw item to JSON for schema discovery
        output_dir: Directory for raw dump output

    Returns:
        List of normalized business dicts
    """
    api_key = os.getenv("APIFY_API_KEY")
    if not api_key:
        raise ValueError("APIFY_API_KEY not found in environment variables")

    client = ApifyClient(api_key)

    run_input = {
        "searchStringsArray": [search_query],
        "maxCrawledPlacesPerSearch": limit,
        "language": language,
        "countryCode": country.lower(),
        "scrapeDirectories": False,
        "deeperCityScrape": False,
        "includeWebResults": False,
        "maxImages": 0,
        "maxReviews": 0,
        "onlyDataFromSearchPage": False,
    }

    print(f"Starting scrape: '{search_query}' (limit: {limit}, country: {country})")
    print(f"Actor: {ACTOR_ID}")

    run = client.actor(ACTOR_ID).call(run_input=run_input, timeout_secs=600)

    results = []
    raw_dumped = False

    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        # Dump first raw item for schema discovery
        if dump_raw and not raw_dumped:
            os.makedirs(output_dir, exist_ok=True)
            raw_path = os.path.join(output_dir, "raw_sample.json")
            with open(raw_path, 'w', encoding='utf-8') as f:
                json.dump(item, f, indent=2, ensure_ascii=False)
            print(f"[DUMP] Saved raw sample to {raw_path}")
            # Also print all top-level keys for quick reference
            print(f"[DUMP] Top-level fields ({len(item)} keys): {sorted(item.keys())}")
            raw_dumped = True

        # Skip permanently closed businesses
        if item.get("permanentlyClosed", False):
            continue

        # Normalize fields — actor uses plural array fields for social/contact
        raw_emails = item.get("emails") or []
        phones_extra = item.get("phones") or []
        biz_domain = item.get("domain") or None
        website = item.get("website") or None

        # Treat social-only "websites" as no website
        # (Instagram/Facebook pages aren't real business websites)
        social_domains = {"instagram", "facebook", "youtube", "tiktok"}
        if website and biz_domain in social_domains:
            website = None
            biz_domain = None

        # Discard businesses whose "website" is a blocked domain (news/directory)
        # These pages belong to the site, not the business
        if biz_domain and biz_domain in BLOCKED_DOMAINS:
            website = None
            raw_emails = []  # All emails from blocked sites are irrelevant
            biz_domain = None

        # Filter emails: keep only those from the business's own domain
        # or from common free providers
        free_providers = {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com",
                          "inbox.lv", "one.lv", "mail.ru"}
        if biz_domain and biz_domain not in social_domains:
            emails = [e for e in raw_emails if e.endswith(f"@{biz_domain}")]
            emails += [e for e in raw_emails
                       if e.split("@")[-1] in free_providers and e not in emails]
        else:
            # No domain known — keep free-provider emails only (safest)
            emails = [e for e in raw_emails if e.split("@")[-1] in free_providers]

        # First non-empty value from social arrays
        def first_of(arr): return arr[0] if arr else None

        # Construct proper Google Maps URL from placeId + title
        # (actor's "url" field is unreliable — sometimes contains the website URL)
        place_id = item.get("placeId") or ""
        title = item.get("title") or ""
        if place_id:
            gmaps_url = (f"https://www.google.com/maps/search/?api=1"
                         f"&query={urllib.parse.quote(title)}"
                         f"&query_place_id={place_id}")
        else:
            gmaps_url = item.get("url") or ""

        business = {
            "place_id": place_id,
            "business_name": title,
            "category": item.get("categoryName") or "",
            "categories": item.get("categories") or [],
            "address": item.get("address") or "",
            "street": item.get("street") or "",
            "city": item.get("city") or "",
            "postal_code": item.get("postalCode") or "",
            "country": item.get("countryCode") or country,
            "phone": item.get("phone") or "",
            "phone_unformatted": item.get("phoneUnformatted") or "",
            "website": website,
            "domain": biz_domain,
            "google_maps_url": gmaps_url,
            "rating": item.get("totalScore"),
            "review_count": item.get("reviewsCount"),
            "emails": emails,
            "phones_extra": phones_extra,
            "facebook": first_of(item.get("facebooks") or []),
            "instagram": first_of(item.get("instagrams") or []),
            "linkedin": first_of(item.get("linkedIns") or []),
            "twitter": first_of(item.get("twitters") or []),
            "youtube": first_of(item.get("youtubes") or []),
            "tiktok": first_of(item.get("tiktoks") or []),
            "whatsapp": first_of(item.get("whatsapps") or []),
        }

        results.append(business)

    print(f"[OK] Scraped {len(results)} businesses")

    # Quick stats
    with_email = sum(1 for r in results if r["emails"])
    with_website = sum(1 for r in results if r["website"])
    with_phone = sum(1 for r in results if r["phone"])
    print(f"     With email: {with_email} ({100*with_email//max(len(results),1)}%)")
    print(f"     With website: {with_website} ({100*with_website//max(len(results),1)}%)")
    print(f"     With phone: {with_phone} ({100*with_phone//max(len(results),1)}%)")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Google Maps with contact details (emails, social)"
    )
    parser.add_argument("--search", required=True, help="Search query")
    parser.add_argument("--limit", type=int, default=500, help="Max results (default: 500)")
    parser.add_argument("--language", default="en", help="Language code (default: en)")
    parser.add_argument("--country", default="lv", help="Country code (default: lv)")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument("--dump-raw", action="store_true", help="Save first raw item for schema discovery")
    parser.add_argument("--output-dir", default=".tmp/gmaps_contact", help="Dir for raw dump (default: .tmp/gmaps_contact)")

    args = parser.parse_args()

    results = scrape_gmaps_with_contacts(
        search_query=args.search,
        limit=args.limit,
        language=args.language,
        country=args.country,
        dump_raw=args.dump_raw,
        output_dir=args.output_dir,
    )

    # Save results
    output_path = args.output
    if not output_path:
        os.makedirs(args.output_dir, exist_ok=True)
        output_path = os.path.join(args.output_dir, "leads.json")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved {len(results)} leads to {output_path}")


if __name__ == "__main__":
    main()

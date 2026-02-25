# [CLI] — run via: py execution/scrape_google_maps.py --help
#!/usr/bin/env python3
"""
Google Maps Business Scraper using Apify
Uses compass/crawler-google-places actor to scrape business data from Google Maps
"""

import os
import json
import argparse
from typing import List, Dict, Optional
from apify_client import ApifyClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def scrape_google_maps(
    search_query: str,
    limit: int = 10,
    language: str = "en",
    country: str = "us"
) -> List[Dict]:
    """
    Scrape businesses from Google Maps using Apify's compass/crawler-google-places actor

    Args:
        search_query: Search query (e.g., "plumbers in Austin TX")
        limit: Maximum number of results to return
        language: Language code for results
        country: Country code for results

    Returns:
        List of business dictionaries with structured data
    """
    # Get API key from environment
    api_key = os.getenv("APIFY_API_KEY")
    if not api_key:
        raise ValueError("APIFY_API_KEY not found in environment variables")

    # Initialize Apify client
    client = ApifyClient(api_key)

    # Prepare input for the actor
    run_input = {
        "searchStringsArray": [search_query],
        "maxCrawledPlacesPerSearch": limit,
        "language": language,
        "countryCode": country,
        "includeReviews": False,  # Don't need full reviews for lead gen
        "includeOpeningHours": True,
        "includeContactInfo": True,
        "includePeopleAlsoSearch": False,
        "includeImages": False,  # Don't need images for lead gen
    }

    print(f"Starting Google Maps scrape for: '{search_query}'")
    print(f"Limit: {limit} results")

    # Run the actor and wait for it to finish
    run = client.actor("compass/crawler-google-places").call(run_input=run_input)

    # Fetch results from the actor's dataset
    results = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        # Extract and structure the business data
        business = {
            "place_id": item.get("placeId"),
            "business_name": item.get("title"),
            "category": item.get("categoryName"),
            "address": item.get("address"),
            "city": item.get("city"),
            "state": item.get("state"),
            "zip_code": item.get("postalCode"),
            "country": item.get("countryCode"),
            "phone": item.get("phone"),
            "website": item.get("website"),
            "google_maps_url": item.get("url"),
            "rating": item.get("totalScore"),
            "review_count": item.get("reviewsCount"),
            "price_level": item.get("priceLevel"),
            "latitude": item.get("location", {}).get("lat") if item.get("location") else None,
            "longitude": item.get("location", {}).get("lng") if item.get("location") else None,
            "business_hours": item.get("openingHours"),
            "permanently_closed": item.get("permanentlyClosed", False),
        }

        # Skip permanently closed businesses
        if business["permanently_closed"]:
            continue

        results.append(business)

    print(f"[OK] Scraped {len(results)} businesses from Google Maps")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Scrape businesses from Google Maps using Apify"
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
        help="Maximum number of results (default: 10)"
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Language code (default: en)"
    )
    parser.add_argument(
        "--country",
        default="us",
        help="Country code (default: us, must be lowercase)"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file path (optional)"
    )

    args = parser.parse_args()

    # Scrape Google Maps
    results = scrape_google_maps(
        search_query=args.search,
        limit=args.limit,
        language=args.language,
        country=args.country
    )

    # Print results (handle Unicode encoding errors on Windows)
    print(f"\nFound {len(results)} businesses:")
    for i, business in enumerate(results, 1):
        try:
            print(f"{i}. {business['business_name']}")
            print(f"   Address: {business['address']}")
            print(f"   Phone: {business['phone'] or 'N/A'}")
            print(f"   Website: {business['website'] or 'N/A'}")
            print()
        except UnicodeEncodeError:
            # Windows console encoding issue - skip printing this entry
            print(f"{i}. [Unicode encoding error - see output file]")
            continue

    # Save to file if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"[OK] Saved results to {args.output}")


if __name__ == "__main__":
    main()

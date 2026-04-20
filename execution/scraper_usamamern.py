# [CLI] -- run via: py execution/scraper_usamamern.py --help
"""
Phase 1 of the backup Apollo pipeline.

Scrapes an Apollo search URL via the usamamern "No Cookies" RapidAPI scraper.
Respects Apollo's ~100-page pagination cap (2,500 leads max per sort direction).

Output: raw lead records (metadata only, NO real emails -- those are locked by
Apollo's unlock mechanism and filled in downstream by email_finder_snipercoder.py
and email_finder_clearpath.py).

Optional dual-sort mode runs both DESC and ASC over the same URL and merges by
person id, giving up to 5,000 unique leads (less any overlap in the middle of
the recommendations_score range).

REQUIRES:
  - RapidAPI key shared with codecrafter (.env: x-rapidapi-key)
  - A paid plan on usamamern's Apollo scraper:
    https://rapidapi.com/usamamern/api/apollo-io-no-cookies-required

Cost: RapidAPI subscription (quota-based, typically ~10K requests/mo).
"""
import argparse
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import log_ok, log_error, save_json  # type: ignore

load_dotenv()

USAMAMERN_HOST = "apollo-io-no-cookies-required.p.rapidapi.com"
USAMAMERN_URL = f"https://{USAMAMERN_HOST}/search_people_via_url"


def _flip_sort_in_url(url: str, ascending: bool) -> str:
    """Replace sortAscending=true/false in the URL with the requested value."""
    target = f"sortAscending={'true' if ascending else 'false'}"
    if "sortAscending=true" in url:
        return url.replace("sortAscending=true", target)
    if "sortAscending=false" in url:
        return url.replace("sortAscending=false", target)
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{target}"


def paginate(url: str, api_key: str, max_pages: int = 100, page_sleep: float = 0.5) -> list:
    """Paginate a single URL + sort variant. Stops at Apollo's ~100 page cap
    (which returns 400 Bad Request) or when a page has 0 results.
    """
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": USAMAMERN_HOST,
        "x-rapidapi-key": api_key,
    }
    all_people = []
    total_pages = None
    page = 1
    while page <= max_pages:
        for attempt in range(3):
            try:
                r = requests.post(USAMAMERN_URL, headers=headers, json={"url": url, "page": page}, timeout=120)
                if r.status_code == 429:
                    log_error(f"page {page}: 429 rate-limited, sleeping 30s")
                    time.sleep(30)
                    continue
                r.raise_for_status()
                data = r.json()["data"]
                break
            except Exception as e:
                log_error(f"page {page} attempt {attempt+1} failed: {e}")
                time.sleep(5)
        else:
            log_error(f"page {page} FAILED after 3 attempts, stopping")
            break

        people = data.get("people") or []
        pagination = data.get("pagination") or {}
        if total_pages is None:
            total_pages = pagination.get("total_pages") or 0
            total_entries = pagination.get("total_entries") or 0
            log_ok(f"total_pages={total_pages}, total_entries={total_entries}")

        all_people.extend(people)
        log_ok(f"page {page}/{total_pages}: +{len(people)} leads (cumulative: {len(all_people)})")

        if len(people) == 0 or (total_pages and page >= total_pages):
            break
        page += 1
        time.sleep(page_sleep)

    return all_people


def get_pool_size(url: str, api_key: str) -> dict:
    """Do a single page-1 request to peek at the total pool size. Used for
    pre-flight recommendations (dual-sort vs single). Returns:
      {'total_entries': int, 'total_pages': int}
    """
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": USAMAMERN_HOST,
        "x-rapidapi-key": api_key,
    }
    r = requests.post(USAMAMERN_URL, headers=headers, json={"url": url, "page": 1}, timeout=60)
    r.raise_for_status()
    pag = r.json()["data"].get("pagination") or {}
    return {
        "total_entries": pag.get("total_entries", 0),
        "total_pages": pag.get("total_pages", 0),
    }


def scrape(url: str, dual_sort: bool, max_pages: int = 100) -> list:
    """Run the scrape. Returns the deduped-by-id list of raw usamamern leads."""
    api_key = os.getenv("x-rapidapi-key")
    if not api_key:
        log_error("x-rapidapi-key missing from .env")
        sys.exit(1)

    all_people = []
    seen_ids = set()

    sort_variants = [False] + ([True] if dual_sort else [])
    for ascending in sort_variants:
        variant_url = _flip_sort_in_url(url, ascending)
        label = "ASC" if ascending else "DESC"
        log_ok(f"=== Running sort={label} ===")
        for person in paginate(variant_url, api_key, max_pages=max_pages):
            if person.get("id") and person["id"] not in seen_ids:
                seen_ids.add(person["id"])
                all_people.append(person)

    return all_people


def main() -> None:
    p = argparse.ArgumentParser(description="Usamamern Apollo RapidAPI scraper (Phase 1 of backup pipeline)")
    p.add_argument("--url", required=True, help="Apollo search URL")
    p.add_argument("--output", required=True, help="Path to write JSON output")
    p.add_argument("--dual-sort", action="store_true", help="Run DESC + ASC sorts and merge (up to 2x coverage)")
    p.add_argument("--max-pages", type=int, default=100, help="Pages per sort variant (Apollo cap ~100)")
    p.add_argument("--peek", action="store_true", help="Only fetch total_entries/total_pages (no scrape)")
    args = p.parse_args()

    if args.peek:
        api_key = os.getenv("x-rapidapi-key")
        info = get_pool_size(args.url, api_key)
        print(json.dumps(info, indent=2))
        return

    leads = scrape(args.url, args.dual_sort, args.max_pages)
    save_json(leads, args.output, mkdir=True)
    log_ok(f"Saved {len(leads)} leads to {args.output}")


if __name__ == "__main__":
    main()

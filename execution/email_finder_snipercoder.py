# [CLI] -- run via: py execution/email_finder_snipercoder.py --help
"""
Phase 2 of the backup Apollo pipeline.

Takes usamamern raw leads (with linkedin_url populated), runs their LinkedIn
URLs through snipercoder/bulk-linkedin-email-finder on Apify, and returns a
merged list with email + phone + profile enrichment where hits are found.

Apify actor: ddgw2oGFaH645BFAq  (snipercoder/bulk-linkedin-email-finder)
Pricing: $0.8 / 1,000 LinkedIn URLs
Hit rate observed: ~30-35% on fresh Apollo-scraped German logistics leads.

Output schema per snipercoder record (keys from actor output):
  01_Name, 02_First_name, 03_Last_name,
  04_Email          <- the email we want
  05_Phone_number   <- phone (rare but occasionally populated)
  06_Linkedin_url, 07_Title, 08_Department, 09_Functions,
  10_Seniority, 11_Headline, 12_Position_history_json,
  13_Current_address, 14_City, 15_Country, 16_Company_name, ...

REQUIRES: APIFY_API_KEY in .env
"""
import argparse
import json
import os
import sys
import time

from apify_client import ApifyClient
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import log_ok, log_error, save_json  # type: ignore

load_dotenv()

SNIPERCODER_ACTOR = "ddgw2oGFaH645BFAq"


def enrich(input_leads: list) -> list:
    token = os.getenv("APIFY_API_KEY")
    if not token:
        log_error("APIFY_API_KEY missing from .env")
        sys.exit(1)

    linkedin_urls = [l.get("linkedin_url") for l in input_leads if l.get("linkedin_url")]
    log_ok(f"Running snipercoder on {len(linkedin_urls)} LinkedIn URLs")

    client = ApifyClient(token)
    t0 = time.time()
    run = client.actor(SNIPERCODER_ACTOR).call(
        run_input={"linkedin_url_or_ids": linkedin_urls},
        timeout_secs=3600,
    )
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    log_ok(f"snipercoder returned {len(items)} records in {time.time()-t0:.0f}s")
    return items


def main() -> None:
    p = argparse.ArgumentParser(description="Snipercoder LinkedIn -> email finder (Phase 2 of backup pipeline)")
    p.add_argument("--input", required=True, help="Path to usamamern raw leads JSON")
    p.add_argument("--output", required=True, help="Path to write snipercoder results JSON")
    args = p.parse_args()

    with open(args.input, encoding="utf-8") as f:
        leads = json.load(f)

    items = enrich(leads)
    save_json(items, args.output, mkdir=True)
    log_ok(f"Saved {len(items)} snipercoder records to {args.output}")


if __name__ == "__main__":
    main()

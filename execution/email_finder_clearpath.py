# [CLI] -- run via: py execution/email_finder_clearpath.py --help
"""
Phase 3 of the backup Apollo pipeline.

Takes raw leads (plus snipercoder results if available), identifies which leads
snipercoder didn't find emails for, and runs those "misses" through
clearpath/email-finder-api on Apify. Clearpath generates common email patterns
(firstname.lastname@domain, flastname@domain, etc.) and SMTP-verifies each,
catching leads whose emails aren't public on LinkedIn.

Apify actor: eWT8czb4kT3gH1OWt  (clearpath/email-finder-api)
Pricing: PAY_PER_EVENT (~$0.003 per email pattern tested; ~2 events per lead)
Hit rate observed: ~70% on German logistics snipercoder-misses.
Input cap: 1,000 people per call -- this script chunks automatically.
Field names (STRICT): firstName, surname, domain (camelCase; "lastName" rejected).

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

CLEARPATH_ACTOR = "eWT8czb4kT3gH1OWt"
CHUNK_SIZE = 1000


def _derive_domain(org: dict) -> str:
    dom = (org.get("primary_domain") or "").strip()
    if dom:
        return dom
    website = (org.get("website_url") or "").strip()
    if website:
        return website.replace("http://", "").replace("https://", "").split("/")[0]
    return ""


def build_misses(leads: list, snipercoder_items: list) -> list:
    """Return clearpath input rows for leads whose LinkedIn URL did NOT get an email from snipercoder."""
    sc_hit_linkedin = set()
    for it in snipercoder_items or []:
        li = (it.get("06_Linkedin_url") or "").strip().lower().rstrip("/")
        em = it.get("04_Email") or ""
        if li and em and "@" in em:
            sc_hit_linkedin.add(li)

    misses = []
    for l in leads:
        li = (l.get("linkedin_url") or "").strip().lower().rstrip("/")
        if not li or li in sc_hit_linkedin:
            continue
        org = l.get("organization") or {}
        dom = _derive_domain(org)
        first, last = l.get("first_name"), l.get("last_name")
        if not (first and last and dom):
            continue
        misses.append({
            "firstName": first,
            "surname": last,
            "domain": dom,
            "companyName": org.get("name", ""),
        })
    return misses


def enrich(misses: list, mode: str = "optimized", use_nicknames: bool = True) -> list:
    token = os.getenv("APIFY_API_KEY")
    if not token:
        log_error("APIFY_API_KEY missing from .env")
        sys.exit(1)
    if not misses:
        return []

    client = ApifyClient(token)
    all_items = []
    for i in range(0, len(misses), CHUNK_SIZE):
        chunk = misses[i:i + CHUNK_SIZE]
        log_ok(f"clearpath chunk {i // CHUNK_SIZE + 1}: {len(chunk)} people")
        t0 = time.time()
        run = client.actor(CLEARPATH_ACTOR).call(
            run_input={"people": chunk, "mode": mode, "useNicknames": use_nicknames},
            timeout_secs=3600,
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        log_ok(f"  -> {len(items)} results in {time.time()-t0:.0f}s")
        all_items.extend(items)
    return all_items


def main() -> None:
    p = argparse.ArgumentParser(description="Clearpath pattern-based email finder (Phase 3 of backup pipeline)")
    p.add_argument("--input-leads", required=True, help="Usamamern raw leads JSON (has first_name, last_name, organization)")
    p.add_argument("--input-snipercoder", required=True, help="Snipercoder results JSON (for determining misses)")
    p.add_argument("--output", required=True, help="Path to write clearpath results JSON")
    p.add_argument("--mode", default="optimized", choices=["optimized", "expanded"])
    p.add_argument("--no-nicknames", action="store_true", help="Disable nickname retry fallback")
    args = p.parse_args()

    with open(args.input_leads, encoding="utf-8") as f:
        leads = json.load(f)
    with open(args.input_snipercoder, encoding="utf-8") as f:
        snipercoder_items = json.load(f)

    misses = build_misses(leads, snipercoder_items)
    log_ok(f"Clearpath input: {len(misses)} snipercoder-misses (of {len(leads)} total leads)")
    items = enrich(misses, mode=args.mode, use_nicknames=not args.no_nicknames)
    save_json(items, args.output, mkdir=True)
    log_ok(f"Saved {len(items)} clearpath records to {args.output}")


if __name__ == "__main__":
    main()

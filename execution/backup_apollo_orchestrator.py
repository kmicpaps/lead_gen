# [ORCHESTRATOR] -- run via: py execution/backup_apollo_orchestrator.py --help
"""
Backup Apollo pipeline orchestrator -- 5-phase flow with disk checkpoints.

Runs when the primary Apollo scrapers (Olympus / CodeCrafter / PeakyDev) aren't
available or produce poor results (stale data, thin niches, etc.). Isolated
from the main registry: this is a sequential enrichment pipeline, not a
parallel scraper.

PHASES
  1  usamamern RapidAPI scrape   -> raw leads (no emails, locked by Apollo)
  2  snipercoder (Apify)          -> LinkedIn URL -> email (high-confidence hits)
  3  clearpath (Apify)            -> name+domain -> email pattern (fills misses)
  4  xmiso (Apify, MillionVerifier)-> classify every found email into tier A/B/C/D
  5  normalize + dedup vs prior   -> final Google Sheet export

Each phase writes a checkpoint JSON to the working directory. Rerun = skip
already-done phases (delete the checkpoint file to force rerun).

See `directives/backup_apollo_pipeline.md` for the full SOP including cost
breakdown, dual-sort recommendations, and tier meanings.

REQUIRED ENV VARS:
  - x-rapidapi-key   (for usamamern)
  - APIFY_API_KEY    (for snipercoder, clearpath, xmiso)
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime

import requests
from apify_client import ApifyClient
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import log_ok, log_error, log_info, save_json  # type: ignore
from scraper_usamamern import get_pool_size, scrape as usamamern_scrape
from email_finder_snipercoder import enrich as snipercoder_enrich
from email_finder_clearpath import build_misses as cp_build_misses, enrich as clearpath_enrich
from email_verifier_xmiso import verify as xmiso_verify

load_dotenv()


# ==================== PHASE ORCHESTRATION ====================

def phase1_scrape(url: str, dual_sort: bool, cp_path: str) -> list:
    if os.path.exists(cp_path):
        leads = json.load(open(cp_path, encoding="utf-8"))
        log_info(f"PHASE 1 skip (checkpoint: {len(leads)} leads)")
        return leads
    log_info("PHASE 1 start: usamamern scrape")
    leads = usamamern_scrape(url, dual_sort=dual_sort)
    save_json(leads, cp_path, mkdir=True)
    log_ok(f"PHASE 1 done: {len(leads)} leads -> {cp_path}")
    return leads


def phase2_snipercoder(leads: list, cp_path: str) -> list:
    if os.path.exists(cp_path):
        items = json.load(open(cp_path, encoding="utf-8"))
        log_info(f"PHASE 2 skip (checkpoint: {len(items)} records)")
        return items
    log_info("PHASE 2 start: snipercoder enrichment")
    items = snipercoder_enrich(leads)
    save_json(items, cp_path, mkdir=True)
    log_ok(f"PHASE 2 done: {len(items)} records -> {cp_path}")
    return items


def phase3_clearpath(leads: list, snipercoder_items: list, cp_path: str) -> list:
    if os.path.exists(cp_path):
        items = json.load(open(cp_path, encoding="utf-8"))
        log_info(f"PHASE 3 skip (checkpoint: {len(items)} records)")
        return items
    log_info("PHASE 3 start: clearpath on snipercoder misses")
    misses = cp_build_misses(leads, snipercoder_items)
    log_info(f"  {len(misses)} misses to pattern-guess")
    items = clearpath_enrich(misses)
    save_json(items, cp_path, mkdir=True)
    log_ok(f"PHASE 3 done: {len(items)} records -> {cp_path}")
    return items


def phase3b_merge(leads: list, sc_items: list, cp_items: list, cp_path: str) -> list:
    """Build one unified record per usamamern lead with best available email + phone."""
    if os.path.exists(cp_path):
        data = json.load(open(cp_path, encoding="utf-8"))
        log_info(f"PHASE 3b skip (checkpoint: {len(data)} merged)")
        return data

    sc_by_li = {}
    for it in sc_items:
        li = (it.get("06_Linkedin_url") or "").lower().rstrip("/")
        if li:
            sc_by_li[li] = it

    cp_by_key = {}
    for it in cp_items:
        key = (
            (it.get("firstName") or "").lower().strip(),
            (it.get("surname") or "").lower().strip(),
            (it.get("domain") or "").lower().strip(),
        )
        cp_by_key[key] = it

    merged = []
    for l in leads:
        li = (l.get("linkedin_url") or "").lower().rstrip("/")
        org = l.get("organization") or {}
        dom = (org.get("primary_domain") or "").lower()
        if not dom and org.get("website_url"):
            dom = org["website_url"].replace("http://", "").replace("https://", "").split("/")[0].lower()

        sc = sc_by_li.get(li) if li else None
        cp_key = (
            (l.get("first_name") or "").lower().strip(),
            (l.get("last_name") or "").lower().strip(),
            dom,
        )
        cp_rec = cp_by_key.get(cp_key)

        email, email_source, email_flags = "", "", {}
        if sc and sc.get("04_Email"):
            email, email_source = sc["04_Email"], "snipercoder"
        elif cp_rec and cp_rec.get("email"):
            email, email_source = cp_rec["email"], "clearpath"
            email_flags = {
                "isCatchAll": cp_rec.get("isCatchAll"),
                "isDeliverable": cp_rec.get("isDeliverable"),
                "isSafeToSend": cp_rec.get("isSafeToSend"),
                "validationStatus": cp_rec.get("validationStatus"),
            }

        phone = ""
        if sc and sc.get("05_Phone_number"):
            phone = sc["05_Phone_number"]
        elif org.get("sanitized_phone"):
            phone = org["sanitized_phone"]
        elif org.get("phone"):
            phone = org["phone"]

        merged.append({
            "usamamern": l, "snipercoder": sc, "clearpath": cp_rec,
            "email": email, "email_source": email_source, "email_flags": email_flags,
            "phone": phone,
        })

    with_email = sum(1 for m in merged if m["email"])
    by_source = Counter(m["email_source"] for m in merged if m["email"])
    log_ok(f"PHASE 3b done: {len(merged)} leads, {with_email} with email ({100*with_email/max(1,len(merged)):.0f}%), by source={dict(by_source)}")
    save_json(merged, cp_path, mkdir=True)
    return merged


def phase4_verify(merged: list, cp_path: str) -> list:
    if os.path.exists(cp_path):
        data = json.load(open(cp_path, encoding="utf-8"))
        log_info(f"PHASE 4 skip (checkpoint: {len(data)} verifications)")
        return data
    emails = [m["email"] for m in merged if m.get("email")]
    log_info(f"PHASE 4 start: xmiso verify {len(emails)} emails")
    results = xmiso_verify(emails)
    save_json(results, cp_path, mkdir=True)
    log_ok(f"PHASE 4 done: {len(results)} verifications -> {cp_path}")
    return results


def phase5_normalize_export(
    merged: list,
    xmiso_results: list,
    campaign_country: str,
    dedup_csv: str,
    output_path: str,
    sheet_title: str,
) -> list:
    existing_emails, existing_linkedin = set(), set()
    if dedup_csv and os.path.exists(dedup_csv):
        with open(dedup_csv, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                e = (row.get("Email") or "").strip().lower()
                if e:
                    existing_emails.add(e)
                li = (row.get("LinkedIn URL") or "").strip().lower().rstrip("/")
                if li:
                    existing_linkedin.add(li)
        log_info(f"PHASE 5 dedup pool: {len(existing_emails)} emails from {dedup_csv}")

    xm_by_email = {it["email"].lower(): it for it in xmiso_results if it.get("email")}

    def titlecase(s):
        return s.title() if s and s.islower() else s

    final, skipped_dup, skipped_no_email = [], 0, 0
    for m in merged:
        email = (m.get("email") or "").strip()
        if not email:
            skipped_no_email += 1
            continue
        email_l = email.lower()
        li_l = ((m.get("usamamern", {}) or {}).get("linkedin_url") or "").strip().lower().rstrip("/")
        if email_l in existing_emails or (li_l and li_l in existing_linkedin):
            skipped_dup += 1
            continue

        xm = xm_by_email.get(email_l, {})
        q, r = xm.get("email_quality") or "", xm.get("email_result") or ""
        tier = "A" if (q == "good" and r == "ok") else \
               "B" if (q == "risky" and r == "catch_all") else \
               "C" if q == "risky" else "D"

        u, org = m["usamamern"] or {}, (m["usamamern"] or {}).get("organization") or {}
        sc = m.get("snipercoder") or {}
        final.append({
            "first_name": titlecase(u.get("first_name") or ""),
            "last_name": titlecase(u.get("last_name") or ""),
            "full_name": titlecase(u.get("name") or ""),
            "title": u.get("title") or sc.get("07_Title") or "",
            "email": email,
            "email_status": f"xmiso:{q}/{r}",
            "email_tier": tier,
            "email_source": m.get("email_source"),
            "linkedin_url": u.get("linkedin_url") or "",
            "phone": m.get("phone") or "",
            "city": titlecase(u.get("city") or ""),
            "country": titlecase(u.get("country") or ""),
            "company_name": titlecase(org.get("name") or ""),
            "company_website": org.get("website_url") or "",
            "company_linkedin": org.get("linkedin_url") or "",
            "company_phone": org.get("sanitized_phone") or org.get("phone") or "",
            "company_domain": org.get("primary_domain") or "",
            "company_country": campaign_country,
            "industry": "",
            "source": f"backup_apollo+{m.get('email_source') or '?'}+xmiso",
        })

    # Sort Tier A first
    tier_order = {"A": 0, "B": 1, "C": 2, "D": 3}
    final.sort(key=lambda l: (tier_order.get(l.get("email_tier"), 9), l.get("company_name", "")))

    tier_counts = Counter(f["email_tier"] for f in final)
    log_ok(f"PHASE 5 done: {len(final)} final | by tier: {dict(tier_counts)} | dup={skipped_dup} no_email={skipped_no_email}")

    save_json(final, output_path, mkdir=True)

    # Upload to Sheets
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_info(f"PHASE 5 uploading to Google Sheets: {sheet_title}")
    cmd = [
        sys.executable,
        os.path.join(script_dir, "google_sheets_exporter.py"),
        "--input", output_path,
        "--sheet-title", sheet_title,
        "--mode", "create",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[-2000:], file=sys.stderr)

    return final


# ==================== MAIN ====================

def extract_country_from_url(url: str) -> str:
    """Pull organizationLocations[]=<country> from an Apollo URL. Returns '' if missing."""
    import re
    import urllib.parse
    m = re.search(r"organizationLocations\[\]=([^&]+)", url)
    if not m:
        return ""
    return urllib.parse.unquote(m.group(1))


def recommend_sort_mode(total_entries: int) -> tuple:
    """Based on Apollo pool size, recommend single vs dual sort.
    Returns (recommended_dual, message).
    """
    if total_entries <= 2500:
        return (False, f"Pool is {total_entries} leads. Single DESC sort is sufficient -- dual would waste API calls.")
    if total_entries <= 5000:
        return (True, f"Pool is {total_entries} leads. Dual sort (DESC+ASC) recommended -- captures full set.")
    return (True, f"Pool is {total_entries} leads (>5K). Dual sort recommended but WILL MISS ~{total_entries - 5000} leads in the middle of recommendations_score range (Apollo's 100-page cap applies per sort direction).")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Backup Apollo pipeline orchestrator (usamamern -> snipercoder -> clearpath -> xmiso -> Sheets)"
    )
    p.add_argument("--url", required=True, help="Apollo search URL")
    p.add_argument("--country", help="Campaign country (e.g. Germany, Latvia). If omitted, auto-extracted from URL's organizationLocations[]")
    p.add_argument("--sheet-title", help="Title for the final Google Sheet. If omitted, defaults to 'Backup Apollo -- {country} {YYYY-MM-DD}'")
    p.add_argument("--work-dir", help="Directory for checkpoint files (default: .tmp/backup_apollo/{timestamp})")
    p.add_argument("--dedup-csv", help="Optional CSV to dedup against (email + LinkedIn URL)")
    p.add_argument("--dual-sort", choices=["yes", "no", "auto"], default="auto",
                   help="'yes' forces DESC+ASC; 'no' forces DESC only; 'auto' (default) uses Apollo pool size")
    p.add_argument("--max-pages", type=int, default=100, help="Pages per sort variant (Apollo cap is ~100)")
    p.add_argument("--assume-yes", action="store_true", help="Skip interactive confirmation on dual-sort recommendation")
    args = p.parse_args()

    # Auto-extract country from URL if not supplied
    country = args.country or extract_country_from_url(args.url)
    if not country:
        sys.exit("Could not determine campaign country. Pass --country or include organizationLocations[] in the URL.")

    # Default sheet title
    sheet_title = args.sheet_title or f"Backup Apollo -- {country} {datetime.now().strftime('%Y-%m-%d')}"

    # Peek at pool to recommend sort strategy
    api_key = os.getenv("x-rapidapi-key")
    if not api_key:
        sys.exit("x-rapidapi-key missing from .env")
    info = get_pool_size(args.url, api_key)
    total = info.get("total_entries", 0)
    rec_dual, rec_msg = recommend_sort_mode(total)
    log_info(rec_msg)

    if args.dual_sort == "auto":
        use_dual = rec_dual
    else:
        use_dual = args.dual_sort == "yes"
        if use_dual != rec_dual:
            log_info(f"Overriding recommendation: using dual_sort={use_dual} (recommended was {rec_dual})")

    if not args.assume_yes and total > 5000:
        ans = input(f"Apollo pool is {total}. Continuing will miss ~{total-5000} middle leads. Proceed? [y/N] ")
        if ans.strip().lower() not in ("y", "yes"):
            sys.exit("Aborted by user")

    # Set up working directory
    work_dir = args.work_dir or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", ".tmp", "backup_apollo",
        datetime.now().strftime("%Y%m%d_%H%M%S"),
    )
    os.makedirs(work_dir, exist_ok=True)
    log_info(f"Working directory: {work_dir}")

    cp = {
        "raw": os.path.join(work_dir, "phase1_usamamern_raw.json"),
        "sc":  os.path.join(work_dir, "phase2_snipercoder.json"),
        "cp":  os.path.join(work_dir, "phase3_clearpath.json"),
        "merged": os.path.join(work_dir, "phase3b_all_emails.json"),
        "xm":  os.path.join(work_dir, "phase4_xmiso.json"),
        "final": os.path.join(work_dir, "phase5_final_normalized.json"),
    }

    t0 = time.time()
    leads = phase1_scrape(args.url, use_dual, cp["raw"])
    sc_items = phase2_snipercoder(leads, cp["sc"])
    cp_items = phase3_clearpath(leads, sc_items, cp["cp"])
    merged = phase3b_merge(leads, sc_items, cp_items, cp["merged"])
    xm_results = phase4_verify(merged, cp["xm"])
    final = phase5_normalize_export(
        merged, xm_results,
        campaign_country=country,
        dedup_csv=args.dedup_csv or "",
        output_path=cp["final"],
        sheet_title=sheet_title,
    )

    log_ok(f"\n=== PIPELINE COMPLETE in {(time.time()-t0)/60:.1f} min ===")
    log_ok(f"Delivered: {len(final)} leads")


if __name__ == "__main__":
    main()

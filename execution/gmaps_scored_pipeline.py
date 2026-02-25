# [CLI] — run via: py execution/gmaps_scored_pipeline.py --help
#!/usr/bin/env python3
"""
Google Maps Lead Gen Pipeline
Scrape → Dedup → Split → Evaluate → Export to Google Sheets

Two output streams:
  - cold_calling: phone-only leads (no email)
  - cold_email_scored: email leads with website quality scores + insights
"""

import os
import sys
import hashlib
import argparse
from datetime import datetime
from typing import List, Dict

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from execution.scrape_gmaps_contact import scrape_gmaps_with_contacts
from execution.lead_splitter import split_leads
from execution.website_evaluator import evaluate_websites_batch
from execution.utils import load_json, save_json

load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'openid',
]

# Pre-test limit: number of leads to scrape when validating search terms
PRE_TEST_LIMIT = 10

COLD_CALLING_HEADERS = [
    "niche", "business_name", "category", "address", "city",
    "phone", "google_maps_url", "rating", "review_count",
]

COLD_EMAIL_HEADERS = [
    "niche", "business_name", "category", "address", "city",
    "phone", "website", "email_1", "email_2",
    "facebook", "instagram", "linkedin",
    "google_maps_url", "rating", "review_count",
    "overall_score", "performance_score", "seo_score",
    "mobile_friendly", "has_ssl", "cms",
    "insight_1", "insight_2", "insight_3",
]


def generate_lead_id(business_name: str, address: str) -> str:
    key = f"{business_name}|{address}".lower().strip()
    return hashlib.md5(key.encode()).hexdigest()


def authenticate_sheets():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return gspread.authorize(creds)


def dedup_leads(leads: List[Dict]) -> List[Dict]:
    """Deduplicate leads by place_id or business_name+address hash."""
    seen_ids = set()
    unique = []
    for lead in leads:
        # Try place_id first, fall back to name+address hash
        lid = lead.get("place_id") or generate_lead_id(
            lead.get("business_name", ""), lead.get("address", "")
        )
        if lid not in seen_ids:
            seen_ids.add(lid)
            unique.append(lead)
    return unique


def lead_to_calling_row(lead: Dict) -> List[str]:
    return [
        str(lead.get("niche", "")),
        str(lead.get("business_name", "")),
        str(lead.get("category", "")),
        str(lead.get("address", "")),
        str(lead.get("city", "")),
        str(lead.get("phone", "")),
        str(lead.get("google_maps_url", "")),
        str(lead.get("rating") or ""),
        str(lead.get("review_count") or ""),
    ]


def lead_to_email_row(lead: Dict) -> List[str]:
    emails = lead.get("emails", [])
    insights = lead.get("insights", [])
    return [
        str(lead.get("niche", "")),
        str(lead.get("business_name", "")),
        str(lead.get("category", "")),
        str(lead.get("address", "")),
        str(lead.get("city", "")),
        str(lead.get("phone", "")),
        str(lead.get("website") or ""),
        str(emails[0]) if len(emails) > 0 else "",
        str(emails[1]) if len(emails) > 1 else "",
        str(lead.get("facebook") or ""),
        str(lead.get("instagram") or ""),
        str(lead.get("linkedin") or ""),
        str(lead.get("google_maps_url", "")),
        str(lead.get("rating") or ""),
        str(lead.get("review_count") or ""),
        str(lead.get("overall_score") or ""),
        str(lead.get("performance_score") or ""),
        str(lead.get("seo_score") or ""),
        str(lead.get("is_mobile_friendly") or ""),
        str(lead.get("has_ssl") or ""),
        str(lead.get("cms") or ""),
        str(insights[0]) if len(insights) > 0 else "",
        str(insights[1]) if len(insights) > 1 else "",
        str(insights[2]) if len(insights) > 2 else "",
    ]


def _safe_tab_name(name: str) -> str:
    """Convert niche name to ASCII-safe tab name for Google Sheets.
    Latvian chars like ā,č,ē,ī,ū,š,ž,ķ,ļ,ņ,ģ get transliterated."""
    _LV_MAP = {
        "ā": "a", "č": "c", "ē": "e", "ģ": "g", "ī": "i",
        "ķ": "k", "ļ": "l", "ņ": "n", "š": "s", "ū": "u", "ž": "z",
        "Ā": "A", "Č": "C", "Ē": "E", "Ģ": "G", "Ī": "I",
        "Ķ": "K", "Ļ": "L", "Ņ": "N", "Š": "S", "Ū": "U", "Ž": "Z",
    }
    safe = "".join(_LV_MAP.get(c, c) for c in name)
    # Keep only alphanumeric, space, underscore, dash
    return "".join(c for c in safe if c.isalnum() or c in " _-")


def export_to_sheets(gc, sheet_url, cold_calling, cold_email, all_leads, niches_used):
    """Export both streams + per-niche email tabs to Google Sheets."""
    spreadsheet = gc.open_by_url(sheet_url)
    print(f"\n[SHEETS] Opened: {spreadsheet.title}")

    existing_tabs = {ws.title: ws for ws in spreadsheet.worksheets()}

    # Known pipeline tabs — anything else is stale and gets deleted
    PIPELINE_TABS = {"cold_calling", "cold_email_scored", "summary"}
    # Per-niche tabs we'll create
    niche_tab_names = set()
    for niche in niches_used:
        niche_tab_names.add(f"email_{_safe_tab_name(niche)}")

    keep_tabs = PIPELINE_TABS | niche_tab_names

    # Delete stale tabs (old V1 niche tabs, etc.) — but keep Sheet1 if it's the only one
    for tab_name, ws in existing_tabs.items():
        if tab_name not in keep_tabs and tab_name != "Sheet1":
            try:
                spreadsheet.del_worksheet(ws)
                print(f"[CLEANUP] Deleted stale tab: '{tab_name}'")
            except Exception as e:
                print(f"[WARN] Could not delete tab '{tab_name}': {e}")

    # Refresh after deletions
    existing_tabs = {ws.title: ws for ws in spreadsheet.worksheets()}

    def get_or_create_tab(name, headers):
        if name in existing_tabs:
            ws = existing_tabs[name]
            ws.clear()
        else:
            ws = spreadsheet.add_worksheet(title=name, rows=2000, cols=len(headers))
        ws.append_row(headers)
        ws.format(f'A1:{chr(64+len(headers))}1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })
        return ws

    # Cold calling tab
    ws_calling = get_or_create_tab("cold_calling", COLD_CALLING_HEADERS)
    if cold_calling:
        rows = [lead_to_calling_row(l) for l in cold_calling]
        ws_calling.append_rows(rows)
        print(f"[OK] Exported {len(rows)} leads to 'cold_calling' tab")

    # Cold email scored tab (all niches combined)
    ws_email = get_or_create_tab("cold_email_scored", COLD_EMAIL_HEADERS)
    if cold_email:
        rows = [lead_to_email_row(l) for l in cold_email]
        ws_email.append_rows(rows)
        print(f"[OK] Exported {len(rows)} leads to 'cold_email_scored' tab")

    # Per-niche cold email tabs
    for niche in niches_used:
        tab_name = f"email_{_safe_tab_name(niche)}"
        niche_leads = [l for l in cold_email if l.get("niche") == niche]
        if niche_leads:
            ws_niche = get_or_create_tab(tab_name, COLD_EMAIL_HEADERS)
            rows = [lead_to_email_row(l) for l in niche_leads]
            ws_niche.append_rows(rows)
            print(f"[OK] Exported {len(rows)} leads to '{tab_name}' tab")
        else:
            print(f"[SKIP] No cold email leads for niche '{niche}'")

    # Summary tab
    ws_summary = get_or_create_tab("summary", ["Metric", "Value"])
    evaluated = [l for l in cold_email if l.get("overall_score") is not None]
    scores = [l["overall_score"] for l in evaluated]
    avg_score = sum(scores) / len(scores) if scores else 0
    below_50 = sum(1 for s in scores if s < 50)

    # CMS breakdown
    cms_counts = {}
    for l in evaluated:
        cms = l.get("cms") or "Unknown/Custom"
        cms_counts[cms] = cms_counts.get(cms, 0) + 1
    cms_str = ", ".join(f"{k}: {v}" for k, v in sorted(cms_counts.items(), key=lambda x: -x[1]))

    # Niche breakdown
    niche_counts = {}
    for l in all_leads:
        n = l.get("niche", "unknown")
        niche_counts[n] = niche_counts.get(n, 0) + 1

    summary_rows = [
        ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")],
        ["Niches", ", ".join(niches_used)],
        ["Total scraped", str(len(all_leads))],
        ["After dedup", str(len(all_leads))],
        ["Cold calling (phone only)", str(len(cold_calling))],
        ["Cold email (has email)", str(len(cold_email))],
        ["Avg website score", f"{avg_score:.0f}/100"],
        ["Websites below 50", f"{below_50} ({100*below_50//max(len(scores),1)}%)"],
        ["CMS breakdown", cms_str],
    ]
    for niche, count in niche_counts.items():
        summary_rows.append([f"Niche: {niche}", str(count)])
    ws_summary.append_rows(summary_rows)
    print(f"[OK] Summary tab updated")

    # Delete Sheet1 if it still exists and we have other tabs
    try:
        all_ws = spreadsheet.worksheets()
        if len(all_ws) > 1:
            for ws in all_ws:
                if ws.title == "Sheet1":
                    spreadsheet.del_worksheet(ws)
                    print(f"[CLEANUP] Deleted 'Sheet1'")
                    break
    except Exception:
        pass

    return spreadsheet.url


def parse_niches_arg(niches_str: List[str]) -> Dict[str, str]:
    """Parse niche:term pairs from CLI args."""
    result = {}
    for item in niches_str:
        if ":" in item:
            label, term = item.split(":", 1)
            result[label.strip()] = term.strip()
        else:
            # Use the term itself as the label
            result[item.strip()] = item.strip()
    return result


def main():
    parser = argparse.ArgumentParser(description="Google Maps Lead Gen Pipeline")
    parser.add_argument("--location", default="Latvia", help="Location (default: Latvia)")
    parser.add_argument("--country", default="lv", help="Country code (default: lv)")
    parser.add_argument("--limit", type=int, default=500, help="Max results per niche (default: 500)")
    parser.add_argument("--language", default="en", help="Language (default: en)")
    parser.add_argument("--niches", nargs="+", required=True,
                        help='Niches as label:term (e.g., beauty:frizieris auto:"auto repair"). REQUIRED.')
    parser.add_argument("--sheet-url", help="Google Sheet URL to export to")
    parser.add_argument("--evaluate-websites", action="store_true", help="Run website evaluation on cold email leads")
    parser.add_argument("--workers", type=int, default=5, help="Parallel workers for website eval (default: 5)")
    parser.add_argument("--skip-scrape", help="Skip scraping, load leads from this JSON file")
    parser.add_argument("--dump-raw", action="store_true", help="Save raw Apify output for first item")
    parser.add_argument("--no-pre-test", action="store_true",
                        help="Skip the pre-test validation of search terms (use only if terms were already tested)")

    args = parser.parse_args()

    niches = parse_niches_arg(args.niches)

    print("=" * 70)
    print("GOOGLE MAPS LEAD GEN PIPELINE")
    print("=" * 70)
    print(f"Location: {args.location}")
    print(f"Country: {args.country}")
    print(f"Limit per niche: {args.limit}")
    print(f"Website evaluation: {args.evaluate_websites}")
    print(f"Pre-test: {'disabled' if args.no_pre_test else 'enabled'}")
    print(f"\nNiches ({len(niches)}):")
    for label, term in niches.items():
        print(f"  {label} → search: '{term}'")
    est_cost = len(niches) * args.limit * 9 / 1000
    print(f"\nEstimated Apify cost: ~${est_cost:.2f} ({len(niches)} x {args.limit} leads @ $9/1K)")
    print()

    # ─── PRE-TEST: VALIDATE SEARCH TERMS ─────────────────────────────
    if not args.skip_scrape and not args.no_pre_test and args.limit > PRE_TEST_LIMIT:
        print(f"\n{'─'*50}")
        print(f"PRE-TEST: Validating {len(niches)} search terms ({PRE_TEST_LIMIT} leads each)")
        print(f"{'─'*50}")

        failed_terms = []
        for label, term in niches.items():
            test_results = scrape_gmaps_with_contacts(
                search_query=term,
                limit=PRE_TEST_LIMIT,
                language=args.language,
                country=args.country,
            )
            if len(test_results) == 0:
                failed_terms.append((label, term))
                print(f"  [FAIL] '{term}' ({label}) → 0 results")
            else:
                # Show categories for verification
                cats = {}
                for r in test_results:
                    c = r.get("category", "")
                    cats[c] = cats.get(c, 0) + 1
                top_cats = ", ".join(f"{k} ({v})" for k, v in sorted(cats.items(), key=lambda x: -x[1])[:3])
                print(f"  [OK]   '{term}' ({label}) → {len(test_results)} results — {top_cats}")

        if failed_terms:
            print(f"\n[ABORT] {len(failed_terms)} search term(s) returned 0 results:")
            for label, term in failed_terms:
                print(f"  - '{term}' ({label})")
            print(f"\nFix the search terms and retry. Use --no-pre-test to skip this check.")
            print(f"Tip: Test new terms with --limit 10 before production runs.")
            return 1

        print(f"\n[OK] All {len(niches)} terms validated. Proceeding with production scrape.\n")

    # ─── STEP 1: SCRAPE ─────────────────────────────────────────────
    if args.skip_scrape:
        print(f"[SKIP] Loading leads from {args.skip_scrape}")
        all_leads = load_json(args.skip_scrape)
    else:
        all_leads = []
        for label, term in niches.items():
            print(f"\n{'─'*50}")
            print(f"SCRAPING: {label} → '{term}'")
            print(f"{'─'*50}")

            leads = scrape_gmaps_with_contacts(
                search_query=term,
                limit=args.limit,
                language=args.language,
                country=args.country,
                dump_raw=args.dump_raw,
            )

            # Tag each lead with its niche
            for lead in leads:
                lead["niche"] = label

            if len(leads) == 0:
                print(f"[WARN] {label}: 0 leads — term '{term}' may not match Google Maps categories for {args.country}")

            all_leads.extend(leads)
            print(f"[OK] {label}: {len(leads)} leads")

        # Check for empty results
        if len(all_leads) == 0:
            print(f"\n[ABORT] All niches returned 0 results. Check search terms.")
            return 1

        # Save raw scraped data
        os.makedirs(".tmp/gmaps_pipeline", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_path = f".tmp/gmaps_pipeline/scraped_{ts}.json"
        save_json(all_leads, raw_path)
        print(f"\n[OK] Saved raw scraped data to {raw_path}")

    # ─── STEP 2: DEDUP ──────────────────────────────────────────────
    before_dedup = len(all_leads)
    all_leads = dedup_leads(all_leads)
    print(f"\n[DEDUP] {before_dedup} → {len(all_leads)} unique leads")

    # ─── STEP 3: SPLIT ──────────────────────────────────────────────
    output_dir = ".tmp/gmaps_pipeline"
    split_result = split_leads(all_leads, output_dir)

    # Load split files
    cold_calling = load_json(split_result["cold_calling"]["file"])
    cold_email = load_json(split_result["cold_email"]["file"])

    # ─── STEP 4: EVALUATE WEBSITES ──────────────────────────────────
    if args.evaluate_websites and cold_email:
        psi_key = os.getenv("GOOGLE_PAGESPEED_API_KEY")

        # Get OAuth access token for PSI (reuse Sheets auth)
        access_token = None
        if not psi_key:
            try:
                creds = None
                if os.path.exists('token.json'):
                    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                if creds and creds.valid:
                    access_token = creds.token
                    print("\n[INFO] Using OAuth token for PageSpeed API")
                elif creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    access_token = creds.token
                    print("\n[INFO] Using refreshed OAuth token for PageSpeed API")
                else:
                    print("\n[INFO] No API key or valid OAuth — PSI may have limited quota")
            except Exception:
                print("\n[INFO] Could not load OAuth token — PSI may have limited quota")

        print(f"\n{'─'*50}")
        print(f"EVALUATING WEBSITES ({len(cold_email)} leads)")
        print(f"{'─'*50}")

        cold_email = evaluate_websites_batch(
            cold_email,
            api_key=psi_key,
            access_token=access_token,
            max_workers=args.workers,
        )

        # Save evaluated data
        eval_path = os.path.join(output_dir, "cold_email_evaluated.json")
        save_json(cold_email, eval_path)
        print(f"[OK] Saved evaluated leads to {eval_path}")

    # ─── STEP 5: EXPORT TO SHEETS ───────────────────────────────────
    if args.sheet_url:
        print(f"\n{'─'*50}")
        print("EXPORTING TO GOOGLE SHEETS")
        print(f"{'─'*50}")

        gc = authenticate_sheets()
        sheet_url = export_to_sheets(
            gc, args.sheet_url,
            cold_calling, cold_email, all_leads,
            list(niches.keys())
        )
        print(f"\nSheet URL: {sheet_url}")
    else:
        print("\n[SKIP] No --sheet-url provided, skipping Sheets export")

    # ─── SUMMARY ─────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("PIPELINE COMPLETE")
    print(f"{'='*70}")
    print(f"Total scraped:     {len(all_leads)}")
    print(f"Cold calling:      {len(cold_calling)}")
    print(f"Cold email:        {len(cold_email)}")
    print(f"No contact:        {split_result['no_contact']['count']}")

    if args.evaluate_websites and cold_email:
        scores = [l["overall_score"] for l in cold_email if l.get("overall_score") is not None]
        if scores:
            print(f"Avg website score: {sum(scores)/len(scores):.0f}/100")

    return 0


if __name__ == "__main__":
    sys.exit(main())

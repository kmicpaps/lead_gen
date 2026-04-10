# [CLI] -- run via: py execution/gmaps_sheets_exporter.py --help
#!/usr/bin/env python3
"""
GMaps Sheets Exporter -- Export GMaps leads to a 3-tab Google Sheet.

Creates or opens a Google Sheet and populates:
  - cold_calling: phone-only leads (9 columns)
  - cold_email_scored: email leads with optional PageSpeed scores (24 columns)
  - summary: totals, avg scores, CMS breakdown, per-niche counts

Auto-creates a new sheet if no --sheet-url is provided.

Usage:
    py execution/gmaps_sheets_exporter.py \\
        --cold-calling .tmp/gmaps/cold_calling.json \\
        --cold-email .tmp/gmaps/cold_email.json \\
        --all-leads .tmp/gmaps/deduped.json \\
        --niches juristi frizieris \\
        --total-scraped 500
"""

import os
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Optional

import gspread

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_json, get_google_credentials

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

COLD_CALLING_HEADERS = [
    "niche", "business_name", "category", "address", "city",
    "phone", "google_maps_url", "rating", "review_count",
]

COLD_EMAIL_HEADERS = [
    "niche", "business_name", "category", "address", "city",
    "phone", "website",
    "email_1", "email_2",
    "facebook", "instagram", "linkedin",
    "google_maps_url", "rating", "review_count",
    "overall_score", "performance_score", "seo_score",
    "lcp_seconds", "is_mobile_friendly", "has_ssl", "cms",
    "insight_1", "insight_2", "insight_3",
]

# Latvian character transliteration for tab names
_LV_MAP = {
    "a\u0304": "a", "c\u030c": "c", "e\u0304": "e", "g\u0327": "g", "i\u0304": "i",
    "k\u0327": "k", "l\u0327": "l", "n\u0327": "n", "s\u030c": "s", "u\u0304": "u", "z\u030c": "z",
    "\u0101": "a", "\u010d": "c", "\u0113": "e", "\u0123": "g", "\u012b": "i",
    "\u0137": "k", "\u013c": "l", "\u0146": "n", "\u0161": "s", "\u016b": "u", "\u017e": "z",
    "\u0100": "A", "\u010c": "C", "\u0112": "E", "\u0122": "G", "\u012a": "I",
    "\u0136": "K", "\u013b": "L", "\u0145": "N", "\u0160": "S", "\u016a": "U", "\u017d": "Z",
}


def _safe_tab_name(name: str) -> str:
    """Convert niche name to ASCII-safe tab name for Google Sheets."""
    safe = "".join(_LV_MAP.get(c, c) for c in name)
    return "".join(c for c in safe if c.isalnum() or c in " _-")


def _col_letter(n: int) -> str:
    """Convert column count to letter (1=A, 26=Z, 27=AA)."""
    if n <= 26:
        return chr(64 + n)
    return chr(64 + (n - 1) // 26) + chr(65 + (n - 1) % 26)


def _lead_to_calling_row(lead: Dict) -> List[str]:
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


def _lead_to_email_row(lead: Dict) -> List[str]:
    emails = lead.get("emails", [])
    if isinstance(emails, str):
        emails = [emails] if emails else []
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
        str(lead.get("lcp_seconds") or ""),
        str(lead.get("is_mobile_friendly") or ""),
        str(lead.get("has_ssl") or ""),
        str(lead.get("cms") or ""),
        str(insights[0]) if len(insights) > 0 else "",
        str(insights[1]) if len(insights) > 1 else "",
        str(insights[2]) if len(insights) > 2 else "",
    ]


def authenticate_sheets():
    """Authenticate with Google Sheets API using the shared workspace token."""
    return gspread.authorize(get_google_credentials())


def export_gmaps_to_sheets(
    cold_calling: List[Dict],
    cold_email: List[Dict],
    all_leads: List[Dict],
    niches: List[str],
    sheet_url: Optional[str] = None,
    title: Optional[str] = None,
    total_scraped: Optional[int] = None,
) -> str:
    """Export GMaps leads to a 3-tab Google Sheet.

    Args:
        cold_calling: leads with phone only
        cold_email: leads with email (optionally scored)
        all_leads: all deduped leads (for summary stats)
        niches: list of niche labels used
        sheet_url: existing sheet URL (creates new if None)
        title: sheet title (only used when creating new)
        total_scraped: pre-dedup count for summary

    Returns:
        Google Sheet URL
    """
    gc = authenticate_sheets()

    if sheet_url:
        spreadsheet = gc.open_by_url(sheet_url)
        print(f"[SHEETS] Opened: {spreadsheet.title}")
    else:
        sheet_title = title or f"GMaps Leads - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        spreadsheet = gc.create(sheet_title)
        print(f"[SHEETS] Created: {sheet_title}")
        print(f"[SHEETS] URL: {spreadsheet.url}")

    existing_tabs = {ws.title: ws for ws in spreadsheet.worksheets()}

    # Known pipeline tabs
    PIPELINE_TABS = {"cold_calling", "cold_email_scored", "summary"}
    niche_tab_names = {f"email_{_safe_tab_name(n)}" for n in niches}
    keep_tabs = PIPELINE_TABS | niche_tab_names

    # Clean up old email_ tabs only
    for tab_name, ws in existing_tabs.items():
        if tab_name not in keep_tabs and tab_name != "Sheet1" and tab_name.startswith("email_"):
            try:
                spreadsheet.del_worksheet(ws)
                print(f"[CLEANUP] Deleted stale tab: '{tab_name}'")
            except Exception as e:
                print(f"[WARN] Could not delete tab '{tab_name}': {e}")

    existing_tabs = {ws.title: ws for ws in spreadsheet.worksheets()}

    def get_or_create_tab(name, headers):
        if name in existing_tabs:
            ws = existing_tabs[name]
            ws.clear()
        else:
            ws = spreadsheet.add_worksheet(title=name, rows=2000, cols=len(headers))
        ws.append_row(headers)
        col = _col_letter(len(headers))
        ws.format(f'A1:{col}1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })
        return ws

    # Cold calling tab
    ws_calling = get_or_create_tab("cold_calling", COLD_CALLING_HEADERS)
    if cold_calling:
        rows = [_lead_to_calling_row(l) for l in cold_calling]
        ws_calling.append_rows(rows)
        print(f"[OK] {len(rows)} leads -> 'cold_calling'")

    # Cold email scored tab
    ws_email = get_or_create_tab("cold_email_scored", COLD_EMAIL_HEADERS)
    if cold_email:
        rows = [_lead_to_email_row(l) for l in cold_email]
        ws_email.append_rows(rows)
        print(f"[OK] {len(rows)} leads -> 'cold_email_scored'")

    # Per-niche email tabs
    for niche in niches:
        tab_name = f"email_{_safe_tab_name(niche)}"
        niche_leads = [l for l in cold_email if l.get("niche") == niche]
        if niche_leads:
            ws_niche = get_or_create_tab(tab_name, COLD_EMAIL_HEADERS)
            rows = [_lead_to_email_row(l) for l in niche_leads]
            ws_niche.append_rows(rows)
            print(f"[OK] {len(rows)} leads -> '{tab_name}'")

    # Summary tab
    ws_summary = get_or_create_tab("summary", ["Metric", "Value"])
    evaluated = [l for l in cold_email if l.get("overall_score") is not None]
    scores = [l["overall_score"] for l in evaluated]
    avg_score = sum(scores) / len(scores) if scores else 0

    cms_counts = {}
    for l in evaluated:
        cms = l.get("cms") or "Unknown"
        cms_counts[cms] = cms_counts.get(cms, 0) + 1
    cms_str = ", ".join(f"{k}: {v}" for k, v in sorted(cms_counts.items(), key=lambda x: -x[1]))

    niche_counts = {}
    for l in all_leads:
        n = l.get("niche", "unknown")
        niche_counts[n] = niche_counts.get(n, 0) + 1

    summary_rows = [
        ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")],
        ["Niches", ", ".join(niches)],
        ["Total scraped", str(total_scraped if total_scraped is not None else len(all_leads))],
        ["After dedup", str(len(all_leads))],
        ["Cold calling (phone only)", str(len(cold_calling))],
        ["Cold email (has email)", str(len(cold_email))],
        ["Avg website score", f"{avg_score:.0f}/100" if scores else "N/A (not scored)"],
        ["CMS breakdown", cms_str or "N/A (not scored)"],
    ]
    for niche, count in niche_counts.items():
        summary_rows.append([f"Niche: {niche}", str(count)])
    ws_summary.append_rows(summary_rows)
    print(f"[OK] Summary tab written")

    # Delete default Sheet1 if we created tabs
    if "Sheet1" in {ws.title for ws in spreadsheet.worksheets()} and len(spreadsheet.worksheets()) > 1:
        try:
            sheet1 = spreadsheet.worksheet("Sheet1")
            spreadsheet.del_worksheet(sheet1)
        except Exception:
            pass

    return spreadsheet.url


def main():
    parser = argparse.ArgumentParser(description="Export GMaps leads to 3-tab Google Sheet")
    parser.add_argument("--cold-calling", required=True, help="JSON file with cold calling leads")
    parser.add_argument("--cold-email", required=True, help="JSON file with cold email leads")
    parser.add_argument("--all-leads", required=True, help="JSON file with all deduped leads (for summary)")
    parser.add_argument("--niches", nargs="+", required=True, help="Niche labels used")
    parser.add_argument("--sheet-url", help="Existing Google Sheet URL (creates new if omitted)")
    parser.add_argument("--title", help="Sheet title (only when creating new)")
    parser.add_argument("--total-scraped", type=int, help="Pre-dedup lead count for summary")

    args = parser.parse_args()

    cold_calling = load_json(args.cold_calling)
    cold_email = load_json(args.cold_email)
    all_leads = load_json(args.all_leads)

    url = export_gmaps_to_sheets(
        cold_calling=cold_calling,
        cold_email=cold_email,
        all_leads=all_leads,
        niches=args.niches,
        sheet_url=args.sheet_url,
        title=args.title,
        total_scraped=args.total_scraped,
    )

    print(f"\nSheet URL: {url}")


if __name__ == "__main__":
    main()

# [CLI] — run via: py execution/website_evaluator.py --help
#!/usr/bin/env python3
"""
Website Evaluator — Scores websites using Google PageSpeed Insights API
and local tech stack detection. Generates cold email insight bullets.

Designed for batch evaluation of lead lists with parallel processing.
"""

import os
import sys
import json
import re
import time
import argparse
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_json, save_json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Score weights for overall composite
WEIGHTS = {
    "performance": 0.35,
    "mobile": 0.20,
    "ssl": 0.15,
    "seo": 0.15,
    "best_practices": 0.15,
}

# CMS detection patterns: (regex_pattern, cms_name)
CMS_PATTERNS = [
    (r'/wp-content/|/wp-includes/|wp-json', "WordPress"),
    (r'<meta\s+name=["\']generator["\']\s+content=["\']WordPress', "WordPress"),
    (r'cdn\.shopify\.com|Shopify\.theme', "Shopify"),
    (r'squarespace\.com|data-squarespace', "Squarespace"),
    (r'static\.wixstatic\.com|X-Wix-', "Wix"),
    (r'weebly\.com|weebly-footer', "Weebly"),
    (r'sites\.google\.com|googleusercontent\.com/site', "Google Sites"),
    (r'webflow\.com|data-wf-', "Webflow"),
    (r'ghost\.org|ghost-api', "Ghost"),
    (r'joomla|\/administrator\/', "Joomla"),
    (r'drupal\.org|Drupal\.settings', "Drupal"),
]

# Framework detection patterns
FRAMEWORK_PATTERNS = [
    (r'__NEXT_DATA__|_next/static', "Next.js"),
    (r'__NUXT__|_nuxt/', "Nuxt.js"),
    (r'data-reactroot|react-dom', "React"),
    (r'ng-version|angular\.js', "Angular"),
    (r'data-v-[a-f0-9]|Vue\.config', "Vue.js"),
    (r'svelte-|__svelte', "Svelte"),
]


def evaluate_website(url: str, api_key: Optional[str] = None, access_token: Optional[str] = None) -> Dict:
    """
    Evaluate a single website's quality.

    Args:
        url: Website URL to evaluate
        api_key: Google PageSpeed Insights API key (optional)
        access_token: OAuth2 access token (optional, used if no api_key)

    Returns:
        Dict with scores, tech stack, and insight bullets
    """
    result = {
        "url": url,
        "status": "error",
        "error_detail": None,
        # PSI scores
        "performance_score": None,
        "accessibility_score": None,
        "seo_score": None,
        "best_practices_score": None,
        # Metrics
        "fcp_seconds": None,
        "lcp_seconds": None,
        "cls": None,
        "tbt_ms": None,
        "speed_index_seconds": None,
        # Tech stack
        "has_ssl": False,
        "cms": None,
        "framework": None,
        "server": None,
        "is_mobile_friendly": None,
        # Computed
        "overall_score": 0,
        "insights": [],
    }

    # Ensure URL has scheme
    if not url.startswith("http"):
        url = "https://" + url
    result["url"] = url

    # Check SSL
    result["has_ssl"] = url.startswith("https://")

    # Step 1: Fetch page HTML + headers for tech stack detection
    html = ""
    headers = {}
    try:
        with httpx.Client(timeout=15, follow_redirects=True, verify=False) as client:
            resp = client.get(url)
            html = resp.text
            headers = dict(resp.headers)
            # Update SSL check based on final URL after redirects
            result["has_ssl"] = str(resp.url).startswith("https://")
    except Exception as e:
        result["error_detail"] = f"fetch_failed: {str(e)[:100]}"
        # Continue — PSI might still work even if direct fetch fails

    # Step 2: Detect tech stack from HTML + headers
    tech = detect_tech_stack(html, headers)
    result["cms"] = tech["cms"]
    result["framework"] = tech["framework"]
    result["server"] = tech["server"]

    # Step 3: Call PageSpeed Insights API
    psi = call_pagespeed_api(url, api_key, access_token)
    if psi:
        result["status"] = "success"
        result["performance_score"] = psi.get("performance_score")
        result["accessibility_score"] = psi.get("accessibility_score")
        result["seo_score"] = psi.get("seo_score")
        result["best_practices_score"] = psi.get("best_practices_score")
        result["fcp_seconds"] = psi.get("fcp_seconds")
        result["lcp_seconds"] = psi.get("lcp_seconds")
        result["cls"] = psi.get("cls")
        result["tbt_ms"] = psi.get("tbt_ms")
        result["speed_index_seconds"] = psi.get("speed_index_seconds")
        result["is_mobile_friendly"] = psi.get("is_mobile_friendly")
    elif html:
        result["status"] = "partial"
        if not result["error_detail"]:
            result["error_detail"] = "PageSpeed API failed but page was reachable"
    else:
        result["status"] = "unreachable"

    # Step 4: Compute overall score
    result["overall_score"] = compute_overall_score(result)

    # Step 5: Generate insight bullets
    result["insights"] = generate_insights(result)

    return result


def call_pagespeed_api(url: str, api_key: Optional[str] = None, access_token: Optional[str] = None) -> Optional[Dict]:
    """Call Google PageSpeed Insights API and extract key metrics.
    Auth priority: API key > OAuth access token > no auth (public, strict rate limit)."""
    try:
        params = {
            "url": url,
            "category": ["PERFORMANCE", "ACCESSIBILITY", "SEO", "BEST_PRACTICES"],
            "strategy": "MOBILE",
        }
        req_headers = {}
        if api_key:
            params["key"] = api_key
        elif access_token:
            req_headers["Authorization"] = f"Bearer {access_token}"
        with httpx.Client(timeout=60) as client:
            resp = client.get(PSI_ENDPOINT, params=params, headers=req_headers)
            if resp.status_code != 200:
                return None
            data = resp.json()

        lr = data.get("lighthouseResult", {})
        cats = lr.get("categories", {})
        audits = lr.get("audits", {})

        def score(cat_key):
            cat = cats.get(cat_key, {})
            s = cat.get("score")
            return int(s * 100) if s is not None else None

        def audit_ms(key):
            val = audits.get(key, {}).get("numericValue")
            return val if val is not None else None

        return {
            "performance_score": score("performance"),
            "accessibility_score": score("accessibility"),
            "seo_score": score("seo"),
            "best_practices_score": score("best-practices"),
            "fcp_seconds": round(audit_ms("first-contentful-paint") / 1000, 2) if audit_ms("first-contentful-paint") else None,
            "lcp_seconds": round(audit_ms("largest-contentful-paint") / 1000, 2) if audit_ms("largest-contentful-paint") else None,
            "cls": round(audit_ms("cumulative-layout-shift"), 3) if audit_ms("cumulative-layout-shift") is not None else None,
            "tbt_ms": int(audit_ms("total-blocking-time")) if audit_ms("total-blocking-time") is not None else None,
            "speed_index_seconds": round(audit_ms("speed-index") / 1000, 2) if audit_ms("speed-index") else None,
            "is_mobile_friendly": audits.get("viewport", {}).get("score") == 1,
        }

    except Exception:
        return None


def detect_tech_stack(html: str, headers: dict) -> Dict:
    """Detect CMS, framework, and server from HTML content and HTTP headers."""
    result = {"cms": None, "framework": None, "server": None}

    # Server from headers
    result["server"] = headers.get("server") or headers.get("Server") or None

    # Check X-Powered-By
    powered = headers.get("x-powered-by") or headers.get("X-Powered-By") or ""

    # CMS detection
    combined = html + " " + powered + " " + " ".join(f"{k}: {v}" for k, v in headers.items())
    for pattern, cms_name in CMS_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            result["cms"] = cms_name
            break

    # Framework detection
    for pattern, fw_name in FRAMEWORK_PATTERNS:
        if re.search(pattern, html, re.IGNORECASE):
            result["framework"] = fw_name
            break

    return result


def compute_overall_score(evaluation: Dict) -> int:
    """Compute weighted overall website quality score (0-100)."""
    components = []
    total_weight = 0

    # Performance
    if evaluation["performance_score"] is not None:
        components.append(evaluation["performance_score"] * WEIGHTS["performance"])
        total_weight += WEIGHTS["performance"]

    # Mobile friendliness
    if evaluation["is_mobile_friendly"] is not None:
        mobile_score = 100 if evaluation["is_mobile_friendly"] else 20
        components.append(mobile_score * WEIGHTS["mobile"])
        total_weight += WEIGHTS["mobile"]

    # SSL
    ssl_score = 100 if evaluation["has_ssl"] else 0
    components.append(ssl_score * WEIGHTS["ssl"])
    total_weight += WEIGHTS["ssl"]

    # SEO
    if evaluation["seo_score"] is not None:
        components.append(evaluation["seo_score"] * WEIGHTS["seo"])
        total_weight += WEIGHTS["seo"]

    # Best practices
    if evaluation["best_practices_score"] is not None:
        components.append(evaluation["best_practices_score"] * WEIGHTS["best_practices"])
        total_weight += WEIGHTS["best_practices"]

    if total_weight == 0:
        return 0

    return int(sum(components) / total_weight)


def generate_insights(evaluation: Dict) -> List[str]:
    """Generate 2-3 actionable insight bullets for cold email personalization."""
    insights = []

    # Slow loading
    lcp = evaluation.get("lcp_seconds")
    if lcp and lcp > 4.0:
        multiplier = round(lcp / 2.5, 1)
        insights.append(f"Your site loads in {lcp}s on mobile — {multiplier}x slower than the 2.5s industry average")
    elif lcp and lcp > 2.5:
        insights.append(f"Your mobile load time ({lcp}s) is above the recommended 2.5s — costing you visitors")

    # No SSL
    if not evaluation.get("has_ssl"):
        insights.append("Your site doesn't use HTTPS — Google penalizes this in search rankings and browsers show warnings")

    # Not mobile friendly
    if evaluation.get("is_mobile_friendly") is False:
        insights.append("Your site isn't optimized for mobile — over 70% of local searches happen on phones")

    # Poor performance
    perf = evaluation.get("performance_score")
    if perf is not None and perf < 40 and not any("loads in" in i for i in insights):
        insights.append(f"Your site scores {perf}/100 on Google's speed test — this directly affects your Google ranking")

    # Poor SEO
    seo = evaluation.get("seo_score")
    if seo is not None and seo < 60:
        insights.append(f"Your SEO score is {seo}/100 — basic fixes could help more customers find you on Google")

    # Outdated CMS
    cms = evaluation.get("cms")
    overall = evaluation.get("overall_score", 0)
    if cms and overall < 50:
        insights.append(f"Your {cms} site scores {overall}/100 — a few optimizations could boost this significantly")

    # Cap at 3 insights, prioritize the first ones
    return insights[:3]


def evaluate_websites_batch(
    leads: List[Dict],
    api_key: Optional[str] = None,
    access_token: Optional[str] = None,
    max_workers: int = 5,
    delay_between: float = 0.2
) -> List[Dict]:
    """
    Evaluate multiple websites in parallel with rate limiting.

    Args:
        leads: list of lead dicts (must have 'website' field)
        api_key: Google PageSpeed API key (optional)
        access_token: OAuth2 access token (optional)
        max_workers: parallel threads
        delay_between: seconds between request dispatches

    Returns:
        List of leads with evaluation fields attached
    """
    # Filter leads that have websites to evaluate
    to_evaluate = [(i, lead) for i, lead in enumerate(leads) if lead.get("website")]
    print(f"\nEvaluating {len(to_evaluate)} websites ({len(leads) - len(to_evaluate)} skipped — no website)")

    results = {}

    def evaluate_one(index, lead):
        time.sleep(delay_between * index)  # Stagger requests
        url = lead["website"]
        evaluation = evaluate_website(url, api_key, access_token)
        return index, evaluation

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(evaluate_one, seq, lead): (idx, lead)
            for seq, (idx, lead) in enumerate(to_evaluate)
        }

        done_count = 0
        for future in as_completed(futures):
            idx, lead = futures[future]
            try:
                _, evaluation = future.result()
                results[idx] = evaluation
                done_count += 1
                if done_count % 10 == 0 or done_count == len(to_evaluate):
                    print(f"  Evaluated {done_count}/{len(to_evaluate)} websites...")
            except Exception as e:
                results[idx] = {
                    "status": "error",
                    "error_detail": str(e)[:200],
                    "overall_score": 0,
                    "insights": [],
                }
                done_count += 1

    # Attach evaluation results to leads
    enriched = []
    for i, lead in enumerate(leads):
        lead_copy = dict(lead)
        if i in results:
            eval_data = results[i]
            lead_copy["eval_status"] = eval_data.get("status", "error")
            lead_copy["overall_score"] = eval_data.get("overall_score", 0)
            lead_copy["performance_score"] = eval_data.get("performance_score")
            lead_copy["seo_score"] = eval_data.get("seo_score")
            lead_copy["best_practices_score"] = eval_data.get("best_practices_score")
            lead_copy["is_mobile_friendly"] = eval_data.get("is_mobile_friendly")
            lead_copy["has_ssl"] = eval_data.get("has_ssl", False)
            lead_copy["cms"] = eval_data.get("cms")
            lead_copy["framework"] = eval_data.get("framework")
            lead_copy["lcp_seconds"] = eval_data.get("lcp_seconds")
            lead_copy["insights"] = eval_data.get("insights", [])
        else:
            # No website — skip evaluation
            lead_copy["eval_status"] = "no_website"
            lead_copy["overall_score"] = None
            lead_copy["insights"] = []
        enriched.append(lead_copy)

    # Print summary
    evaluated = [e for e in enriched if e.get("eval_status") == "success"]
    if evaluated:
        scores = [e["overall_score"] for e in evaluated if e["overall_score"] is not None]
        avg = sum(scores) / len(scores) if scores else 0
        below_50 = sum(1 for s in scores if s < 50)
        print(f"\nEvaluation summary:")
        print(f"  Successful: {len(evaluated)}/{len(to_evaluate)}")
        print(f"  Avg score: {avg:.0f}/100")
        print(f"  Below 50: {below_50} ({100*below_50//max(len(scores),1)}%)")

    return enriched


def main():
    parser = argparse.ArgumentParser(description="Evaluate website quality using PageSpeed Insights")
    parser.add_argument("--url", help="Single URL to evaluate")
    parser.add_argument("--input", help="Input JSON file with leads (batch mode)")
    parser.add_argument("--output", help="Output JSON file")
    parser.add_argument("--workers", type=int, default=5, help="Parallel workers (default: 5)")

    args = parser.parse_args()

    api_key = os.getenv("GOOGLE_PAGESPEED_API_KEY")
    if not api_key:
        print("[INFO] No API key — using public PageSpeed API (rate limit ~60 req/100s)")

    if args.url:
        # Single URL mode
        result = evaluate_website(args.url, api_key)
        print(json.dumps(result, indent=2))
        if args.output:
            save_json(result, args.output)

    elif args.input:
        # Batch mode
        leads = load_json(args.input)

        enriched = evaluate_websites_batch(leads, api_key, max_workers=args.workers)

        output_path = args.output or args.input.replace(".json", "_evaluated.json")
        save_json(enriched, output_path)
        print(f"\n[OK] Saved evaluated leads to {output_path}")

    else:
        parser.error("Provide either --url or --input")


if __name__ == "__main__":
    main()

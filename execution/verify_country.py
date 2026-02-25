# [CLI] — run via: py execution/verify_country.py --help
"""
Country Verification for Lead Lists

Classifies leads as domestic/foreign/uncertain based on company signals
(domain TLD, email TLD, phone prefix, company_country field), removes
foreign leads, and optionally enriches uncertain leads via Lead Magic API.

Usage:
    # Full verification with Lead Magic enrichment
    py execution/verify_country.py \
        --input leads.json \
        --country LV \
        --output-dir .tmp/verified

    # Dry run — show classification stats without writing files
    py execution/verify_country.py \
        --input leads.json \
        --country LV \
        --dry-run

    # Skip API enrichment — classify only by signals
    py execution/verify_country.py \
        --input leads.json \
        --country LV \
        --skip-enrichment \
        --output-dir .tmp/verified
"""

import os
import sys
import json
import argparse
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

# Extensible country configuration
# tld: home country TLD
# phone: home phone prefix
# foreign_tlds: TLDs that definitively indicate a foreign company
# neutral_tlds: TLDs that could be any country (.com, .eu, etc.)
COUNTRY_CONFIG = {
    "LV": {
        "name": "Latvia",
        "tld": ".lv",
        "phone": "+371",
        "foreign_tlds": [
            ".fi", ".ee", ".lt", ".de", ".uk", ".co.uk", ".se", ".no", ".dk",
            ".pl", ".ru", ".by", ".ua", ".cz", ".sk", ".hu", ".ro", ".bg",
            ".hr", ".rs", ".fr", ".es", ".it", ".nl", ".at", ".ch", ".be",
            ".pt", ".ie", ".gr", ".tr", ".us", ".ca", ".au", ".nz", ".jp",
            ".cn", ".in", ".br", ".mx", ".za", ".il", ".ae", ".sg", ".hk",
            ".kr", ".tw", ".mt",
        ],
        "neutral_tlds": [".com", ".eu", ".net", ".org", ".io", ".co", ".group", ".info", ".ai", ".app", ".dev", ".pro", ".space", ".house", ".fish", ".delivery", ".pet"],
    },
    "NZ": {
        "name": "New Zealand",
        "tld": ".nz",
        "phone": "+64",
        "foreign_tlds": [
            ".au", ".uk", ".co.uk", ".us", ".in", ".sg", ".cn", ".jp",
            ".de", ".fr", ".ca", ".za", ".hk",
        ],
        "neutral_tlds": [".com", ".net", ".org", ".io", ".co", ".ai", ".app", ".dev"],
    },
    "IT": {
        "name": "Italy",
        "tld": ".it",
        "phone": "+39",
        "foreign_tlds": [
            ".de", ".fr", ".es", ".uk", ".co.uk", ".at", ".ch", ".nl",
            ".be", ".pl", ".cz", ".ro", ".bg", ".hr", ".se", ".no", ".dk",
            ".fi", ".us", ".ca",
        ],
        "neutral_tlds": [".com", ".eu", ".net", ".org", ".io", ".co"],
    },
    "SE": {
        "name": "Sweden",
        "tld": ".se",
        "phone": "+46",
        "foreign_tlds": [
            ".fi", ".dk", ".no", ".de", ".uk", ".co.uk", ".pl", ".ee",
            ".lv", ".lt", ".nl", ".fr", ".es", ".it", ".us", ".ca",
        ],
        "neutral_tlds": [".com", ".eu", ".net", ".org", ".io", ".co", ".nu"],
    },
    "NO": {
        "name": "Norway",
        "tld": ".no",
        "phone": "+47",
        "foreign_tlds": [
            ".se", ".dk", ".fi", ".de", ".uk", ".co.uk", ".pl", ".nl",
            ".fr", ".es", ".it", ".us", ".ca", ".ee", ".lv", ".lt",
        ],
        "neutral_tlds": [".com", ".eu", ".net", ".org", ".io", ".co"],
    },
    "PL": {
        "name": "Poland",
        "tld": ".pl",
        "phone": "+48",
        "foreign_tlds": [
            ".de", ".cz", ".sk", ".lt", ".ua", ".uk", ".co.uk", ".fr",
            ".nl", ".se", ".no", ".dk", ".fi", ".ee", ".lv", ".us", ".ca",
        ],
        "neutral_tlds": [".com", ".eu", ".net", ".org", ".io", ".co"],
    },
    "DE": {
        "name": "Germany",
        "tld": ".de",
        "phone": "+49",
        "foreign_tlds": [
            ".at", ".ch", ".fr", ".nl", ".be", ".pl", ".cz", ".dk",
            ".se", ".uk", ".co.uk", ".it", ".es", ".us", ".ca",
        ],
        "neutral_tlds": [".com", ".eu", ".net", ".org", ".io", ".co"],
    },
    "AT": {
        "name": "Austria",
        "tld": ".at",
        "phone": "+43",
        "foreign_tlds": [
            ".de", ".ch", ".it", ".hu", ".cz", ".sk", ".si", ".hr",
            ".fr", ".nl", ".uk", ".co.uk", ".pl", ".us",
        ],
        "neutral_tlds": [".com", ".eu", ".net", ".org", ".io", ".co"],
    },
}


# Compound TLDs that need special extraction
COMPOUND_TLDS = {".co.uk", ".co.nz", ".com.au", ".co.za", ".co.jp", ".co.kr", ".com.br", ".co.in"}


def get_domain_tld(domain):
    """
    Extract effective TLD from a domain.
    Handles compound TLDs: 'company.co.uk' -> '.co.uk'
    """
    if not domain:
        return ""
    domain = domain.lower().strip()
    # Check compound TLDs first
    for ctld in COMPOUND_TLDS:
        if domain.endswith(ctld):
            return ctld
    # Simple TLD
    parts = domain.rsplit(".", 1)
    if len(parts) == 2:
        return "." + parts[1]
    return ""


def get_phone_prefix(lead):
    """
    Extract phone country prefix from any phone field.
    Returns the prefix like '+371' or '' if no phone.
    """
    phone = (
        lead.get("organization_phone", "")
        or lead.get("company_phone", "")
        or lead.get("phone", "")
        or ""
    ).strip()
    if not phone:
        return ""
    # Normalize: some phones start with country code without +
    if phone.startswith("+"):
        # Extract prefix: +371, +64, +49, etc. (1-3 digits after +)
        # Try longest match first for ambiguous cases
        return phone[:4] if len(phone) >= 4 else phone
    return ""


def classify_lead(lead, country_code):
    """
    Classify a single lead as 'domestic', 'foreign', or 'uncertain'.

    Priority:
    1. company_country field (strongest signal if present)
    2. Domain TLD
    3. Email TLD
    4. Phone prefix
    5. If no signals -> uncertain
    """
    config = COUNTRY_CONFIG.get(country_code.upper())
    if not config:
        return "uncertain", "unknown_country_code"

    home_tld = config["tld"]
    home_phone = config["phone"]
    foreign_tlds = set(config["foreign_tlds"])
    neutral_tlds = set(config["neutral_tlds"])

    # 1. Check company_country field (strongest signal)
    cc = (lead.get("company_country") or "").strip().upper()
    if cc:
        if cc == country_code.upper() or cc == config["name"].upper():
            return "domestic", "company_country"
        else:
            return "foreign", f"company_country={cc}"

    # Gather signals
    domain = (lead.get("company_domain") or "").lower().strip()
    email = (lead.get("email") or "").lower().strip()
    domain_tld = get_domain_tld(domain)
    email_tld = get_domain_tld(email.split("@")[-1]) if "@" in email else ""
    phone_prefix = get_phone_prefix(lead)

    domestic_signals = []
    foreign_signals = []

    # 2. Domain TLD
    if domain_tld:
        if domain_tld == home_tld:
            domestic_signals.append(f"domain={domain_tld}")
        elif domain_tld in foreign_tlds:
            foreign_signals.append(f"domain={domain_tld}")

    # 3. Email TLD
    if email_tld and email_tld != domain_tld:  # Don't double-count same TLD
        if email_tld == home_tld:
            domestic_signals.append(f"email={email_tld}")
        elif email_tld in foreign_tlds:
            foreign_signals.append(f"email={email_tld}")

    # 4. Phone prefix
    if phone_prefix:
        if phone_prefix.startswith(home_phone):
            domestic_signals.append(f"phone={phone_prefix}")
        elif phone_prefix.startswith("+"):
            foreign_signals.append(f"phone={phone_prefix}")

    # Decision
    if domestic_signals and not foreign_signals:
        return "domestic", ",".join(domestic_signals)
    if foreign_signals and not domestic_signals:
        return "foreign", ",".join(foreign_signals)
    if domestic_signals and foreign_signals:
        # Conflicting signals — mark uncertain
        return "uncertain", f"conflict:domestic={','.join(domestic_signals)}|foreign={','.join(foreign_signals)}"
    # No signals at all
    return "uncertain", "no_signals"


def classify_all(leads, country_code):
    """
    Classify all leads. Returns dict with domestic/foreign/uncertain lists + stats.
    """
    domestic = []
    foreign = []
    uncertain = []
    reason_counts = Counter()

    for lead in leads:
        classification, reason = classify_lead(lead, country_code)
        lead["_country_classification"] = classification
        lead["_classification_reason"] = reason
        reason_counts[reason] += 1

        if classification == "domestic":
            domestic.append(lead)
        elif classification == "foreign":
            foreign.append(lead)
        else:
            uncertain.append(lead)

    return {
        "domestic": domestic,
        "foreign": foreign,
        "uncertain": uncertain,
        "reason_counts": reason_counts,
    }


def enrich_uncertain(uncertain_leads, country_code):
    """
    Enrich uncertain leads via Lead Magic Company Search API.
    Reuses functions from company_country_enricher.py.

    Returns: (now_domestic, now_foreign, still_uncertain, credits_used)
    """
    api_key = os.getenv("LeadMagic-X-API-Key") or os.getenv("LEADMAGIC_API_KEY")
    if not api_key:
        print("WARNING: No Lead Magic API key found. Skipping enrichment.", file=sys.stderr)
        return [], [], uncertain_leads, 0

    # Import enrichment functions
    sys.path.insert(0, os.path.dirname(__file__))
    from company_country_enricher import search_company, enrich_domains, progress, progress_lock

    # Reset progress counters
    with progress_lock:
        for key in progress:
            progress[key] = 0

    # Collect unique domains from uncertain leads
    domains_to_lookup = set()
    for lead in uncertain_leads:
        domain = (lead.get("company_domain") or "").strip().lower()
        if domain:
            domains_to_lookup.add(domain)

    if not domains_to_lookup:
        print(f"  No domains to enrich among {len(uncertain_leads)} uncertain leads")
        return [], [], uncertain_leads, 0

    print(f"\nEnriching {len(domains_to_lookup)} unique domains from {len(uncertain_leads)} uncertain leads...")

    # Call Lead Magic API
    domain_results = enrich_domains(list(domains_to_lookup), api_key)
    credits_used = sum(r.get("credits", 0) for r in domain_results.values())

    # Apply results and re-classify
    now_domestic = []
    now_foreign = []
    still_uncertain = []

    config = COUNTRY_CONFIG.get(country_code.upper(), {})

    for lead in uncertain_leads:
        domain = (lead.get("company_domain") or "").strip().lower()
        if domain and domain in domain_results:
            result = domain_results[domain]
            country = result.get("country")
            if country:
                lead["company_country"] = country
                lead["company_country_source"] = "leadmagic_company_search"
                # Re-classify with new info
                cc = country.upper()
                if cc == country_code.upper() or cc == config.get("name", "").upper():
                    lead["_country_classification"] = "domestic"
                    lead["_classification_reason"] = f"enriched:company_country={country}"
                    now_domestic.append(lead)
                else:
                    lead["_country_classification"] = "foreign"
                    lead["_classification_reason"] = f"enriched:company_country={country}"
                    now_foreign.append(lead)
                continue

        # Domain not found or no country result
        still_uncertain.append(lead)

    return now_domestic, now_foreign, still_uncertain, credits_used


def print_stats(total, domestic, foreign, uncertain, credits=0, label=""):
    """Print classification summary."""
    prefix = f"[{label}] " if label else ""
    print(f"\n{prefix}Country Verification Results:")
    print(f"  Total:     {total}")
    print(f"  Domestic:  {len(domestic)} ({len(domestic)/max(total,1)*100:.1f}%)")
    print(f"  Foreign:   {len(foreign)} ({len(foreign)/max(total,1)*100:.1f}%)")
    print(f"  Uncertain: {len(uncertain)} ({len(uncertain)/max(total,1)*100:.1f}%)")
    if credits:
        print(f"  Lead Magic credits: {credits}")


def main():
    parser = argparse.ArgumentParser(description="Verify lead country by company signals + Lead Magic enrichment")
    parser.add_argument("--input", required=True, help="Path to leads JSON file")
    parser.add_argument("--country", required=True, help="Target country code (e.g. LV, NZ, IT)")
    parser.add_argument("--output-dir", default=".tmp/verified", help="Output directory")
    parser.add_argument("--output-prefix", default="verified", help="Output file prefix")
    parser.add_argument("--skip-enrichment", action="store_true", help="Skip Lead Magic API enrichment")
    parser.add_argument("--dry-run", action="store_true", help="Show stats without writing files")

    args = parser.parse_args()

    country_code = args.country.upper()
    if country_code not in COUNTRY_CONFIG:
        print(f"WARNING: Country '{country_code}' not in COUNTRY_CONFIG. "
              f"Available: {', '.join(COUNTRY_CONFIG.keys())}", file=sys.stderr)
        print(f"Proceeding with basic classification only.", file=sys.stderr)

    # Load leads
    from utils import load_leads
    leads = load_leads(args.input)
    print(f"Loaded {len(leads)} leads from {args.input}")
    print(f"Target country: {country_code} ({COUNTRY_CONFIG.get(country_code, {}).get('name', 'Unknown')})")

    # Step 1: Classify by signals
    result = classify_all(leads, country_code)
    domestic = result["domestic"]
    foreign = result["foreign"]
    uncertain = result["uncertain"]

    print_stats(len(leads), domestic, foreign, uncertain, label="Pre-enrichment")

    # Show top rejection reasons
    print(f"\n  Top classification reasons:")
    for reason, count in result["reason_counts"].most_common(15):
        print(f"    {reason}: {count}")

    # Step 2: Enrich uncertain leads
    credits_used = 0
    if uncertain and not args.skip_enrichment and not args.dry_run:
        enriched_domestic, enriched_foreign, still_uncertain, credits_used = enrich_uncertain(
            uncertain, country_code
        )
        domestic.extend(enriched_domestic)
        foreign.extend(enriched_foreign)
        uncertain = still_uncertain

        print_stats(len(leads), domestic, foreign, uncertain, credits=credits_used, label="Post-enrichment")

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        return 0

    # Step 3: Save results
    from utils import save_leads

    # Remove internal classification fields before saving
    for lead in domestic:
        lead.pop("_country_classification", None)
        lead.pop("_classification_reason", None)

    verified_path = save_leads(domestic, args.output_dir, args.output_prefix)
    print(f"\nVerified leads saved: {verified_path}")

    # Save rejected leads (with reason for debugging)
    rejected = foreign + uncertain
    for lead in rejected:
        # Keep classification reason on rejected leads for debugging
        lead["_rejection_reason"] = lead.pop("_classification_reason", "unknown")
        lead.pop("_country_classification", None)

    if rejected:
        rejected_path = os.path.join(
            args.output_dir,
            f"rejected_{timestamp}_{len(rejected)}leads.json"
        )
        with open(rejected_path, "w", encoding="utf-8") as f:
            json.dump(rejected, f, indent=2, ensure_ascii=False)
        print(f"Rejected leads saved: {rejected_path}")

    # Print final filepath to stdout for caller to capture
    print(verified_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

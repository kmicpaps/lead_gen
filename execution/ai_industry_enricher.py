# [CLI] — run via: py execution/ai_industry_enricher.py --help
"""
AI Industry Enricher

Enriches leads with industry categorization using two paths:
1. Path A (70% of leads): Convert SIC/NAICS codes to readable industry names via AI
2. Path B (30% of leads): Scrape company website and categorize industry via AI

Usage:
    python ai_industry_enricher.py --input leads.json
    python ai_industry_enricher.py --input leads.json --ai-provider anthropic
    python ai_industry_enricher.py --input leads.json --force-regenerate
    python ai_industry_enricher.py --input leads.json --output-dir .tmp/industries
"""

import json
import argparse
import time
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from utils import RateLimiter

# Load environment variables
load_dotenv()

# Import AI clients
try:
    import openai
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None

# Import website scraper
sys.path.append(str(Path(__file__).parent))
try:
    from scrape_website_content import scrape_website
except ImportError:
    scrape_website = None

# Configuration
RATE_LIMIT_OPENAI = 50  # requests per second
RATE_LIMIT_ANTHROPIC = 5  # requests per second
MAX_WORKERS = 30  # Increased from 10 to 30 for faster processing
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30


def extract_industry_data(lead: Dict) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Extract SIC/NAICS codes from org_name or company website.

    Returns:
        (has_codes, codes_dict, website_url)
        - has_codes: True if SIC/NAICS codes found
        - codes_dict: {'sic_codes': [...], 'naics_codes': [...]} or None
        - website_url: Company website URL or None
    """
    org_name = lead.get('org_name', {})

    # Check if org_name is a dict (Olympus format)
    if isinstance(org_name, dict):
        sic_codes = org_name.get('sic_codes', [])
        naics_codes = org_name.get('naics_codes', [])

        # If we have valid codes
        if sic_codes or naics_codes:
            return True, {'sic_codes': sic_codes, 'naics_codes': naics_codes}, None

    # No codes - get website for Path B
    website_url = lead.get('website_url') or lead.get('company_website')
    if isinstance(org_name, dict):
        website_url = website_url or org_name.get('website_url')

    return False, None, website_url


def classify_from_codes_openai(sic_codes: List[str], naics_codes: List[str],
                               api_key: str, rate_limiter: RateLimiter) -> str:
    """
    Convert SIC/NAICS codes to human-readable industry name via OpenAI.

    Args:
        sic_codes: List of SIC codes
        naics_codes: List of NAICS codes
        api_key: OpenAI API key
        rate_limiter: Rate limiter instance

    Returns:
        Industry name (2-5 words)
    """
    if not openai:
        raise ImportError("openai package not installed")

    # Format codes for prompt
    sic_str = ", ".join(sic_codes) if sic_codes else "None"
    naics_str = ", ".join(naics_codes) if naics_codes else "None"

    prompt = f"""You are categorizing companies based on their industry classification codes.

SIC Codes: {sic_str}
NAICS Codes: {naics_str}

Based on these industry codes, provide a single, human-readable industry category name.
Use 2-5 words maximum. Be specific but concise.

Examples:
- SIC 8712, NAICS 54131 → "Architectural Services"
- SIC 5091, NAICS 42312 → "Furniture Wholesale"
- SIC 7372, NAICS 51121 → "Software Development"

Return ONLY the industry name, nothing else."""

    rate_limiter.acquire()

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=20,
        temperature=0.3
    )

    industry = response.choices[0].message.content.strip()
    return industry


def classify_from_codes_anthropic(sic_codes: List[str], naics_codes: List[str],
                                  api_key: str, rate_limiter: RateLimiter) -> str:
    """
    Convert SIC/NAICS codes to human-readable industry name via Anthropic.

    Args:
        sic_codes: List of SIC codes
        naics_codes: List of NAICS codes
        api_key: Anthropic API key
        rate_limiter: Rate limiter instance

    Returns:
        Industry name (2-5 words)
    """
    if not anthropic:
        raise ImportError("anthropic package not installed")

    # Format codes for prompt
    sic_str = ", ".join(sic_codes) if sic_codes else "None"
    naics_str = ", ".join(naics_codes) if naics_codes else "None"

    prompt = f"""You are categorizing companies based on their industry classification codes.

SIC Codes: {sic_str}
NAICS Codes: {naics_str}

Based on these industry codes, provide a single, human-readable industry category name.
Use 2-5 words maximum. Be specific but concise.

Examples:
- SIC 8712, NAICS 54131 → "Architectural Services"
- SIC 5091, NAICS 42312 → "Furniture Wholesale"
- SIC 7372, NAICS 51121 → "Software Development"

Return ONLY the industry name, nothing else."""

    rate_limiter.acquire()

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=20,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )

    industry = response.content[0].text.strip()
    return industry


def classify_from_website_openai(website_content: str, company_name: str,
                                 api_key: str, rate_limiter: RateLimiter) -> str:
    """
    Categorize industry from website content via OpenAI.

    Args:
        website_content: Scraped website content (truncated to 2000 chars)
        company_name: Company name
        api_key: OpenAI API key
        rate_limiter: Rate limiter instance

    Returns:
        Industry name (2-5 words)
    """
    if not openai:
        raise ImportError("openai package not installed")

    # Truncate content
    content = website_content[:2000]

    prompt = f"""You are categorizing a company's primary industry based on their website.

Company Name: {company_name}
Website Content: {content}

Categorize this company's PRIMARY industry in 2-5 words.
Be specific and professional. Focus on their main business activity.

Examples:
- "Digital Marketing Agency"
- "SaaS Software"
- "Construction Services"
- "Financial Consulting"

Return ONLY the industry category, nothing else."""

    rate_limiter.acquire()

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=20,
        temperature=0.3
    )

    industry = response.choices[0].message.content.strip()
    return industry


def classify_from_website_anthropic(website_content: str, company_name: str,
                                    api_key: str, rate_limiter: RateLimiter) -> str:
    """
    Categorize industry from website content via Anthropic.

    Args:
        website_content: Scraped website content (truncated to 2000 chars)
        company_name: Company name
        api_key: Anthropic API key
        rate_limiter: Rate limiter instance

    Returns:
        Industry name (2-5 words)
    """
    if not anthropic:
        raise ImportError("anthropic package not installed")

    # Truncate content
    content = website_content[:2000]

    prompt = f"""You are categorizing a company's primary industry based on their website.

Company Name: {company_name}
Website Content: {content}

Categorize this company's PRIMARY industry in 2-5 words.
Be specific and professional. Focus on their main business activity.

Examples:
- "Digital Marketing Agency"
- "SaaS Software"
- "Construction Services"
- "Financial Consulting"

Return ONLY the industry category, nothing else."""

    rate_limiter.acquire()

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=20,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )

    industry = response.content[0].text.strip()
    return industry


def enrich_single_lead(lead: Dict, ai_provider: str, api_key: str,
                      rate_limiter: RateLimiter) -> Dict:
    """
    Process one lead with retry logic (3 attempts, exponential backoff).

    Args:
        lead: Lead dict
        ai_provider: 'openai' or 'anthropic'
        api_key: API key for chosen provider
        rate_limiter: Rate limiter instance

    Returns:
        Updated lead dict with industry fields
    """
    # Check if already has industry (and not force regenerate)
    if lead.get('industry') and not hasattr(enrich_single_lead, 'force_regenerate'):
        return lead

    # Extract industry data
    has_codes, codes_dict, website_url = extract_industry_data(lead)

    for attempt in range(MAX_RETRIES):
        try:
            if has_codes:
                # Path A: Convert codes to industry name
                sic_codes = codes_dict['sic_codes']
                naics_codes = codes_dict['naics_codes']

                if ai_provider == 'openai':
                    industry = classify_from_codes_openai(sic_codes, naics_codes, api_key, rate_limiter)
                else:
                    industry = classify_from_codes_anthropic(sic_codes, naics_codes, api_key, rate_limiter)

                # Add fields
                lead['industry'] = industry
                lead['industry_source'] = 'sic_naics'
                lead['industry_generated_by'] = ai_provider
                lead['industry_generated_at'] = datetime.now(timezone.utc).isoformat()
                lead['industry_error'] = None

                return lead

            elif website_url:
                # Path B: Scrape website and categorize
                if not scrape_website:
                    raise ImportError("scrape_website_content module not available")

                # Scrape website
                website_content = scrape_website(website_url, timeout=15)

                if not website_content or len(website_content) < 50:
                    # No meaningful content
                    lead['industry'] = ''
                    lead['industry_error'] = 'no_content'
                    return lead

                # Get company name
                org_name = lead.get('org_name')
                if isinstance(org_name, dict):
                    company_name = lead.get('company_name') or org_name.get('name', 'Unknown')
                else:
                    company_name = lead.get('company_name') or lead.get('name') or org_name or 'Unknown'

                if isinstance(company_name, dict):
                    company_name = 'Unknown'

                # Categorize via AI
                if ai_provider == 'openai':
                    industry = classify_from_website_openai(website_content, company_name, api_key, rate_limiter)
                else:
                    industry = classify_from_website_anthropic(website_content, company_name, api_key, rate_limiter)

                # Add fields
                lead['industry'] = industry
                lead['industry_source'] = 'website'
                lead['industry_generated_by'] = ai_provider
                lead['industry_generated_at'] = datetime.now(timezone.utc).isoformat()
                lead['industry_error'] = None

                return lead

            else:
                # No data available
                lead['industry'] = ''
                lead['industry_error'] = 'no_data'
                return lead

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                # Exponential backoff
                wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s
                time.sleep(wait_time)
            else:
                # Final attempt failed
                error_type = 'scrape_failed' if website_url and not has_codes else 'ai_failed'
                lead['industry'] = ''
                lead['industry_error'] = error_type
                return lead

    return lead


def enrich_leads_concurrent(leads: List[Dict], ai_provider: str, api_key: str,
                           force_regenerate: bool = False) -> Tuple[List[Dict], Dict]:
    """
    Process all leads concurrently.

    Args:
        leads: List of lead dicts
        ai_provider: 'openai' or 'anthropic'
        api_key: API key for chosen provider
        force_regenerate: Regenerate industry for leads that already have it

    Returns:
        (updated_leads, stats)
    """
    # Set force regenerate flag
    if force_regenerate:
        enrich_single_lead.force_regenerate = True

    # Filter leads that need enrichment
    leads_to_process = []
    for lead in leads:
        if force_regenerate or not lead.get('industry'):
            leads_to_process.append(lead)

    print(f"\n[INFO] Processing {len(leads_to_process)} leads (skipping {len(leads) - len(leads_to_process)} with existing industry)")

    # Create rate limiter
    rate_limit = RATE_LIMIT_OPENAI if ai_provider == 'openai' else RATE_LIMIT_ANTHROPIC
    rate_limiter = RateLimiter(rate_limit)

    # Process concurrently
    enriched_leads = []
    stats = {
        'total': len(leads_to_process),
        'success': 0,
        'failed': 0,
        'sic_naics': 0,
        'website': 0,
        'no_data': 0,
        'scrape_failed': 0,
        'ai_failed': 0
    }

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(enrich_single_lead, lead, ai_provider, api_key, rate_limiter): lead
            for lead in leads_to_process
        }

        completed = 0
        for future in as_completed(futures):
            enriched_lead = future.result()
            enriched_leads.append(enriched_lead)

            completed += 1

            # Track stats
            if enriched_lead.get('industry'):
                stats['success'] += 1
                source = enriched_lead.get('industry_source', '')
                if source == 'sic_naics':
                    stats['sic_naics'] += 1
                elif source == 'website':
                    stats['website'] += 1
            else:
                stats['failed'] += 1
                error = enriched_lead.get('industry_error', '')
                if error == 'no_data':
                    stats['no_data'] += 1
                elif error == 'scrape_failed':
                    stats['scrape_failed'] += 1
                elif error == 'ai_failed':
                    stats['ai_failed'] += 1

            # Progress update every 10 leads
            if completed % 10 == 0 or completed == len(leads_to_process):
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                print(f"[PROGRESS] {completed}/{len(leads_to_process)} processed | {stats['success']} success | {stats['failed']} failed | {rate:.1f} leads/sec")

    # Clean up force_regenerate flag to prevent it persisting across calls
    if hasattr(enrich_single_lead, 'force_regenerate'):
        delattr(enrich_single_lead, 'force_regenerate')

    # Update original leads list with enriched data
    enriched_dict = {id(lead): enriched for lead, enriched in zip(leads_to_process, enriched_leads)}
    for i, lead in enumerate(leads):
        if id(lead) in enriched_dict:
            leads[i] = enriched_dict[id(lead)]

    elapsed = time.time() - start_time
    print(f"\n[COMPLETE] Processed {len(leads_to_process)} leads in {elapsed:.1f}s ({len(leads_to_process)/max(elapsed, 0.1):.1f} leads/sec)")

    return leads, stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='AI Industry Enricher')
    parser.add_argument('--input', required=True, help='Input JSON file with leads')
    parser.add_argument('--output-dir', default='.tmp', help='Output directory (default: .tmp)')
    parser.add_argument('--ai-provider', choices=['openai', 'anthropic'], default='openai',
                       help='AI provider to use (default: openai)')
    parser.add_argument('--force-regenerate', action='store_true',
                       help='Regenerate industry for leads that already have it')

    args = parser.parse_args()

    # Load API key
    if args.ai_provider == 'openai':
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("[ERROR] OPENAI_API_KEY not found in .env")
            sys.exit(1)
        if not openai:
            print("[ERROR] openai package not installed. Run: pip install openai")
            sys.exit(1)
    else:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            print("[ERROR] ANTHROPIC_API_KEY not found in .env")
            sys.exit(1)
        if not anthropic:
            print("[ERROR] anthropic package not installed. Run: pip install anthropic")
            sys.exit(1)

    # Load leads
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {args.input}")
        sys.exit(1)

    print(f"[INFO] Loading leads from {args.input}")
    with open(input_path, 'r', encoding='utf-8') as f:
        leads = json.load(f)

    print(f"[INFO] Loaded {len(leads)} leads")
    print(f"[INFO] Using AI provider: {args.ai_provider}")

    # Enrich leads
    enriched_leads, stats = enrich_leads_concurrent(leads, args.ai_provider, api_key, args.force_regenerate)

    # Save output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f"industry_enriched_{timestamp}_{len(enriched_leads)}leads.json"
    output_path = output_dir / output_filename

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enriched_leads, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Saved enriched leads to {output_path}")

    # Print statistics
    print("\n=== Industry Enrichment Statistics ===")
    print(f"Total processed: {stats['total']}")
    print(f"Successful: {stats['success']} ({stats['success']/stats['total']*100:.1f}%)")
    print(f"  - From SIC/NAICS codes: {stats['sic_naics']} ({stats['sic_naics']/stats['total']*100:.1f}%)")
    print(f"  - From website: {stats['website']} ({stats['website']/stats['total']*100:.1f}%)")
    print(f"Failed: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")
    print(f"  - No data: {stats['no_data']}")
    print(f"  - Scrape failed: {stats['scrape_failed']}")
    print(f"  - AI failed: {stats['ai_failed']}")


if __name__ == '__main__':
    main()

# [CLI] — run via: py execution/ai_casual_name_generator.py --help
"""
AI-powered casual organization name enrichment.
Generates human-friendly, casual versions of formal company names.

Usage:
    py execution/enrich_casual_org_names.py --input leads.json
    py execution/enrich_casual_org_names.py --input leads.json --ai-provider anthropic
    py execution/enrich_casual_org_names.py --input leads.json --force-regenerate
"""

import os
import sys
import json
import argparse
import time
from datetime import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import RateLimiter

# Load environment variables
load_dotenv()

# Rate limiting
RATE_LIMIT_OPENAI = 50  # requests per second
RATE_LIMIT_ANTHROPIC = 5  # requests per second
MAX_WORKERS = 10  # concurrent threads


def generate_casual_name_openai(company_name, api_key, rate_limiter):
    """
    Generate casual name using OpenAI API.
    Returns: (casual_name, success)
    """
    try:
        import openai

        rate_limiter.acquire()

        client = openai.OpenAI(api_key=api_key)

        prompt = f"""Given this company name, generate a short, casual, human-friendly version:
Company name: "{company_name}"

Rules:
- Remove legal suffixes (Sp. Z O.o., LLC, Ltd, Inc, GmbH, AB, AS, etc.)
- Remove marketing taglines and slogans
- Extract core brand name
- Keep 1-2 words maximum
- Return ONLY the casual name, nothing else

Examples:
"Tatran Group 3r Reduce, Reuse, Recycle ... In Harmony With The Nature" → "Tatran"
"Pmtech Engineering" → "Pmtech"
"Prefasprzęt Sp. Z O.o." → "Prefasprzęt"
"ABC Marketing Solutions LLC" → "ABC Marketing"
"Digital Growth Agency Inc." → "Digital Growth"
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates casual, human-friendly company names."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=50,
            timeout=30
        )

        casual_name = response.choices[0].message.content.strip()

        # Validate output
        if not casual_name or len(casual_name) > len(company_name):
            return None, False

        return casual_name, True

    except Exception as e:
        print(f"OpenAI API error for '{company_name}': {e}", file=sys.stderr)
        return None, False


def generate_casual_name_anthropic(company_name, api_key, rate_limiter):
    """
    Generate casual name using Anthropic API.
    Returns: (casual_name, success)
    """
    try:
        import anthropic

        rate_limiter.acquire()

        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""Given this company name, generate a short, casual, human-friendly version:
Company name: "{company_name}"

Rules:
- Remove legal suffixes (Sp. Z O.o., LLC, Ltd, Inc, GmbH, AB, AS, etc.)
- Remove marketing taglines and slogans
- Extract core brand name
- Keep 1-2 words maximum
- Return ONLY the casual name, nothing else

Examples:
"Tatran Group 3r Reduce, Reuse, Recycle ... In Harmony With The Nature" → "Tatran"
"Pmtech Engineering" → "Pmtech"
"Prefasprzęt Sp. Z O.o." → "Prefasprzęt"
"ABC Marketing Solutions LLC" → "ABC Marketing"
"Digital Growth Agency Inc." → "Digital Growth"
"""

        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=50,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ],
            timeout=30
        )

        casual_name = message.content[0].text.strip()

        # Validate output
        if not casual_name or len(casual_name) > len(company_name):
            return None, False

        return casual_name, True

    except Exception as e:
        print(f"Anthropic API error for '{company_name}': {e}", file=sys.stderr)
        return None, False


def enrich_single_lead(lead, ai_provider, api_key, rate_limiter):
    """
    Enrich a single lead with casual org name.
    Returns: updated lead
    """
    # Handle both company_name (string) and org_name (object) formats
    company_name = lead.get('company_name', '')

    # If company_name is empty, try org_name (B2B finder format)
    if not company_name and 'org_name' in lead:
        org_name_obj = lead.get('org_name', {})
        if isinstance(org_name_obj, dict):
            company_name = org_name_obj.get('name', '')
        elif isinstance(org_name_obj, str):
            company_name = org_name_obj

    company_name = company_name.strip()

    if not company_name:
        lead['casual_org_name'] = ''
        lead['casual_org_name_error'] = 'missing_company_name'
        return lead

    # Truncate very long names
    if len(company_name) > 500:
        company_name = company_name[:200]
        print(f"Warning: Truncated long company name: {lead.get('company_name', '')[:50]}...")

    # Retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if ai_provider == 'openai':
                casual_name, success = generate_casual_name_openai(company_name, api_key, rate_limiter)
            elif ai_provider == 'anthropic':
                casual_name, success = generate_casual_name_anthropic(company_name, api_key, rate_limiter)
            else:
                raise ValueError(f"Unknown AI provider: {ai_provider}")

            if success and casual_name:
                lead['casual_org_name'] = casual_name
                lead['casual_org_name_generated_by'] = ai_provider
                lead['casual_org_name_generated_at'] = datetime.now().isoformat()
                return lead

            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                print(f"Failed after {max_retries} attempts: {company_name}", file=sys.stderr)
                lead['casual_org_name'] = ''
                lead['casual_org_name_error'] = str(e)
                return lead

    # Fallback: remove legal suffixes manually
    fallback_name = remove_legal_suffixes(company_name)
    lead['casual_org_name'] = fallback_name
    lead['casual_org_name_generated_by'] = 'fallback'
    lead['casual_org_name_generated_at'] = datetime.now().isoformat()

    return lead


def remove_legal_suffixes(company_name):
    """Fallback: manually remove common legal suffixes"""
    suffixes = [
        'LLC', 'Ltd', 'Inc', 'Corp', 'Corporation', 'Company', 'Co.',
        'GmbH', 'AG', 'SA', 'SL', 'AB', 'AS', 'Oy', 'Sp. z o.o.',
        'Sp. Z O.o.', 'S.A.', 'S.L.', 'B.V.', 'N.V.', 'Limited'
    ]

    name = company_name.strip()

    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
            break

    # Remove trailing commas and periods
    name = name.rstrip('.,')

    return name


def enrich_leads_concurrent(leads, ai_provider, api_key, force_regenerate=False):
    """
    Enrich leads with casual org names concurrently.
    """
    # Helper function to check if lead has company info
    def has_company_info(lead):
        if lead.get('company_name'):
            return True
        org_name = lead.get('org_name', {})
        if isinstance(org_name, dict) and org_name.get('name'):
            return True
        if isinstance(org_name, str) and org_name.strip():
            return True
        return False

    # Filter leads that need enrichment
    leads_to_enrich = []
    for lead in leads:
        if not has_company_info(lead):
            continue
        if force_regenerate or not lead.get('casual_org_name'):
            leads_to_enrich.append(lead)

    if not leads_to_enrich:
        print("No leads need casual name enrichment")
        return leads

    print(f"\nEnriching {len(leads_to_enrich)} leads with casual org names...")
    print(f"AI Provider: {ai_provider.upper()}")

    rate_limit = RATE_LIMIT_OPENAI if ai_provider == 'openai' else RATE_LIMIT_ANTHROPIC
    print(f"Rate limit: {rate_limit} req/sec")
    print(f"Estimated time: ~{len(leads_to_enrich) / rate_limit:.1f} seconds\n")

    rate_limiter = RateLimiter(rate_limit)
    enriched_count = 0
    failed_count = 0

    # Create a mapping to preserve order
    lead_map = {id(lead): lead for lead in leads}

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all enrichment tasks
        future_to_lead = {
            executor.submit(enrich_single_lead, lead, ai_provider, api_key, rate_limiter): id(lead)
            for lead in leads_to_enrich
        }

        # Process completed tasks
        processed = 0
        for future in as_completed(future_to_lead):
            processed += 1
            lead_id = future_to_lead[future]

            try:
                updated_lead = future.result()
                lead_map[lead_id] = updated_lead

                if updated_lead.get('casual_org_name'):
                    enriched_count += 1
                else:
                    failed_count += 1

                if processed % 25 == 0:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed if elapsed > 0 else 0
                    print(f"  Enriched {processed}/{len(leads_to_enrich)} | Success: {enriched_count} ({rate:.1f}/sec)")

            except Exception as e:
                print(f"Error in future: {e}", file=sys.stderr)
                failed_count += 1

    elapsed_time = time.time() - start_time
    actual_rate = len(leads_to_enrich) / elapsed_time if elapsed_time > 0 else 0

    print(f"\nEnrichment complete in {elapsed_time:.1f}s ({actual_rate:.1f} leads/sec):")
    print(f"  Total processed: {len(leads_to_enrich)}")
    print(f"  Successfully enriched: {enriched_count} ({enriched_count/len(leads_to_enrich)*100:.1f}%)")
    print(f"  Failed: {failed_count}")

    return leads


def main():
    parser = argparse.ArgumentParser(description='AI-powered casual organization name enrichment')
    parser.add_argument('--input', required=True, help='Path to leads JSON file')
    parser.add_argument('--output-dir', default='.tmp/ai_enriched', help='Output directory')
    parser.add_argument('--output-prefix', default='casual_enriched', help='Output file prefix')
    parser.add_argument('--ai-provider', default='openai', choices=['openai', 'anthropic'], help='AI provider to use')
    parser.add_argument('--force-regenerate', action='store_true', help='Regenerate existing casual names')

    args = parser.parse_args()

    # Get API key based on provider
    if args.ai_provider == 'openai':
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("Error: OPENAI_API_KEY not found in .env", file=sys.stderr)
            return 1
    elif args.ai_provider == 'anthropic':
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            print("Error: ANTHROPIC_API_KEY not found in .env", file=sys.stderr)
            return 1

    try:
        # Load leads
        with open(args.input, 'r', encoding='utf-8') as f:
            leads = json.load(f)

        if not leads:
            print("No leads to enrich", file=sys.stderr)
            return 1

        print(f"Loaded {len(leads)} leads")

        # Count leads with company names (handle both formats)
        def has_company_info(lead):
            if lead.get('company_name'):
                return True
            org_name = lead.get('org_name', {})
            if isinstance(org_name, dict) and org_name.get('name'):
                return True
            if isinstance(org_name, str) and org_name.strip():
                return True
            return False

        has_company_name = len([l for l in leads if has_company_info(l)])
        print(f"Leads with company names: {has_company_name}")

        if has_company_name == 0:
            print("No leads have company names. Nothing to enrich.")
            return 0

        # Enrich leads
        leads = enrich_leads_concurrent(leads, args.ai_provider, api_key, args.force_regenerate)

        # Save enriched leads
        os.makedirs(args.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{args.output_prefix}_{timestamp}_{len(leads)}leads.json"
        filepath = os.path.join(args.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(leads, f, indent=2, ensure_ascii=False)

        print(f"\nEnriched leads saved to: {filepath}")
        print(filepath)  # Print filepath to stdout for caller

        return 0

    except Exception as e:
        print(f"Error enriching casual org names: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

# [CLI] — run via: py execution/ai_icebreaker_generator.py --help
"""
AI-powered icebreaker enrichment with website scraping.
Generates personalized icebreaker messages for cold outreach.

Usage:
    py execution/enrich_icebreakers.py --input leads.json
    py execution/enrich_icebreakers.py --input leads.json --ai-provider anthropic
    py execution/enrich_icebreakers.py --input leads.json --template my_template.txt
    py execution/enrich_icebreakers.py --input leads.json --skip-scraping
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

# Import website scraper
from website_scraper import scrape_website

# Load environment variables
load_dotenv()

# Rate limiting
RATE_LIMIT_OPENAI = 50  # requests per second for AI
RATE_LIMIT_ANTHROPIC = 5  # requests per second for AI
SCRAPING_RATE_LIMIT = 10  # concurrent scraping requests
MAX_WORKERS = 10  # concurrent threads


def get_company_website(lead):
    """
    Extract company website from lead, handling both flat and nested formats.
    Returns: website URL string or empty string
    """
    # Try flat field first
    website_value = lead.get('company_website', '')
    website = website_value.strip() if website_value else ''

    # If empty, try nested org_name object (B2B finder format)
    if not website and 'org_name' in lead:
        org_name_obj = lead.get('org_name', {})
        if isinstance(org_name_obj, dict):
            website_value = org_name_obj.get('website_url', '')
            website = website_value.strip() if website_value else ''

    return website


def scrape_single_website(lead, scraping_errors_log):
    """
    Scrape website content for a single lead.
    Returns: updated lead with website_content field
    """
    website_url = get_company_website(lead)

    if not website_url:
        lead['icebreaker_error'] = 'missing_website'
        return lead

    try:
        # Scrape website
        result = scrape_website(website_url, timeout=30, retry_attempts=3)

        if result['success']:
            lead['website_content'] = result['content']
            lead['website_scraped_url'] = result['url']
            return lead
        else:
            # Scraping failed
            lead['icebreaker_error'] = f"scrape_failed: {result['error']}"
            scraping_errors_log.append({
                'company': lead.get('company_name', ''),
                'website': website_url,
                'error': result['error']
            })
            return lead

    except Exception as e:
        lead['icebreaker_error'] = f"scrape_exception: {str(e)}"
        scraping_errors_log.append({
            'company': lead.get('company_name', ''),
            'website': website_url,
            'error': str(e)
        })
        return lead


def generate_icebreaker_openai(lead, api_key, rate_limiter, user_template=None):
    """
    Generate icebreaker using OpenAI API.
    Returns: (icebreaker_text, success)
    """
    try:
        import openai

        rate_limiter.acquire()

        client = openai.OpenAI(api_key=api_key)

        # Prepare lead info
        full_name = lead.get('full_name', '').strip()
        company_name = lead.get('casual_org_name', '') or lead.get('company_name', '')
        job_title = lead.get('job_title', '').strip()
        website_content = lead.get('website_content', '').strip()

        if not website_content or len(website_content) < 50:
            return None, False

        # Build prompt
        if user_template:
            prompt = f"""You are writing a personalized cold outreach icebreaker for a B2B prospect.

Lead information:
- Name: {full_name}
- Company: {company_name}
- Job title: {job_title}
- Website content: {website_content}

User template for tone and structure:
{user_template}

Instructions:
1. Use the user template as a guide for tone and structure
2. Fill in personalized details from the website content
3. Reference something SPECIFIC from their website (not generic)
4. Keep it 1-2 sentences
5. Feel casual and human (not salesy or robotic)
6. Match the style of the template while personalizing with their website info

Return ONLY the icebreaker text, nothing else. No greetings, no signatures, just the icebreaker."""
        else:
            prompt = f"""You are writing a personalized cold outreach icebreaker for a B2B prospect.

Lead information:
- Name: {full_name}
- Company: {company_name}
- Job title: {job_title}
- Website content: {website_content}

Write a 1-2 sentence personalized icebreaker that:
1. References something SPECIFIC from their website (not generic)
2. Shows genuine interest in their business
3. Feels casual and human (not salesy or robotic)
4. Connects to a potential business need or mutual interest
5. Uses natural, conversational language

Examples:
- "Read your LinkedIn about driving digital strategy and noticed Pierce Media's focus on custom results. That blend caught my eye, so I decided to reach out."
- "Hi Thomas! Roman Media Group's focus on local service growth stood out—systems thinking plus digital marketing is a rare combo. Caught my eye, decided to reach out."

Return ONLY the icebreaker text, nothing else. No greetings, no signatures, just the icebreaker."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates personalized, casual icebreakers for B2B cold outreach."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150,
            timeout=30
        )

        icebreaker = response.choices[0].message.content.strip()
        # Remove surrounding quotes if AI added them
        icebreaker = icebreaker.strip('"').strip("'")

        # Validate output
        if not icebreaker or len(icebreaker) < 50 or len(icebreaker) > 300:
            return None, False

        # Check for placeholder text
        if '[' in icebreaker or '{' in icebreaker:
            return None, False

        return icebreaker, True

    except Exception as e:
        print(f"OpenAI API error for '{lead.get('company_name', 'Unknown')}': {e}", file=sys.stderr)
        return None, False


def generate_icebreaker_anthropic(lead, api_key, rate_limiter, user_template=None):
    """
    Generate icebreaker using Anthropic API.
    Returns: (icebreaker_text, success)
    """
    try:
        import anthropic

        rate_limiter.acquire()

        client = anthropic.Anthropic(api_key=api_key)

        # Prepare lead info
        full_name = lead.get('full_name', '').strip()
        company_name = lead.get('casual_org_name', '') or lead.get('company_name', '')
        job_title = lead.get('job_title', '').strip()
        website_content = lead.get('website_content', '').strip()

        if not website_content or len(website_content) < 50:
            return None, False

        # Build prompt
        if user_template:
            prompt = f"""You are writing a personalized cold outreach icebreaker for a B2B prospect.

Lead information:
- Name: {full_name}
- Company: {company_name}
- Job title: {job_title}
- Website content: {website_content}

User template for tone and structure:
{user_template}

Instructions:
1. Use the user template as a guide for tone and structure
2. Fill in personalized details from the website content
3. Reference something SPECIFIC from their website (not generic)
4. Keep it 1-2 sentences
5. Feel casual and human (not salesy or robotic)
6. Match the style of the template while personalizing with their website info

Return ONLY the icebreaker text, nothing else. No greetings, no signatures, just the icebreaker."""
        else:
            prompt = f"""You are writing a personalized cold outreach icebreaker for a B2B prospect.

Lead information:
- Name: {full_name}
- Company: {company_name}
- Job title: {job_title}
- Website content: {website_content}

Write a 1-2 sentence personalized icebreaker that:
1. References something SPECIFIC from their website (not generic)
2. Shows genuine interest in their business
3. Feels casual and human (not salesy or robotic)
4. Connects to a potential business need or mutual interest
5. Uses natural, conversational language

Examples:
- "Read your LinkedIn about driving digital strategy and noticed Pierce Media's focus on custom results. That blend caught my eye, so I decided to reach out."
- "Hi Thomas! Roman Media Group's focus on local service growth stood out—systems thinking plus digital marketing is a rare combo. Caught my eye, decided to reach out."

Return ONLY the icebreaker text, nothing else. No greetings, no signatures, just the icebreaker."""

        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=150,
            temperature=0.7,
            messages=[
                {"role": "user", "content": prompt}
            ],
            timeout=30
        )

        icebreaker = message.content[0].text.strip()

        # Validate output
        if not icebreaker or len(icebreaker) < 50 or len(icebreaker) > 300:
            return None, False

        # Check for placeholder text
        if '[' in icebreaker or '{' in icebreaker:
            return None, False

        return icebreaker, True

    except Exception as e:
        print(f"Anthropic API error for '{lead.get('company_name', 'Unknown')}': {e}", file=sys.stderr)
        return None, False


def enrich_single_icebreaker(lead, ai_provider, api_key, rate_limiter, user_template=None):
    """
    Generate icebreaker for a single lead (assumes website already scraped).
    Returns: updated lead
    """
    # Skip if no website content
    if not lead.get('website_content'):
        if not lead.get('icebreaker_error'):
            lead['icebreaker_error'] = 'no_content'
        return lead

    # Retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if ai_provider == 'openai':
                icebreaker, success = generate_icebreaker_openai(lead, api_key, rate_limiter, user_template)
            elif ai_provider == 'anthropic':
                icebreaker, success = generate_icebreaker_anthropic(lead, api_key, rate_limiter, user_template)
            else:
                raise ValueError(f"Unknown AI provider: {ai_provider}")

            if success and icebreaker:
                lead['icebreaker'] = icebreaker
                lead['icebreaker_generated_by'] = ai_provider
                lead['icebreaker_generated_at'] = datetime.now().isoformat()
                return lead

            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                print(f"Failed after {max_retries} attempts: {lead.get('company_name', 'Unknown')}", file=sys.stderr)
                lead['icebreaker'] = ''
                lead['icebreaker_error'] = 'ai_failed'
                return lead

    # Failed to generate icebreaker
    lead['icebreaker'] = ''
    lead['icebreaker_error'] = 'ai_failed'
    return lead


def enrich_icebreakers(leads, ai_provider, api_key, skip_scraping=False, force_regenerate=False, user_template=None):
    """
    Enrich leads with icebreakers using website scraping + AI generation.
    """
    # Filter leads that need enrichment
    leads_to_enrich = []
    for lead in leads:
        if not get_company_website(lead):
            continue
        if force_regenerate or not lead.get('icebreaker'):
            leads_to_enrich.append(lead)

    if not leads_to_enrich:
        print("No leads need icebreaker enrichment")
        return leads

    print(f"\n=== Icebreaker Enrichment ===")
    print(f"Total leads to enrich: {len(leads_to_enrich)}")
    print(f"AI Provider: {ai_provider.upper()}")

    scraping_errors_log = []

    # Step 1: Scrape websites (if not skipping)
    if not skip_scraping:
        leads_to_scrape = [l for l in leads_to_enrich if not l.get('website_content')]

        if leads_to_scrape:
            print(f"\n[Step 1/2] Scraping {len(leads_to_scrape)} websites...")
            print(f"Concurrent requests: {SCRAPING_RATE_LIMIT}")
            print(f"Estimated time: ~{len(leads_to_scrape) / SCRAPING_RATE_LIMIT:.1f} seconds\n")

            scraped_count = 0
            failed_count = 0
            start_time = time.time()

            lead_map = {id(lead): lead for lead in leads}

            with ThreadPoolExecutor(max_workers=SCRAPING_RATE_LIMIT) as executor:
                future_to_lead = {
                    executor.submit(scrape_single_website, lead, scraping_errors_log): id(lead)
                    for lead in leads_to_scrape
                }

                processed = 0
                for future in as_completed(future_to_lead):
                    processed += 1
                    lead_id = future_to_lead[future]

                    try:
                        updated_lead = future.result()
                        lead_map[lead_id] = updated_lead

                        if updated_lead.get('website_content'):
                            scraped_count += 1
                        else:
                            failed_count += 1

                        if processed % 25 == 0:
                            elapsed = time.time() - start_time
                            rate = processed / elapsed if elapsed > 0 else 0
                            print(f"  Scraped {processed}/{len(leads_to_scrape)} | Success: {scraped_count} ({rate:.1f}/sec)")

                    except Exception as e:
                        print(f"Error in scraping future: {e}", file=sys.stderr)
                        failed_count += 1

            elapsed_time = time.time() - start_time
            actual_rate = len(leads_to_scrape) / elapsed_time if elapsed_time > 0 else 0

            print(f"\nScraping complete in {elapsed_time:.1f}s ({actual_rate:.1f} websites/sec):")
            print(f"  Attempted: {len(leads_to_scrape)}")
            print(f"  Successfully scraped: {scraped_count} ({scraped_count/len(leads_to_scrape)*100:.1f}%)")
            print(f"  Failed: {failed_count}")

    # Step 2: Generate icebreakers using AI
    leads_with_content = [l for l in leads_to_enrich if l.get('website_content')]

    if not leads_with_content:
        print("\nNo leads have website content. Cannot generate icebreakers.")
        return leads

    print(f"\n[Step 2/2] Generating {len(leads_with_content)} icebreakers using AI...")

    rate_limit = RATE_LIMIT_OPENAI if ai_provider == 'openai' else RATE_LIMIT_ANTHROPIC
    print(f"Rate limit: {rate_limit} req/sec")
    print(f"Estimated time: ~{len(leads_with_content) / rate_limit:.1f} seconds\n")

    rate_limiter = RateLimiter(rate_limit)
    enriched_count = 0
    failed_count = 0

    lead_map = {id(lead): lead for lead in leads}
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_lead = {
            executor.submit(enrich_single_icebreaker, lead, ai_provider, api_key, rate_limiter, user_template): id(lead)
            for lead in leads_with_content
        }

        processed = 0
        for future in as_completed(future_to_lead):
            processed += 1
            lead_id = future_to_lead[future]

            try:
                updated_lead = future.result()
                lead_map[lead_id] = updated_lead

                if updated_lead.get('icebreaker'):
                    enriched_count += 1
                else:
                    failed_count += 1

                if processed % 25 == 0:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed if elapsed > 0 else 0
                    print(f"  Generated {processed}/{len(leads_with_content)} | Success: {enriched_count} ({rate:.1f}/sec)")

            except Exception as e:
                print(f"Error in AI generation future: {e}", file=sys.stderr)
                failed_count += 1

    elapsed_time = time.time() - start_time
    actual_rate = len(leads_with_content) / elapsed_time if elapsed_time > 0 else 0

    print(f"\nIcebreaker generation complete in {elapsed_time:.1f}s ({actual_rate:.1f} leads/sec):")
    print(f"  Total processed: {len(leads_with_content)}")
    print(f"  Successfully generated: {enriched_count} ({enriched_count/len(leads_with_content)*100:.1f}%)")
    print(f"  Failed: {failed_count}")

    # Save scraping errors log if any
    if scraping_errors_log:
        error_log_path = '.tmp/scraping_errors.log'
        os.makedirs(os.path.dirname(error_log_path), exist_ok=True)
        with open(error_log_path, 'w', encoding='utf-8') as f:
            json.dump(scraping_errors_log, f, indent=2, ensure_ascii=False)
        print(f"\nScraping errors logged to: {error_log_path}")

    return leads


def main():
    parser = argparse.ArgumentParser(description='AI-powered icebreaker enrichment with website scraping')
    parser.add_argument('--input', required=True, help='Path to leads JSON file')
    parser.add_argument('--output-dir', default='.tmp/ai_enriched', help='Output directory')
    parser.add_argument('--output-prefix', default='icebreaker_enriched', help='Output file prefix')
    parser.add_argument('--ai-provider', default='openai', choices=['openai', 'anthropic'], help='AI provider to use')
    parser.add_argument('--template', help='Path to user template file (optional)')
    parser.add_argument('--skip-scraping', action='store_true', help='Skip website scraping (use existing website_content)')
    parser.add_argument('--force-regenerate', action='store_true', help='Regenerate existing icebreakers')

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

    # Load user template if provided
    user_template = None
    if args.template:
        try:
            with open(args.template, 'r', encoding='utf-8') as f:
                user_template = f.read().strip()
            print(f"Loaded user template: {args.template}")
        except Exception as e:
            print(f"Warning: Could not load template file: {e}", file=sys.stderr)

    try:
        # Load leads
        with open(args.input, 'r', encoding='utf-8') as f:
            leads = json.load(f)

        if not leads:
            print("No leads to enrich", file=sys.stderr)
            return 1

        print(f"Loaded {len(leads)} leads")

        # Count leads with company websites (handle both flat and nested formats)
        has_website = len([l for l in leads if get_company_website(l)])
        print(f"Leads with company websites: {has_website}")

        if has_website == 0:
            print("No leads have company websites. Nothing to enrich.")
            return 0

        # Enrich leads
        leads = enrich_icebreakers(
            leads,
            args.ai_provider,
            api_key,
            skip_scraping=args.skip_scraping,
            force_regenerate=args.force_regenerate,
            user_template=user_template
        )

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
        print(f"Error enriching icebreakers: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

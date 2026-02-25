# [CLI] — run via: py execution/generate_sales_sample.py --help
"""
Sales Sample Generator - Creates demo deliverables for prospective clients.

Workflow:
1. Phase 1: Analyze prospect website → ICP + Apollo filter suggestions
2. Phase 2: Scrape 2-3 sample leads from Apollo (requires user-provided URL)
3. Phase 3: Enrich leads (website + LinkedIn)
4. Phase 4: Generate email sequence + personalized first emails
5. Output: Markdown report

Usage:
    # Phase 1 only (discovery)
    py execution/generate_sales_sample.py phase1 --prospect-url https://example.com

    # Full workflow (after getting Apollo URL)
    py execution/generate_sales_sample.py complete \
        --prospect-url https://example.com \
        --apollo-url "https://app.apollo.io/#/people?..."

    # With reference copies
    py execution/generate_sales_sample.py complete \
        --prospect-url https://example.com \
        --apollo-url "..." \
        --reference-copies campaigns/example_agency/reference_copies
"""

import os
import sys
import json
import argparse
import time
import re
from datetime import datetime
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Import existing tools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_json, save_json
from client_discovery import (
    scrape_website_multi_page,
    analyze_with_ai,
    create_client_json,
    clean_url
)
from website_scraper import scrape_website
from linkedin_enricher import enrich_linkedin_profiles

# Constants
MAX_SAMPLE_LEADS = 3
DEFAULT_OUTPUT_DIR = '.tmp/samples'


def run_phase1_discovery(prospect_url, notes="", ai_provider="openai"):
    """
    Phase 1: Analyze prospect website and generate ICP + Apollo filter suggestions.
    Returns: discovery data dict
    """
    print("=" * 60)
    print("PHASE 1: DISCOVERY")
    print("=" * 60)
    print(f"Analyzing: {prospect_url}")
    print()

    # Scrape website
    print("Scraping website pages...")
    scrape_results, total_content = scrape_website_multi_page(prospect_url)

    if not total_content or len(total_content) < 100:
        raise Exception("Could not extract enough content from website")

    # AI analysis
    print("\nRunning AI analysis...")
    analysis = analyze_with_ai(total_content, notes, ai_provider)

    # Create client structure
    client_data = create_client_json(analysis, prospect_url)

    return {
        'client_data': client_data,
        'analysis': analysis,
        'scrape_results': scrape_results,
        'total_content': total_content
    }


def print_phase1_results(discovery):
    """Print Phase 1 results and Apollo filter suggestions."""
    client = discovery['client_data']
    analysis = discovery['analysis']
    apollo = client.get('apollo_filters', {})

    print("\n" + "=" * 60)
    print("PHASE 1 COMPLETE - DISCOVERY RESULTS")
    print("=" * 60)

    print(f"\nBusiness: {client['company_name']}")
    print(f"Industry: {client['industry']}")
    print(f"Product: {client['product']}")
    print(f"Value Proposition: {client.get('value_proposition', 'N/A')}")

    print("\n--- Recommended ICP ---")
    icp = client.get('icp', {})
    print(f"Description: {icp.get('description', 'N/A')}")
    print(f"Company Size: {icp.get('company_size', 'N/A')}")
    print(f"Industries: {', '.join(icp.get('industries', []))}")
    print(f"Job Titles: {', '.join(icp.get('job_titles', []))}")
    print(f"Locations: {', '.join(icp.get('locations', []))}")

    print("\n--- Pain Points ---")
    for pain in icp.get('pain_points', []):
        print(f"  - {pain}")

    print("\n--- Apollo Filter Suggestions ---")
    print(f"person_titles: {json.dumps(apollo.get('person_titles', []))}")
    print(f"person_seniorities: {json.dumps(apollo.get('person_seniorities', []))}")
    print(f"organization_num_employees_ranges: {json.dumps(apollo.get('organization_num_employees_ranges', []))}")
    print(f"organization_locations: {json.dumps(apollo.get('organization_locations', []))}")
    print(f"industries: {json.dumps(apollo.get('industries', []))}")

    print("\n" + "=" * 60)
    print("ACTION REQUIRED")
    print("=" * 60)
    print("""
1. Review the ICP and Apollo filter suggestions above
2. Open Apollo.io and create a search using these filters
3. Copy the Apollo search URL
4. Run Phase 2-4 with:

   py execution/generate_sales_sample.py complete \\
       --prospect-url {url} \\
       --apollo-url "YOUR_APOLLO_URL_HERE"
""".format(url=client.get('website', '')))


def read_apollo_cookie_from_env():
    """Read Apollo cookie from .env file (handles multiline JSON)."""
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            env_content = f.read()

        # Find APOLLO_COOKIE=[...] in the file
        match = re.search(r'(?:^|\n)APOLLO_COOKIE=(\[.*?\n\])', env_content, re.DOTALL | re.MULTILINE)
        if match:
            cookie_str = match.group(1)
            try:
                return json.loads(cookie_str)
            except json.JSONDecodeError:
                import ast
                return ast.literal_eval(cookie_str)
        raise Exception("APOLLO_COOKIE not found in .env")
    except Exception as e:
        raise Exception(f"Failed to read Apollo cookie: {e}")


def read_apify_key_from_env():
    """Read Apify API key from .env file."""
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('APIFY_API_KEY='):
                    return line.split('=', 1)[1].strip()
    except:
        pass
    return os.getenv('APIFY_API_KEY')


def scrape_sample_leads_from_apollo(apollo_url, max_leads=100):
    """
    Phase 2: Scrape sample leads from Apollo using Olympus scraper.
    Returns: list of lead dicts
    """
    print("\n" + "=" * 60)
    print("PHASE 2: LEAD SAMPLING")
    print("=" * 60)
    print(f"Scraping up to {max_leads} sample leads from Apollo...")
    print()

    # Import Olympus scraper components
    try:
        from scraper_olympus_b2b_finder import (
            normalize_apollo_url,
            detect_country_from_url
        )
        from apify_client import ApifyClient
    except ImportError as e:
        raise Exception(f"Could not import Olympus scraper: {e}")

    # Get API key
    api_key = read_apify_key_from_env()
    if not api_key:
        raise Exception("APIFY_API_KEY not found in .env")

    # Load cookie from .env (handles multiline JSON)
    cookie = read_apollo_cookie_from_env()

    # Normalize URL and detect country
    apollo_url = normalize_apollo_url(apollo_url)
    country = detect_country_from_url(apollo_url)

    print(f"Detected country: {country}")
    print(f"Using Olympus B2B Finder scraper...")

    # Initialize Apify client
    client = ApifyClient(api_key)

    # Calculate pages needed (Apollo shows 25 leads per page)
    leads_per_page = 25
    pages_needed = (max_leads + leads_per_page - 1) // leads_per_page

    # Run the actor
    run_input = {
        "apolloUrl": apollo_url,
        "apolloCookie": cookie,
        "country": country,
        "startPageNumber": 1,
        "endPageNumber": pages_needed,
        "resultsPerPage": leads_per_page
    }

    print("Starting Apify actor run...")
    run = client.actor("olympus/b2b-leads-finder").call(run_input=run_input)

    # Fetch results
    leads = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        leads.append(item)
        if len(leads) >= max_leads:
            break

    print(f"Scraped {len(leads)} sample leads")

    # Normalize lead format
    normalized_leads = []
    for lead in leads:
        normalized_leads.append({
            'first_name': lead.get('firstName', ''),
            'last_name': lead.get('lastName', ''),
            'name': f"{lead.get('firstName', '')} {lead.get('lastName', '')}".strip(),
            'title': lead.get('title', ''),
            'email': lead.get('email', ''),
            'linkedin_url': lead.get('linkedinUrl', ''),
            'org_name': lead.get('organizationName', ''),
            'website_url': lead.get('organizationWebsite', ''),
            'city': lead.get('city', ''),
            'country': lead.get('country', ''),
        })

    return normalized_leads


def enrich_leads_for_sample(leads, api_key=None):
    """
    Phase 3: Enrich leads with website content and LinkedIn data.
    Returns: enriched leads list
    """
    print("\n" + "=" * 60)
    print("PHASE 3: ENRICHMENT")
    print("=" * 60)

    # Get Lead Magic API key
    if not api_key:
        api_key = os.getenv('LeadMagic-X-API-Key')
    if not api_key:
        print("WARNING: LeadMagic-X-API-Key not found - skipping LinkedIn enrichment")

    # Website enrichment
    print("\nEnriching company websites...")
    for i, lead in enumerate(leads):
        website = lead.get('website_url')
        if website:
            print(f"  [{i+1}/{len(leads)}] Scraping {website}")
            result = scrape_website(website)
            if result['success']:
                lead['website_content'] = result['content']
                print(f"       Extracted {len(result['content'])} chars")
            else:
                lead['website_content'] = ''
                print(f"       Failed: {result['error']}")
        else:
            lead['website_content'] = ''
            print(f"  [{i+1}/{len(leads)}] No website URL")

    # LinkedIn enrichment
    if api_key:
        print("\nEnriching LinkedIn profiles...")
        leads = enrich_linkedin_profiles(leads, api_key, force_regenerate=False, limit=None)
    else:
        print("\nSkipping LinkedIn enrichment (no API key)")

    return leads


def select_best_leads_for_personalization(leads, top_n=3):
    """
    Score and select the best leads for personalization based on enrichment quality.
    Leads with more/better enrichment data = better personalization opportunities.
    """
    print(f"\nScoring {len(leads)} leads for personalization potential...")

    scored_leads = []
    for lead in leads:
        score = 0
        reasons = []

        # Website content (0-30 points)
        website_len = len(lead.get('website_content', ''))
        if website_len > 2000:
            score += 30
            reasons.append(f"Rich website content ({website_len} chars)")
        elif website_len > 500:
            score += 15
            reasons.append(f"Some website content ({website_len} chars)")

        # LinkedIn bio (0-25 points)
        bio = lead.get('linkedin_bio', '')
        if len(bio) > 100:
            score += 25
            reasons.append(f"LinkedIn bio ({len(bio)} chars)")
        elif bio:
            score += 10
            reasons.append("Brief LinkedIn bio")

        # LinkedIn experience (0-25 points)
        experience = lead.get('linkedin_experience', [])
        if len(experience) >= 3:
            score += 25
            reasons.append(f"Rich work history ({len(experience)} positions)")
        elif experience:
            score += 10
            reasons.append(f"Some work history ({len(experience)} positions)")

        # LinkedIn headline (0-10 points)
        if lead.get('linkedin_headline'):
            score += 10
            reasons.append("Has LinkedIn headline")

        # Has email (0-10 points bonus)
        if lead.get('email'):
            score += 10
            reasons.append("Has email")

        scored_leads.append({
            'lead': lead,
            'score': score,
            'reasons': reasons
        })

    # Sort by score descending
    scored_leads.sort(key=lambda x: x['score'], reverse=True)

    # Print top leads
    print(f"\nTop {top_n} leads for personalization:")
    for i, sl in enumerate(scored_leads[:top_n], 1):
        lead = sl['lead']
        print(f"  {i}. {lead.get('name', 'Unknown')} @ {lead.get('org_name', 'Unknown')} (score: {sl['score']})")
        for reason in sl['reasons'][:3]:
            print(f"       - {reason}")

    return [sl['lead'] for sl in scored_leads[:top_n]]


def generate_email_sequence(discovery, reference_copies_path=None, ai_provider="openai"):
    """
    Generate a 3-email sequence template based on prospect's value proposition.
    Returns: dict with sequence data
    """
    client = discovery['client_data']

    # Load reference copies if provided
    reference_content = ""
    if reference_copies_path:
        emails_path = os.path.join(reference_copies_path, 'emails.json')
        if os.path.exists(emails_path):
            ref_data = load_json(emails_path)
            # Format for AI
            reference_content = "\n\nREFERENCE COPIES (use as tone/style guide):\n"
            for copy in ref_data.get('copies', [])[:5]:
                reference_content += f"\n---\nPosition: {copy.get('position')}\nSubject: {copy.get('subject')}\nBody:\n{copy.get('body')}\n---\n"

    prompt = f"""You are writing a cold email sequence for a B2B lead generation campaign.

CLIENT CONTEXT:
- Company: {client['company_name']}
- Product/Service: {client['product']}
- Value Proposition: {client.get('value_proposition', 'Not specified')}
- Target Audience: {client['icp'].get('description', 'Not specified')}
- Pain Points: {', '.join(client['icp'].get('pain_points', []))}
{reference_content}

Generate a 3-email sequence with the following structure:

EMAIL 1 (Initial - Day 0):
- Curiosity-driven subject line
- Opens with {{{{icebreaker}}}} placeholder
- Mentions a pain point
- Soft CTA (15-min call)

EMAIL 2 (Follow-up - Day 3):
- Reply-style subject (Re: ...)
- Case study or social proof
- Specific metric/result
- Direct CTA

EMAIL 3 (Breakup - Day 7):
- Short subject line
- Acknowledges no response
- Leaves door open
- Final CTA

Use these placeholders: {{{{first_name}}}}, {{{{company}}}}, {{{{icebreaker}}}}, {{{{industry}}}}, {{{{sender_name}}}}

Return as JSON:
{{
  "emails": [
    {{
      "position": "initial",
      "day": 0,
      "subject": "...",
      "body": "..."
    }},
    {{
      "position": "followup_1",
      "day": 3,
      "subject": "...",
      "body": "..."
    }},
    {{
      "position": "breakup",
      "day": 7,
      "subject": "...",
      "body": "..."
    }}
  ]
}}

Return ONLY the JSON, no other text."""

    # Call AI
    if ai_provider == "anthropic":
        result = _call_anthropic_for_emails(prompt)
    else:
        result = _call_openai_for_emails(prompt)

    return result


def generate_personalized_emails(leads, discovery, ai_provider="openai"):
    """
    Generate personalized first emails for each sample lead.
    Returns: list of personalized email dicts
    """
    client = discovery['client_data']
    personalized_emails = []

    for lead in leads:
        # Build context from enrichment
        context_parts = []

        # Website content
        if lead.get('website_content'):
            context_parts.append(f"Company website content:\n{lead['website_content'][:1000]}")

        # LinkedIn data
        if lead.get('linkedin_bio'):
            context_parts.append(f"LinkedIn bio: {lead['linkedin_bio']}")
        if lead.get('linkedin_headline'):
            context_parts.append(f"LinkedIn headline: {lead['linkedin_headline']}")
        if lead.get('linkedin_experience'):
            exp_text = "\n".join([
                f"- {e.get('title', '')} at {e.get('company', '')} ({e.get('period', '')})"
                for e in lead.get('linkedin_experience', [])[:3]
            ])
            context_parts.append(f"Work experience:\n{exp_text}")

        enrichment_context = "\n\n".join(context_parts) if context_parts else "Limited enrichment data available."

        prompt = f"""You are writing a personalized cold email for a B2B lead generation campaign.

CLIENT (who is sending):
- Company: {client['company_name']}
- Product/Service: {client['product']}
- Value Proposition: {client.get('value_proposition', 'Not specified')}

LEAD (who is receiving):
- Name: {lead.get('first_name', '')} {lead.get('last_name', '')}
- Title: {lead.get('title', '')}
- Company: {lead.get('org_name', '')}

ENRICHMENT DATA:
{enrichment_context}

Write a personalized first email with:
1. A "super interesting" icebreaker that references SPECIFIC details from the enrichment data
2. Connect their situation to the client's value proposition
3. Keep it under 150 words
4. End with a soft CTA (15-min call)

The icebreaker MUST be specific and interesting, NOT generic like:
- BAD: "I saw your company is in the tech industry"
- BAD: "I noticed you're the CEO"
- GOOD: "I noticed you just launched your new analytics platform - the real-time dashboard feature caught my eye"
- GOOD: "Your 12 years scaling marketing teams, from Google to now leading growth at DataFlow, is impressive"

Return as JSON:
{{
  "subject": "Short, personalized subject line",
  "body": "Full email body",
  "icebreaker_used": "The specific icebreaker line you used",
  "personalization_source": "What data you used (website, LinkedIn bio, experience, etc.)"
}}

Return ONLY the JSON, no other text."""

        # Call AI
        if ai_provider == "anthropic":
            result = _call_anthropic_for_emails(prompt)
        else:
            result = _call_openai_for_emails(prompt)

        result['lead_name'] = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
        result['lead_company'] = lead.get('org_name', '')
        personalized_emails.append(result)

    return personalized_emails


def _call_openai_for_emails(prompt):
    """Call OpenAI API for email generation."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env")

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2000
        },
        timeout=60
    )

    if response.status_code != 200:
        raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")

    result = response.json()
    content = result['choices'][0]['message']['content']

    # Parse JSON
    try:
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse AI response as JSON: {e}\nResponse: {content}")


def _call_anthropic_for_emails(prompt):
    """Call Anthropic API for email generation."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in .env")

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        },
        json={
            "model": "claude-3-haiku-20240307",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=60
    )

    if response.status_code != 200:
        raise Exception(f"Anthropic API error: {response.status_code} - {response.text}")

    result = response.json()
    content = result['content'][0]['text']

    # Parse JSON
    try:
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse AI response as JSON: {e}\nResponse: {content}")


def generate_sample_report(discovery, leads, email_sequence, personalized_emails, output_path):
    """
    Generate the final markdown report.
    """
    client = discovery['client_data']
    icp = client.get('icp', {})
    apollo = client.get('apollo_filters', {})

    report = f"""# Sales Sample: {client['company_name']}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 1. Business Analysis

| Field | Value |
|-------|-------|
| **Company** | {client['company_name']} |
| **Industry** | {client['industry']} |
| **Product/Service** | {client['product']} |
| **Value Proposition** | {client.get('value_proposition', 'N/A')} |
| **Website** | {client.get('website', '')} |

### Target Audience Analysis

{icp.get('description', 'Not specified')}

### Pain Points
{chr(10).join(['- ' + p for p in icp.get('pain_points', ['Not identified'])])}

### Buying Signals
{chr(10).join(['- ' + s for s in icp.get('buying_signals', ['Not identified'])])}

---

## 2. Recommended ICP

| Filter | Suggestion |
|--------|------------|
| **Job Titles** | {', '.join(icp.get('job_titles', []))} |
| **Company Size** | {icp.get('company_size', 'N/A')} |
| **Industries** | {', '.join(icp.get('industries', []))} |
| **Locations** | {', '.join(icp.get('locations', []))} |

### Apollo Filter Suggestions

```json
{{
  "person_titles": {json.dumps(apollo.get('person_titles', []))},
  "person_seniorities": {json.dumps(apollo.get('person_seniorities', []))},
  "organization_num_employees_ranges": {json.dumps(apollo.get('organization_num_employees_ranges', []))},
  "organization_locations": {json.dumps(apollo.get('organization_locations', []))},
  "industries": {json.dumps(apollo.get('industries', []))}
}}
```

---

## 3. Sample Leads

"""

    # Add each lead
    for i, lead in enumerate(leads, 1):
        report += f"""### Lead {i}: {lead.get('first_name', '')} {lead.get('last_name', '')} - {lead.get('org_name', '')}

| Field | Value |
|-------|-------|
| **Name** | {lead.get('name', '')} |
| **Title** | {lead.get('title', '')} |
| **Company** | {lead.get('org_name', '')} |
| **Email** | {lead.get('email', 'N/A')} |
| **LinkedIn** | {lead.get('linkedin_url', 'N/A')} |
| **Location** | {lead.get('city', '')}, {lead.get('country', '')} |

**Enrichment Data:**
"""
        if lead.get('website_content'):
            report += f"- **Company Website:** {len(lead['website_content'])} chars extracted\n"
        if lead.get('linkedin_bio'):
            report += f"- **LinkedIn Bio:** {lead['linkedin_bio'][:200]}...\n"
        if lead.get('linkedin_headline'):
            report += f"- **LinkedIn Headline:** {lead['linkedin_headline']}\n"
        if lead.get('linkedin_tenure_years'):
            report += f"- **Tenure:** {lead['linkedin_tenure_years']} years experience\n"
        if lead.get('linkedin_experience'):
            report += "- **Recent Experience:**\n"
            for exp in lead.get('linkedin_experience', [])[:2]:
                report += f"  - {exp.get('title', '')} at {exp.get('company', '')} ({exp.get('period', '')})\n"

        report += "\n"

    # Email sequence template
    report += """---

## 4. Email Sequence Template

"""
    if email_sequence and 'emails' in email_sequence:
        for email in email_sequence['emails']:
            report += f"""### Email: {email.get('position', 'Unknown').replace('_', ' ').title()} (Day {email.get('day', 0)})

**Subject:** {email.get('subject', '')}

```
{email.get('body', '')}
```

"""

    # Personalized emails
    report += """---

## 5. Personalized Sample Emails

"""
    for pe in personalized_emails:
        report += f"""### For {pe.get('lead_name', 'Unknown')} ({pe.get('lead_company', '')})

**Subject:** {pe.get('subject', '')}

```
{pe.get('body', '')}
```

**Personalization source:** {pe.get('personalization_source', 'N/A')}

---

"""

    # Next steps
    report += """## 6. Next Steps

1. **Review this sample** and provide feedback on tone, approach, and personalization quality
2. **If interested**, we'll run a full campaign with your target lead count
3. **Typical timeline:** Campaign setup in 1-2 days, leads delivered within a week

---

*Generated by Sales Sample Generator*
"""

    # Write report
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    return output_path


def main():
    parser = argparse.ArgumentParser(description='Sales Sample Generator')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Phase 1 command
    phase1_parser = subparsers.add_parser('phase1', help='Run discovery phase only')
    phase1_parser.add_argument('--prospect-url', required=True, help='Prospect website URL')
    phase1_parser.add_argument('--notes', default='', help='Additional notes about the prospect')
    phase1_parser.add_argument('--ai-provider', choices=['openai', 'anthropic'], default='openai')
    phase1_parser.add_argument('--output-dir', default=DEFAULT_OUTPUT_DIR, help='Output directory')

    # Complete command
    complete_parser = subparsers.add_parser('complete', help='Run full sample generation')
    complete_parser.add_argument('--prospect-url', required=True, help='Prospect website URL')
    complete_parser.add_argument('--apollo-url', required=True, help='Apollo search URL for sample leads')
    complete_parser.add_argument('--notes', default='', help='Additional notes about the prospect')
    complete_parser.add_argument('--reference-copies', default=None, help='Path to reference copies folder')
    complete_parser.add_argument('--ai-provider', choices=['openai', 'anthropic'], default='openai')
    complete_parser.add_argument('--output-dir', default=DEFAULT_OUTPUT_DIR, help='Output directory')
    complete_parser.add_argument('--max-leads', type=int, default=MAX_SAMPLE_LEADS, help='Max sample leads')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    try:
        if args.command == 'phase1':
            # Phase 1 only
            url = clean_url(args.prospect_url)
            discovery = run_phase1_discovery(url, args.notes, args.ai_provider)
            print_phase1_results(discovery)

            # Save discovery to file for later use
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            discovery_path = os.path.join(args.output_dir, f"discovery_{timestamp}.json")
            # Exclude large content from saved file
            save_data = {
                'client_data': discovery['client_data'],
                'analysis': discovery['analysis']
            }
            save_json(save_data, discovery_path)
            print(f"\nDiscovery saved to: {discovery_path}")

            return 0

        elif args.command == 'complete':
            # Full workflow
            url = clean_url(args.prospect_url)

            # Phase 1: Discovery
            discovery = run_phase1_discovery(url, args.notes, args.ai_provider)
            print_phase1_results(discovery)

            # Phase 2: Lead sampling
            leads = scrape_sample_leads_from_apollo(args.apollo_url, args.max_leads)

            if not leads:
                print("\nERROR: No leads found. Check your Apollo URL and try again.")
                return 1

            # Phase 3: Enrichment
            leads = enrich_leads_for_sample(leads)

            # Phase 4: Lead selection + Email generation
            print("\n" + "=" * 60)
            print("PHASE 4: LEAD SELECTION + EMAIL GENERATION")
            print("=" * 60)

            # Select best leads for personalization
            best_leads = select_best_leads_for_personalization(leads, top_n=3)

            print("\nGenerating email sequence template...")
            email_sequence = generate_email_sequence(discovery, args.reference_copies, args.ai_provider)

            print("Generating personalized emails for top 3 leads...")
            personalized_emails = generate_personalized_emails(best_leads, discovery, args.ai_provider)

            # Generate report
            print("\nGenerating final report...")
            company_name = discovery['client_data']['company_name']
            safe_name = re.sub(r'[^a-zA-Z0-9]', '_', company_name).lower()[:30]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = os.path.join(args.output_dir, f"sample_{safe_name}_{timestamp}.md")

            generate_sample_report(discovery, leads, email_sequence, personalized_emails, report_path)

            print("\n" + "=" * 60)
            print("SAMPLE GENERATION COMPLETE")
            print("=" * 60)
            print(f"\nReport saved to: {report_path}")
            print(f"\nTotal leads sampled: {len(leads)}")
            print(f"Personalized emails generated: {len(personalized_emails)}")

            return 0

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

# [CLI] — run via: py execution/client_discovery.py --help
"""
Client Discovery - AI-powered website analysis for ICP generation.
Analyzes client websites to generate recommended Ideal Customer Profile and Apollo filters.

Usage:
    py execution/client_discovery.py --url https://example.com
    py execution/client_discovery.py --url https://example.com --email contact@example.com --notes "B2B SaaS"
"""

import os
import sys
import json
import argparse
import requests
import re
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import save_json

# Page patterns to try for each section
PAGE_PATTERNS = {
    'home': ['/'],
    'about': ['/about', '/about-us', '/company', '/o-nas', '/par-mums', '/uber-uns', '/qui-sommes-nous'],
    'services': ['/services', '/solutions', '/what-we-do', '/pakalpojumi', '/dienstleistungen', '/our-services'],
    'case_studies': ['/case-studies', '/work', '/portfolio', '/clients', '/projects', '/success-stories'],
    'team': ['/team', '/leadership', '/our-team', '/about-us#team', '/about#team']
}

# Max content per page
MAX_CONTENT_PER_PAGE = 3000
MAX_TOTAL_CONTENT = 10000


def clean_url(url):
    """Normalize and validate URL."""
    if not url:
        return None
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def get_base_domain(url):
    """Extract base domain from URL."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def extract_text_content(soup, max_chars=3000):
    """Extract meaningful text content from BeautifulSoup object."""
    # Remove non-content elements
    for tag in soup(['script', 'style', 'noscript', 'iframe', 'nav', 'footer', 'header']):
        tag.decompose()

    text_parts = []

    # Priority selectors
    priority_selectors = [
        'h1', 'h2', 'h3',
        '[class*="hero"]', '[class*="headline"]', '[class*="banner"]',
        '[class*="about"]', '[id*="about"]',
        '[class*="service"]', '[class*="solution"]',
        'main', '[role="main"]', 'article',
        '.content', '#content', '[class*="content"]'
    ]

    for selector in priority_selectors:
        try:
            elements = soup.select(selector)
            for el in elements[:5]:
                text = el.get_text(strip=True, separator=' ')
                if text and len(text) > 20:
                    text_parts.append(text)
        except Exception:
            continue

    # Combine and clean
    combined = ' '.join(text_parts)
    combined = ' '.join(combined.split())  # Normalize whitespace

    # Truncate
    if len(combined) > max_chars:
        combined = combined[:max_chars]

    return combined


def scrape_page(url, timeout=30):
    """Scrape a single page and return its content."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            content = extract_text_content(soup)
            return {'success': True, 'content': content, 'url': response.url}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}', 'url': url}

    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'timeout', 'url': url}
    except requests.exceptions.ConnectionError:
        return {'success': False, 'error': 'connection_error', 'url': url}
    except Exception as e:
        return {'success': False, 'error': str(e), 'url': url}


def scrape_website_multi_page(base_url):
    """Scrape multiple pages from a website."""
    base_domain = get_base_domain(base_url)
    results = {}
    total_content = ""

    print(f"Scraping website: {base_domain}")
    print()

    for section, patterns in PAGE_PATTERNS.items():
        # Stop if we have enough content
        if len(total_content) >= MAX_TOTAL_CONTENT:
            print(f"  [{section}] Skipped (content limit reached)")
            continue

        # Try each pattern until one succeeds
        for pattern in patterns:
            url = urljoin(base_domain, pattern)
            result = scrape_page(url)

            if result['success'] and result['content']:
                # Truncate if needed
                remaining = MAX_TOTAL_CONTENT - len(total_content)
                content = result['content'][:min(MAX_CONTENT_PER_PAGE, remaining)]

                results[section] = {
                    'url': result['url'],
                    'content': content,
                    'chars': len(content)
                }
                total_content += f"\n\n=== {section.upper()} PAGE ===\n{content}"
                print(f"  [{section}] Scraped {len(content)} chars from {pattern}")
                break
        else:
            print(f"  [{section}] No content found")
            results[section] = {'url': None, 'content': '', 'chars': 0}

    print(f"\nTotal content scraped: {len(total_content)} chars from {sum(1 for r in results.values() if r['content'])} pages")

    return results, total_content


def analyze_with_ai(content, notes="", ai_provider="openai"):
    """Send content to AI for analysis."""
    prompt = f"""You are analyzing a company's website to help create a lead generation strategy for THEIR sales team.

Website Content:
{content}

Additional Notes: {notes if notes else "None provided"}

CRITICAL INSTRUCTION - BUYER vs PEER INDUSTRIES:
The "target_industries" and Apollo "industries" fields must contain industries of companies that would BUY FROM this company - NOT similar/peer companies.

Example of WRONG thinking:
- Company: Software development agency
- WRONG target industries: "Software Development", "IT Services" (these are peers/competitors)
- CORRECT target industries: "iGaming", "Financial Services", "Media & Entertainment", "Healthcare" (these are BUYERS)

Example of CORRECT thinking:
- Company: Marketing agency
- Their customers are companies that NEED marketing help (retailers, SaaS, manufacturers)
- NOT other marketing agencies

Ask yourself: "What types of companies would HIRE this company's services or BUY their product?"

Analyze this company and provide a structured JSON response:

{{
  "company_analysis": {{
    "company_name": "Extracted or inferred company name",
    "industry": "Primary industry of THIS company (e.g., 'Software Development', 'Digital Marketing')",
    "business_model": "B2B / B2C / Both",
    "product_service": "Brief description of what they sell/offer (1-2 sentences)",
    "value_proposition": "Their main differentiator or promise to customers",
    "company_size_estimate": "Startup / Small (1-50) / Medium (51-200) / Large (200+)",
    "geographic_focus": ["Country 1", "Country 2"],
    "verticals_served": ["Industry 1", "Industry 2", "Industry 3"]
  }},
  "ideal_customer_profile": {{
    "description": "2-3 sentence description of ideal customer (who BUYS from this company)",
    "target_company_size": "e.g., '51-200 employees' or '11-50 employees'",
    "target_industries": ["BUYER Industry 1", "BUYER Industry 2", "BUYER Industry 3"],
    "target_job_titles": ["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"],
    "target_locations": ["Country/Region 1", "Country/Region 2"],
    "pain_points": ["Pain point 1", "Pain point 2", "Pain point 3"],
    "buying_signals": ["Signal 1", "Signal 2"]
  }},
  "apollo_filter_suggestions": {{
    "person_titles": ["CTO", "CEO", "VP Engineering"],
    "person_seniorities": ["owner", "c_suite", "vp", "director", "manager"],
    "organization_num_employees_ranges": ["11-20", "21-50", "51-100", "101-200"],
    "organization_locations": ["Latvia", "Lithuania", "Estonia"],
    "industries": ["BUYER industries - companies that would HIRE/BUY from this company"],
    "keywords": ["relevant business keywords for buyer companies"]
  }},
  "confidence_score": 0.85,
  "notes": "Any caveats or areas of uncertainty"
}}

REMEMBER: Industries must be BUYER industries, not peer industries. A software dev shop's customers are iGaming operators, banks, media companies - NOT other dev shops.

Return ONLY the JSON, no other text or markdown formatting."""

    if ai_provider == "anthropic":
        return _call_anthropic(prompt)
    else:
        return _call_openai(prompt)


def _call_openai(prompt):
    """Call OpenAI API."""
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
            "temperature": 0.3,
            "max_tokens": 2000
        },
        timeout=60
    )

    if response.status_code != 200:
        raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")

    result = response.json()
    content = result['choices'][0]['message']['content']

    # Parse JSON from response
    try:
        # Try to extract JSON if wrapped in markdown
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse AI response as JSON: {e}\nResponse: {content}")


def _call_anthropic(prompt):
    """Call Anthropic API."""
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

    # Parse JSON from response
    try:
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse AI response as JSON: {e}\nResponse: {content}")


def generate_client_id(company_name):
    """Generate a clean client_id from company name."""
    # Remove special characters, convert to lowercase, replace spaces with underscores
    client_id = re.sub(r'[^a-zA-Z0-9\s]', '', company_name)
    client_id = client_id.lower().strip().replace(' ', '_')
    # Limit length
    client_id = client_id[:30]
    return client_id


def create_client_json(analysis, url, email=None):
    """Create client.json structure from AI analysis."""
    company = analysis.get('company_analysis', {})
    icp = analysis.get('ideal_customer_profile', {})
    apollo = analysis.get('apollo_filter_suggestions', {})

    company_name = company.get('company_name', 'Unknown')
    client_id = generate_client_id(company_name)

    client_data = {
        "client_id": client_id,
        "company_name": company_name,
        "contact_email": email or "",
        "website": url,
        "industry": company.get('industry', ''),
        "product": company.get('product_service', ''),
        "business_model": company.get('business_model', 'B2B'),
        "value_proposition": company.get('value_proposition', ''),
        "icp": {
            "description": icp.get('description', ''),
            "job_titles": icp.get('target_job_titles', []),
            "company_size": icp.get('target_company_size', ''),
            "industries": icp.get('target_industries', []),
            "locations": icp.get('target_locations', []),
            "pain_points": icp.get('pain_points', []),
            "buying_signals": icp.get('buying_signals', [])
        },
        "apollo_filters": {
            "person_titles": apollo.get('person_titles', []),
            "person_seniorities": apollo.get('person_seniorities', []),
            "organization_num_employees_ranges": apollo.get('organization_num_employees_ranges', []),
            "organization_locations": apollo.get('organization_locations', []),
            "industries": apollo.get('industries', []),
            "keywords": apollo.get('keywords', [])
        },
        "discovery": {
            "source": "ai_analysis",
            "analyzed_at": datetime.now(timezone.utc).isoformat() + 'Z',
            "confidence": analysis.get('confidence_score', 0.0),
            "notes": analysis.get('notes', '')
        },
        "created_at": datetime.now(timezone.utc).isoformat() + 'Z',
        "updated_at": datetime.now(timezone.utc).isoformat() + 'Z',
        "campaigns": []
    }

    return client_data


def generate_report(client_data, scrape_results):
    """Generate a markdown discovery report."""
    icp = client_data.get('icp', {})
    apollo = client_data.get('apollo_filters', {})
    discovery = client_data.get('discovery', {})

    pages_scraped = sum(1 for r in scrape_results.values() if r.get('content'))

    report = f"""# Client Discovery Report: {client_data['company_name']}

## Company Analysis
- **Industry:** {client_data.get('industry', 'Unknown')}
- **Business Model:** {client_data.get('business_model', 'Unknown')}
- **Product/Service:** {client_data.get('product', 'Unknown')}
- **Value Proposition:** {client_data.get('value_proposition', 'Unknown')}
- **Website:** {client_data.get('website', '')}

## Recommended ICP
- **Target Companies:** {icp.get('description', 'Not specified')}
- **Company Size:** {icp.get('company_size', 'Not specified')}
- **Industries:** {', '.join(icp.get('industries', []))}
- **Decision Makers:** {', '.join(icp.get('job_titles', []))}
- **Locations:** {', '.join(icp.get('locations', []))}

### Pain Points
{chr(10).join(['- ' + p for p in icp.get('pain_points', ['Not identified'])])}

### Buying Signals
{chr(10).join(['- ' + s for s in icp.get('buying_signals', ['Not identified'])])}

## Apollo Filter Suggestions

### Person Filters
- **Titles:** {', '.join(apollo.get('person_titles', []))}
- **Seniorities:** {', '.join(apollo.get('person_seniorities', []))}

### Organization Filters
- **Employee Ranges:** {', '.join(apollo.get('organization_num_employees_ranges', []))}
- **Locations:** {', '.join(apollo.get('organization_locations', []))}
- **Industries:** {', '.join(apollo.get('industries', []))}

### Keywords
{', '.join(apollo.get('keywords', []))}

## Confidence: {int(discovery.get('confidence', 0) * 100)}%

## Notes
{discovery.get('notes', 'None')}

---
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Pages analyzed: {pages_scraped} ({', '.join([k for k, v in scrape_results.items() if v.get('content')])})
"""

    return report


def main():
    parser = argparse.ArgumentParser(description='Client Discovery - AI-powered website analysis')
    parser.add_argument('--url', required=True, help='Client website URL')
    parser.add_argument('--email', default='', help='Client contact email')
    parser.add_argument('--notes', default='', help='Additional notes about the client')
    parser.add_argument('--ai-provider', choices=['openai', 'anthropic'], default='openai', help='AI provider to use')
    parser.add_argument('--auto-save', action='store_true', help='Automatically save without confirmation')
    parser.add_argument('--output-dir', default='campaigns', help='Base output directory')

    args = parser.parse_args()

    # Clean URL
    url = clean_url(args.url)
    if not url:
        print("Error: Invalid URL provided", file=sys.stderr)
        return 1

    print("=" * 60)
    print("CLIENT DISCOVERY")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"AI Provider: {args.ai_provider}")
    print()

    try:
        # Step 1: Scrape website
        print("STEP 1: Scraping website...")
        print("-" * 40)
        scrape_results, total_content = scrape_website_multi_page(url)

        if not total_content or len(total_content) < 100:
            print("\nError: Could not extract enough content from website", file=sys.stderr)
            print("Try checking if the website is accessible and has text content.")
            return 1

        # Step 2: AI Analysis
        print("\nSTEP 2: Analyzing with AI...")
        print("-" * 40)
        analysis = analyze_with_ai(total_content, args.notes, args.ai_provider)
        print(f"Analysis complete. Confidence: {analysis.get('confidence_score', 0) * 100:.0f}%")

        # Step 3: Generate client data
        print("\nSTEP 3: Generating client profile...")
        print("-" * 40)
        client_data = create_client_json(analysis, url, args.email)
        client_id = client_data['client_id']

        # Step 4: Generate report
        report = generate_report(client_data, scrape_results)

        # Display results
        print("\n" + "=" * 60)
        print("DISCOVERY RESULTS")
        print("=" * 60)
        print(f"\nCompany: {client_data['company_name']}")
        print(f"Client ID: {client_id}")
        print(f"Industry: {client_data['industry']}")
        print(f"Product: {client_data['product']}")
        print(f"\nICP Summary:")
        print(f"  - Description: {client_data['icp']['description'][:100]}...")
        print(f"  - Target Titles: {', '.join(client_data['icp']['job_titles'][:3])}...")
        print(f"  - Locations: {', '.join(client_data['icp']['locations'])}")
        print(f"\nConfidence: {client_data['discovery']['confidence'] * 100:.0f}%")

        # Step 5: Save files
        client_dir = os.path.join(args.output_dir, client_id)
        os.makedirs(client_dir, exist_ok=True)
        os.makedirs(os.path.join(client_dir, 'apollo_lists'), exist_ok=True)
        os.makedirs(os.path.join(client_dir, 'google_maps_lists'), exist_ok=True)

        # Save draft client.json
        draft_path = os.path.join(client_dir, 'client_draft.json')
        save_json(client_data, draft_path)
        print(f"\nDraft saved: {draft_path}")

        # Save report
        report_path = os.path.join(client_dir, 'discovery_report.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report saved: {report_path}")

        # Auto-save or prompt
        if args.auto_save:
            # Copy draft to final
            final_path = os.path.join(client_dir, 'client.json')
            save_json(client_data, final_path)
            print(f"\nClient activated: {final_path}")
        else:
            print("\n" + "-" * 40)
            print("NEXT STEPS:")
            print(f"1. Review the draft: {draft_path}")
            print(f"2. Review the report: {report_path}")
            print("3. Make any needed edits to the draft")
            print(f"4. When ready, rename to client.json or run:")
            print(f"   py execution/client_manager.py approve {client_id}")

        return 0

    except Exception as e:
        print(f"\nError during discovery: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

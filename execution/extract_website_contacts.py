# [CLI] — run via: py execution/extract_website_contacts.py --help
#!/usr/bin/env python3
"""
Website Contact Extractor
Scrapes a business website and uses Claude to extract structured contact information
"""

import os
import re
import json
import argparse
import time
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
import httpx
import html2text
from anthropic import Anthropic
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Lazy-initialized client (avoids crash on import if API key is missing)
_anthropic_client = None

def get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _anthropic_client

# Contact page patterns (priority order)
CONTACT_PATTERNS = [
    "/contact", "/about", "/team", "/contact-us", "/about-us", "/our-team",
    "/staff", "/people", "/meet-the-team", "/leadership", "/management",
    "/founders", "/who-we-are", "/company", "/meet-us", "/our-story",
    "/the-team", "/employees", "/directory", "/locations", "/offices"
]

# HTTP client settings
HTTP_TIMEOUT = 10.0
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Content limits
MAX_CONTENT_LENGTH = 50000  # Truncate content to 50K chars
MAX_CONTACT_PAGES = 5


def stringify_value(value):
    """Convert any value to a string, handling dicts and lists"""
    if isinstance(value, dict):
        return json.dumps(value)
    elif isinstance(value, list):
        return ", ".join(str(v) for v in value)
    elif value is None:
        return ""
    return str(value)


def fetch_url(url: str, timeout: float = HTTP_TIMEOUT) -> Optional[str]:
    """
    Fetch a URL and return its HTML content
    Handles errors gracefully (403, 503, DNS errors, etc.)
    """
    try:
        headers = {"User-Agent": USER_AGENT}
        response = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code in [403, 503]:
            print(f"  [WARN] HTTP {e.response.status_code} for {url}")
        else:
            print(f"  [WARN] HTTP error {e.response.status_code} for {url}")
        return None
    except httpx.TimeoutException:
        print(f"  [WARN] Timeout fetching {url}")
        return None
    except Exception as e:
        print(f"  [WARN] Error fetching {url}: {str(e)[:100]}")
        return None


def html_to_markdown(html: str) -> str:
    """Convert HTML to clean markdown text"""
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    converter.ignore_emphasis = False
    converter.body_width = 0  # Don't wrap lines
    return converter.handle(html)


def find_contact_pages(base_url: str, html: str, max_pages: int = MAX_CONTACT_PAGES) -> List[str]:
    """
    Find contact-related pages from the HTML content
    Returns up to max_pages URLs matching contact patterns
    """
    soup = BeautifulSoup(html, 'html.parser')
    found_urls: Set[str] = set()

    # Find all links
    for link in soup.find_all('a', href=True):
        href = link['href'].lower()

        # Check if the link matches any contact pattern
        for pattern in CONTACT_PATTERNS:
            if pattern in href:
                full_url = urljoin(base_url, link['href'])
                # Ensure it's the same domain
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    found_urls.add(full_url)
                    break

        if len(found_urls) >= max_pages:
            break

    return list(found_urls)[:max_pages]


def search_duckduckgo(query: str) -> Dict[str, any]:
    """
    Search DuckDuckGo and return snippets + first relevant result page
    Uses the HTML version (html.duckduckgo.com) which doesn't require API or block
    """
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={query}"
        headers = {"User-Agent": USER_AGENT}

        response = httpx.get(search_url, headers=headers, timeout=HTTP_TIMEOUT, follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract search result snippets
        snippets = []
        results = soup.find_all('div', class_='result')[:3]  # Get top 3 results

        for result in results:
            snippet_elem = result.find('a', class_='result__snippet')
            if snippet_elem:
                snippets.append(snippet_elem.get_text(strip=True))

        # Get first result URL and fetch its content
        first_result_url = None
        first_result_content = None

        if results:
            first_link = results[0].find('a', class_='result__url')
            if first_link and first_link.get('href'):
                # DuckDuckGo uses redirect URLs, extract the actual URL
                redirect_url = first_link['href']
                if 'uddg=' in redirect_url:
                    # Extract actual URL from redirect
                    actual_url = redirect_url.split('uddg=')[1].split('&')[0]
                    from urllib.parse import unquote
                    first_result_url = unquote(actual_url)

                    # Skip Facebook URLs (always return 400)
                    if 'facebook.com' not in first_result_url:
                        html_content = fetch_url(first_result_url)
                        if html_content:
                            first_result_content = html_to_markdown(html_content)

        return {
            "snippets": snippets,
            "first_result_url": first_result_url,
            "first_result_content": first_result_content
        }

    except Exception as e:
        print(f"  [WARN] DuckDuckGo search failed: {str(e)[:100]}")
        return {"snippets": [], "first_result_url": None, "first_result_content": None}


def extract_contacts_with_claude(
    business_name: str,
    main_page_content: str,
    contact_pages_content: List[str],
    search_results: Dict
) -> Dict:
    """
    Use Claude 3.5 Haiku to extract structured contact information
    """
    # Combine all content
    all_content = f"# Main Website Page\n\n{main_page_content}\n\n"

    if contact_pages_content:
        all_content += "# Additional Contact Pages\n\n"
        for i, content in enumerate(contact_pages_content, 1):
            all_content += f"## Page {i}\n\n{content}\n\n"

    if search_results.get("snippets"):
        all_content += "# Web Search Results\n\n"
        all_content += "\n".join(f"- {s}" for s in search_results["snippets"])
        all_content += "\n\n"

    if search_results.get("first_result_content"):
        all_content += f"# First Search Result Content\n\n{search_results['first_result_content']}\n\n"

    # Truncate if too long
    if len(all_content) > MAX_CONTENT_LENGTH:
        all_content = all_content[:MAX_CONTENT_LENGTH] + "\n\n[Content truncated...]"

    # Create prompt for Claude
    prompt = f"""You are extracting contact information from a business website and search results.

Business Name: {business_name}

Extract the following information in JSON format:

{{
  "emails": ["list of all email addresses found"],
  "phone_numbers": ["list of all phone numbers found"],
  "addresses": ["physical addresses found"],
  "social_media": {{
    "facebook": "url or null",
    "twitter": "url or null",
    "linkedin": "url or null",
    "instagram": "url or null",
    "youtube": "url or null",
    "tiktok": "url or null"
  }},
  "owner_info": {{
    "name": "owner/founder name or null",
    "title": "their position or null",
    "email": "direct email if found or null",
    "phone": "direct phone if found or null",
    "linkedin": "personal linkedin or null"
  }},
  "team_members": [
    {{"name": "person name", "title": "their title", "email": "email or null", "phone": "phone or null", "linkedin": "linkedin or null"}}
  ],
  "business_hours": "operating hours as string or null",
  "additional_contacts": ["other contact methods like WhatsApp, Calendly, etc."]
}}

Rules:
- Return ONLY valid JSON, no other text
- Use null for missing values, not empty strings
- For business_hours, return a simple string like "Mon-Fri 9am-5pm" or null
- Normalize phone numbers to readable format
- Extract all emails and phones you can find
- If you find multiple team members, include them all
- If no owner info is found, return null for all owner_info fields

Website and Search Content:

{all_content}
"""

    try:
        response = get_anthropic_client().messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract JSON from response
        response_text = response.content[0].text.strip()

        # Handle markdown code blocks — search for ```json first, then try each block
        if "```" in response_text:
            blocks = response_text.split("```")
            parsed = None
            # First pass: look for a block that starts with "json"
            for block in blocks[1::2]:  # odd-indexed elements are inside fences
                if block.startswith("json"):
                    try:
                        parsed = json.loads(block[4:].strip())
                        break
                    except json.JSONDecodeError:
                        continue
            # Second pass: try every fenced block as raw JSON
            if parsed is None:
                for block in blocks[1::2]:
                    candidate = block.strip()
                    # Strip optional language tag on first line
                    if candidate and not candidate.startswith("{"):
                        candidate = candidate.split("\n", 1)[-1].strip()
                    try:
                        parsed = json.loads(candidate)
                        break
                    except json.JSONDecodeError:
                        continue
            if parsed is not None:
                response_text = json.dumps(parsed)  # re-serialize so the json.loads below works cleanly
            # If no block parsed, fall through and let json.loads raise on the raw text

        result = json.loads(response_text)

        # Stringify any dict/list values (like business_hours)
        if "business_hours" in result:
            result["business_hours"] = stringify_value(result["business_hours"])

        return result

    except Exception as e:
        print(f"  [ERROR] Claude extraction failed: {str(e)}")
        return {
            "emails": [],
            "phone_numbers": [],
            "addresses": [],
            "social_media": {},
            "owner_info": {},
            "team_members": [],
            "business_hours": None,
            "additional_contacts": []
        }


def extract_website_contacts(website_url: str, business_name: str) -> Dict:
    """
    Main function to extract contacts from a website

    Args:
        website_url: The business website URL
        business_name: The business name (for search context)

    Returns:
        Dictionary with extracted contact information and metadata
    """
    print(f"\n[INFO] Extracting contacts from: {website_url}")

    result = {
        "website": website_url,
        "enrichment_status": "pending",
        "pages_scraped": 0,
        "search_enriched": False,
        "extracted_data": {}
    }

    # Fetch main page
    print("  [1/3] Fetching main page...")
    main_html = fetch_url(website_url)
    if not main_html:
        result["enrichment_status"] = "error: failed to fetch main page"
        return result

    main_content = html_to_markdown(main_html)
    result["pages_scraped"] = 1

    # Find and fetch contact pages
    print("  [2/3] Finding contact pages...")
    contact_urls = find_contact_pages(website_url, main_html)
    contact_pages_content = []

    for url in contact_urls:
        print(f"    - Fetching: {url}")
        html = fetch_url(url)
        if html:
            contact_pages_content.append(html_to_markdown(html))
            result["pages_scraped"] += 1
            time.sleep(0.5)  # Be polite

    # Search for owner/contact info (DISABLED - DuckDuckGo blocks 90%+ of requests)
    # print("  [3/4] Searching for owner info...")
    # search_query = f'"{business_name}" owner email contact'
    # search_results = search_duckduckgo(search_query)
    # result["search_enriched"] = bool(search_results.get("snippets"))

    # Skip DuckDuckGo search to save time (failing with 403 errors)
    search_results = {"snippets": [], "first_result_url": None, "first_result_content": None}
    result["search_enriched"] = False

    # Extract with Claude
    print("  [3/3] Extracting contacts with Claude...")
    extracted = extract_contacts_with_claude(
        business_name,
        main_content,
        contact_pages_content,
        search_results
    )

    result["extracted_data"] = extracted
    result["enrichment_status"] = "success"

    print("  [OK] Contact extraction complete")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Extract contact information from a business website"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Business website URL"
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Business name (for search context)"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file path (optional)"
    )

    args = parser.parse_args()

    # Extract contacts
    result = extract_website_contacts(args.url, args.name)

    # Print results
    print("\n" + "="*60)
    print("EXTRACTION RESULTS")
    print("="*60)
    print(f"Status: {result['enrichment_status']}")
    print(f"Pages scraped: {result['pages_scraped']}")
    print(f"Search enriched: {result['search_enriched']}")
    print()

    if result["extracted_data"]:
        data = result["extracted_data"]

        print(f"Emails: {', '.join(data.get('emails', [])) or 'None'}")
        print(f"Phone numbers: {', '.join(data.get('phone_numbers', [])) or 'None'}")
        print(f"Business hours: {data.get('business_hours') or 'None'}")
        print()

        if data.get("owner_info", {}).get("name"):
            owner = data["owner_info"]
            print(f"Owner: {owner['name']} ({owner.get('title', 'N/A')})")
            print(f"  Email: {owner.get('email') or 'N/A'}")
            print(f"  Phone: {owner.get('phone') or 'N/A'}")
            print()

        if data.get("team_members"):
            print(f"Team members: {len(data['team_members'])}")
            for member in data["team_members"][:3]:  # Show first 3
                print(f"  - {member.get('name')} ({member.get('title', 'N/A')})")
            print()

        social = data.get("social_media", {})
        social_links = [f"{k}: {v}" for k, v in social.items() if v]
        if social_links:
            print("Social media:")
            for link in social_links:
                print(f"  - {link}")

    # Save to file if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n[OK] Saved results to {args.output}")


if __name__ == "__main__":
    main()

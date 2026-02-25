# [HYBRID] — both importable library and standalone script
"""
Website content scraping utility for AI enrichment.
Extracts relevant content from company websites for icebreaker generation.

Usage:
    from scrape_website_content import scrape_website
    content = scrape_website("https://example.com")
"""

import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse, urljoin


def clean_url(url):
    """
    Clean and normalize URL.
    """
    if not url:
        return None

    url = url.strip()

    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    return url


def extract_text_content(soup):
    """
    Extract meaningful text content from BeautifulSoup object.
    Focuses on hero text, about sections, services, and value propositions.
    """
    # Remove script and style elements
    for script in soup(["script", "style", "noscript", "iframe"]):
        script.decompose()

    text_parts = []

    # Priority 1: Hero/headline sections
    hero_selectors = [
        'h1', '[class*="hero"]', '[class*="headline"]',
        '[class*="banner"]', '[class*="intro"]'
    ]
    for selector in hero_selectors:
        elements = soup.select(selector)
        for el in elements[:3]:  # First 3 matches
            text = el.get_text(strip=True)
            if text and len(text) > 10:
                text_parts.append(text)

    # Priority 2: About sections
    about_selectors = [
        '[class*="about"]', '[id*="about"]',
        '[class*="who-we-are"]', '[class*="company"]'
    ]
    for selector in about_selectors:
        elements = soup.select(selector)
        for el in elements[:2]:  # First 2 matches
            text = el.get_text(strip=True, separator=' ')
            if text and len(text) > 30:
                text_parts.append(text)

    # Priority 3: Services/Products
    service_selectors = [
        '[class*="service"]', '[class*="product"]',
        '[class*="solution"]', '[class*="offer"]'
    ]
    for selector in service_selectors:
        elements = soup.select(selector)
        for el in elements[:3]:  # First 3 matches
            text = el.get_text(strip=True, separator=' ')
            if text and len(text) > 20:
                text_parts.append(text)

    # Priority 4: Main content area
    main_selectors = ['main', '[role="main"]', '[class*="content"]']
    for selector in main_selectors:
        elements = soup.select(selector)
        if elements:
            text = elements[0].get_text(strip=True, separator=' ')
            if text and len(text) > 50:
                text_parts.append(text)
            break

    # Fallback: If we didn't get enough content, extract all body text
    combined_text = ' '.join(text_parts)
    if len(combined_text) < 100:
        # Try body tag as last resort
        body = soup.find('body')
        if body:
            body_text = body.get_text(strip=True, separator=' ')
            body_text = ' '.join(body_text.split())  # Clean up spaces
            if len(body_text) > len(combined_text):
                combined_text = body_text

    # Clean up multiple spaces
    combined_text = ' '.join(combined_text.split())

    # Truncate to 2000 characters
    if len(combined_text) > 2000:
        combined_text = combined_text[:2000]

    return combined_text


def scrape_website(url, timeout=30, retry_attempts=3):
    """
    Scrape website content from a given URL.

    Args:
        url (str): Website URL to scrape
        timeout (int): Request timeout in seconds
        retry_attempts (int): Number of retry attempts

    Returns:
        dict: {
            'success': bool,
            'content': str or None,
            'error': str or None,
            'url': str (final URL after redirects)
        }
    """
    result = {
        'success': False,
        'content': None,
        'error': None,
        'url': url
    }

    # Clean URL
    url = clean_url(url)
    if not url:
        result['error'] = 'invalid_url'
        return result

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    for attempt in range(retry_attempts):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
                verify=True
            )

            # Update URL if redirected
            result['url'] = response.url

            if response.status_code == 200:
                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract content
                content = extract_text_content(soup)

                if content and len(content.strip()) >= 50:
                    result['success'] = True
                    result['content'] = content
                    return result
                else:
                    result['error'] = 'no_content'
                    return result

            elif response.status_code == 403:
                result['error'] = 'forbidden'
                return result

            elif response.status_code == 404:
                result['error'] = 'not_found'
                return result

            elif response.status_code == 429:
                # Rate limited - wait and retry
                if attempt < retry_attempts - 1:
                    time.sleep(5 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    result['error'] = 'rate_limited'
                    return result

            else:
                result['error'] = f'http_error_{response.status_code}'
                return result

        except requests.exceptions.Timeout:
            if attempt < retry_attempts - 1:
                # Try with shorter timeout
                timeout = max(15, timeout // 2)
                continue
            else:
                result['error'] = 'timeout'
                return result

        except requests.exceptions.TooManyRedirects:
            result['error'] = 'too_many_redirects'
            return result

        except requests.exceptions.SSLError:
            result['error'] = 'ssl_error'
            return result

        except requests.exceptions.ConnectionError:
            result['error'] = 'connection_error'
            return result

        except Exception as e:
            result['error'] = f'unknown_error: {str(e)}'
            return result

    result['error'] = 'max_retries_exceeded'
    return result


def scrape_about_page(base_url, timeout=30):
    """
    Try to scrape the /about page if it exists.

    Args:
        base_url (str): Base website URL
        timeout (int): Request timeout in seconds

    Returns:
        dict: Same as scrape_website()
    """
    # Try common about page URLs
    about_paths = ['/about', '/about-us', '/company', '/who-we-are', '/o-nas']

    base_url = clean_url(base_url)
    if not base_url:
        return {'success': False, 'content': None, 'error': 'invalid_url', 'url': base_url}

    parsed = urlparse(base_url)
    base_domain = f"{parsed.scheme}://{parsed.netloc}"

    for path in about_paths:
        about_url = urljoin(base_domain, path)
        result = scrape_website(about_url, timeout=timeout, retry_attempts=1)

        if result['success']:
            return result

    # No about page found
    return {'success': False, 'content': None, 'error': 'no_about_page', 'url': base_url}


if __name__ == "__main__":
    # Test the scraper
    import sys

    if len(sys.argv) < 2:
        print("Usage: py execution/scrape_website_content.py <url>")
        sys.exit(1)

    test_url = sys.argv[1]

    print(f"Scraping: {test_url}")
    result = scrape_website(test_url)

    print(f"\nSuccess: {result['success']}")
    print(f"Final URL: {result['url']}")

    if result['success']:
        print(f"\nContent ({len(result['content'])} chars):")
        print(result['content'][:500] + "..." if len(result['content']) > 500 else result['content'])
    else:
        print(f"Error: {result['error']}")

    # Try about page
    print(f"\n\nTrying about page...")
    about_result = scrape_about_page(test_url)

    print(f"Success: {about_result['success']}")
    if about_result['success']:
        print(f"Content ({len(about_result['content'])} chars):")
        print(about_result['content'][:500] + "..." if len(about_result['content']) > 500 else about_result['content'])
    else:
        print(f"Error: {about_result['error']}")

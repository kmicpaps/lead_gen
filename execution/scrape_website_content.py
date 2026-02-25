# [CLI] — run via: py execution/scrape_website_content.py --help
"""
Wrapper module for website scraping to match ai_industry_enricher expectations.
"""

from website_scraper import scrape_website as _scrape_website


def scrape_website(url, timeout=15):
    """
    Scrape website content and return just the text content.

    Args:
        url (str): Website URL to scrape
        timeout (int): Request timeout in seconds

    Returns:
        str: Scraped content text, or raises exception on failure
    """
    result = _scrape_website(url, timeout=timeout, retry_attempts=2)

    if result['success'] and result['content']:
        return result['content']
    elif result['error']:
        # Raise exception so enricher can handle it properly
        raise Exception(f"Scrape failed: {result['error']}")
    else:
        raise Exception("Scrape failed: no content")

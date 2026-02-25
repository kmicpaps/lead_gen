# [LIBRARY] — imported by other scripts, not run directly
"""
Error Handler for Lead Generation Workflow
Provides user-friendly error messages and troubleshooting steps.
"""

import json


def parse_rapidapi_error(error_response, error_message=''):
    """
    Parse RapidAPI error and return user-friendly message with troubleshooting steps.

    Args:
        error_response: Response object or dict from RapidAPI
        error_message: String error message if available

    Returns:
        dict with 'error_type', 'message', 'user_action'
    """

    error_info = {
        'error_type': 'unknown',
        'message': '',
        'user_action': ''
    }

    # Convert response to dict if needed
    if hasattr(error_response, 'json'):
        try:
            response_data = error_response.json()
        except Exception:
            response_data = {}
    elif isinstance(error_response, dict):
        response_data = error_response
    else:
        response_data = {}

    # Check status code
    status_code = getattr(error_response, 'status_code', None) or response_data.get('status_code')

    # Parse based on status code
    if status_code == 401 or status_code == 403:
        error_info['error_type'] = 'authentication'
        error_info['message'] = 'RapidAPI authentication failed.'
        error_info['user_action'] = """
TROUBLESHOOTING STEPS:
1. Check that 'x-rapidapi-key' in .env is correct
2. Verify your RapidAPI subscription is active at https://rapidapi.com/
3. Ensure you haven't exceeded your monthly quota (50k leads)
4. Try regenerating your RapidAPI key if issue persists
"""

    elif status_code == 429:
        error_info['error_type'] = 'rate_limit'
        error_info['message'] = 'RapidAPI rate limit exceeded.'
        error_info['user_action'] = """
TROUBLESHOOTING STEPS:
1. Wait 60 seconds and retry
2. Check your RapidAPI subscription tier limits
3. If this persists, you may have exceeded your monthly quota (50k leads)
4. Consider upgrading your RapidAPI plan
"""

    elif 'cookie' in error_message.lower() or 'unauthorized' in error_message.lower():
        error_info['error_type'] = 'cookie_expired'
        error_info['message'] = 'Apollo cookie has expired or is invalid.'
        error_info['user_action'] = """
TROUBLESHOOTING STEPS:
1. Log into https://app.apollo.io/ in your browser
2. Open browser DevTools (F12)
3. Go to Application > Cookies > apollo.io
4. Use a cookie export extension (e.g., EditThisCookie) to export all cookies as JSON
5. Update APOLLO_COOKIE in .env file with the exported JSON array
6. Ensure the cookie is formatted as: APOLLO_COOKIE=[{...}]
7. Re-run the workflow

Note: Apollo cookies typically expire after 30 days.
"""

    elif status_code == 500 or status_code == 502 or status_code == 503:
        error_info['error_type'] = 'server_error'
        error_info['message'] = 'RapidAPI service is experiencing issues.'
        error_info['user_action'] = """
TROUBLESHOOTING STEPS:
1. Wait 5-10 minutes and retry
2. Check RapidAPI status page for service outages
3. If issue persists after 30 minutes, contact RapidAPI support
4. Consider using Apify-only mode with --skip-rapidapi flag
"""

    elif status_code == 400:
        error_info['error_type'] = 'bad_request'
        error_info['message'] = 'Invalid Apollo URL or parameters.'
        error_info['user_action'] = """
TROUBLESHOOTING STEPS:
1. Verify your Apollo URL is correct and complete
2. Test the URL directly in browser at https://app.apollo.io/
3. Ensure the URL includes filter parameters (should contain '?')
4. Try simplifying filters if the URL is very complex
"""

    else:
        error_info['error_type'] = 'unknown'
        error_info['message'] = f'RapidAPI scraper failed: {error_message or "Unknown error"}'
        error_info['user_action'] = """
TROUBLESHOOTING STEPS:
1. Check .env file has all required variables:
   - x-rapidapi-key
   - x-rapidapi-host
   - APOLLO_COOKIE
2. Verify your internet connection
3. Check the error log at .tmp/error_log_*.txt for details
4. Contact support if issue persists
"""

    return error_info


def parse_apify_error(error_response, error_message=''):
    """
    Parse Apify error and return user-friendly message with troubleshooting steps.

    Args:
        error_response: Response object or dict from Apify
        error_message: String error message if available

    Returns:
        dict with 'error_type', 'message', 'user_action'
    """

    error_info = {
        'error_type': 'unknown',
        'message': '',
        'user_action': ''
    }

    # Convert response to dict if needed
    if hasattr(error_response, 'json'):
        try:
            response_data = error_response.json()
        except Exception:
            response_data = {}
    elif isinstance(error_response, dict):
        response_data = error_response
    else:
        response_data = {}

    # Check status code
    status_code = getattr(error_response, 'status_code', None) or response_data.get('status_code')

    # Parse based on status code
    if status_code == 401 or status_code == 403:
        error_info['error_type'] = 'authentication'
        error_info['message'] = 'Apify authentication failed.'
        error_info['user_action'] = """
TROUBLESHOOTING STEPS:
1. Check that 'APIFY_API_KEY' in .env is correct
2. Verify your Apify account at https://console.apify.com/
3. Ensure your API token hasn't been revoked
4. Try regenerating your Apify API token if issue persists
"""

    elif status_code == 429:
        error_info['error_type'] = 'rate_limit'
        error_info['message'] = 'Apify rate limit exceeded.'
        error_info['user_action'] = """
TROUBLESHOOTING STEPS:
1. Wait 5 minutes and retry
2. Check your Apify account usage at https://console.apify.com/
3. Your paid plan should have sufficient limits - contact Apify support if this persists
"""

    elif 'credit' in error_message.lower() or 'insufficient' in error_message.lower():
        error_info['error_type'] = 'insufficient_credits'
        error_info['message'] = 'Apify account has insufficient credits or compute units.'
        error_info['user_action'] = """
TROUBLESHOOTING STEPS:
1. Check your Apify account balance at https://console.apify.com/
2. Verify your paid plan is active
3. Add more credits or upgrade your plan if needed
4. Contact Apify support if you believe this is an error
"""

    elif 'timeout' in error_message.lower():
        error_info['error_type'] = 'timeout'
        error_info['message'] = 'Apify scraper timed out.'
        error_info['user_action'] = """
TROUBLESHOOTING STEPS:
1. Retry the operation - temporary network issues may have occurred
2. Reduce the number of leads requested
3. Simplify your filter criteria
4. Check Apify status page for service issues
"""

    else:
        error_info['error_type'] = 'unknown'
        error_info['message'] = f'Apify scraper failed: {error_message or "Unknown error"}'
        error_info['user_action'] = """
TROUBLESHOOTING STEPS:
1. Check .env file has APIFY_API_KEY set correctly
2. Verify your Apify account is active at https://console.apify.com/
3. Check the error log at .tmp/error_log_*.txt for details
4. Simplify filter criteria and retry
5. Contact support if issue persists
"""

    return error_info


def format_error_message(error_info):
    """
    Format error info into a user-friendly message.

    Args:
        error_info: Dict from parse_rapidapi_error or parse_apify_error

    Returns:
        Formatted string message
    """
    return f"""
{'='*60}
ERROR: {error_info['error_type'].upper().replace('_', ' ')}
{'='*60}

{error_info['message']}

{error_info['user_action']}
{'='*60}
"""


def suggest_next_steps(rapidapi_failed, apify_failed):
    """
    Suggest next steps based on which scrapers failed.

    Args:
        rapidapi_failed: Boolean
        apify_failed: Boolean

    Returns:
        String with suggested actions
    """

    if rapidapi_failed and apify_failed:
        return """
BOTH SCRAPERS FAILED

You have the following options:
1. Fix both issues above and retry the full workflow
2. Fix RapidAPI issue and run with --skip-apify flag
3. Fix Apify issue and run with --skip-rapidapi flag
4. Contact support for assistance

The workflow requires at least ONE scraper to succeed.
"""

    elif rapidapi_failed:
        return """
RAPIDAPI SCRAPER FAILED

The workflow will continue with Apify scraper only.
To use both scrapers:
1. Fix the RapidAPI issue above
2. Re-run the workflow without --skip-rapidapi flag
"""

    elif apify_failed:
        return """
APIFY SCRAPER FAILED

The workflow will continue with RapidAPI scraper only.
To use both scrapers:
1. Fix the Apify issue above
2. Re-run the workflow without --skip-apify flag
"""

    else:
        return "All scrapers operational. Proceeding with workflow."

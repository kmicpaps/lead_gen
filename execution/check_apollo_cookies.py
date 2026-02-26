# [HYBRID] — both importable library and standalone script
"""
Quick health check for Apollo cookies

Usage: py execution/check_apollo_cookies.py
"""

import sys
import re
import json
from datetime import datetime

def main():
    """Check Apollo cookie health and expiration"""
    try:
        # Load cookies from .env
        with open('.env', 'r', encoding='utf-8') as f:
            env_content = f.read()

        # Find APOLLO_COOKIE in .env
        match = re.search(r'(?:^|\n)APOLLO_COOKIE=(\[.*?\])', env_content, re.DOTALL | re.MULTILINE)

        if not match:
            print("❌ APOLLO_COOKIE not found in .env")
            print("")
            print("Please add your Apollo cookies to the .env file.")
            print("Format: APOLLO_COOKIE=[...]")
            return 1

        apollo_cookie_str = match.group(1)

        try:
            # Try parsing as JSON
            cookies = json.loads(apollo_cookie_str)
        except json.JSONDecodeError:
            # Try with single quotes replaced
            try:
                fixed_str = apollo_cookie_str.replace("'", '"')
                cookies = json.loads(fixed_str)
            except json.JSONDecodeError as e:
                print(f"❌ Could not parse APOLLO_COOKIE: {e}")
                print("")
                print("Please ensure APOLLO_COOKIE is valid JSON format.")
                return 1

        print(f"✅ Found {len(cookies)} cookies in .env")
        print("")

        # Check expiration
        expired = []
        expiring_soon = []
        valid = []

        for cookie in cookies:
            cookie_name = cookie.get('name', 'unknown')

            if 'expirationDate' in cookie:
                try:
                    exp_timestamp = cookie['expirationDate']
                    exp_date = datetime.fromtimestamp(exp_timestamp)
                    days_left = (exp_date - datetime.now()).days

                    if days_left < 0:
                        expired.append((cookie_name, days_left))
                    elif days_left < 7:
                        expiring_soon.append((cookie_name, days_left))
                    else:
                        valid.append((cookie_name, days_left))
                except (ValueError, TypeError) as e:
                    print(f"⚠️  Warning: Could not parse expiration for cookie '{cookie_name}'")

        # Display results
        if expired:
            print(f"❌ {len(expired)} cookie(s) have EXPIRED:")
            for name, days in expired:
                print(f"   - {name} (expired {abs(days)} days ago)")
            print("")
            print("⚠️  ACTION REQUIRED: Refresh your Apollo cookies!")
            print("")
            print("Steps:")
            print("1. Go to https://app.apollo.io and log in")
            print("2. Install EditThisCookie extension")
            print("3. Click extension → Export cookies")
            print("4. Replace APOLLO_COOKIE in .env with new cookies")
            print("")
            return 1

        elif expiring_soon:
            print(f"⚠️  {len(expiring_soon)} cookie(s) expiring soon:")
            for name, days in expiring_soon:
                print(f"   - {name} ({days} day{'s' if days != 1 else ''} remaining)")
            print("")
            print("💡 Consider refreshing cookies proactively to avoid workflow disruptions.")
            print("")

        if valid:
            print(f"✅ {len(valid)} cookie(s) are valid (>7 days)")

        if not expired and not expiring_soon and valid:
            print("")
            print("🎉 All Apollo cookies are healthy!")
            print("")

        return 0

    except FileNotFoundError:
        print("❌ .env file not found")
        print("")
        print("Please create a .env file with your Apollo cookies.")
        return 1
    except Exception as e:
        print(f"❌ Error checking cookies: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

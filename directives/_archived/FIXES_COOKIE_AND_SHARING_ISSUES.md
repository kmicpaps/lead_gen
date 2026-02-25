# Fixes for Cookie Validation and Google Sheets Sharing Issues

**Date**: 2025-12-11
**Context**: Austria Marketing Agencies campaign revealed two critical issues

## Issue 1: Google Sheets Not Shared by Default

### Problem
- Google Sheets were created but not automatically shared
- Required manual intervention to make sheets accessible
- Links wouldn't work without proper permissions

### Root Cause
- `google_sheets_exporter.py` created sheets but didn't set sharing permissions
- Missing Drive API permission call after sheet creation

### Fix Applied
**File**: `execution/google_sheets_exporter.py`

Added automatic sharing after sheet creation (lines 77-91):
```python
# Share the sheet with anyone who has the link (editor access)
try:
    drive_service = build('drive', 'v3', credentials=creds)
    permission = {
        'type': 'anyone',
        'role': 'writer'
    }
    drive_service.permissions().create(
        fileId=spreadsheet_id,
        body=permission
    ).execute()
    print(f"Sheet shared: Anyone with the link can edit")
except HttpError as share_err:
    print(f"Warning: Could not share sheet automatically: {share_err}")
    print(f"You may need to share the sheet manually")
```

**Status**: ✅ FIXED

---

## Issue 2: Silent Cookie Validation Failures

### Problem
- Olympus scraper failed with "Session Validation Failed" error
- Only returned 3 leads instead of requested 2000
- Fast orchestrator silently fell back to other scrapers
- User was never notified that cookies needed refreshing
- AI agent didn't ask user to renew cookies as expected

### Root Causes

1. **Scraper doesn't detect session validation errors**
   - `scraper_olympus_b2b_finder.py` only checks for empty dataset
   - Doesn't inspect dataset items for error messages like "Session Validation Failed"
   - Doesn't read actor logs for authentication failures

2. **Orchestrator masks cookie failures**
   - `fast_lead_orchestrator.py` treats low lead counts as "need more scrapers"
   - Doesn't distinguish between "cookie failure" and "insufficient results"
   - Silently switches to backup scrapers

3. **No user notification protocol**
   - No clear signal to user that cookies expired
   - No pause to ask user to refresh cookies
   - System continues with degraded data sources

### Fixes Needed

#### Fix 1: Enhanced Cookie Validation Detection

**File**: `execution/scraper_olympus_b2b_finder.py`

Add detailed dataset inspection after download:

```python
# After line 254: dataset_items = list(client.dataset(run['defaultDatasetId']).iterate_items())

# Check for session validation errors in dataset
cookie_validation_failed = False
for item in dataset_items[:10]:  # Check first 10 items
    item_str = str(item)
    if any(error in item_str for error in [
        'Session Validation Failed',
        'Resurrect the run',
        'cookie',
        'authentication',
        'login required'
    ]):
        cookie_validation_failed = True
        break

if cookie_validation_failed:
    print("\n" + "="*70, file=sys.stderr)
    print("🚫 COOKIE VALIDATION FAILED", file=sys.stderr)
    print("="*70, file=sys.stderr)
    print("", file=sys.stderr)
    print("The Apollo session cookie has expired.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Action required:", file=sys.stderr)
    print("1. Log into Apollo in your browser", file=sys.stderr)
    print("2. Export fresh cookies using EditThisCookie extension", file=sys.stderr)
    print("3. Update APOLLO_COOKIE in .env file", file=sys.stderr)
    print("4. Re-run the scraper", file=sys.stderr)
    print("", file=sys.stderr)
    print("="*70, file=sys.stderr)
    return 2  # Special exit code for cookie failures

# Check for suspiciously low results (possible cookie issue)
if len(dataset_items) < args.max_leads * 0.01:  # Less than 1% of requested
    print(f"\n⚠️  Warning: Got {len(dataset_items)} leads (requested {args.max_leads})", file=sys.stderr)
    print("This could indicate a cookie validation issue.", file=sys.stderr)
    print("If this persists, refresh your Apollo cookies.", file=sys.stderr)
```

**Exit Codes**:
- `0`: Success
- `1`: General error
- `2`: Cookie validation failed (special handling needed)

#### Fix 2: Orchestrator Cookie Failure Handling

**File**: `execution/fast_lead_orchestrator.py`

Modify Olympus scraper call to detect cookie failures:

```python
# Around line 183: olympus_success, olympus_output = run_command(...)

# Check for cookie validation failure
if olympus_success == False and 'COOKIE VALIDATION FAILED' in olympus_output:
    print(f"\n{'='*70}")
    print(f"[CRITICAL] Olympus scraper: Cookie validation failed")
    print(f"{'='*70}")
    print("")
    print("❌ Cannot proceed without fresh Apollo cookies.")
    print("")
    print("ACTION REQUIRED:")
    print("1. Log into Apollo (https://app.apollo.io)")
    print("2. Export cookies using EditThisCookie extension")
    print("3. Update APOLLO_COOKIE in .env file")
    print("4. Run the orchestrator again")
    print("")
    print(f"{'='*70}")

    # Ask user if they want to continue with backup scrapers or stop
    user_choice = input("\nContinue with backup scrapers (code_crafter/peakydev)? [y/N]: ").strip().lower()

    if user_choice != 'y':
        print("[STOPPED] Exiting to allow cookie refresh.")
        print("Re-run the same command after updating cookies.")
        return 1

    print("[CONTINUING] Using backup scrapers without Olympus...")
```

#### Fix 3: AI Agent Cookie Renewal Protocol

**File**: `directives/lead_generation_v5_optimized.md`

Add new section after line 100:

```markdown
## Cookie Validation Failure Protocol

**Detection**:
- Olympus returns very few leads (< 1% of target)
- Error message contains "Session Validation Failed"
- Exit code 2 from Olympus scraper

**Agent Actions** (MANDATORY):
1. **STOP the workflow immediately**
2. **Alert the user** with clear message:
   ```
   ⚠️  COOKIE VALIDATION FAILED

   The Apollo session cookie has expired.

   Please:
   1. Log into Apollo: https://app.apollo.io
   2. Export cookies using EditThisCookie extension
   3. Update APOLLO_COOKIE in .env file
   4. Confirm when ready to continue
   ```
3. **WAIT for user confirmation** before proceeding
4. **DO NOT** silently fall back to other scrapers
5. **DO NOT** continue the workflow without fresh cookies

**Reasoning**:
- Olympus provides the highest quality leads from Apollo
- Backup scrapers may have different data quality
- User should explicitly choose degraded mode vs. waiting for cookies
```

#### Fix 4: Directive Update for AI Behavior

**File**: `CLAUDE.md` (project-level instructions)

Add to Layer 2 (Orchestration) section:

```markdown
### Cookie Validation Failures

When any scraper reports cookie/session validation failures:
1. **IMMEDIATELY NOTIFY THE USER** - Don't silently fail over
2. **STOP THE WORKFLOW** - Don't continue with degraded scrapers
3. **ASK FOR ACTION** - Prompt user to refresh cookies
4. **WAIT FOR CONFIRMATION** - Don't proceed until user confirms

**Example**:
```
User, the Olympus scraper failed due to expired cookies.

This means Apollo won't return quality data. I can either:
A) Wait while you refresh cookies (recommended - 2 minutes)
B) Continue with backup scrapers (lower quality, may miss leads)

Which would you prefer?
```

This is CRITICAL for data quality. Never silently downgrade data sources.
```

---

## Additional Recommendations

### 1. Add Cookie Expiration Warning

**File**: `execution/scraper_olympus_b2b_finder.py`

Add proactive cookie age checking:

```python
# Check cookie age at startup
def check_cookie_age(apollo_cookie):
    """Warn if cookies might be stale"""
    # Check for typical cookie expiry fields
    for cookie in apollo_cookie:
        if 'expirationDate' in cookie:
            exp_date = datetime.fromtimestamp(cookie['expirationDate'])
            days_until_expiry = (exp_date - datetime.now()).days
            if days_until_expiry < 7:
                print(f"⚠️  Warning: Cookies expire in {days_until_expiry} days", file=sys.stderr)
                print(f"Consider refreshing cookies soon to avoid failures", file=sys.stderr)
```

### 2. Add Health Check Command

**File**: `execution/check_apollo_cookies.py` (NEW FILE)

Create a dedicated cookie health check tool:

```python
"""
Quick health check for Apollo cookies
Usage: py execution/check_apollo_cookies.py
"""

import sys
import re
import json
from datetime import datetime

def main():
    # Load cookies from .env
    with open('.env', 'r') as f:
        env_content = f.read()

    match = re.search(r'APOLLO_COOKIE=(\[.*?\n\])', env_content, re.DOTALL)
    if not match:
        print("❌ APOLLO_COOKIE not found in .env")
        return 1

    try:
        cookies = json.loads(match.group(1))
        print(f"✅ Found {len(cookies)} cookies")

        # Check expiration
        expired = []
        expiring_soon = []
        for cookie in cookies:
            if 'expirationDate' in cookie:
                exp_date = datetime.fromtimestamp(cookie['expirationDate'])
                days_left = (exp_date - datetime.now()).days

                if days_left < 0:
                    expired.append((cookie['name'], days_left))
                elif days_left < 7:
                    expiring_soon.append((cookie['name'], days_left))

        if expired:
            print(f"\n❌ {len(expired)} cookies have EXPIRED:")
            for name, days in expired:
                print(f"   - {name} (expired {abs(days)} days ago)")
            print("\n⚠️  ACTION REQUIRED: Refresh your Apollo cookies!")
            return 1
        elif expiring_soon:
            print(f"\n⚠️  {len(expiring_soon)} cookies expiring soon:")
            for name, days in expiring_soon:
                print(f"   - {name} ({days} days remaining)")
            print("\nConsider refreshing cookies proactively")
        else:
            print("\n✅ All cookies are valid")

        return 0

    except Exception as e:
        print(f"❌ Error parsing cookies: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

### 3. Add Pre-Flight Cookie Check

**File**: `execution/fast_lead_orchestrator.py`

Add at the start of main():

```python
# Pre-flight cookie health check
print("Running pre-flight checks...")
cookie_check = subprocess.run(['py', 'execution/check_apollo_cookies.py'],
                               capture_output=True, text=True)

if cookie_check.returncode != 0:
    print(cookie_check.stdout)
    print("\n⚠️  Cookie health check failed!")
    user_choice = input("Continue anyway? [y/N]: ").strip().lower()
    if user_choice != 'y':
        print("Exiting. Please refresh cookies and try again.")
        return 1
```

### 4. Update Workflow Documentation

**File**: `QUICK_START_OPTIMIZED.md`

Add troubleshooting section:

```markdown
## Troubleshooting

### "Cookie Validation Failed" Error

If you see this error, your Apollo cookies have expired.

**Quick Fix** (2 minutes):
1. Open Chrome/Firefox
2. Go to https://app.apollo.io and log in
3. Install EditThisCookie extension
4. Click extension → Export cookies
5. Open `.env` file
6. Replace APOLLO_COOKIE=[...] with new cookies
7. Re-run the command

**Prevention**:
- Check cookie health weekly: `py execution/check_apollo_cookies.py`
- Refresh cookies proactively before they expire
```

---

## Implementation Checklist

- [x] Fix 1: Google Sheets auto-sharing (COMPLETED)
- [ ] Fix 2: Enhanced cookie validation detection in scraper
- [ ] Fix 3: Orchestrator cookie failure handling
- [ ] Fix 4: Update directive with cookie protocol
- [ ] Fix 5: Update CLAUDE.md with AI behavior rules
- [ ] Recommendation 1: Add cookie expiration warning
- [ ] Recommendation 2: Create health check script
- [ ] Recommendation 3: Add pre-flight checks to orchestrator
- [ ] Recommendation 4: Update quick start guide

---

## Testing Plan

### Test 1: Expired Cookie Detection
1. Intentionally use expired cookies
2. Run Olympus scraper
3. Verify exit code 2 and clear error message
4. Verify orchestrator stops and asks user

### Test 2: Auto-Sharing Verification
1. Create new Google Sheet
2. Verify "Sheet shared" message appears
3. Open link in incognito window
4. Verify access without login

### Test 3: Health Check Tool
1. Run `py execution/check_apollo_cookies.py`
2. Verify accurate expiration reporting
3. Test with mix of valid/expired cookies

---

## Impact

**Before**:
- ❌ Silent cookie failures
- ❌ Degraded data quality
- ❌ User frustration with broken links
- ❌ Manual sharing required

**After**:
- ✅ Immediate cookie failure detection
- ✅ User notified and prompted for action
- ✅ Sheets automatically shared
- ✅ Proactive cookie health monitoring
- ✅ Clear troubleshooting guidance

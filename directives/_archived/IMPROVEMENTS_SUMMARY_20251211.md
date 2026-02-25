# Lead Generation System Improvements - December 11, 2025

## Summary

Based on the Austria Marketing Agencies campaign, we identified and fixed two critical issues and added AI agent behavior guidelines.

---

## ✅ Issue 1: Google Sheets Not Shared - FIXED

### Problem
- Google Sheets were created but not accessible via link
- Required manual intervention to share sheets
- Users couldn't open sheets without explicit permissions

### Solution
**File**: `execution/google_sheets_exporter.py` (lines 77-91)

Added automatic sharing after sheet creation:
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
```

**Result**: All future Google Sheets are automatically shared and accessible.

---

## ✅ Issue 2: Silent Cookie Validation Failures - FIXED

### Problem
- Olympus scraper failed with "Session Validation Failed"
- Returned only 3 leads instead of 2,000
- System silently fell back to backup scrapers
- AI agent didn't ask user to refresh cookies
- User was never notified of the cookie issue

### Root Causes
1. Scraper didn't detect session validation errors in dataset
2. Orchestrator treated low lead counts as "need more scrapers"
3. No user notification protocol for cookie failures

### Solutions Implemented

#### 1. Enhanced Cookie Detection
**File**: `execution/scraper_olympus_b2b_finder.py` (lines 264-300)

Added dataset inspection for cookie validation errors:
```python
# Check for session validation errors in dataset
cookie_validation_failed = False
for item in dataset_items[:10]:  # Check first 10 items
    item_str = str(item).lower()
    if any(error in item_str for error in [
        'session validation failed',
        'resurrect the run',
        'cookie expired',
        'authentication failed',
        'login required'
    ]):
        cookie_validation_failed = True
        break

if cookie_validation_failed:
    print("🚫 COOKIE VALIDATION FAILED")
    print("The Apollo session cookie has expired.")
    print("ACTION REQUIRED: Refresh cookies and re-run")
    return 2  # Special exit code for cookie failures

# Check for suspiciously low results
if len(dataset_items) < max(10, args.max_leads * 0.01):
    print(f"⚠️  Warning: Got only {len(dataset_items)} leads")
    print("This may indicate a cookie validation issue.")
```

**Exit codes**:
- `0` = Success
- `1` = General error
- `2` = Cookie validation failed (requires user action)

#### 2. Orchestrator Cookie Handling
**File**: `execution/fast_lead_orchestrator.py` (lines 188-213)

Added cookie failure detection and user prompting:
```python
# Check for cookie validation failure (exit code 2)
if olympus_exit_code == 2 or 'COOKIE VALIDATION FAILED' in olympus_output:
    print("[CRITICAL] Olympus scraper: Cookie validation failed")
    print("❌ Apollo session cookie has expired.")
    print("")
    print("ACTION REQUIRED:")
    print("1. Log into Apollo: https://app.apollo.io")
    print("2. Export cookies using EditThisCookie extension")
    print("3. Update APOLLO_COOKIE in .env file")
    print("4. Run the orchestrator again")
    print("")

    user_choice = input("Continue with backup scrapers? [y/N]: ").strip().lower()

    if user_choice != 'y':
        print("[STOPPED] Exiting to allow cookie refresh.")
        return 1

    print("[CONTINUING] Using backup scrapers without Olympus...")
    print("Note: Data quality may be lower.")
```

**Behavior**: Workflow stops and asks user before continuing with degraded data sources.

#### 3. Cookie Health Check Tool
**New File**: `execution/check_apollo_cookies.py`

Proactive cookie monitoring:
```bash
$ py execution/check_apollo_cookies.py
✅ Found 24 cookies in .env

⚠️  2 cookie(s) expiring soon:
   - session_id (5 days remaining)
   - auth_token (3 days remaining)

💡 Consider refreshing cookies proactively to avoid workflow disruptions.
```

Features:
- Checks cookie expiration dates
- Warns when cookies expire within 7 days
- Identifies already-expired cookies
- Provides step-by-step refresh instructions

---

## ✅ Issue 3: AI Agent Behavior - IMPROVED

### Problem
- AI agent constantly polled status every 1-2 seconds
- Wasted resources checking BashOutput repeatedly
- No clear guidance on efficient monitoring

### Solution
**File**: `CLAUDE.md` (lines 96-125)

Added explicit AI agent protocols:

#### Efficient Status Monitoring
```
DO:
- Use time.sleep() with reasonable intervals (10-30 seconds)
- Wait for subprocess completion instead of polling
- Run commands in background when appropriate

DON'T:
- Poll status every 1-2 seconds (wastes resources)
- Make HTTP requests in tight loops
- Repeatedly check BashOutput without delays
```

#### Cookie Validation Protocol
```
When scraper reports cookie validation failure:

1. IMMEDIATELY NOTIFY THE USER - Don't silently fail over
2. STOP THE WORKFLOW - Don't continue with degraded scrapers
3. ASK FOR ACTION - Prompt user to refresh cookies
4. WAIT FOR CONFIRMATION - Don't proceed until user confirms
```

**File**: `directives/lead_generation_v5_optimized.md` (lines 86-139)

Added cookie validation failure protocol with decision tree.

---

## Testing & Validation

### Test Cookie Detection
```bash
# Test with expired cookies
py execution/check_apollo_cookies.py

# Should detect expiration and provide clear guidance
```

### Test Sheet Sharing
```bash
# Create a test sheet
py execution/google_sheets_exporter.py \
  --input "test_leads.json" \
  --sheet-title "Test Sheet"

# Verify "Sheet shared" message appears
# Open link in incognito window - should work without login
```

### Test Orchestrator Cookie Handling
```bash
# With fresh cookies - should complete normally
py execution/fast_lead_orchestrator.py \
  --client-id test \
  --campaign-name "Test Campaign" \
  --apollo-url "..." \
  --target-leads 100

# With expired cookies - should stop and ask user
```

---

## File Changes Summary

### Modified Files
1. ✅ `execution/google_sheets_exporter.py` - Auto-sharing
2. ✅ `execution/scraper_olympus_b2b_finder.py` - Cookie detection
3. ✅ `execution/fast_lead_orchestrator.py` - User prompting
4. ✅ `CLAUDE.md` - AI agent protocols
5. ✅ `directives/lead_generation_v5_optimized.md` - Cookie protocol

### New Files
1. ✅ `execution/check_apollo_cookies.py` - Cookie health check
2. ✅ `directives/FIXES_COOKIE_AND_SHARING_ISSUES.md` - Detailed fix documentation
3. ✅ `directives/IMPROVEMENTS_SUMMARY_20251211.md` - This file

---

## Impact

### Before
- ❌ Sheets not accessible via link (manual sharing required)
- ❌ Silent cookie failures (degraded data quality)
- ❌ No user notification of cookie issues
- ❌ AI agent constant status polling
- ❌ Backup scrapers used without user consent

### After
- ✅ Sheets automatically shared (works immediately)
- ✅ Cookie failures detected (exit code 2)
- ✅ User notified and prompted for decision
- ✅ AI agent uses efficient monitoring
- ✅ User chooses data quality vs. speed trade-off

---

## Usage Guidelines

### For Users

1. **Check cookie health weekly**:
   ```bash
   py execution/check_apollo_cookies.py
   ```

2. **Refresh cookies proactively** (before expiration):
   - Go to https://app.apollo.io
   - Login
   - Use EditThisCookie extension → Export
   - Update `APOLLO_COOKIE` in `.env`

3. **When prompted about cookie failures**:
   - Option A: Refresh cookies (recommended - 2 min, best quality)
   - Option B: Continue with backups (faster, lower quality)

### For AI Agents

1. **Monitor long-running commands efficiently**:
   - Use subprocess.run() with timeout
   - Sleep 10-30 seconds between status checks
   - Don't poll constantly

2. **Handle cookie validation failures**:
   - Detect exit code 2 or error messages
   - Notify user immediately
   - Stop workflow and wait for decision
   - Never silently downgrade data sources

3. **Update directives when learning**:
   - Document new API behaviors
   - Record error patterns
   - Improve error messages

---

## Maintenance

### Weekly
- Run cookie health check
- Review scraper error logs
- Check Google Sheets accessibility

### Monthly
- Refresh Apollo cookies proactively
- Review and update directives
- Test full workflow end-to-end

### When Issues Occur
1. Check cookie health first
2. Review scraper exit codes
3. Inspect error messages
4. Update directives with learnings
5. Self-anneal the system

---

## Next Steps

Optional future improvements:

1. **Pre-flight checks** in orchestrator:
   - Auto-run cookie health check before scraping
   - Prevent workflows with expired cookies

2. **Cookie age warnings** in scraper:
   - Warn when cookies < 7 days from expiration
   - Proactive notification

3. **Automated cookie refresh**:
   - Browser automation to refresh cookies
   - Reduce manual intervention

4. **Enhanced monitoring**:
   - Log all cookie validation events
   - Track scraper success rates
   - Alert on pattern changes

---

## Documentation

- **Detailed fixes**: [FIXES_COOKIE_AND_SHARING_ISSUES.md](FIXES_COOKIE_AND_SHARING_ISSUES.md)
- **Lead gen workflow**: [lead_generation_v5_optimized.md](lead_generation_v5_optimized.md)
- **AI agent instructions**: [CLAUDE.md](../CLAUDE.md)
- **Cookie health check**: `execution/check_apollo_cookies.py`

---

**Date**: December 11, 2025
**Trigger**: Austria Marketing Agencies campaign
**Status**: ✅ All fixes implemented and tested

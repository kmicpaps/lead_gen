# [CLI]
"""
Setup Wizard — Check workspace readiness after a fresh clone or move.

Verifies: Python dependencies, .env configuration, API key presence,
Google credentials, directory structure, and system health.

SECURITY: This script checks whether API keys EXIST in .env but NEVER
reads, prints, or loads their actual values. It only checks non-emptiness.

Usage:
    py execution/setup_wizard.py           # Full check
    py execution/setup_wizard.py --json    # Machine-readable output
"""

import os
import sys
import json
import importlib
import argparse

# Windows console encoding fix
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import log_ok, log_error, log_warn, log_info

# Project root (one level up from execution/)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Package name -> import name mapping (where they differ)
PACKAGE_IMPORT_MAP = {
    'python-dotenv': 'dotenv',
    'google-auth': 'google.auth',
    'google-auth-oauthlib': 'google_auth_oauthlib',
    'google-auth-httplib2': 'google_auth_httplib2',
    'google-api-python-client': 'googleapiclient',
    'beautifulsoup4': 'bs4',
    'apify-client': 'apify_client',
}

# Required API keys (must be non-empty for the system to work)
REQUIRED_KEYS = [
    ('APIFY_API_KEY', 'Apify Console > Integrations'),
    ('ANTHROPIC_API_KEY', 'https://console.anthropic.com/'),
    ('OPENAI_API_KEY', 'https://platform.openai.com/'),
]

# Optional API keys (nice to have, system works without them)
OPTIONAL_KEYS = [
    ('LeadMagic-X-API-Key', 'https://leadmagic.io/ (email verification)'),
    ('x-rapidapi-key', 'https://rapidapi.com/ (not actively used)'),
]

# Special key with format validation
SPECIAL_KEYS = [
    ('APOLLO_COOKIE', 'Apollo.io browser cookies (JSON array format)'),
]


def parse_requirements():
    """Parse requirements.txt and return list of package names."""
    req_path = os.path.join(ROOT_DIR, 'requirements.txt')
    if not os.path.exists(req_path):
        return []
    packages = []
    with open(req_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Strip version specifier: "pandas>=2.1.0" -> "pandas"
            pkg = line.split('>=')[0].split('==')[0].split('<=')[0].split('<')[0].split('>')[0].strip()
            if pkg:
                packages.append(pkg)
    return packages


def check_package_installed(package_name):
    """Check if a Python package is importable."""
    import_name = PACKAGE_IMPORT_MAP.get(package_name, package_name.replace('-', '_'))
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def parse_env_keys(env_path):
    """
    Parse .env file and return dict of key -> has_value (bool).

    SECURITY: Only checks whether values are non-empty.
    Does NOT store, print, or return actual values.
    """
    keys = {}
    if not os.path.exists(env_path):
        return keys
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip()
            # For APOLLO_COOKIE, check JSON array format
            if key == 'APOLLO_COOKIE':
                keys[key] = value.startswith('[') and len(value) > 2
            else:
                keys[key] = len(value) > 0
    return keys


def check_dependencies(results):
    """Check Python package dependencies."""
    packages = parse_requirements()
    if not packages:
        results['warnings'].append("requirements.txt not found or empty")
        return

    installed = 0
    missing = []
    for pkg in packages:
        if check_package_installed(pkg):
            installed += 1
            results['details'].append(('ok', f"{pkg}"))
        else:
            missing.append(pkg)
            results['failures'].append(f"DEPENDENCIES: {pkg} not installed -> pip install {pkg}")
            results['details'].append(('fail', f"{pkg} -> pip install {pkg}"))

    results['categories']['dependencies'] = {
        'count': len(packages),
        'installed': installed,
        'missing': len(missing),
    }


def check_env_file(results):
    """Check .env file exists."""
    env_path = os.path.join(ROOT_DIR, '.env')
    example_path = os.path.join(ROOT_DIR, '.env.example')

    if os.path.exists(env_path):
        results['details'].append(('ok', '.env exists'))
        results['categories']['env_file'] = {'status': 'ok'}
    else:
        if os.path.exists(example_path):
            results['failures'].append("ENV: .env not found -> cp .env.example .env")
            results['details'].append(('fail', '.env not found -> cp .env.example .env'))
        else:
            results['failures'].append("ENV: .env not found and no .env.example template")
            results['details'].append(('fail', '.env not found (no template available)'))
        results['categories']['env_file'] = {'status': 'missing'}


def check_api_keys(results):
    """Check API keys are configured (without reading values)."""
    env_path = os.path.join(ROOT_DIR, '.env')
    env_keys = parse_env_keys(env_path)

    configured = 0
    total_required = len(REQUIRED_KEYS) + len(SPECIAL_KEYS)

    # Required keys
    for key, source in REQUIRED_KEYS:
        if env_keys.get(key):
            configured += 1
            results['details'].append(('ok', f"{key}"))
        else:
            results['failures'].append(f"API KEYS: {key} not set -> {source}")
            results['details'].append(('fail', f"{key} -> {source}"))

    # Special keys (APOLLO_COOKIE)
    for key, source in SPECIAL_KEYS:
        if env_keys.get(key):
            configured += 1
            results['details'].append(('ok', f"{key} (JSON array format)"))
        elif key in env_keys:
            results['warnings'].append(f"API KEYS: {key} set but not in JSON array format")
            results['details'].append(('warn', f"{key} — not in JSON array format"))
        else:
            results['warnings'].append(f"API KEYS: {key} not set — Olympus scraper won't work")
            results['details'].append(('warn', f"{key} not set (Olympus scraper needs it)"))

    # Optional keys
    for key, source in OPTIONAL_KEYS:
        if env_keys.get(key):
            results['details'].append(('ok', f"{key} (optional)"))
        else:
            results['details'].append(('skip', f"{key} (optional — {source})"))

    results['categories']['api_keys'] = {
        'configured': configured,
        'required': total_required,
    }


def check_google_credentials(results):
    """Check Google OAuth credentials exist."""
    creds_path = os.path.join(ROOT_DIR, 'credentials.json')
    token_path = os.path.join(ROOT_DIR, 'token.json')

    if os.path.exists(creds_path):
        results['details'].append(('ok', 'credentials.json'))
    else:
        results['failures'].append("GOOGLE: credentials.json not found -> download from Google Cloud Console")
        results['details'].append(('fail', 'credentials.json not found -> Google Cloud Console > OAuth > Download'))

    if os.path.exists(token_path):
        results['details'].append(('ok', 'token.json'))
    else:
        results['details'].append(('info', 'token.json not found (auto-generated on first Sheets export)'))

    results['categories']['google'] = {
        'credentials': os.path.exists(creds_path),
        'token': os.path.exists(token_path),
    }


def check_directories(results):
    """Check required directory structure exists."""
    dirs = [
        ('campaigns/', True),
        ('campaigns/_template/', True),
        ('.tmp/', False),  # Can be auto-created
    ]

    for dir_rel, required in dirs:
        dir_path = os.path.join(ROOT_DIR, dir_rel)
        if os.path.isdir(dir_path):
            results['details'].append(('ok', dir_rel))
        elif required:
            results['warnings'].append(f"DIRECTORIES: {dir_rel} not found")
            results['details'].append(('warn', f"{dir_rel} not found"))
        else:
            # Auto-create optional directories
            try:
                os.makedirs(dir_path, exist_ok=True)
                results['details'].append(('ok', f"{dir_rel} (created)"))
            except OSError:
                results['warnings'].append(f"DIRECTORIES: Could not create {dir_rel}")
                results['details'].append(('warn', f"{dir_rel} could not be created"))


def check_system_health(results):
    """Run the system health check and include results."""
    try:
        from system_health_check import run_checks
        health = run_checks('full')

        for check_name, cat_data in health['categories'].items():
            count = cat_data['count']
            fails = sum(1 for s, _ in cat_data['results'] if s == 'fail')
            warns = sum(1 for s, _ in cat_data['results'] if s == 'warn')
            if fails == 0 and warns == 0:
                results['details'].append(('ok', f"{check_name}: {count} checked, all OK"))
            else:
                results['details'].append(('warn', f"{check_name}: {count} checked, {fails} failures, {warns} warnings"))

        # Propagate any health check failures
        results['failures'].extend(health.get('failures', []))
        results['warnings'].extend(health.get('warnings', []))
        results['categories']['health'] = {'status': 'ok' if not health['failures'] else 'issues'}

    except Exception as e:
        results['warnings'].append(f"HEALTH: Could not run system health check: {e}")
        results['categories']['health'] = {'status': 'error', 'error': str(e)}


def run_setup_check():
    """Run all setup checks and return results."""
    results = {
        'failures': [],
        'warnings': [],
        'details': [],
        'categories': {},
    }

    check_dependencies(results)
    check_env_file(results)
    check_api_keys(results)
    check_google_credentials(results)
    check_directories(results)
    check_system_health(results)

    return results


def print_results(results):
    """Print human-readable setup check results."""
    print("=" * 50)
    print("WORKSPACE SETUP CHECK")
    print("=" * 50)
    print()

    # Group details by section
    sections = [
        ("PYTHON DEPENDENCIES", lambda d: d[1].split()[0] in [p for p in parse_requirements()]),
        ("ENVIRONMENT FILE", lambda d: '.env' in d[1] and 'KEY' not in d[1]),
        ("API KEYS (values hidden)", lambda d: any(k[0] in d[1] for k in REQUIRED_KEYS + OPTIONAL_KEYS + SPECIAL_KEYS)),
        ("GOOGLE CREDENTIALS", lambda d: 'credentials' in d[1].lower() or 'token' in d[1].lower()),
        ("DIRECTORIES", lambda d: d[1].endswith('/') or '(created)' in d[1]),
        ("SYSTEM HEALTH", lambda d: ':' in d[1] and 'checked' in d[1]),
    ]

    used = set()
    for section_name, matcher in sections:
        section_items = []
        for i, (status, msg) in enumerate(results['details']):
            if i not in used and matcher((status, msg)):
                section_items.append((status, msg))
                used.add(i)

        if section_items:
            print(f"{section_name}")
            for status, msg in section_items:
                if status == 'ok':
                    log_ok(msg)
                elif status == 'fail':
                    log_error(msg)
                elif status == 'warn':
                    log_warn(msg)
                elif status == 'skip':
                    print(f"  [SKIP] {msg}")
                elif status == 'info':
                    log_info(msg)
            print()

    # Any ungrouped items
    ungrouped = [(s, m) for i, (s, m) in enumerate(results['details']) if i not in used]
    if ungrouped:
        print("OTHER")
        for status, msg in ungrouped:
            if status == 'ok':
                log_ok(msg)
            elif status == 'fail':
                log_error(msg)
            else:
                log_warn(msg)
        print()

    # Summary
    total = len(results['details'])
    ok_count = sum(1 for s, _ in results['details'] if s in ('ok', 'skip', 'info'))
    fail_count = len(results['failures'])
    warn_count = len(results['warnings'])

    print("=" * 50)
    if fail_count == 0:
        log_ok(f"READY — {ok_count}/{total} checks passed")
        if warn_count > 0:
            print(f"  ({warn_count} non-blocking warnings)")
    else:
        print(f"ACTION NEEDED: {fail_count} required fix(es), {warn_count} warning(s)")


def print_json(results):
    """Print machine-readable JSON output."""
    output = {
        'status': 'ready' if not results['failures'] else 'action_needed',
        'failures': results['failures'],
        'warnings': results['warnings'],
        'categories': results['categories'],
        'checks': [{'status': s, 'message': m} for s, m in results['details']],
    }
    print(json.dumps(output, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description='Workspace setup wizard — check readiness after clone or move.'
    )
    parser.add_argument('--json', action='store_true',
                        help='Output machine-readable JSON')
    args = parser.parse_args()

    results = run_setup_check()

    if args.json:
        print_json(results)
    else:
        print_results(results)

    return 1 if results['failures'] else 0


if __name__ == '__main__':
    sys.exit(main())

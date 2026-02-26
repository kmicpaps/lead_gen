# [CLI]
"""
System Health Check — Structural consistency checker for the lead generation codebase.

Verifies alignment between scraper registry, normalizer, directives, skills, and scripts.
This is a quick structural check (~10 seconds), not a deep semantic audit.

Usage:
    py execution/system_health_check.py                    # Full check (all categories)
    py execution/system_health_check.py --check registry   # Single category
    py execution/system_health_check.py --check normalizer
    py execution/system_health_check.py --check directives
    py execution/system_health_check.py --check markers
    py execution/system_health_check.py --check imports
    py execution/system_health_check.py --json             # Machine-readable output
"""

import os
import sys
import ast
import re
import json
import argparse
import glob as glob_module

# Sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import log_ok, log_error, log_warn, log_info

# Project root (one level up from execution/)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXECUTION_DIR = os.path.join(ROOT_DIR, 'execution')
DIRECTIVES_DIR = os.path.join(ROOT_DIR, 'directives')
SKILLS_DIR = os.path.join(ROOT_DIR, '.claude', 'skills')

VALID_MARKERS = {'# [CLI]', '# [LIBRARY]', '# [ORCHESTRATOR]', '# [HYBRID]'}
SKIP_DIRS = {'_archived', '__pycache__'}


def get_execution_scripts():
    """Get all .py files in execution/ excluding archived and pycache."""
    scripts = []
    for f in os.listdir(EXECUTION_DIR):
        if f.endswith('.py') and not f.startswith('__'):
            full_path = os.path.join(EXECUTION_DIR, f)
            if os.path.isfile(full_path):
                scripts.append(f)
    return sorted(scripts)


def check_registry(results):
    """Check scraper registry consistency."""
    try:
        from scraper_registry import SCRAPER_REGISTRY
    except ImportError as e:
        results['failures'].append(f"REGISTRY: Cannot import scraper_registry: {e}")
        return

    category_results = []

    # Check each registry entry has an existing script
    for name, config in SCRAPER_REGISTRY.items():
        script_path = config.get('script', '')
        full_path = os.path.join(ROOT_DIR, script_path)
        if os.path.exists(full_path):
            category_results.append(('ok', f"{name} -> {script_path}"))
        else:
            results['failures'].append(f"REGISTRY: {name} -> {script_path} (file not found)")
            category_results.append(('fail', f"{name} -> {script_path} (NOT FOUND)"))

    # Check scraper_*.py files have registry entries (exclude archived)
    scraper_files = [f for f in get_execution_scripts() if f.startswith('scraper_') and f != 'scraper_registry.py']
    registered_scripts = {os.path.basename(c.get('script', '')) for c in SCRAPER_REGISTRY.values()}

    for sf in scraper_files:
        if sf not in registered_scripts:
            results['warnings'].append(f"REGISTRY: {sf} has no registry entry")
            category_results.append(('warn', f"{sf} has no registry entry"))

    results['categories']['registry'] = {
        'count': len(SCRAPER_REGISTRY),
        'results': category_results
    }


def check_normalizer(results):
    """Check normalizer has functions for all registered scrapers."""
    try:
        from scraper_registry import SCRAPER_REGISTRY
    except ImportError:
        results['failures'].append("NORMALIZER: Cannot import scraper_registry")
        return

    normalizer_path = os.path.join(EXECUTION_DIR, 'lead_normalizer.py')
    if not os.path.exists(normalizer_path):
        results['failures'].append("NORMALIZER: lead_normalizer.py not found")
        return

    # Parse AST to find normalize_* functions
    with open(normalizer_path, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        results['failures'].append(f"NORMALIZER: lead_normalizer.py has syntax error: {e}")
        return

    # Find all function definitions named normalize_*
    normalize_funcs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('normalize_'):
            normalize_funcs.add(node.name)

    category_results = []

    # Check each registry scraper has a normalize function
    for name in SCRAPER_REGISTRY:
        func_name = f'normalize_{name}'
        if func_name in normalize_funcs:
            category_results.append(('ok', f"{func_name}() found"))
        else:
            results['failures'].append(f"NORMALIZER: {func_name}() missing for scraper '{name}'")
            category_results.append(('fail', f"{func_name}() MISSING"))

    # Check normalize_lead() dispatcher handles all registry keys
    # Look for 'source == ' patterns in the source
    dispatcher_sources = set(re.findall(r"source\s*==\s*['\"](\w+)['\"]", source))
    for name in SCRAPER_REGISTRY:
        if name not in dispatcher_sources:
            results['warnings'].append(f"NORMALIZER: normalize_lead() dispatcher may not handle '{name}'")
            category_results.append(('warn', f"normalize_lead() may not handle '{name}'"))

    results['categories']['normalizer'] = {
        'count': len(SCRAPER_REGISTRY),
        'results': category_results
    }


def check_directives(results):
    """Check directive and skill file references are valid."""
    category_results = []

    # 1. Check directives/README.md — every listed .md file in active tables exists
    readme_path = os.path.join(DIRECTIVES_DIR, 'README.md')
    if not os.path.exists(readme_path):
        results['warnings'].append("DIRECTIVES: directives/README.md not found")
    else:
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()

        # Only check the active section (before "## Archived")
        archived_pos = readme_content.find('## Archived')
        active_section = readme_content[:archived_pos] if archived_pos > 0 else readme_content

        # Extract directive filenames from table rows: | `filename.md` |
        # Only match files that look like directive names (not CLAUDE.md, etc.)
        listed_files = re.findall(r'\|\s*`(\w[\w_]*\.md)`\s*\|', active_section)
        for fname in listed_files:
            if fname == 'README.md':
                continue
            fpath = os.path.join(DIRECTIVES_DIR, fname)
            if os.path.exists(fpath):
                category_results.append(('ok', f"directives/{fname}"))
            else:
                results['failures'].append(f"DIRECTIVES: directives/{fname} listed in README.md but not found")
                category_results.append(('fail', f"directives/{fname} NOT FOUND"))

    # 2. Check each skill's directive and script references
    if os.path.isdir(SKILLS_DIR):
        for skill_name in sorted(os.listdir(SKILLS_DIR)):
            skill_path = os.path.join(SKILLS_DIR, skill_name, 'SKILL.md')
            if not os.path.exists(skill_path):
                continue

            with open(skill_path, 'r', encoding='utf-8') as f:
                skill_content = f.read()

            # Check directive references: directives/*.md
            directive_refs = re.findall(r'directives/(\w[\w_]*\.md)', skill_content)
            for dref in directive_refs:
                dpath = os.path.join(DIRECTIVES_DIR, dref)
                if not os.path.exists(dpath):
                    results['warnings'].append(f"DIRECTIVES: skill '{skill_name}' references directives/{dref} (not found)")
                    category_results.append(('warn', f"skill/{skill_name} -> directives/{dref} NOT FOUND"))

            # Check script references: execution/*.py
            script_refs = re.findall(r'execution/([\w_]+\.py)', skill_content)
            for sref in script_refs:
                spath = os.path.join(EXECUTION_DIR, sref)
                # Also check _archived
                archived_path = os.path.join(EXECUTION_DIR, '_archived', sref)
                if not os.path.exists(spath) and not os.path.exists(archived_path):
                    results['warnings'].append(f"DIRECTIVES: skill '{skill_name}' references execution/{sref} (not found)")
                    category_results.append(('warn', f"skill/{skill_name} -> execution/{sref} NOT FOUND"))

    directive_count = len([f for f in os.listdir(DIRECTIVES_DIR)
                          if f.endswith('.md') and f != 'README.md' and os.path.isfile(os.path.join(DIRECTIVES_DIR, f))])
    skill_count = len([d for d in os.listdir(SKILLS_DIR)
                      if os.path.isdir(os.path.join(SKILLS_DIR, d))]) if os.path.isdir(SKILLS_DIR) else 0

    if not category_results:
        category_results.append(('ok', 'All directive files exist and all skill references are valid'))

    results['categories']['directives'] = {
        'count': f"{directive_count} directives, {skill_count} skills",
        'results': category_results
    }


def check_markers(results):
    """Check every execution script has a valid marker on line 1."""
    scripts = get_execution_scripts()
    category_results = []
    valid_count = 0

    for script in scripts:
        fpath = os.path.join(EXECUTION_DIR, script)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
        except Exception as e:
            results['failures'].append(f"MARKERS: Cannot read {script}: {e}")
            category_results.append(('fail', f"{script}: cannot read"))
            continue

        # Check if first line matches a valid marker (may have trailing comment)
        marker_match = False
        for marker in VALID_MARKERS:
            if first_line.startswith(marker):
                marker_match = True
                break

        if marker_match:
            valid_count += 1
        else:
            results['failures'].append(f"MARKERS: {script} — invalid or missing marker (got: '{first_line[:60]}')")
            category_results.append(('fail', f"{script}: invalid marker"))

    if valid_count == len(scripts):
        category_results.insert(0, ('ok', f"All {valid_count} scripts have valid markers"))
    else:
        category_results.insert(0, ('warn', f"{valid_count}/{len(scripts)} scripts have valid markers"))

    results['categories']['markers'] = {
        'count': len(scripts),
        'results': category_results
    }


def check_imports(results):
    """Check every execution script parses without syntax errors."""
    scripts = get_execution_scripts()
    category_results = []
    pass_count = 0

    for script in scripts:
        fpath = os.path.join(EXECUTION_DIR, script)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                source = f.read()
            ast.parse(source)
            pass_count += 1
        except SyntaxError as e:
            results['failures'].append(f"IMPORTS: {script} — SyntaxError at line {e.lineno}: {e.msg}")
            category_results.append(('fail', f"{script}: SyntaxError line {e.lineno}"))
        except Exception as e:
            results['failures'].append(f"IMPORTS: {script} — {e}")
            category_results.append(('fail', f"{script}: {e}"))

    if pass_count == len(scripts):
        category_results.insert(0, ('ok', f"All {pass_count} scripts parse successfully"))
    else:
        category_results.insert(0, ('warn', f"{pass_count}/{len(scripts)} scripts parse successfully"))

    results['categories']['imports'] = {
        'count': len(scripts),
        'results': category_results
    }


CHECKERS = {
    'registry': ('REGISTRY', check_registry),
    'normalizer': ('NORMALIZER', check_normalizer),
    'directives': ('DIRECTIVES', check_directives),
    'markers': ('MARKERS', check_markers),
    'imports': ('IMPORTS', check_imports),
}


def run_checks(scope='full'):
    """Run health checks and return results dict."""
    results = {
        'failures': [],
        'warnings': [],
        'categories': {},
    }

    if scope == 'full':
        checks_to_run = list(CHECKERS.keys())
    elif scope in CHECKERS:
        checks_to_run = [scope]
    else:
        results['failures'].append(f"Unknown check scope: {scope}")
        return results

    for check_name in checks_to_run:
        _, check_fn = CHECKERS[check_name]
        check_fn(results)

    return results


def print_results(results):
    """Print human-readable results."""
    print("=" * 50)
    print("SYSTEM HEALTH CHECK")
    print("=" * 50)
    print()

    for check_name, (display_name, _) in CHECKERS.items():
        if check_name not in results['categories']:
            continue

        cat = results['categories'][check_name]
        count = cat['count']
        print(f"{display_name} ({count})")

        for status, msg in cat['results']:
            if status == 'ok':
                log_ok(msg)
            elif status == 'warn':
                log_warn(msg)
            elif status == 'fail':
                log_error(msg)

        print()

    # Summary
    failures = len(results['failures'])
    warnings = len(results['warnings'])
    print("-" * 50)
    if failures == 0 and warnings == 0:
        log_ok(f"All checks passed")
    else:
        print(f"SUMMARY: {failures} failure(s), {warnings} warning(s)")
        if failures > 0:
            print()
            print("FAILURES:")
            for f in results['failures']:
                log_error(f)
        if warnings > 0:
            print()
            print("WARNINGS:")
            for w in results['warnings']:
                log_warn(w)


def print_json(results):
    """Print machine-readable JSON output."""
    output = {
        'status': 'pass' if not results['failures'] else 'fail',
        'failures': results['failures'],
        'warnings': results['warnings'],
        'categories': {}
    }
    for check_name in results['categories']:
        cat = results['categories'][check_name]
        output['categories'][check_name] = {
            'count': cat['count'],
            'ok': sum(1 for s, _ in cat['results'] if s == 'ok'),
            'warnings': sum(1 for s, _ in cat['results'] if s == 'warn'),
            'failures': sum(1 for s, _ in cat['results'] if s == 'fail'),
            'details': [{'status': s, 'message': m} for s, m in cat['results']],
        }
    print(json.dumps(output, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description='System health check — verify structural consistency across the codebase.'
    )
    parser.add_argument('--check', choices=list(CHECKERS.keys()),
                        help='Run a specific check category (default: all)')
    parser.add_argument('--json', action='store_true',
                        help='Output machine-readable JSON')
    args = parser.parse_args()

    scope = args.check or 'full'
    results = run_checks(scope)

    if args.json:
        print_json(results)
    else:
        print_results(results)

    return 1 if results['failures'] else 0


if __name__ == '__main__':
    sys.exit(main())

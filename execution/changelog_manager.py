# [HYBRID] — both importable library and standalone CLI
"""
Changelog Manager — track fixes, features, refactors, and other changes.

Stores entries in docs/changelog.json and auto-generates docs/CHANGELOG.md.

Usage:
    py execution/changelog_manager.py add --type fix --severity high --summary "..." --files file1.py
    py execution/changelog_manager.py query --type fix --since 2026-02-20
    py execution/changelog_manager.py report
    py execution/changelog_manager.py stats
"""

import os
import json
import sys
import argparse
from datetime import datetime, timezone
from fnmatch import fnmatch

# Fix Windows console encoding for Unicode output
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_json, save_json, log_ok, log_info, log_error

# Paths relative to workspace root (scripts are called from root)
CHANGELOG_JSON = "docs/changelog.json"
CHANGELOG_MD = "docs/CHANGELOG.md"

VALID_TYPES = ("fix", "feature", "refactor", "audit", "directive", "deprecation")
VALID_SEVERITIES = ("critical", "high", "medium", "low")


# ---------------------------------------------------------------------------
# Data I/O
# ---------------------------------------------------------------------------

def load_changelog(filepath=CHANGELOG_JSON):
    """Load changelog or return empty structure if file doesn't exist."""
    if os.path.exists(filepath):
        try:
            return load_json(filepath)
        except (json.JSONDecodeError, ValueError) as e:
            log_warn(f"Corrupted changelog {filepath}: {e}. Starting fresh.")
            return {"version": 1, "entries": []}
    return {"version": 1, "entries": []}


def save_changelog(data, filepath=CHANGELOG_JSON):
    """Save changelog JSON and regenerate CHANGELOG.md."""
    os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
    save_json(data, filepath)
    generate_markdown(data)
    return filepath


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def generate_entry_id(existing_entries=None):
    """Generate {YYYYMMDD}_{HHMMSS}_{seq} ID. Auto-increments seq within same second."""
    now = datetime.now(timezone.utc)
    prefix = now.strftime("%Y%m%d_%H%M%S")

    # Find highest seq for this second
    seq = 1
    if existing_entries:
        for entry in existing_entries:
            if entry.get("id", "").startswith(prefix):
                try:
                    existing_seq = int(entry["id"].split("_")[-1])
                    seq = max(seq, existing_seq + 1)
                except (ValueError, IndexError):
                    pass

    return f"{prefix}_{seq:03d}"


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def add_entry(entry_type, summary, files_changed=None, severity=None,
              description=None, related_audit=None, tags=None, filepath=CHANGELOG_JSON):
    """
    Add a changelog entry. Returns the created entry dict.

    Args:
        entry_type: fix, feature, refactor, audit, directive, deprecation
        summary: One-line description (max 120 chars)
        files_changed: List of relative file paths
        severity: critical, high, medium, low (required for fix/audit)
        description: Optional longer explanation
        related_audit: Optional audit finding ID
        tags: Optional list of tags
    """
    if entry_type not in VALID_TYPES:
        raise ValueError(f"Invalid type '{entry_type}'. Must be one of: {VALID_TYPES}")
    if not summary or not isinstance(summary, str):
        raise ValueError(f"summary must be a non-empty string, got {type(summary).__name__}")
    if severity and severity not in VALID_SEVERITIES:
        raise ValueError(f"Invalid severity '{severity}'. Must be one of: {VALID_SEVERITIES}")

    data = load_changelog(filepath)

    entry = {
        "id": generate_entry_id(data["entries"]),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": entry_type,
        "summary": summary[:120],
        "files_changed": files_changed or [],
    }

    if severity:
        entry["severity"] = severity
    if description:
        entry["description"] = description
    if related_audit:
        entry["related_audit"] = related_audit
    if tags:
        entry["tags"] = tags

    data["entries"].append(entry)
    save_changelog(data, filepath)

    log_ok(f"Changelog entry {entry['id']}: {summary}")
    return entry


def query_entries(entry_type=None, severity=None, file_pattern=None,
                  tag=None, since=None, limit=50, filepath=CHANGELOG_JSON):
    """
    Query changelog entries with optional filters.

    Args:
        entry_type: Filter by type
        severity: Filter by severity
        file_pattern: Glob pattern to match against files_changed (e.g. "*scraper*")
        tag: Filter by tag
        since: ISO date string (e.g. "2026-02-20") — entries on or after this date
        limit: Max entries to return
    """
    data = load_changelog(filepath)
    results = []

    for entry in reversed(data["entries"]):  # newest first
        if entry_type and entry.get("type") != entry_type:
            continue
        if severity and entry.get("severity") != severity:
            continue
        if tag and tag not in entry.get("tags", []):
            continue
        if since:
            entry_date = entry.get("timestamp", "")[:10]
            if entry_date < since:
                continue
        if file_pattern:
            files = entry.get("files_changed", [])
            if not any(fnmatch(f, file_pattern) for f in files):
                continue

        results.append(entry)
        if len(results) >= limit:
            break

    return results


def get_stats(since=None, filepath=CHANGELOG_JSON):
    """Return summary stats: count by type, count by severity, files most changed."""
    entries = query_entries(since=since, limit=10000, filepath=filepath)

    by_type = {}
    by_severity = {}
    file_counts = {}

    for entry in entries:
        t = entry.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

        s = entry.get("severity")
        if s:
            by_severity[s] = by_severity.get(s, 0) + 1

        for f in entry.get("files_changed", []):
            file_counts[f] = file_counts.get(f, 0) + 1

    # Top 10 most-changed files
    top_files = sorted(file_counts.items(), key=lambda x: -x[1])[:10]

    return {
        "total_entries": len(entries),
        "by_type": by_type,
        "by_severity": by_severity,
        "top_files_changed": top_files,
        "date_range": {
            "earliest": entries[-1]["timestamp"][:10] if entries else None,
            "latest": entries[0]["timestamp"][:10] if entries else None,
        }
    }


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def generate_markdown(data=None, filepath=CHANGELOG_MD):
    """Generate human-readable CHANGELOG.md grouped by date, then by type."""
    if data is None:
        data = load_changelog()

    lines = [
        "# Changelog",
        "",
        "Auto-generated from `docs/changelog.json` by `execution/changelog_manager.py`.",
        "Do not edit manually.",
        "",
    ]

    # Group entries by date
    by_date = {}
    for entry in data["entries"]:
        date = entry.get("timestamp", "")[:10]
        by_date.setdefault(date, []).append(entry)

    # Sort dates descending
    type_labels = {
        "fix": "Fixes",
        "feature": "Features",
        "refactor": "Refactors",
        "audit": "Audits",
        "directive": "Directive Updates",
        "deprecation": "Deprecations",
    }

    for date in sorted(by_date.keys(), reverse=True):
        lines.append(f"## {date}")
        lines.append("")

        # Group by type within date
        by_type = {}
        for entry in by_date[date]:
            t = entry.get("type", "other")
            by_type.setdefault(t, []).append(entry)

        for t in VALID_TYPES:
            if t not in by_type:
                continue
            lines.append(f"### {type_labels.get(t, t.title())}")
            lines.append("")
            for entry in by_type[t]:
                sev = entry.get("severity", "")
                badge = f"**[{sev.upper()}]** " if sev else ""
                files = ", ".join(f"`{f}`" for f in entry.get("files_changed", []))
                file_str = f" -- {files}" if files else ""
                lines.append(f"- {badge}{entry['summary']}{file_str}")
            lines.append("")

    os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    return filepath


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_add(args):
    entry = add_entry(
        entry_type=args.type,
        summary=args.summary,
        files_changed=args.files or [],
        severity=args.severity,
        description=args.description,
        related_audit=args.related_audit,
        tags=args.tags,
    )
    print(f"Entry ID: {entry['id']}")
    return 0


def cmd_query(args):
    results = query_entries(
        entry_type=args.type,
        severity=args.severity,
        file_pattern=args.file,
        tag=args.tag,
        since=args.since,
        limit=args.limit or 50,
    )
    if not results:
        print("No matching entries found.")
        return 0

    for entry in results:
        sev = f" [{entry['severity'].upper()}]" if entry.get('severity') else ""
        files = ", ".join(entry.get("files_changed", []))
        print(f"  {entry['id']}  {entry['type']}{sev}  {entry['summary']}")
        if files:
            print(f"    Files: {files}")
    print(f"\n{len(results)} entries found.")
    return 0


def cmd_report(args):
    data = load_changelog()
    path = generate_markdown(data)
    log_ok(f"Generated {path} ({len(data['entries'])} entries)")
    return 0


def cmd_stats(args):
    stats = get_stats(since=args.since)

    print(f"\n{'='*50}")
    print("CHANGELOG STATS")
    print(f"{'='*50}")
    print(f"Total entries: {stats['total_entries']}")

    if stats['date_range']['earliest']:
        print(f"Date range: {stats['date_range']['earliest']} — {stats['date_range']['latest']}")

    if stats['by_type']:
        print(f"\nBy type:")
        for t, count in sorted(stats['by_type'].items(), key=lambda x: -x[1]):
            print(f"  {t:15s} {count}")

    if stats['by_severity']:
        print(f"\nBy severity:")
        for s, count in sorted(stats['by_severity'].items(), key=lambda x: -x[1]):
            print(f"  {s:15s} {count}")

    if stats['top_files_changed']:
        print(f"\nTop changed files:")
        for f, count in stats['top_files_changed']:
            print(f"  [{count}] {f}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Changelog Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # add
    p_add = subparsers.add_parser("add", help="Add a changelog entry")
    p_add.add_argument("--type", required=True, choices=VALID_TYPES)
    p_add.add_argument("--summary", required=True, help="One-line description")
    p_add.add_argument("--files", nargs="+", help="Files changed")
    p_add.add_argument("--severity", choices=VALID_SEVERITIES)
    p_add.add_argument("--description", help="Longer explanation")
    p_add.add_argument("--related-audit", help="Related audit finding ID")
    p_add.add_argument("--tags", nargs="+", help="Tags for querying")

    # query
    p_query = subparsers.add_parser("query", help="Query changelog entries")
    p_query.add_argument("--type", choices=VALID_TYPES)
    p_query.add_argument("--severity", choices=VALID_SEVERITIES)
    p_query.add_argument("--file", help="Glob pattern for files (e.g. *scraper*)")
    p_query.add_argument("--tag", help="Filter by tag")
    p_query.add_argument("--since", help="Entries on or after this date (YYYY-MM-DD)")
    p_query.add_argument("--limit", type=int, default=50)

    # report
    subparsers.add_parser("report", help="Regenerate CHANGELOG.md")

    # stats
    p_stats = subparsers.add_parser("stats", help="Show changelog statistics")
    p_stats.add_argument("--since", help="Stats from this date onward (YYYY-MM-DD)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    handlers = {
        "add": cmd_add,
        "query": cmd_query,
        "report": cmd_report,
        "stats": cmd_stats,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

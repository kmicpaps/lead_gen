# [HYBRID] — both importable library and standalone CLI
"""
Audit Logger — track audit findings, mark fixes, generate reports.

Stores audit records in docs/audit_log.json.

Usage:
    py execution/audit_logger.py start --scope full --summary "Audit Round 4"
    py execution/audit_logger.py finding --audit ID --severity high --category logic_error --summary "..." --file path
    py execution/audit_logger.py fix --finding ID --description "Changed X to Y"
    py execution/audit_logger.py open --severity high
    py execution/audit_logger.py report --audit ID
    py execution/audit_logger.py stats
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone

# Fix Windows console encoding for Unicode output
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_json, save_json, log_ok, log_info, log_warn, log_error

AUDIT_LOG_PATH = "docs/audit_log.json"

VALID_SEVERITIES = ("critical", "high", "medium", "low", "info")
VALID_STATUSES = ("open", "fixed", "wontfix", "deferred")
VALID_CATEGORIES = (
    "logic_error", "data_flow", "dead_code", "missing_feature",
    "documentation", "performance", "security", "style"
)


# ---------------------------------------------------------------------------
# Data I/O
# ---------------------------------------------------------------------------

def load_audit_log(filepath=AUDIT_LOG_PATH):
    """Load audit log or return empty structure."""
    if os.path.exists(filepath):
        try:
            return load_json(filepath)
        except (json.JSONDecodeError, ValueError) as e:
            log_warn(f"Corrupted audit log {filepath}: {e}. Starting fresh.")
            return {"version": 1, "audits": []}
    return {"version": 1, "audits": []}


def save_audit_log(data, filepath=AUDIT_LOG_PATH):
    """Save audit log JSON."""
    os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
    save_json(data, filepath)
    return filepath


def _generate_audit_id(existing_audits):
    """Generate audit ID: {YYYYMMDD}_{HHMMSS}_{seq}."""
    now = datetime.now(timezone.utc)
    prefix = now.strftime("%Y%m%d_%H%M%S")
    seq = 1
    for audit in existing_audits:
        if audit.get("id", "").startswith(prefix):
            try:
                existing_seq = int(audit["id"].split("_")[-1])
                seq = max(seq, existing_seq + 1)
            except (ValueError, IndexError):
                pass
    return f"{prefix}_{seq:03d}"


def _find_audit(data, audit_id):
    """Find audit by ID. Returns (index, audit_dict) or (None, None)."""
    for i, audit in enumerate(data["audits"]):
        if audit["id"] == audit_id:
            return i, audit
    return None, None


def _find_finding(data, finding_id):
    """Find a finding across all audits. Returns (audit_idx, finding_idx, finding_dict) or (None, None, None)."""
    for ai, audit in enumerate(data["audits"]):
        for fi, finding in enumerate(audit.get("findings", [])):
            if finding["id"] == finding_id:
                return ai, fi, finding
    return None, None, None


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def create_audit(scope, summary, files_reviewed=0, filepath=AUDIT_LOG_PATH):
    """
    Create a new audit record. Returns the audit dict with generated ID.

    Args:
        scope: "full", "execution", "directives", "skills", or specific file path
        summary: Description of the audit scope
        files_reviewed: Number of files reviewed (can be updated later)
    """
    data = load_audit_log(filepath)

    audit = {
        "id": _generate_audit_id(data["audits"]),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": scope,
        "summary": summary,
        "stats": {
            "files_reviewed": files_reviewed,
            "findings_total": 0,
            "findings_by_severity": {},
        },
        "findings": [],
    }

    data["audits"].append(audit)
    save_audit_log(data, filepath)

    log_ok(f"Created audit {audit['id']}: {summary}")
    return audit


def add_finding(audit_id, severity, category, summary, file,
                line=None, description=None, filepath=AUDIT_LOG_PATH):
    """
    Add a finding to an existing audit. Returns the finding dict.

    Args:
        audit_id: Parent audit ID
        severity: critical, high, medium, low, info
        category: logic_error, data_flow, dead_code, etc.
        summary: One-line description
        file: Relative path to affected file
        line: Optional line number
        description: Optional detailed explanation
    """
    if severity not in VALID_SEVERITIES:
        raise ValueError(f"Invalid severity '{severity}'. Must be one of: {VALID_SEVERITIES}")
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category '{category}'. Must be one of: {VALID_CATEGORIES}")

    data = load_audit_log(filepath)
    idx, audit = _find_audit(data, audit_id)

    if audit is None:
        raise ValueError(f"Audit '{audit_id}' not found")

    # Generate finding ID
    finding_seq = len(audit["findings"]) + 1
    finding_id = f"{audit_id}_F{finding_seq:02d}"

    finding = {
        "id": finding_id,
        "severity": severity,
        "status": "open",
        "category": category,
        "summary": summary,
        "file": file,
    }

    if line is not None:
        finding["line"] = line
    if description:
        finding["description"] = description

    audit["findings"].append(finding)

    # Update stats
    audit["stats"]["findings_total"] = len(audit["findings"])
    sev_counts = {}
    for f in audit["findings"]:
        s = f["severity"]
        sev_counts[s] = sev_counts.get(s, 0) + 1
    audit["stats"]["findings_by_severity"] = sev_counts

    save_audit_log(data, filepath)

    log_ok(f"Finding {finding_id} [{severity.upper()}]: {summary}")
    return finding


def update_finding(finding_id, status, fix_description=None,
                   fix_changelog_id=None, filepath=AUDIT_LOG_PATH):
    """
    Update a finding's status (fixed, wontfix, deferred).

    Args:
        finding_id: The finding ID to update
        status: New status (fixed, wontfix, deferred)
        fix_description: How it was fixed
        fix_changelog_id: Cross-reference to changelog entry
    """
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {VALID_STATUSES}")

    data = load_audit_log(filepath)
    ai, fi, finding = _find_finding(data, finding_id)

    if finding is None:
        raise ValueError(f"Finding '{finding_id}' not found")

    finding["status"] = status

    if status == "fixed":
        finding["fixed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if fix_description:
        finding["fix_description"] = fix_description
    if fix_changelog_id:
        finding["fix_changelog_id"] = fix_changelog_id

    save_audit_log(data, filepath)

    log_ok(f"Finding {finding_id} → {status}")
    return finding


def get_open_findings(severity=None, file_pattern=None, filepath=AUDIT_LOG_PATH):
    """Get all findings with status=open, optionally filtered."""
    from fnmatch import fnmatch

    data = load_audit_log(filepath)
    results = []

    for audit in data["audits"]:
        for finding in audit.get("findings", []):
            if finding.get("status") != "open":
                continue
            if severity and finding.get("severity") != severity:
                continue
            if file_pattern and not fnmatch(finding.get("file", ""), file_pattern):
                continue
            results.append({**finding, "audit_id": audit["id"]})

    return results


def generate_audit_report(audit_id=None, filepath=AUDIT_LOG_PATH):
    """
    Generate markdown summary for an audit (or all audits).

    Args:
        audit_id: Specific audit to report on (None = summary of all)

    Returns:
        Markdown string
    """
    data = load_audit_log(filepath)
    lines = []

    if audit_id:
        _, audit = _find_audit(data, audit_id)
        if not audit:
            return f"Audit '{audit_id}' not found."
        audits = [audit]
    else:
        audits = data["audits"]

    for audit in audits:
        lines.append(f"# {audit['summary']}")
        lines.append(f"**ID:** {audit['id']} | **Scope:** {audit['scope']} | **Date:** {audit['timestamp'][:10]}")
        lines.append(f"**Files reviewed:** {audit['stats']['files_reviewed']} | **Findings:** {audit['stats']['findings_total']}")
        lines.append("")

        # Stats
        sev = audit["stats"].get("findings_by_severity", {})
        if sev:
            parts = [f"{s}: {c}" for s, c in sorted(sev.items())]
            lines.append(f"**By severity:** {', '.join(parts)}")
            lines.append("")

        # Count by status
        status_counts = {}
        for f in audit.get("findings", []):
            st = f.get("status", "open")
            status_counts[st] = status_counts.get(st, 0) + 1
        if status_counts:
            parts = [f"{s}: {c}" for s, c in sorted(status_counts.items())]
            lines.append(f"**By status:** {', '.join(parts)}")
            lines.append("")

        # Findings by severity
        for sev_level in VALID_SEVERITIES:
            findings = [f for f in audit.get("findings", []) if f["severity"] == sev_level]
            if not findings:
                continue

            lines.append(f"## {sev_level.upper()} ({len(findings)})")
            lines.append("")
            lines.append("| # | Status | File | Summary |")
            lines.append("|---|--------|------|---------|")
            for f in findings:
                status_icon = {"open": "OPEN", "fixed": "FIXED", "wontfix": "WONTFIX", "deferred": "DEFER"}.get(f["status"], f["status"])
                line_str = f":{f['line']}" if f.get('line') else ""
                lines.append(f"| {f['id']} | {status_icon} | `{f['file']}{line_str}` | {f['summary']} |")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def get_audit_stats(filepath=AUDIT_LOG_PATH):
    """Summary: total audits, open findings by severity, fix rate, common categories."""
    data = load_audit_log(filepath)

    total_audits = len(data["audits"])
    all_findings = []
    for audit in data["audits"]:
        all_findings.extend(audit.get("findings", []))

    total_findings = len(all_findings)
    open_count = sum(1 for f in all_findings if f.get("status") == "open")
    fixed_count = sum(1 for f in all_findings if f.get("status") == "fixed")
    fix_rate = (fixed_count / total_findings * 100) if total_findings > 0 else 0

    open_by_severity = {}
    for f in all_findings:
        if f.get("status") == "open":
            s = f["severity"]
            open_by_severity[s] = open_by_severity.get(s, 0) + 1

    by_category = {}
    for f in all_findings:
        c = f.get("category", "unknown")
        by_category[c] = by_category.get(c, 0) + 1

    return {
        "total_audits": total_audits,
        "total_findings": total_findings,
        "open_findings": open_count,
        "fixed_findings": fixed_count,
        "fix_rate_pct": round(fix_rate, 1),
        "open_by_severity": open_by_severity,
        "by_category": by_category,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_start(args):
    audit = create_audit(
        scope=args.scope,
        summary=args.summary,
        files_reviewed=args.files_reviewed or 0,
    )
    print(f"Audit ID: {audit['id']}")
    return 0


def cmd_finding(args):
    finding = add_finding(
        audit_id=args.audit,
        severity=args.severity,
        category=args.category,
        summary=args.summary,
        file=args.file,
        line=args.line,
        description=args.description,
    )
    print(f"Finding ID: {finding['id']}")
    return 0


def cmd_fix(args):
    update_finding(
        finding_id=args.finding,
        status="fixed",
        fix_description=args.description,
        fix_changelog_id=args.changelog_id,
    )
    return 0


def cmd_open(args):
    findings = get_open_findings(severity=args.severity, file_pattern=args.file)
    if not findings:
        print("No open findings.")
        return 0

    print(f"\n{'='*60}")
    print(f"OPEN FINDINGS ({len(findings)})")
    print(f"{'='*60}")
    for f in findings:
        line_str = f":{f['line']}" if f.get('line') else ""
        print(f"  [{f['severity'].upper():8s}] {f['id']}  {f['file']}{line_str}")
        print(f"             {f['summary']}")
    return 0


def cmd_report(args):
    report = generate_audit_report(audit_id=args.audit)
    print(report)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        log_ok(f"Report saved to {args.output}")
    return 0


def cmd_stats(args):
    stats = get_audit_stats()

    print(f"\n{'='*50}")
    print("AUDIT STATS")
    print(f"{'='*50}")
    print(f"Total audits:    {stats['total_audits']}")
    print(f"Total findings:  {stats['total_findings']}")
    print(f"  Open:          {stats['open_findings']}")
    print(f"  Fixed:         {stats['fixed_findings']}")
    print(f"  Fix rate:      {stats['fix_rate_pct']}%")

    if stats['open_by_severity']:
        print(f"\nOpen by severity:")
        for s, c in sorted(stats['open_by_severity'].items()):
            print(f"  {s:15s} {c}")

    if stats['by_category']:
        print(f"\nAll findings by category:")
        for cat, c in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
            print(f"  {cat:20s} {c}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Audit Logger")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # start
    p_start = subparsers.add_parser("start", help="Start a new audit")
    p_start.add_argument("--scope", required=True, help="full, execution, directives, skills, or file path")
    p_start.add_argument("--summary", required=True, help="Audit description")
    p_start.add_argument("--files-reviewed", type=int, help="Number of files reviewed")

    # finding
    p_find = subparsers.add_parser("finding", help="Log an audit finding")
    p_find.add_argument("--audit", required=True, help="Parent audit ID")
    p_find.add_argument("--severity", required=True, choices=VALID_SEVERITIES)
    p_find.add_argument("--category", required=True, choices=VALID_CATEGORIES)
    p_find.add_argument("--summary", required=True, help="One-line description")
    p_find.add_argument("--file", required=True, help="Affected file path")
    p_find.add_argument("--line", type=int, help="Line number")
    p_find.add_argument("--description", help="Detailed explanation")

    # fix
    p_fix = subparsers.add_parser("fix", help="Mark a finding as fixed")
    p_fix.add_argument("--finding", required=True, help="Finding ID")
    p_fix.add_argument("--description", help="How it was fixed")
    p_fix.add_argument("--changelog-id", help="Related changelog entry ID")

    # open
    p_open = subparsers.add_parser("open", help="List open findings")
    p_open.add_argument("--severity", choices=VALID_SEVERITIES)
    p_open.add_argument("--file", help="Glob pattern for file filter")

    # report
    p_report = subparsers.add_parser("report", help="Generate audit report")
    p_report.add_argument("--audit", help="Specific audit ID (default: all)")
    p_report.add_argument("--output", help="Write report to file")

    # stats
    subparsers.add_parser("stats", help="Show audit statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    handlers = {
        "start": cmd_start,
        "finding": cmd_finding,
        "fix": cmd_fix,
        "open": cmd_open,
        "report": cmd_report,
        "stats": cmd_stats,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

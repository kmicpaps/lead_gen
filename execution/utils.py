# [LIBRARY] — imported by other scripts, not run directly
"""
Shared utilities for the lead generation pipeline.

Centralizes common patterns duplicated across 40+ scripts:
- JSON file loading/saving (generic and lead-specific)
- Thread-safe rate limiting for API calls
- Consistent status logging prefixes
- Timestamped output file naming

Usage:
    from utils import load_leads, save_leads, get_output_path
    from utils import load_json, save_json
    from utils import RateLimiter
    from utils import log_ok, log_error, log_warn, log_info, log_progress
"""

import os
import sys
import json
import time
import threading
from datetime import datetime

# Auto-setup sibling imports so scripts can do `from utils import ...`
# and then also `from apollo_url_parser import ...` without extra path setup
_execution_dir = os.path.dirname(os.path.abspath(__file__))
if _execution_dir not in sys.path:
    sys.path.insert(0, _execution_dir)


def load_leads(filepath):
    """
    Load leads from a JSON file.

    Args:
        filepath: Path to JSON file containing a list of lead dicts

    Returns:
        list[dict]: List of lead dictionaries

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not a JSON list
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        leads = json.load(f)

    if not isinstance(leads, list):
        raise ValueError(f"Expected JSON list, got {type(leads).__name__} in {filepath}")

    return leads


def save_leads(leads, output_dir, prefix, suffix=""):
    """
    Save leads to a timestamped JSON file.

    Creates the output directory if it doesn't exist.
    Filename pattern: {prefix}{suffix}_{YYYYMMDD_HHMMSS}_{count}leads.json

    Args:
        leads: List of lead dicts to save
        output_dir: Directory to write the file (created if missing)
        prefix: Filename prefix (e.g. "filtered", "verified", "raw_leads")
        suffix: Optional suffix before timestamp (e.g. "_test")

    Returns:
        str: Full path to the saved file
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = get_output_path(output_dir, prefix, len(leads), suffix)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)

    return filepath


def get_output_path(output_dir, prefix, count, suffix=""):
    """
    Generate a timestamped output file path (without saving).

    Pattern: {output_dir}/{prefix}{suffix}_{YYYYMMDD_HHMMSS}_{count}leads.json

    Args:
        output_dir: Output directory
        prefix: Filename prefix
        count: Lead count (appears in filename)
        suffix: Optional suffix (e.g. "_test")

    Returns:
        str: Full file path
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}{suffix}_{timestamp}_{count}leads.json"
    return os.path.join(output_dir, filename)


# ---------------------------------------------------------------------------
# Generic JSON I/O (for dicts, configs, caches — not just lead lists)
# ---------------------------------------------------------------------------

def load_json(filepath):
    """
    Load any JSON file (dict, list, or scalar).

    Unlike load_leads(), this does NOT validate the result type.
    Use for client.json, mapping caches, config files, etc.

    Args:
        filepath: Path to JSON file

    Returns:
        Parsed JSON (any type)

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data, filepath, mkdir=False):
    """
    Save data to a JSON file with consistent encoding.

    Args:
        data: Any JSON-serializable object
        filepath: Full destination path
        mkdir: If True, create parent directories

    Returns:
        str: The filepath written to
    """
    if mkdir:
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return filepath


# ---------------------------------------------------------------------------
# Thread-safe rate limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """
    Thread-safe interval-based rate limiter.

    Usage:
        limiter = RateLimiter(requests_per_second=5)
        limiter.acquire()  # blocks until next request is allowed
    """

    def __init__(self, requests_per_second):
        self.interval = 1.0 / requests_per_second
        self._lock = threading.Lock()
        self._last_request = 0.0

    def acquire(self):
        """Block until the next request is allowed."""
        with self._lock:
            now = time.time()
            wait = self._last_request + self.interval - now
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.time()


# ---------------------------------------------------------------------------
# Status logging helpers (optional — standardize output prefixes)
# ---------------------------------------------------------------------------

def log_ok(msg):
    """Print a success message."""
    print(f"[OK] {msg}")


def log_warn(msg):
    """Print a warning message."""
    print(f"[WARN] {msg}")


def log_error(msg):
    """Print an error message."""
    print(f"[ERROR] {msg}")


def log_info(msg):
    """Print an informational message."""
    print(f"[INFO] {msg}")


def log_skip(msg):
    """Print a skip/bypass message."""
    print(f"[SKIP] {msg}")


def log_result(msg):
    """Print a result/output path message."""
    print(f"[RESULT] {msg}")


def log_progress(current, total, extra=""):
    """Print a progress update with percentage."""
    pct = (current / total * 100) if total > 0 else 0
    msg = f"[PROGRESS] {current}/{total} ({pct:.0f}%)"
    if extra:
        msg += f" | {extra}"
    print(msg)

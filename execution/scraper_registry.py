# [LIBRARY] — imported by other scripts, not run directly
"""
Scraper Registry — Single source of truth for all scraper metadata.

Used by:
- fast_lead_orchestrator.py (scraper selection, command building, output discovery)
- filter_gap_analyzer.py (filter support per scraper)
- post_scrape_filter.py (imports SCRAPER_SUPPORT from here)
- pre_flight display (filter mapping display)

Adding a new scraper:
1. Add an entry to SCRAPER_REGISTRY below
2. Write the scraper script in execution/
3. Add a normalize_<name>() function + elif branch to lead_normalizer.py
"""

import os
import sys
import re

# Ensure sibling imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

SCRAPER_REGISTRY = {
    "olympus": {
        # Identity
        "display_name": "Olympus",
        "script": "execution/scraper_olympus_b2b_finder.py",

        # Command template — {script}, {apollo_url}, {max_leads} are interpolated
        # country_arg is appended only when country is provided
        "cli_template": 'py {script} --apollo-url "{apollo_url}" --max-leads {max_leads}',
        "country_arg": "--country {country}",

        # Output (used by orchestrator for file discovery + campaign copy)
        "output_dir": ".tmp/b2b_finder",
        "output_prefix": "b2b_leads",
        "campaign_filename": "olympus_leads.json",

        # Limits
        "max_leads": None,       # No internal cap
        "min_leads": None,
        "test_leads": None,      # Test mode not supported

        # Auth
        "needs_cookies": True,
        "cookie_exit_code": 2,

        # Filter support (migrated from filter_gap_analyzer.py)
        "supported_filters": {
            "titles", "seniority", "industries", "keywords", "locations",
            "org_locations", "company_size", "email_status", "functions",
            "revenue", "funding"
        },

        # Location & industry behavior (for pre-flight display)
        "location_type": "org_location",
        "location_transform": None,        # Passes URL directly
        "industry_taxonomy": "apollo_native",
        "industry_transform": None,

        # Pre-flight display
        "preflight_notes": [
            "Passes Apollo URL directly to Apify actor",
            "Filters by: orgLocation (company HQ)",
            "Industries: Apollo hex IDs (no mapping needed)",
        ],
        "preflight_warnings": [],

        # Orchestrator behavior
        "role": "primary",       # "primary" runs first solo, "backup" runs in parallel
        "timeout": 600,
    },

    "codecrafter": {
        "display_name": "CodeCrafter",
        "script": "execution/scraper_codecrafter.py",
        "cli_template": 'py {script} --apollo-url "{apollo_url}" --max-leads {max_leads}',
        "country_arg": None,     # CC doesn't take --country

        "output_dir": ".tmp/codecrafter",
        "output_prefix": "codecrafter_leads",
        "campaign_filename": "codecrafter_leads.json",

        "max_leads": 5000,
        "min_leads": 25,
        "test_leads": 25,

        "needs_cookies": False,
        "cookie_exit_code": None,

        "supported_filters": {
            "titles", "seniority", "industries", "keywords", "locations",
            "org_locations", "company_size", "functions", "revenue", "funding"
        },

        "location_type": "contact_location",
        "location_transform": "lowercase",
        "industry_taxonomy": "v1",
        "industry_transform": "lowercase",

        "preflight_notes": [
            "Filters by: contact_location (lowercase)",
        ],
        "preflight_warnings": [],

        "role": "backup",
        "timeout": 600,
    },

    "peakydev": {
        "display_name": "PeakyDev",
        "script": "execution/scraper_peakydev.py",
        "cli_template": 'py {script} --apollo-url "{apollo_url}" --max-leads {max_leads}',
        "country_arg": None,

        "output_dir": ".tmp/peakydev",
        "output_prefix": "peakydev_leads",
        "campaign_filename": "peakydev_leads.json",

        "max_leads": 5000,
        "min_leads": 1000,
        "test_leads": 1000,

        "needs_cookies": False,
        "cookie_exit_code": None,

        "supported_filters": {
            "titles", "seniority", "industries", "keywords",
            "org_locations", "locations", "company_size",
            "email_status", "functions", "revenue", "funding"
        },

        "location_type": "company_country",
        "location_transform": "title_case",
        "industry_taxonomy": "v2",
        "industry_transform": "v1_to_v2",

        "preflight_notes": [
            "Filters by companyCountry (company HQ) when org_locations set",
            "Filters by personCountry (where person lives) when person locations set",
            "Titles: lowercase via personTitle",
            "Seniority: mapped to PeakyDev labels (Founder, CXO, Director, etc.)",
        ],
        "preflight_warnings": [],

        "role": "backup",
        "timeout": 600,
    },
}


# ---------------------------------------------------------------------------
# Derived constants (backwards-compatible names for existing consumers)
# ---------------------------------------------------------------------------

# Used by filter_gap_analyzer.py and post_scrape_filter.py
SCRAPER_SUPPORT = {
    name: cfg["supported_filters"]
    for name, cfg in SCRAPER_REGISTRY.items()
}

# Valid scraper names (for --scrapers CLI validation)
VALID_SCRAPER_NAMES = set(SCRAPER_REGISTRY.keys())

# Primary scraper(s) — run first, before backup scrapers
PRIMARY_SCRAPERS = [
    name for name, cfg in SCRAPER_REGISTRY.items()
    if cfg["role"] == "primary"
]

# Backup scrapers — run in parallel after primary
BACKUP_SCRAPERS = [
    name for name, cfg in SCRAPER_REGISTRY.items()
    if cfg["role"] == "backup"
]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_scraper(name):
    """Get scraper config by name. Raises KeyError if not found."""
    if name not in SCRAPER_REGISTRY:
        raise KeyError(
            f"Unknown scraper '{name}'. "
            f"Valid scrapers: {', '.join(sorted(SCRAPER_REGISTRY.keys()))}"
        )
    return SCRAPER_REGISTRY[name]


def build_scraper_command(name, apollo_url, max_leads, country=None):
    """
    Build the CLI command string for a scraper.

    Clamps max_leads to scraper's min/max limits.
    Appends country_arg only if country is provided and scraper supports it.

    Returns:
        Command string ready for subprocess
    """
    config = get_scraper(name)

    # Clamp max_leads to scraper limits
    if config["max_leads"] and max_leads > config["max_leads"]:
        max_leads = config["max_leads"]
    if config["min_leads"] and max_leads < config["min_leads"]:
        max_leads = config["min_leads"]

    cmd = config["cli_template"].format(
        script=config["script"],
        apollo_url=apollo_url,
        max_leads=max_leads,
    )

    # Append country arg if scraper supports it and country is provided
    if country and config.get("country_arg"):
        cmd += " " + config["country_arg"].format(country=country)

    return cmd


def get_default_target(name, remaining, max_leads_mode):
    """
    Calculate target lead count for a scraper based on mode and limits.

    Args:
        name: Scraper registry key
        remaining: How many more leads the pipeline needs
        max_leads_mode: 'maximum' or 'target'

    Returns:
        int: Target lead count for this scraper
    """
    config = get_scraper(name)

    if max_leads_mode == 'maximum':
        return config["max_leads"] or 5000

    target = max(remaining, config["min_leads"] or 500)
    if config["max_leads"]:
        target = min(target, config["max_leads"])
    return target

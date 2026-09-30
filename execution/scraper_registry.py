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
        "max_leads": 50000,      # Actor cap per run
        "min_leads": 100,        # Actor rejects maxResults < 100
        "test_leads": 100,

        # Auth: actor is "[NO COOKIES]" since ~Sep 2026 (structured filters, no searchUrl)
        "needs_cookies": False,
        "cookie_exit_code": None,

        # Filter support (migrated from filter_gap_analyzer.py)
        "supported_filters": {
            "titles", "seniority", "industries", "keywords", "locations",
            "org_locations", "company_size"
        },

        # Location & industry behavior (for pre-flight display)
        "location_type": "company_country",
        "location_transform": "title_case",
        "industry_taxonomy": "v1",
        "industry_transform": None,

        # Pre-flight display
        "preflight_notes": [
            "Structured filters (no Apollo URL / cookies since Sep 2026)",
            "Filters by: companyCountry (company HQ); keywords -> webKeywords (strict match)",
            "Industries: resolved names, validated against live actor schema",
        ],
        "preflight_warnings": [
            "No email-status filter: emails are pattern guesses (email_status='guessed')",
        ],

        # Orchestrator behavior
        "timeout": 2700,

        # Pricing (USD per 1k leads; Apify BRONZE tier 2026-09-24, +$0.01 start)
        "pricing": {"cost_per_1k": 2.00},

        # Time benchmarks (observed real-world performance)
        "time_benchmark": {
            "observed_leads": 100,
            "observed_minutes": 1,   # 100 leads in 4-17 s (2026-09-24); conservative
            "leads_per_min": 300,
        },
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
            "org_locations", "company_size", "revenue", "funding"
        },

        "location_type": "contact_location",
        "location_transform": "lowercase",
        "industry_taxonomy": "v1",
        "industry_transform": "lowercase",

        "preflight_notes": [
            "Filters by: contact_location (lowercase)",
        ],
        "preflight_warnings": [],

        # 2026-09-24: 3,000 leads took >10 min (~300/min incl. startup); a 600 s
        # timeout dropped a SUCCEEDED, fully-billed run. Allow ~1 h.
        "timeout": 3600,

        # Pricing (USD per 1k leads, based on observed RapidAPI costs)
        "pricing": {"cost_per_1k": 2.00},

        # Time benchmarks (observed real-world performance)
        "time_benchmark": {
            "observed_leads": 10000,
            "observed_minutes": 29,
            "leads_per_min": 345,
        },
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
        "min_leads": 100,        # Actor minimum since 2026-09-21 (was 1000)
        "test_leads": 100,

        "needs_cookies": False,
        "cookie_exit_code": None,

        "supported_filters": {
            "titles", "seniority", "industries", "keywords",
            "org_locations", "locations", "company_size", "revenue"
        },

        "location_type": "company_country",
        "location_transform": "title_case",
        "industry_taxonomy": "v2",
        "industry_transform": "v1_to_v2",

        "preflight_notes": [
            "Filters by companyCountry (company HQ) when org_locations set",
            "Filters by personCountry (where person lives) when person locations set",
            "Titles: personTitle; keywords -> webKeywords (strict match)",
            "Seniority: Apollo's own lowercase values",
        ],
        "preflight_warnings": [
            "No email-status filter since 2026-09-21: enforce --require-email afterwards",
        ],

        "timeout": 600,

        # Pricing (USD per 1k leads; Apify BRONZE tier 2026-09-24, +$0.10 start)
        "pricing": {"cost_per_1k": 1.70},

        # Time benchmarks (observed real-world performance)
        "time_benchmark": {
            "observed_leads": 4000,
            "observed_minutes": 14,
            "leads_per_min": 286,
        },
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

# All scraper names in registry order
ALL_SCRAPERS = list(SCRAPER_REGISTRY.keys())


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


def estimate_time(name, target_leads):
    """Estimate scrape time in minutes based on observed benchmarks."""
    config = get_scraper(name)
    benchmark = config.get("time_benchmark", {})
    leads_per_min = benchmark.get("leads_per_min", 100)
    return max(1, round(target_leads / leads_per_min))


def estimate_cost(name, target_leads):
    """Estimate cost in USD for target_leads."""
    config = get_scraper(name)
    cost_per_1k = config.get("pricing", {}).get("cost_per_1k", 0)
    return cost_per_1k * target_leads / 1000


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

    target = max(remaining, config["min_leads"] if config["min_leads"] is not None else 0)
    if config["max_leads"]:
        target = min(target, config["max_leads"])
    return target

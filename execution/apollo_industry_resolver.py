# [CLI] — run via: py execution/apollo_industry_resolver.py --help
"""
Apollo Industry ID Resolver

Resolves Apollo.io hex-encoded industry tag IDs (MongoDB ObjectIDs) to
human-readable industry names. These IDs appear in Apollo search URLs as
`organizationIndustryTagIds[]` parameters.

Strategy:
1. Learned mappings: Persistent JSON file (146+ verified mappings)
2. Dynamic learning: Mine Olympus scraper output for industry names
3. Cache: Save/load campaign-specific industry intent

When new IDs are discovered, use --add to save them permanently to the
learned mappings file.

Usage:
    # As module
    from apollo_industry_resolver import resolve_industry_ids, resolve_industry_names_to_hex

    # As CLI
    py execution/apollo_industry_resolver.py --resolve 5567cd4773696439b1130000
    py execution/apollo_industry_resolver.py --reverse-lookup "Construction,Retail,Banking"
    py execution/apollo_industry_resolver.py --apollo-url "https://..." --olympus-file leads.json
    py execution/apollo_industry_resolver.py --list-known
    py execution/apollo_industry_resolver.py --add 5567e0e0736964198de70700 "Construction"
    py execution/apollo_industry_resolver.py --list-learned
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_json, save_json, load_leads


# ---------------------------------------------------------------------------
# Static mapping: REMOVED
# All mappings now live in apollo_industry_learned_mappings.json (loaded below).
# The old static map had 30/33 wrong hex IDs (sourced from unreliable data).
# Correct IDs were manually verified from Apollo's UI on 2026-02-24.
# ---------------------------------------------------------------------------
APOLLO_INDUSTRY_MAP = {}


# ---------------------------------------------------------------------------
# Persistent learned mappings
# Stored in a JSON sidecar file so they survive across sessions.
# Loaded at module init and merged into APOLLO_INDUSTRY_MAP.
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_LEARNED_MAPPINGS_FILE = os.path.join(_SCRIPT_DIR, "apollo_industry_learned_mappings.json")


def _load_learned_mappings() -> int:
    """Load learned mappings from JSON file and merge into the static map."""
    if os.path.isfile(_LEARNED_MAPPINGS_FILE):
        try:
            learned = load_json(_LEARNED_MAPPINGS_FILE)
            APOLLO_INDUSTRY_MAP.update(learned)
            return len(learned)
        except (json.JSONDecodeError, IOError) as e:
            print(f"WARNING: Could not load learned mappings: {e}", file=sys.stderr)
    return 0


def _save_learned_mapping(hex_id: str, industry_name: str):
    """Persist a single mapping to the learned mappings file."""
    learned = {}
    if os.path.isfile(_LEARNED_MAPPINGS_FILE):
        try:
            learned = load_json(_LEARNED_MAPPINGS_FILE)
        except (json.JSONDecodeError, IOError):
            pass
    learned[hex_id] = industry_name
    save_json(learned, _LEARNED_MAPPINGS_FILE)


# Load learned mappings on module import
_LEARNED_COUNT = _load_learned_mappings()


# ---------------------------------------------------------------------------
# LinkedIn V1 Industry Taxonomy (all 147 unique names)
# Uses "&" format to match Apollo's actual output.
# The is_valid_industry() function normalizes "and" <-> "&" for comparison.
# ---------------------------------------------------------------------------
LINKEDIN_INDUSTRIES = frozenset({
    "Accounting",
    "Airlines/Aviation",
    "Alternative Dispute Resolution",
    "Alternative Medicine",
    "Animation",
    "Apparel & Fashion",
    "Architecture & Planning",
    "Arts & Crafts",
    "Automotive",
    "Aviation & Aerospace",
    "Banking",
    "Biotechnology",
    "Broadcast Media",
    "Building Materials",
    "Business Supplies & Equipment",
    "Capital Markets",
    "Chemicals",
    "Civic & Social Organization",
    "Civil Engineering",
    "Commercial Real Estate",
    "Computer & Network Security",
    "Computer Games",
    "Computer Hardware",
    "Computer Networking",
    "Computer Software",
    "Construction",
    "Consumer Electronics",
    "Consumer Goods",
    "Consumer Services",
    "Cosmetics",
    "Dairy",
    "Defense & Space",
    "Design",
    "Education Management",
    "E-Learning",
    "Electrical/Electronic Manufacturing",
    "Entertainment",
    "Environmental Services",
    "Events Services",
    "Executive Office",
    "Facilities Services",
    "Farming",
    "Financial Services",
    "Fine Art",
    "Fishery",
    "Food & Beverages",
    "Food Production",
    "Fund-Raising",
    "Furniture",
    "Gambling & Casinos",
    "Glass, Ceramics & Concrete",
    "Government Administration",
    "Government Relations",
    "Graphic Design",
    "Health, Wellness & Fitness",
    "Higher Education",
    "Hospital & Health Care",
    "Hospitality",
    "Human Resources",
    "Import & Export",
    "Individual & Family Services",
    "Industrial Automation",
    "Information Services",
    "Information Technology & Services",
    "Insurance",
    "International Affairs",
    "International Trade & Development",
    "Internet",
    "Investment Banking",
    "Investment Management",
    "Judiciary",
    "Law Enforcement",
    "Law Practice",
    "Legal Services",
    "Legislative Office",
    "Leisure, Travel & Tourism",
    "Libraries",
    "Logistics & Supply Chain",
    "Luxury Goods & Jewelry",
    "Machinery",
    "Management Consulting",
    "Maritime",
    "Market Research",
    "Marketing & Advertising",
    "Mechanical or Industrial Engineering",
    "Media Production",
    "Medical Devices",
    "Medical Practice",
    "Mental Health Care",
    "Military",
    "Mining & Metals",
    "Motion Pictures & Film",
    "Museums & Institutions",
    "Music",
    "Nanotechnology",
    "Newspapers",
    "Non-Profit Organization Management",
    "Oil & Energy",
    "Online Media",
    "Outsourcing/Offshoring",
    "Package/Freight Delivery",
    "Packaging & Containers",
    "Paper & Forest Products",
    "Performing Arts",
    "Pharmaceuticals",
    "Philanthropy",
    "Photography",
    "Plastics",
    "Political Organization",
    "Primary/Secondary Education",
    "Printing",
    "Professional Training & Coaching",
    "Program Development",
    "Public Policy",
    "Public Relations & Communications",
    "Public Safety",
    "Publishing",
    "Railroad Manufacture",
    "Ranching",
    "Real Estate",
    "Recreational Facilities & Services",
    "Religious Institutions",
    "Renewables & Environment",
    "Research",
    "Restaurants",
    "Retail",
    "Security & Investigations",
    "Semiconductors",
    "Shipbuilding",
    "Sporting Goods",
    "Sports",
    "Staffing & Recruiting",
    "Supermarkets",
    "Telecommunications",
    "Textiles",
    "Think Tanks",
    "Tobacco",
    "Translation & Localization",
    "Transportation/Trucking/Railroad",
    "Utilities",
    "Venture Capital & Private Equity",
    "Veterinary",
    "Warehousing",
    "Wholesale",
    "Wine & Spirits",
    "Wireless",
    "Writing & Editing",
})

# Pre-computed normalized set for fast validation lookups.
# Keys are lowercased with " and " replaced by " & ".
_LINKEDIN_INDUSTRIES_NORMALIZED = frozenset(
    name.lower().strip().replace(' and ', ' & ') for name in LINKEDIN_INDUSTRIES
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_industry_ids(hex_ids: list) -> tuple:
    """
    Convert Apollo hex industry tag IDs to human-readable names.
    Returns (resolved: list[str], unresolved: list[str])
    """
    resolved = []
    unresolved = []
    for hid in hex_ids:
        name = APOLLO_INDUSTRY_MAP.get(hid)
        if name:
            if name not in resolved:
                resolved.append(name)
        else:
            unresolved.append(hid)
    return resolved, unresolved


def learn_from_olympus(olympus_leads: list) -> list:
    """
    Extract unique industry text names from Olympus scraper output.
    Olympus returns industry in various locations depending on data format:
    - Raw format: organization.industries (list of strings, lowercase)
    - Raw format: organization.industry (string)
    - Pre-normalized: industry (string)
    Returns sorted list of unique industry names found (title-cased).
    """
    industries = set()
    for lead in olympus_leads:
        found = []

        # Check flat field first (pre-normalized format)
        if lead.get('industry'):
            found.append(str(lead['industry']).strip())

        # Check organization object (raw format)
        org = None
        if isinstance(lead.get('organization'), dict):
            org = lead['organization']
        elif isinstance(lead.get('org_name'), dict):
            org = lead['org_name']

        if org:
            # Check 'industries' (plural, list of strings - raw Apollo format)
            if isinstance(org.get('industries'), list):
                for item in org['industries']:
                    if isinstance(item, str) and item.strip():
                        found.append(item.strip())
            # Check 'industry' (singular string)
            elif org.get('industry'):
                found.append(str(org['industry']).strip())

        for val in found:
            if val and val not in ('[]', '{}', 'None', 'nan'):
                # Title-case for consistency (raw data is often lowercase)
                # But preserve special patterns like &, /
                normalized = _title_case_industry(val)
                industries.add(normalized)

    return sorted(industries)


def _title_case_industry(name: str) -> str:
    """
    Title-case an industry name while preserving special patterns.
    'building materials' -> 'Building Materials'
    'food & beverages' -> 'Food & Beverages'
    'information technology & services' -> 'Information Technology & Services'
    """
    # If already title-cased or mixed case, return as-is
    if name != name.lower():
        return name
    # Title case each word, but keep '&', '/', 'or' lowercase-aware
    words = name.split()
    result = []
    for i, word in enumerate(words):
        if word in ('&', 'or', '/') and i > 0:
            result.append(word)
        elif '/' in word:
            # Handle "transportation/trucking/railroad"
            result.append('/'.join(w.capitalize() for w in word.split('/')))
        else:
            result.append(word.capitalize())
    return ' '.join(result)


def get_intended_industries(apollo_filters: dict, olympus_leads: list = None,
                            cache_path: str = None) -> dict:
    """
    Determine the intended industries for a campaign by combining:
    1. Resolved hex IDs from Apollo URL (static mapping)
    2. Industry names mined from Olympus output (dynamic learning)
    3. Keyword tags from Apollo URL (semantic intent)

    Args:
        apollo_filters: Parsed Apollo URL filters (from apollo_url_parser.parse_apollo_url)
        olympus_leads: Optional list of raw Olympus leads to mine
        cache_path: Optional path to save/load cached intent

    Returns dict with:
        - resolved: list of industry names from hex ID resolution
        - unresolved_ids: list of hex IDs that couldn't be resolved
        - olympus_industries: list of industries from Olympus output
        - keywords: list of keyword tags from Apollo URL
        - all_intended: combined deduplicated list of all intended industries
    """
    # 1. Resolve hex IDs
    hex_ids = apollo_filters.get('industries', [])
    resolved, unresolved = resolve_industry_ids(hex_ids)

    # 2. Mine Olympus output if available
    olympus_industries = []
    if olympus_leads:
        olympus_industries = learn_from_olympus(olympus_leads)

    # 3. Try loading from cache if no Olympus data
    if not olympus_industries and cache_path and os.path.exists(cache_path):
        try:
            cached = load_json(cache_path)
            olympus_industries = cached.get('olympus_industries', [])
        except (json.JSONDecodeError, IOError):
            pass

    # 4. Get keywords from Apollo URL
    keywords = apollo_filters.get('keywords', [])

    # 5. Combine all intended industries (deduplicated, order-preserving)
    all_intended = list(dict.fromkeys(resolved + olympus_industries))

    result = {
        'resolved': resolved,
        'unresolved_ids': unresolved,
        'olympus_industries': olympus_industries,
        'keywords': keywords,
        'all_intended': all_intended,
    }

    # 6. Save to cache if path provided
    if cache_path:
        try:
            save_json(result, cache_path, mkdir=True)
        except IOError:
            pass

    return result


def _normalize_industry(name: str) -> str:
    """Normalize an industry name for comparison: lowercase + 'and' -> '&'."""
    return name.lower().strip().replace(' and ', ' & ')


def is_valid_industry(name: str) -> bool:
    """
    Check if an industry name is in the LinkedIn V1 taxonomy.
    Normalizes both 'and' and '&' so either format matches.
    """
    return _normalize_industry(name) in _LINKEDIN_INDUSTRIES_NORMALIZED


def resolve_industry_names_to_hex(industry_names: list) -> tuple:
    """
    Convert industry names to hex IDs (reverse of resolve_industry_ids).

    Returns: (resolved: dict{name: hex_id}, unresolved: list[name])
    Handles '&' vs 'and' normalization automatically.
    """
    # Build reverse map: name -> hex_id (normalized key for matching)
    reverse_map = {}
    for hex_id, name in APOLLO_INDUSTRY_MAP.items():
        reverse_map[_normalize_industry(name)] = (name, hex_id)

    resolved = {}
    unresolved = []
    for input_name in industry_names:
        norm = _normalize_industry(input_name)
        if norm in reverse_map:
            canonical_name, hex_id = reverse_map[norm]
            resolved[canonical_name] = hex_id
        else:
            unresolved.append(input_name)
    return resolved, unresolved


def add_mapping(hex_id: str, industry_name: str, persist: bool = True):
    """
    Add a new hex ID to industry name mapping.
    If persist=True (default), saves to the learned mappings JSON file
    so the mapping is available in all future runs.
    """
    APOLLO_INDUSTRY_MAP[hex_id] = industry_name
    if persist:
        _save_learned_mapping(hex_id, industry_name)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    """CLI: resolve hex IDs, show mappings, or add new mappings."""
    import argparse
    parser = argparse.ArgumentParser(description='Apollo Industry ID Resolver')
    parser.add_argument('--resolve', nargs='+', help='Hex IDs to resolve')
    parser.add_argument('--list-known', action='store_true', help='List all known mappings')
    parser.add_argument('--list-learned', action='store_true', help='List only learned (persistent) mappings')
    parser.add_argument('--add', nargs=2, metavar=('HEX_ID', 'INDUSTRY_NAME'),
                        help='Add a hex ID -> industry name mapping permanently')
    parser.add_argument('--force', action='store_true',
                        help='Force add mapping even if name not in LinkedIn taxonomy')
    parser.add_argument('--reverse-lookup', help='Comma-separated industry names to convert to hex IDs')
    parser.add_argument('--apollo-url', help='Parse Apollo URL and resolve industries')
    parser.add_argument('--olympus-file', help='Path to Olympus leads JSON to learn from')
    parser.add_argument('--cache', help='Path to save/load industry intent cache')

    args = parser.parse_args()

    # --- Add a new mapping ---
    if args.add:
        hex_id, name = args.add
        if not is_valid_industry(name) and not args.force:
            print(f"WARNING: '{name}' is not in the LinkedIn V1 industry taxonomy.", file=sys.stderr)
            name_lower = name.lower()
            matches = [ind for ind in sorted(LINKEDIN_INDUSTRIES)
                       if name_lower in ind.lower() or ind.lower() in name_lower]
            if matches:
                print("Closest matches:", file=sys.stderr)
                for m in matches[:5]:
                    print(f"  - {m}", file=sys.stderr)
            print(f"\nUse --force to add anyway, or use the exact taxonomy name.", file=sys.stderr)
            return 1
        add_mapping(hex_id, name, persist=True)
        print(f"Saved: {hex_id} -> {name}")
        print(f"File: {_LEARNED_MAPPINGS_FILE}")
        print(f"Total known mappings: {len(APOLLO_INDUSTRY_MAP)}")
        return 0

    # --- Reverse lookup: name -> hex ID ---
    if args.reverse_lookup:
        names = [n.strip() for n in args.reverse_lookup.split(',') if n.strip()]
        resolved, unresolved = resolve_industry_names_to_hex(names)
        if resolved:
            print(f"Resolved ({len(resolved)}):")
            for name, hex_id in sorted(resolved.items()):
                print(f"  {name} -> {hex_id}")
        if unresolved:
            print(f"\nUnresolved ({len(unresolved)}):")
            for name in unresolved:
                print(f"  {name}")
                # Suggest close matches
                name_lower = name.lower()
                matches = [ind for ind in sorted(LINKEDIN_INDUSTRIES)
                           if name_lower in ind.lower() or ind.lower() in name_lower]
                for m in matches[:3]:
                    print(f"    -> Did you mean: {m}?")
        return 0

    # --- List learned mappings only ---
    if args.list_learned:
        if not os.path.isfile(_LEARNED_MAPPINGS_FILE):
            print("No learned mappings yet.")
            return 0
        learned = load_json(_LEARNED_MAPPINGS_FILE)
        print(f"Learned mappings ({len(learned)}):")
        for hid, name in sorted(learned.items(), key=lambda x: x[1]):
            print(f"  {hid} -> {name}")
        print(f"\nFile: {_LEARNED_MAPPINGS_FILE}")
        return 0

    if args.list_known:
        print(f"Known mappings: {len(APOLLO_INDUSTRY_MAP)} (all learned from {_LEARNED_MAPPINGS_FILE})")
        for hid, name in sorted(APOLLO_INDUSTRY_MAP.items(), key=lambda x: x[1]):
            print(f"  {hid} -> {name}")
        print(f"\nLinkedIn industries: {len(LINKEDIN_INDUSTRIES)}")
        return 0

    if args.resolve:
        resolved, unresolved = resolve_industry_ids(args.resolve)
        print("Resolved:")
        for name in resolved:
            print(f"  {name}")
        if unresolved:
            print(f"\nUnresolved ({len(unresolved)}):")
            for hid in unresolved:
                print(f"  {hid}")
        return 0

    if args.apollo_url:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from apollo_url_parser import parse_apollo_url

        filters = parse_apollo_url(args.apollo_url)

        olympus_leads = None
        if args.olympus_file:
            olympus_leads = load_leads(args.olympus_file)

        intent = get_intended_industries(filters, olympus_leads, args.cache)

        print("=== INDUSTRY INTENT ===")
        print(f"\nResolved from hex IDs ({len(intent['resolved'])}):")
        for name in intent['resolved']:
            print(f"  {name}")

        if intent['unresolved_ids']:
            print(f"\nUnresolved hex IDs ({len(intent['unresolved_ids'])}):")
            for hid in intent['unresolved_ids']:
                print(f"  {hid}")

        if intent['olympus_industries']:
            print(f"\nFrom Olympus output ({len(intent['olympus_industries'])}):")
            for name in intent['olympus_industries']:
                print(f"  {name}")

        if intent['keywords']:
            print(f"\nKeyword tags ({len(intent['keywords'])}):")
            for kw in intent['keywords']:
                print(f"  {kw}")

        print(f"\nAll intended industries ({len(intent['all_intended'])}):")
        for name in intent['all_intended']:
            print(f"  {name}")

        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

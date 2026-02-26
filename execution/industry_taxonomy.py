# [LIBRARY] — imported by other scripts, not run directly
"""
Industry Taxonomy Mapper

Shared module for converting between LinkedIn V1 (Apollo) and V2 (PeakyDev)
industry name taxonomies.

V1: Apollo's internal taxonomy, e.g. "Food & Beverages", "Computer Software"
V2: PeakyDev/modern LinkedIn taxonomy, e.g. "Food and Beverage Services", "Software Development"

Usage:
    from industry_taxonomy import v1_to_v2, v2_to_v1, normalize_to_v1, build_combined_whitelist
"""


# V1 (Apollo/LinkedIn Legacy) → V2 (PeakyDev/LinkedIn Current)
# One V1 name can map to multiple V2 names (one-to-many)
V1_TO_V2 = {
    "Food & Beverages": ["Food and Beverage Services", "Food and Beverage Manufacturing", "Food and Beverage Retail"],
    "Food Production": ["Food and Beverage Manufacturing"],
    "Logistics & Supply Chain": ["Transportation, Logistics, Supply Chain and Storage"],
    "Industrial Automation": ["Automation Machinery Manufacturing"],
    "Warehousing": ["Warehousing and Storage"],
    "Computer Software": ["Software Development"],
    "Information Technology & Services": ["IT Services and IT Consulting"],
    "Marketing & Advertising": ["Marketing Services", "Advertising Services"],
    "Hospital & Health Care": ["Hospitals and Health Care"],
    "Health, Wellness & Fitness": ["Health, Wellness & Fitness", "Wellness and Fitness Services"],
    "Mechanical or Industrial Engineering": ["Industrial Machinery Manufacturing"],
    "Electrical/Electronic Manufacturing": ["Appliances, Electrical, and Electronics Manufacturing"],
    "Package/Freight Delivery": ["Freight and Package Transportation"],
    "Glass, Ceramics & Concrete": ["Glass, Ceramics and Concrete Manufacturing"],
    "Packaging & Containers": ["Packaging and Containers Manufacturing"],
    "Public Relations & Communications": ["Public Relations and Communications Services"],
    "Human Resources": ["Human Resources Services"],
    "Staffing & Recruiting": ["Staffing and Recruiting"],
    "Professional Training & Coaching": ["Professional Training and Coaching"],
    "Venture Capital & Private Equity": ["Venture Capital and Private Equity Principals"],
    "Import & Export": ["Wholesale Import and Export"],
    "Transportation/Trucking/Railroad": ["Truck Transportation", "Rail Transportation"],
    "Computer & Network Security": ["Computer and Network Security"],
    "Online Media": ["Online Media"],
    "Broadcast Media": ["Broadcast Media Production and Distribution"],
    "Oil & Energy": ["Oil and Gas", "Oil, Gas, and Mining"],
    "Mining & Metals": ["Mining", "Metal Ore Mining"],
    "Renewables & Environment": ["Services for Renewable Energy", "Environmental Services"],
    "Luxury Goods & Jewelry": ["Luxury Goods & Jewelry"],
    "Leisure, Travel & Tourism": ["Leisure, Travel & Tourism"],
    "Non-Profit Organization Management": ["Non-profit Organization Management"],
}

# Auto-built reverse map: V2 → V1 (many-to-one)
# When multiple V1 names map to the same V2 name (e.g. both "Food & Beverages" and
# "Food Production" map to "Food and Beverage Manufacturing"), we pick the first one found.
V2_TO_V1 = {}
for _v1, _v2_list in V1_TO_V2.items():
    for _v2 in _v2_list:
        if _v2 not in V2_TO_V1:
            V2_TO_V1[_v2] = _v1

# Case-insensitive lookup dicts
_V2_TO_V1_LOWER = {k.lower(): v for k, v in V2_TO_V1.items()}
_V1_TO_V2_LOWER = {k.lower(): v for k, v in V1_TO_V2.items()}


def v1_to_v2(v1_names):
    """
    Convert V1 industry names to V2 equivalents for PeakyDev API input.
    Names not in the mapping are passed through as-is.
    Returns deduplicated list preserving order.
    """
    mapped = []
    seen = set()
    for v1 in v1_names:
        v2_list = V1_TO_V2.get(v1) or V1_TO_V2.get(v1.strip()) or _V1_TO_V2_LOWER.get(v1.lower().strip())
        if v2_list:
            for v2 in v2_list:
                if v2 not in seen:
                    seen.add(v2)
                    mapped.append(v2)
        else:
            if v1 not in seen:
                seen.add(v1)
                mapped.append(v1)
    return mapped


def v2_to_v1(v2_name):
    """
    Convert a single V2 industry name back to V1.
    Returns the original name if no mapping exists.
    """
    return V2_TO_V1.get(v2_name) or _V2_TO_V1_LOWER.get(v2_name.lower(), v2_name)


def normalize_to_v1(industry_name):
    """
    Normalize any industry name to V1 taxonomy.
    If it's a known V2 name, converts to V1.
    If already V1 or unknown, returns as-is.
    """
    if not industry_name:
        return industry_name
    # Check if it's a known V2 name
    v1 = V2_TO_V1.get(industry_name)
    if v1:
        return v1
    # Case-insensitive fallback
    v1 = _V2_TO_V1_LOWER.get(industry_name.lower())
    if v1:
        return v1
    # Already V1 or unknown — return as-is
    return industry_name


def build_combined_whitelist(v1_names):
    """
    Given a list of V1 industry names, build a set containing
    BOTH V1 originals AND all V2 equivalents (case-insensitive).

    Used by the quality filter to match leads from any scraper,
    regardless of whether they use V1 or V2 taxonomy.
    """
    combined = set()
    for v1 in v1_names:
        # Normalize " and " / " & " so filter matching works with both taxonomies
        combined.add(v1.lower().replace(' and ', ' & '))
        combined.add(v1.lower().replace(' & ', ' and '))
        combined.add(v1.lower())
        v2_list = V1_TO_V2.get(v1) or _V1_TO_V2_LOWER.get(v1.lower())
        if v2_list:
            for v2 in v2_list:
                combined.add(v2.lower())
                combined.add(v2.lower().replace(' and ', ' & '))
                combined.add(v2.lower().replace(' & ', ' and '))
    return combined

# [HYBRID] — both importable library and standalone script
"""
Name Diacritics Fixer

Restores Latvian (and other) diacritical marks to names by extracting
the original characters from LinkedIn URL slugs.

LinkedIn URLs preserve the original Unicode characters in URL-encoded form,
while Apollo's API returns ASCII-normalized names.

Example:
    Name in Apollo: "Artis Miezitis"
    LinkedIn URL: "http://www.linkedin.com/in/artis-miez%c4%abtis-33052036"
    URL-decoded slug: "artis-miezītis-33052036"
    Fixed name: "Artis Miezītis"

Supports: Latvian (ā, ē, ī, ū, ķ, ļ, ņ, š, ž, ģ, č), Polish, Lithuanian, etc.
"""

import sys
import re
from urllib.parse import unquote, urlparse
from typing import Dict, Any, Optional, Tuple
import unicodedata

# Fix Windows console encoding for Unicode output
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass  # Older Python versions


def extract_linkedin_slug(linkedin_url: str) -> Optional[str]:
    """
    Extract the name slug from a LinkedIn URL.

    Args:
        linkedin_url: Full LinkedIn URL

    Returns:
        The slug portion (e.g., "artis-miezītis-33052036") or None
    """
    if not linkedin_url:
        return None

    try:
        # Parse the URL
        parsed = urlparse(linkedin_url)
        path = parsed.path

        # LinkedIn profile URLs are like /in/name-slug or /in/name-slug-123456
        if '/in/' not in path:
            return None

        # Extract the slug after /in/
        slug = path.split('/in/')[-1].strip('/')

        # URL-decode to get Unicode characters
        decoded_slug = unquote(slug)

        return decoded_slug
    except Exception:
        return None


def remove_trailing_numbers(slug: str) -> str:
    """
    Remove trailing numeric IDs from LinkedIn slugs.

    LinkedIn often appends random IDs like:
    - "name-surname-12345678" (pure numbers)
    - "name-surname-a1234567" (alphanumeric with numbers)
    - "name-surname-1a2b3c4d" (mixed)
    - "name-surname-ba474720" (letters then numbers)

    We only remove segments that look like IDs (contain digits), not valid name parts.
    """
    # Split by hyphen and examine last segment
    parts = slug.split('-')

    if len(parts) <= 2:
        # Just first-last, no ID to remove
        return slug

    # Check if last segment looks like a LinkedIn ID
    # IDs are typically 6+ chars and contain at least one digit
    last_part = parts[-1]

    # Remove if: 6+ chars AND contains at least one digit AND isn't all letters
    # This preserves valid name parts like "smith" but removes "ba474720", "12345678"
    if len(last_part) >= 6 and any(c.isdigit() for c in last_part):
        parts = parts[:-1]

    # Also check second-to-last if it's also a numeric ID (handles -123-456 patterns)
    if len(parts) > 2:
        second_last = parts[-1]
        if second_last.isdigit() and len(second_last) >= 3:
            parts = parts[:-1]

    return '-'.join(parts)


def slug_to_name_parts(slug: str) -> Tuple[str, str]:
    """
    Convert a LinkedIn slug to first and last name.

    Args:
        slug: Decoded LinkedIn slug (e.g., "artis-miezītis")

    Returns:
        Tuple of (first_name, last_name)
    """
    if not slug:
        return ('', '')

    # Remove trailing numbers
    clean_slug = remove_trailing_numbers(slug)

    # Split by hyphens
    parts = clean_slug.split('-')

    # Filter out empty parts
    parts = [p for p in parts if p]

    if not parts:
        return ('', '')

    if len(parts) == 1:
        # Single name - treat as first name
        return (parts[0].title(), '')

    if len(parts) == 2:
        # Standard first-last
        return (parts[0].title(), parts[1].title())

    # Multiple parts - first is first name, rest combined as last name
    # This handles cases like "anna-maria-smith" -> "Anna Maria", "Smith"
    # Or "john-van-der-berg" -> "John", "Van Der Berg"

    # Heuristic: if last part looks like a common surname suffix,
    # combine appropriately
    first_name = parts[0].title()

    # Check if this looks like a multi-part last name (van, de, der, etc.)
    name_prefixes = {'van', 'von', 'de', 'der', 'den', 'la', 'le', 'di', 'da', 'du'}

    # Find where last name starts
    last_name_start = 1
    for i, part in enumerate(parts[1:], 1):
        if part.lower() in name_prefixes:
            last_name_start = i
            break

    # If no prefix found, assume second part onwards is last name
    last_name = ' '.join(p.title() for p in parts[last_name_start:])

    # If we had a prefix match, include everything from there
    if last_name_start > 1:
        # First name might include middle parts
        first_name = ' '.join(p.title() for p in parts[:last_name_start])

    return (first_name, last_name)


def normalize_name_case(name: str) -> str:
    """
    Properly capitalize a name, handling edge cases.

    Handles:
    - McDonald, O'Brien, etc.
    - van der Berg (lowercase prefixes)
    - ALL CAPS input
    """
    if not name:
        return name

    # First, title case
    result = name.title()

    # Fix common patterns
    # Mc/Mac followed by capital
    result = re.sub(r'\bMc([a-z])', lambda m: f'Mc{m.group(1).upper()}', result)
    result = re.sub(r'\bMac([a-z])', lambda m: f'Mac{m.group(1).upper()}', result)

    # O' names
    result = re.sub(r"\bO'([a-z])", lambda m: f"O'{m.group(1).upper()}", result)

    # Lowercase prefixes (only if not at start of name)
    prefixes = ['Van', 'Von', 'De', 'Der', 'Den', 'La', 'Le', 'Di', 'Da', 'Du']
    words = result.split()
    if len(words) > 1:
        for i, word in enumerate(words[1:], 1):  # Skip first word
            if word in prefixes:
                words[i] = word.lower()
        result = ' '.join(words)

    return result


def names_match_ignoring_diacritics(name1: str, name2: str) -> bool:
    """
    Check if two names match when ignoring diacritical marks.

    Example: "Miezitis" matches "Miezītis"
    """
    if not name1 or not name2:
        return False

    # Normalize to NFD form and remove combining characters (diacritics)
    def strip_diacritics(s):
        return ''.join(
            c for c in unicodedata.normalize('NFD', s.lower())
            if unicodedata.category(c) != 'Mn'
        )

    return strip_diacritics(name1) == strip_diacritics(name2)


def fix_name_from_linkedin(
    first_name: str,
    last_name: str,
    full_name: str,
    linkedin_url: str
) -> Dict[str, str]:
    """
    Fix name diacritics using LinkedIn URL.

    Args:
        first_name: ASCII first name from Apollo
        last_name: ASCII last name from Apollo
        full_name: ASCII full name from Apollo
        linkedin_url: LinkedIn profile URL

    Returns:
        Dict with fixed 'first_name', 'last_name', 'name' keys
    """
    result = {
        'first_name': first_name or '',
        'last_name': last_name or '',
        'name': full_name or ''
    }

    # Extract and decode LinkedIn slug
    slug = extract_linkedin_slug(linkedin_url)
    if not slug:
        return result

    # Parse slug into name parts
    slug_first, slug_last = slug_to_name_parts(slug)

    if not slug_first and not slug_last:
        return result

    # Verify the names match (ignoring diacritics) before replacing
    # This prevents incorrect replacements when LinkedIn slug doesn't match

    first_matches = names_match_ignoring_diacritics(first_name, slug_first)
    last_matches = names_match_ignoring_diacritics(last_name, slug_last)

    # Update names if they match
    if first_matches and slug_first:
        result['first_name'] = normalize_name_case(slug_first)

    if last_matches and slug_last:
        result['last_name'] = normalize_name_case(slug_last)

    # Rebuild full name
    if result['first_name'] or result['last_name']:
        result['name'] = f"{result['first_name']} {result['last_name']}".strip()

    return result


def fix_lead_names(lead: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fix diacritics in a lead's name fields using LinkedIn URL.

    Args:
        lead: Lead dictionary with name fields and linkedin_url

    Returns:
        Lead dictionary with fixed names (modified in place)
    """
    linkedin_url = lead.get('linkedin_url', '') or lead.get('linkedinUrl', '')

    if not linkedin_url:
        return lead

    # Get current name fields
    first_name = lead.get('first_name', '') or lead.get('firstName', '') or ''
    last_name = lead.get('last_name', '') or lead.get('lastName', '') or ''
    full_name = lead.get('name', '') or lead.get('full_name', '') or lead.get('fullName', '') or ''

    # Fix names
    fixed = fix_name_from_linkedin(first_name, last_name, full_name, linkedin_url)

    # Update lead with fixed names
    if 'first_name' in lead:
        lead['first_name'] = fixed['first_name']
    if 'firstName' in lead:
        lead['firstName'] = fixed['first_name']

    if 'last_name' in lead:
        lead['last_name'] = fixed['last_name']
    if 'lastName' in lead:
        lead['lastName'] = fixed['last_name']

    if 'name' in lead:
        lead['name'] = fixed['name']
    if 'full_name' in lead:
        lead['full_name'] = fixed['name']
    if 'fullName' in lead:
        lead['fullName'] = fixed['name']

    return lead


def fix_leads_batch(leads: list) -> list:
    """
    Fix diacritics for a batch of leads.

    Args:
        leads: List of lead dictionaries

    Returns:
        List of leads with fixed names
    """
    fixed_count = 0

    for lead in leads:
        original_name = lead.get('name', '') or lead.get('full_name', '')
        fix_lead_names(lead)
        new_name = lead.get('name', '') or lead.get('full_name', '')

        if original_name != new_name:
            fixed_count += 1

    print(f"Fixed diacritics in {fixed_count}/{len(leads)} leads")
    return leads


# CLI for testing
if __name__ == '__main__':
    import sys

    # Test cases
    test_cases = [
        {
            'first_name': 'Artis',
            'last_name': 'Miezitis',
            'name': 'Artis Miezitis',
            'linkedin_url': 'http://www.linkedin.com/in/artis-miez%c4%abtis-33052036'
        },
        {
            'first_name': 'Elina',
            'last_name': 'Vulane',
            'name': 'Elina Vulane',
            'linkedin_url': 'http://www.linkedin.com/in/el%c4%abna-vul%c4%81ne-1a2951127'
        },
        {
            'first_name': 'Inguna',
            'last_name': 'Smite',
            'name': 'Inguna Smite',
            'linkedin_url': 'http://www.linkedin.com/in/ing%c5%abna-%c5%a1mite-3a1b23151'
        },
        {
            'first_name': 'Anda',
            'last_name': 'Kalnina',
            'name': 'Anda Kalnina',
            'linkedin_url': 'http://www.linkedin.com/in/anda-kalni%c5%86a-ba474720'
        },
        {
            'first_name': 'Janis',
            'last_name': 'Teivens',
            'name': 'Janis Teivens',
            'linkedin_url': 'http://www.linkedin.com/in/j%c4%81nis-j%c4%93kabs-teivens-858009125'
        }
    ]

    print("Testing name diacritics fixer:\n")
    print("-" * 70)

    for test in test_cases:
        original = test['name']
        fixed_lead = fix_lead_names(test.copy())
        fixed = fixed_lead['name']

        status = "FIXED" if original != fixed else "NO CHANGE"
        print(f"{status}: {original} -> {fixed}")
        print(f"  URL: {test['linkedin_url'][:60]}...")
        print()

    print("-" * 70)
    print("Done!")

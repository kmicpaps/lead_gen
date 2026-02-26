# [LIBRARY] — imported by other scripts, not run directly
"""
Lead Normalization Library

Normalizes leads from different scrapers (Olympus, CodeCrafter, PeakyDev) into a unified format.
Each scraper has its own field mappings which are documented here.

Also includes diacritics restoration for names using LinkedIn URL slugs.
This fixes the issue where Apollo API returns ASCII-normalized names (e.g., "Kalnina" instead of "Kalniņa").
"""

import os
import sys
from urllib.parse import urlparse
from typing import Dict, Any, List

# Sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from name_diacritics_fixer import fix_lead_names
from industry_taxonomy import normalize_to_v1


def extract_domain_from_url(url: str) -> str:
    """Extract domain from website URL"""
    if not url:
        return ''
    try:
        parsed = urlparse(str(url))
        domain = parsed.netloc or parsed.path
        return domain.replace('www.', '')
    except Exception:
        return ''


def is_junk_lead(lead: Dict[str, Any]) -> bool:
    """Check if lead is a junk/log message"""
    name = lead.get('name', '') or lead.get('full_name', '') or lead.get('fullName', '')
    if name:
        junk_patterns = ['👀', '⏳', '📈', '🟢', 'Actor', 'Scanning pages', 'enhance scraping',
                         'check the log', 'monitor', 'Refer to the log', 'To enhance scraping']
        return any(pattern in str(name) for pattern in junk_patterns)
    return False


def normalize_olympus(lead: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize Olympus (B2B Leads Finder) lead format.

    Olympus Field Mappings:
    - First Name: first_name
    - Last Name: last_name
    - Full Name: name
    - Job Title: title
    - Email: email
    - Email Status: email_status
    - LinkedIn URL: linkedin_url
    - City: city
    - Country: country
    - Company Name: organization.name
    - Company Website: organization.website_url
    - Company LinkedIn: organization.linkedin_url
    - Company Phone: organization.phone or organization.primary_phone.number
    - Company Domain: organization.primary_domain
    - Industry: organization.naics_codes / organization.sic_codes (convert if needed)
    """
    normalized = {
        'first_name': lead.get('first_name', ''),
        'last_name': lead.get('last_name', ''),
        'name': lead.get('name', ''),
        'title': lead.get('title', ''),
        'email': lead.get('email', ''),
        'email_status': lead.get('email_status', ''),
        'linkedin_url': lead.get('linkedin_url', ''),
        'city': lead.get('city', ''),
        'country': lead.get('country', ''),
        'source': 'olympus'
    }

    # Extract company fields from organization object (or org_name dict - same structure)
    org = None
    if 'organization' in lead and isinstance(lead['organization'], dict):
        org = lead['organization']
    elif 'org_name' in lead and isinstance(lead['org_name'], dict):
        org = lead['org_name']

    if org:
        normalized['company_name'] = org.get('name', '')
        normalized['company_website'] = org.get('website_url', '')
        normalized['company_linkedin'] = org.get('linkedin_url', '')

        # Get phone from multiple possible locations
        phone = org.get('phone', '')
        if not phone and isinstance(org.get('primary_phone'), dict):
            phone = org.get('primary_phone', {}).get('number', '')
        normalized['company_phone'] = phone

        normalized['company_domain'] = org.get('primary_domain', '')
        normalized['company_country'] = ''  # Filled by Lead Magic enrichment later

        # Industry from NAICS/SIC codes — extract text description if available
        industry = ''
        if org.get('naics_codes') and isinstance(org['naics_codes'], list):
            for code in org['naics_codes']:
                if isinstance(code, dict) and code.get('naics_description'):
                    industry = code['naics_description']
                    break
        if not industry and org.get('sic_codes') and isinstance(org['sic_codes'], list):
            for code in org['sic_codes']:
                if isinstance(code, dict) and code.get('sic_description'):
                    industry = code['sic_description']
                    break
        normalized['industry'] = industry
    else:
        # No organization data
        normalized['company_name'] = ''
        normalized['company_website'] = ''
        normalized['company_linkedin'] = ''
        normalized['company_phone'] = ''
        normalized['company_domain'] = ''
        normalized['company_country'] = ''
        normalized['industry'] = ''

    # Derive domain from website if missing
    if not normalized['company_domain'] and normalized['company_website']:
        normalized['company_domain'] = extract_domain_from_url(normalized['company_website'])

    return normalized


def normalize_codecrafter(lead: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize CodeCrafter lead format.

    CodeCrafter Field Mappings:
    - First Name: first_name
    - Last Name: last_name
    - Full Name: full_name
    - Job Title: job_title
    - Email: email
    - Email Status: {not available}
    - LinkedIn URL: linkedin
    - City: city
    - Country: country
    - Company Name: company_name
    - Company Website: company_website
    - Company LinkedIn: company_linkedin
    - Company Phone: company_phone
    - Company Domain: company_domain
    - Industry: industry
    """
    normalized = {
        'first_name': lead.get('first_name', ''),
        'last_name': lead.get('last_name', ''),
        'name': lead.get('full_name', ''),
        'title': lead.get('job_title', ''),
        'email': lead.get('email', ''),
        'email_status': '',  # Not available in CodeCrafter
        'linkedin_url': lead.get('linkedin', ''),  # KEY: linkedin not linkedin_url
        'city': lead.get('city', ''),
        'country': lead.get('country', ''),
        'company_name': lead.get('company_name', ''),
        'company_website': lead.get('company_website', ''),
        'company_linkedin': lead.get('company_linkedin', ''),
        'company_phone': lead.get('company_phone', ''),
        'company_domain': lead.get('company_domain', ''),
        'company_country': '',  # Filled by Lead Magic enrichment later
        'industry': lead.get('industry', ''),
        'source': 'codecrafter'
    }

    # Derive company_domain from website if missing
    if not normalized['company_domain'] and normalized['company_website']:
        normalized['company_domain'] = extract_domain_from_url(normalized['company_website'])

    return normalized


def normalize_peakydev(lead: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize PeakyDev lead format.

    PeakyDev Field Mappings:
    - First Name: firstName
    - Last Name: lastName
    - Full Name: fullName
    - Job Title: position
    - Email: email
    - Email Status: {not available}
    - LinkedIn URL: linkedinUrl
    - City: {not available}
    - Country: country
    - Company Name: organizationName
    - Company Website: organizationWebsite
    - Company LinkedIn: organizationLinkedinUrl
    - Company Phone: {not available}
    - Company Domain: {derived from website}
    - Industry: organizationIndustry
    """
    normalized = {
        'first_name': lead.get('firstName', ''),
        'last_name': lead.get('lastName', ''),
        'name': lead.get('fullName', ''),
        'title': lead.get('position', ''),
        'email': lead.get('email', ''),
        'email_status': '',  # Not available
        'linkedin_url': lead.get('linkedinUrl', ''),  # KEY: linkedinUrl not linkedin_url
        'city': '',  # Not available in PeakyDev
        'country': lead.get('country', ''),
        'company_name': lead.get('organizationName', ''),
        'company_website': lead.get('organizationWebsite', ''),
        'company_linkedin': lead.get('organizationLinkedinUrl', ''),
        'company_phone': '',  # Not available
        'company_domain': '',
        'company_country': '',  # Filled by Lead Magic enrichment later
        'industry': lead.get('organizationIndustry', ''),
        'source': 'peakydev'
    }

    # Derive company_domain from website
    if normalized['company_website']:
        normalized['company_domain'] = extract_domain_from_url(normalized['company_website'])

    # Normalize V2 industry names back to V1 (PeakyDev returns V2 taxonomy)
    if normalized.get('industry'):
        normalized['industry'] = normalize_to_v1(normalized['industry'])

    return normalized


def is_pre_normalized(lead: Dict[str, Any]) -> bool:
    """
    Check if lead is already in pre-normalized format (scrapers sometimes do this).
    Pre-normalized format has: first_name, linkedin_url (not linkedin), org_name as STRING (not dict)
    """
    has_linkedin_url = 'linkedin_url' in lead
    has_org_name_string = 'org_name' in lead and isinstance(lead.get('org_name'), str)
    lacks_raw_fields = 'full_name' not in lead and 'fullName' not in lead
    return has_linkedin_url and has_org_name_string and lacks_raw_fields


def normalize_pre_normalized(lead: Dict[str, Any], source: str) -> Dict[str, Any]:
    """
    Handle leads that are already in a pre-normalized format.
    Some scrapers post-process their output into a unified format.
    """
    normalized = {
        'first_name': lead.get('first_name', ''),
        'last_name': lead.get('last_name', ''),
        'name': lead.get('name', ''),
        'title': lead.get('title', ''),
        'email': lead.get('email', ''),
        'email_status': lead.get('email_status', ''),
        'linkedin_url': lead.get('linkedin_url', ''),
        'city': lead.get('city', ''),
        'country': lead.get('country', ''),
        'company_name': lead.get('org_name', ''),  # Pre-normalized uses org_name
        'company_website': lead.get('website_url', ''),
        'company_linkedin': lead.get('company_linkedin', ''),
        'company_phone': lead.get('company_phone', '') or lead.get('organization_phone', ''),
        'company_domain': lead.get('company_domain', ''),
        'company_country': lead.get('company_country', ''),  # Preserve if already set
        'industry': lead.get('industry', ''),
        'source': source
    }

    # Derive domain if missing
    if not normalized['company_domain'] and normalized['company_website']:
        normalized['company_domain'] = extract_domain_from_url(normalized['company_website'])

    return normalized


def normalize_lead(lead: Dict[str, Any], source: str, fix_diacritics: bool = True) -> Dict[str, Any]:
    """
    Normalize a lead based on its source scraper.

    Args:
        lead: Raw lead data from scraper
        source: Source scraper name ('olympus', 'codecrafter', or 'peakydev')
        fix_diacritics: Whether to restore diacritics from LinkedIn URLs (default: True)

    Returns:
        Normalized lead with unified field names and restored diacritics
    """
    if is_junk_lead(lead):
        return None

    # Check if already pre-normalized (some scrapers do this)
    source = source.lower()
    if is_pre_normalized(lead):
        normalized = normalize_pre_normalized(lead, source)
    else:
        if source == 'olympus':
            normalized = normalize_olympus(lead)
        elif source == 'codecrafter':
            normalized = normalize_codecrafter(lead)
        elif source == 'peakydev':
            normalized = normalize_peakydev(lead)
        else:
            raise ValueError(f"Unknown source: {source}")

    # Fix diacritics using LinkedIn URL if available
    if fix_diacritics and normalized:
        normalized = fix_lead_names(normalized)

    return normalized


def normalize_leads_batch(leads: List[Dict[str, Any]], source: str, fix_diacritics: bool = True) -> List[Dict[str, Any]]:
    """
    Normalize a batch of leads from the same source.

    Args:
        leads: List of raw leads from scraper
        source: Source scraper name
        fix_diacritics: Whether to restore diacritics from LinkedIn URLs (default: True)

    Returns:
        List of normalized leads (junk leads filtered out, diacritics restored)
    """
    normalized = []
    fixed_count = 0

    for lead in leads:
        original_name = lead.get('name', '') or lead.get('full_name', '') or lead.get('fullName', '')
        norm_lead = normalize_lead(lead, source, fix_diacritics=fix_diacritics)
        if norm_lead is not None:
            new_name = norm_lead.get('name', '')
            if original_name != new_name and fix_diacritics:
                fixed_count += 1
            normalized.append(norm_lead)

    if fix_diacritics and fixed_count > 0:
        print(f"  Restored diacritics in {fixed_count}/{len(normalized)} lead names")

    return normalized

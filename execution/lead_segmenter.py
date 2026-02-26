# [CLI] — run via: py execution/lead_segmenter.py --help
#!/usr/bin/env python3
"""
Lead Segmenter for Cold Email Campaigns

Assigns segment IDs and translates English website insights to Latvian.
Deterministic -- no AI calls, pure template mapping.

Usage:
    python execution/lead_segmenter.py \
        --input .tmp/gmaps_pipeline/cold_email_evaluated.json \
        --output .tmp/gmaps_pipeline/cold_email_segmented.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ── Latvian insight translations ──────────────────────────────────────
# Maps English insight patterns to short Latvian versions (max 15 words).
# Order matters: first match wins.

INSIGHT_PATTERNS = [
    # Slow loading: "Your site loads in {X}s on mobile — {Y}x slower..."
    {
        "match": r"loads? in ([\d.]+)s",
        "template_lv": "Paskatījos uz {casual_name} lapu no telefona. Ielādējās {lcp} sekundēs.",
    },
    # Slow loading alt: "mobile load time ({X}s) is above..."
    {
        "match": r"load time \(([\d.]+)s\)",
        "template_lv": "Paskatījos uz {casual_name} lapu no telefona. Ielādējās {lcp} sekundēs.",
    },
    # No SSL: "doesn't use HTTPS"
    {
        "match": r"HTTPS|doesn't use HTTPS|ssl",
        "template_lv": "Atvēru {casual_name} lapu un pārlūks uzreiz brīdināja par drošību. Nav HTTPS.",
    },
    # Not mobile friendly
    {
        "match": r"mobile|isn't optimized for mobile",
        "template_lv": "Paskatījos uz {casual_name} lapu no telefona. Mobilajā versijā neizskatās labi.",
    },
    # Poor performance score: "scores {X}/100 on Google's speed test"
    {
        "match": r"scores? (\d+)/100 on Google",
        "template_lv": "Paskatījos uz {casual_name} lapu. Google ātruma testā saņēma {perf}/100.",
    },
    # Poor SEO: "SEO score is {X}/100"
    {
        "match": r"SEO score is (\d+)/100",
        "template_lv": "Paskatījos uz {casual_name} lapu. SEO vērtējumā saņēma {seo}/100.",
    },
    # Outdated CMS: "{CMS} site scores {X}/100"
    {
        "match": r"(\w+) site scores? (\d+)/100",
        "template_lv": "Paskatījos uz {casual_name} lapu. Google testā saņēma {score}/100.",
    },
]

NICHE_NAMES_LV = {
    "beauty": "skaistumkopšanas salons",
    "juristi": "juridiskais birojs",
    "buvnieki": "būvniecības uzņēmums",
}

# Fallback for leads with no insights -- uses casual_name
FALLBACK_INSIGHT_LV = "Apskatīju {casual_name} lapu."

# ── Casual business name cleanup ─────────────────────────────────────
# Strips SIA, quotes, niche descriptors, etc. to get a short brand name.

# Niche descriptor phrases to strip (case-insensitive)
_NICHE_DESCRIPTORS = [
    r"skaistumkopšanas (salons?|pakalpojum\w+)",
    r"friziersalons?",
    r"frizieris",
    r"kosmetologs?",
    r"salons?\b",
    r"beauty\s*salon",
    r"health\s+and\s+beauty",
    r"barbershop",
    r"hair\s+bar",
    r"juridisk\w+ (pakalpojumu )?birojs?",
    r"advokātu birojs?",
    r"zvērināt\w+ advokāt\w+",
    r"būvniecības (pakalpojum\w+|uzņēmum\w+)",
    r"remonta un būvniecības pakalpojum\w+",
    r"būvuzraudzīb\w+",
    r"veikals?\s*[-]?\s*\w*",
]


def make_casual_name(business_name: str) -> str:
    """Create a short, casual brand name from a GMaps business name.

    Rules applied in order:
    1. Take first part before / or | separators
    2. Strip parenthetical text
    3. Strip SIA anywhere, strip quotes
    4. Strip " - descriptor" suffixes (keep shorter/brand part)
    5. Strip niche descriptors
    6. Title-case individual ALL-CAPS words (>3 chars)
    7. If result is empty, fall back to original minus SIA/quotes
    """
    name = business_name.strip()
    if not name:
        return name

    # 1. Split on / or | separators, take the shortest meaningful part (brand name)
    if '|' in name or '/' in name:
        # Split on both separators
        parts = re.split(r'[/|]', name)
        parts = [p.strip() for p in parts if p.strip()]
        if parts:
            # Take shortest part that's > 2 chars (likely the brand name)
            valid = [p for p in parts if len(p) > 2]
            name = min(valid, key=len) if valid else parts[0]

    # 2. Strip parenthetical text (e.g. "OS Eksperti (stuff)" -> "OS Eksperti")
    name = re.sub(r'\s*\([^)]*\)', '', name).strip()

    # 3. Strip SIA anywhere and all types of quotes
    name = re.sub(r'\bSIA\b', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'[\u0022\u0027\u201c\u201d\u201e\u00ab\u00bb"„"\u2018\u2019]+', '', name).strip()

    # 4. Strip " - descriptor" suffix (keep shorter/brand part)
    if ' - ' in name:
        parts = [p.strip() for p in name.split(' - ')]
        # Keep the shorter part (likely the brand name)
        name = min(parts, key=len) if len(parts) == 2 else parts[0]
        if not name:
            name = parts[0]

    # 5. Strip niche descriptors
    for desc in _NICHE_DESCRIPTORS:
        name = re.sub(r',?\s*' + desc, '', name, flags=re.IGNORECASE).strip()

    # 6. Strip long comma-separated tails (e.g. "LOKO, cirtainiem un lokainiem matiem")
    if ',' in name:
        parts = name.split(',', 1)
        tail = parts[1].strip() if len(parts) > 1 else ''
        if len(tail) > 15:
            name = parts[0].strip()

    # 7. Clean up leftover commas, spaces, and punctuation
    name = re.sub(r'^[,\s]+|[,\s]+$', '', name)
    name = re.sub(r'\s{2,}', ' ', name)

    # 8. Title-case individual ALL-CAPS words (>2 chars, keeps GG/EU as-is)
    words = name.split()
    fixed_words = []
    for w in words:
        if w.isupper() and len(w) > 2 and not w.endswith('.lv'):
            fixed_words.append(w.title())
        else:
            fixed_words.append(w)
    name = ' '.join(fixed_words)

    # 9. If still too long (>30 chars), take first 3 words
    if len(name) > 30:
        name = ' '.join(name.split()[:3])

    # Fallback: if cleanup ate everything, use "Jūsu" (works in all templates)
    if len(name.strip()) < 2:
        name = "Jūsu"

    return name.strip()


def translate_insight(insight_en: str, lead: dict) -> str:
    """Translate a single English insight to Latvian using template matching."""
    casual_name = lead.get("casual_name", lead.get("business_name", ""))

    for pattern in INSIGHT_PATTERNS:
        m = re.search(pattern["match"], insight_en, re.IGNORECASE)
        if m:
            template = pattern["template_lv"]
            # Fill in values from regex groups (contextual) and lead data (fallback)
            groups = m.groups()
            # Use named dict so each template placeholder gets the right value
            fmt = {
                "casual_name": casual_name,
                "lcp": groups[0] if groups and "lcp" in template else lead.get("lcp_seconds", ""),
                "perf": groups[0] if groups and "perf" in template else lead.get("performance_score", ""),
                "seo": groups[0] if groups and "seo" in template else lead.get("seo_score", ""),
                "cms": groups[0] if groups and "cms" in template else lead.get("cms", ""),
                "score": groups[1] if len(groups) > 1 else (groups[0] if groups and "score" in template else lead.get("overall_score", "")),
            }
            result = template.format(**fmt)
            return result
    return FALLBACK_INSIGHT_LV.format(casual_name=casual_name)


def assign_segment(lead: dict) -> str:
    """Assign segment_id based on niche + score threshold."""
    niche = lead.get("niche", "unknown")
    score = lead.get("overall_score")
    insights = lead.get("insights", [])

    if score is not None and score >= 70 and not insights:
        quality = "decent"
    elif score is not None and score >= 70 and insights:
        # Has insights but score is decent -- still "decent" unless insights are severe
        quality = "decent"
    else:
        quality = "poor"

    # Map niche names to ASCII segment prefixes (must match template filenames)
    niche_map = {
        "beauty": "beauty", "juristi": "juristi",
        "buvnieki": "buvnieki", "būvnieki": "buvnieki",
    }
    niche_key = niche_map.get(niche, niche)

    return f"{niche_key}_{quality}"


def segment_leads(leads: list) -> list:
    """Add segment_id, casual_name, insight_lv, and niche_lv to each lead."""
    for lead in leads:
        # Casual business name (must come before insight translation)
        lead["casual_name"] = make_casual_name(lead.get("business_name", ""))

        # Segment assignment
        lead["segment_id"] = assign_segment(lead)

        # Latvian insight translation (uses casual_name)
        insights = lead.get("insights", [])
        if insights:
            lead["insight_lv"] = translate_insight(insights[0], lead)
        else:
            lead["insight_lv"] = FALLBACK_INSIGHT_LV.format(
                casual_name=lead["casual_name"]
            )

        # Latvian niche name
        niche = lead.get("niche", "unknown")
        lead["niche_lv"] = NICHE_NAMES_LV.get(niche, niche)

    return leads


def print_summary(leads: list):
    """Print segment breakdown."""
    segments = {}
    for lead in leads:
        seg = lead["segment_id"]
        segments[seg] = segments.get(seg, 0) + 1

    print("\n" + "=" * 50)
    print("SEGMENTATION SUMMARY")
    print("=" * 50)
    print(f"Total leads: {len(leads)}")
    print()
    for seg, count in sorted(segments.items()):
        print(f"  {seg}: {count}")

    # Insight QA: check max word count
    over_15 = 0
    has_emdash = 0
    for lead in leads:
        words = len(lead.get("insight_lv", "").split())
        if words > 15:
            over_15 += 1
        if "\u2014" in lead.get("insight_lv", ""):
            has_emdash += 1

    print()
    if over_15 > 0:
        print(f"[WARN] {over_15} leads have insight_lv > 15 words")
    else:
        print("[OK] All insight_lv fields are 15 words or fewer")
    if has_emdash > 0:
        print(f"[WARN] {has_emdash} leads have em-dash in insight_lv")
    else:
        print("[OK] No em-dashes in insight_lv fields")


def main():
    parser = argparse.ArgumentParser(description="Segment leads and translate insights to Latvian")
    parser.add_argument("--input", required=True, help="Path to evaluated cold_email JSON")
    parser.add_argument("--output", required=True, help="Path to write segmented JSON")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        leads = json.load(f)

    print(f"[INFO] Loaded {len(leads)} leads from {input_path}")

    leads = segment_leads(leads)
    print_summary(leads)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Saved segmented leads to {output_path}")


if __name__ == "__main__":
    main()

# [CLI] — run via: py execution/industry_relevance_filter.py --help
"""
Industry Relevance Filter

Post-merge quality gate that validates lead industries against Apollo search intent.
Uses AI to score each unique industry name as relevant/maybe/irrelevant.

Key optimization: Scores per unique industry name (~50-100 per campaign), NOT per lead.
Cost: ~$0.01 per campaign run.

Usage:
    py execution/industry_relevance_filter.py \
        --input .tmp/merged/merged_leads.json \
        --apollo-url "https://app.apollo.io/#/people?..." \
        --output-dir .tmp/filtered/ \
        --output-prefix "industry_filtered"

    # With cached Olympus data for better intent detection:
    py execution/industry_relevance_filter.py \
        --input .tmp/merged/merged_leads.json \
        --apollo-url "https://app.apollo.io/#/people?..." \
        --olympus-file .tmp/b2b_finder/olympus_leads.json \
        --output-dir .tmp/filtered/

    # With cached intent from previous run:
    py execution/industry_relevance_filter.py \
        --input .tmp/merged/merged_leads.json \
        --intent-cache .tmp/example_mfg_industry_cache.json \
        --output-dir .tmp/filtered/
"""

import os
import sys
import json
import argparse
import re
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apollo_url_parser import parse_apollo_url
from apollo_industry_resolver import get_intended_industries
from utils import load_json, save_json, load_leads


# ---------------------------------------------------------------------------
# AI Scoring
# ---------------------------------------------------------------------------

def _build_scoring_prompt(unique_industries: list, intended_industries: list,
                          keywords: list) -> str:
    """Build the prompt for AI industry classification."""
    intended_str = "\n".join(f"- {ind}" for ind in intended_industries) if intended_industries else "- (none specified)"
    keywords_str = "\n".join(f"- {kw}" for kw in keywords) if keywords else "- (none specified)"
    industries_str = "\n".join(f"{i+1}. {ind}" for i, ind in enumerate(unique_industries))

    return f"""You are classifying industries for a B2B lead filtering system.

The user searched for leads in these industries:
{intended_str}

With these keyword tags:
{keywords_str}

For each industry below, classify it as:
- "relevant": Directly matches or is a sub-category of the intended industries
- "maybe": Related but not directly matching (e.g., "Civil Engineering" when searching for "Construction")
- "irrelevant": Clearly unrelated to the search intent

Industries to classify:
{industries_str}

Return a JSON object where keys are industry names and values are objects with "score" and "reason" fields.
Example: {{"Construction": {{"score": "relevant", "reason": "Direct match"}}, "Gambling & Casinos": {{"score": "irrelevant", "reason": "Unrelated to construction/building"}}}}

IMPORTANT: Return ONLY the JSON object, no other text."""


def _extract_json_from_text(text: str) -> dict:
    """
    Try to extract a JSON object from text that may contain extra content.
    Handles cases where the AI returns markdown fences or extra commentary.
    """
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try stripping markdown code fences
    if "```" in text:
        # Extract content between first ``` and last ```
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

    # Try finding the first { and last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    print(f"  WARNING: Could not extract JSON from AI response ({len(text)} chars)", file=sys.stderr)
    return {}


def _call_openai(prompt: str) -> str:
    """Call OpenAI API and return response text."""
    try:
        import openai
    except ImportError:
        raise ImportError("openai package not installed. Run: pip install openai")
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def _call_anthropic(prompt: str) -> str:
    """Call Anthropic API and return response text."""
    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic package not installed. Run: pip install anthropic")
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=4096,
        temperature=0.1,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _fallback_exact_match(unique_industries: list, intended_industries: list) -> dict:
    """
    Simple exact-match fallback when AI is unavailable.
    Only marks industries that exactly match intended_industries as relevant;
    everything else as irrelevant.
    """
    # Normalize intended industries for case-insensitive comparison
    intended_lower = {ind.lower().strip() for ind in intended_industries}
    scores = {}
    for ind in unique_industries:
        if ind.lower().strip() in intended_lower:
            scores[ind] = {"score": "relevant", "reason": "Exact match (fallback mode)"}
        else:
            scores[ind] = {"score": "irrelevant", "reason": "No exact match (fallback mode)"}
    return scores


def score_industries_batch(unique_industries: list, intended_industries: list,
                           keywords: list, ai_provider: str = "openai") -> dict:
    """
    Score a batch of unique industry names against the Apollo intent.

    Args:
        unique_industries: List of unique industry names from merged leads
        intended_industries: List of intended industry names (from resolver)
        keywords: List of keyword tags from Apollo URL
        ai_provider: "openai" or "anthropic"

    Returns:
        Dict mapping industry name -> {"score": "relevant"|"maybe"|"irrelevant", "reason": str}
    """
    if not unique_industries:
        return {}

    prompt = _build_scoring_prompt(unique_industries, intended_industries, keywords)

    try:
        if ai_provider == "openai":
            result_text = _call_openai(prompt)
        else:
            result_text = _call_anthropic(prompt)

        scores = _extract_json_from_text(result_text)

        if not scores:
            print("  WARNING: Could not parse AI response, falling back to exact match",
                  file=sys.stderr)
            return _fallback_exact_match(unique_industries, intended_industries)

        # Validate that every industry has a valid score entry
        valid_scores = ("relevant", "maybe", "irrelevant")
        for ind in unique_industries:
            if ind not in scores:
                # Try case-insensitive lookup
                found = False
                for key in scores:
                    if key.lower().strip() == ind.lower().strip():
                        scores[ind] = scores[key]
                        found = True
                        break
                if not found:
                    # Default unscored industries to "maybe"
                    scores[ind] = {"score": "maybe", "reason": "Not scored by AI"}
            else:
                # Ensure valid structure
                entry = scores[ind]
                if not isinstance(entry, dict) or entry.get("score") not in valid_scores:
                    scores[ind] = {"score": "maybe", "reason": "Invalid AI response"}

        return scores

    except Exception as e:
        print(f"  WARNING: AI call failed ({e}), falling back to exact match",
              file=sys.stderr)
        return _fallback_exact_match(unique_industries, intended_industries)


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def filter_by_relevance(leads: list, scores: dict, include_maybe: bool = True) -> tuple:
    """
    Filter leads based on industry relevance scores.

    Args:
        leads: List of leads to filter
        scores: Dict from score_industries_batch()
        include_maybe: Whether to keep "maybe" scored leads (default True)

    Returns:
        (kept_leads, removed_leads, report_lines)
    """
    kept_leads = []
    removed_leads = []
    report_lines = []

    kept_counts = Counter()
    removed_counts = Counter()

    for lead in leads:
        industry = (lead.get("industry") or "").strip()

        # Keep leads with empty/missing industry — don't penalize missing data
        if not industry:
            kept_leads.append(lead)
            kept_counts["(no industry)"] += 1
            continue

        entry = scores.get(industry)

        # If industry wasn't scored (shouldn't happen but handle gracefully), keep it
        if not entry:
            # Try case-insensitive lookup
            found = False
            for key, val in scores.items():
                if key.lower().strip() == industry.lower().strip():
                    entry = val
                    found = True
                    break
            if not found:
                kept_leads.append(lead)
                kept_counts[industry] += 1
                continue

        score = entry.get("score", "maybe")

        if score == "relevant":
            kept_leads.append(lead)
            kept_counts[industry] += 1
        elif score == "maybe" and include_maybe:
            kept_leads.append(lead)
            kept_counts[industry] += 1
        else:
            lead_copy = dict(lead)
            lead_copy["_removal_reason"] = f"Industry '{industry}' scored '{score}': {entry.get('reason', 'N/A')}"
            removed_leads.append(lead_copy)
            removed_counts[industry] += 1

    # Build report lines
    report_lines.append(f"Kept: {len(kept_leads)} leads")
    report_lines.append(f"Removed: {len(removed_leads)} leads")
    if removed_counts:
        report_lines.append("")
        report_lines.append("Top removed industries:")
        for ind, count in removed_counts.most_common(15):
            entry = scores.get(ind, {})
            report_lines.append(f"  {ind}: {count} leads ({entry.get('score', '?')} - {entry.get('reason', 'N/A')})")

    return kept_leads, removed_leads, report_lines


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AI-powered industry relevance filter")
    parser.add_argument("--input", required=True, help="Path to merged leads JSON")
    parser.add_argument("--apollo-url", help="Apollo search URL")
    parser.add_argument("--olympus-file", help="Path to raw Olympus leads for learning")
    parser.add_argument("--intent-cache", help="Path to cached industry intent JSON")
    parser.add_argument("--output-dir", default=".tmp/filtered", help="Output directory")
    parser.add_argument("--output-prefix", default="industry_filtered", help="Output file prefix")
    parser.add_argument("--ai-provider", default="openai", choices=["openai", "anthropic"])
    parser.add_argument("--exclude-maybe", action="store_true", help="Exclude maybe-scored industries")
    parser.add_argument("--dry-run", action="store_true", help="Show scores without filtering")
    args = parser.parse_args()

    # -----------------------------------------------------------------------
    # 1. Validate inputs
    # -----------------------------------------------------------------------
    if not args.apollo_url and not args.intent_cache:
        print("ERROR: Must provide either --apollo-url or --intent-cache", file=sys.stderr)
        return 1

    if not os.path.isfile(args.input):
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        return 1

    # Check API key availability
    if args.ai_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set in environment", file=sys.stderr)
        return 1
    if args.ai_provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set in environment", file=sys.stderr)
        return 1

    # -----------------------------------------------------------------------
    # 2. Load leads
    # -----------------------------------------------------------------------
    print(f"Loading leads from {args.input}...")
    leads = load_leads(args.input)
    print(f"  Loaded {len(leads)} leads")

    # -----------------------------------------------------------------------
    # 3. Get intended industries
    # -----------------------------------------------------------------------
    print("\nResolving search intent...")

    if args.intent_cache and os.path.isfile(args.intent_cache):
        # Load from cache
        intent = load_json(args.intent_cache)
        intended_industries = intent.get("all_intended", [])
        keywords = intent.get("keywords", [])
        print(f"  Loaded intent from cache: {args.intent_cache}")
    else:
        # Parse Apollo URL and optionally mine Olympus data
        apollo_filters = parse_apollo_url(args.apollo_url)

        olympus_leads = None
        if args.olympus_file and os.path.isfile(args.olympus_file):
            print(f"  Loading Olympus data from {args.olympus_file}...")
            olympus_leads = load_leads(args.olympus_file)
            print(f"  Loaded {len(olympus_leads)} Olympus leads for intent learning")

        intent = get_intended_industries(apollo_filters, olympus_leads)
        intended_industries = intent.get("all_intended", [])
        keywords = intent.get("keywords", [])

    print(f"  Intended industries ({len(intended_industries)}):")
    for ind in intended_industries:
        print(f"    - {ind}")
    if keywords:
        print(f"  Keywords ({len(keywords)}):")
        for kw in keywords:
            print(f"    - {kw}")

    # -----------------------------------------------------------------------
    # 4. Extract unique industries from leads
    # -----------------------------------------------------------------------
    industry_counter = Counter()
    for lead in leads:
        industry = (lead.get("industry") or "").strip()
        if industry:
            industry_counter[industry] += 1

    unique_industries = sorted(industry_counter.keys())
    no_industry_count = sum(1 for lead in leads if not (lead.get("industry") or "").strip())

    print(f"\n  Unique industries in leads: {len(unique_industries)}")
    print(f"  Leads with no industry: {no_industry_count}")

    if not unique_industries:
        print("\nNo industries to score. Nothing to filter.")
        return 0

    # -----------------------------------------------------------------------
    # 5. Score industries with AI
    # -----------------------------------------------------------------------
    print(f"\nScoring {len(unique_industries)} unique industries with {args.ai_provider}...")
    scores = score_industries_batch(unique_industries, intended_industries, keywords,
                                    ai_provider=args.ai_provider)

    # -----------------------------------------------------------------------
    # 6. Print scoring report
    # -----------------------------------------------------------------------
    relevant_count = 0
    maybe_count = 0
    irrelevant_count = 0

    print(f"\n{'='*80}")
    print(f"{'INDUSTRY':<45} {'COUNT':>6}  {'SCORE':<12} REASON")
    print(f"{'='*80}")

    for ind in sorted(unique_industries, key=lambda x: (
        {"relevant": 0, "maybe": 1, "irrelevant": 2}.get(scores.get(x, {}).get("score", "maybe"), 1),
        x.lower()
    )):
        entry = scores.get(ind, {})
        score = entry.get("score", "?")
        reason = entry.get("reason", "")
        count = industry_counter.get(ind, 0)

        # Truncate long industry names and reasons for display
        ind_display = ind[:43] + ".." if len(ind) > 45 else ind
        reason_display = reason[:40] + ".." if len(reason) > 42 else reason

        if score == "relevant":
            relevant_count += 1
        elif score == "maybe":
            maybe_count += 1
        elif score == "irrelevant":
            irrelevant_count += 1

        print(f"{ind_display:<45} {count:>6}  {score:<12} {reason_display}")

    print(f"{'='*80}")
    print(f"Score summary: {relevant_count} relevant, {maybe_count} maybe, {irrelevant_count} irrelevant")

    # -----------------------------------------------------------------------
    # 7. Dry run — stop here if requested
    # -----------------------------------------------------------------------
    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        return 0

    # -----------------------------------------------------------------------
    # 8. Filter leads
    # -----------------------------------------------------------------------
    include_maybe = not args.exclude_maybe
    kept_leads, removed_leads, report_lines = filter_by_relevance(
        leads, scores, include_maybe=include_maybe
    )

    print(f"\n--- FILTER RESULTS ---")
    for line in report_lines:
        print(f"  {line}")

    # -----------------------------------------------------------------------
    # 9. Save outputs
    # -----------------------------------------------------------------------
    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Filtered leads
    output_path = os.path.join(args.output_dir,
                               f"{args.output_prefix}_{timestamp}_{len(kept_leads)}leads.json")
    save_json(kept_leads, output_path)
    print(f"\n  Filtered leads saved: {output_path}")

    # Removed leads (for review)
    if removed_leads:
        removed_path = os.path.join(args.output_dir,
                                    f"{args.output_prefix}_{timestamp}_removed_{len(removed_leads)}leads.json")
        save_json(removed_leads, removed_path)
        print(f"  Removed leads saved: {removed_path}")

    # Scores sidecar (for caching/debugging)
    scores_path = os.path.join(args.output_dir,
                               f"{args.output_prefix}_{timestamp}_scores.json")
    scores_output = {
        "timestamp": timestamp,
        "ai_provider": args.ai_provider,
        "intended_industries": intended_industries,
        "keywords": keywords,
        "include_maybe": include_maybe,
        "total_leads": len(leads),
        "kept_leads": len(kept_leads),
        "removed_leads": len(removed_leads),
        "scores": scores,
    }
    save_json(scores_output, scores_path)
    print(f"  Scores saved: {scores_path}")

    # -----------------------------------------------------------------------
    # 10. Summary
    # -----------------------------------------------------------------------
    print(f"\n{'='*50}")
    print(f"  SUMMARY")
    print(f"{'='*50}")
    print(f"  Input:     {len(leads)} leads")
    print(f"  Kept:      {len(kept_leads)} leads ({len(kept_leads)/max(len(leads),1)*100:.1f}%)")
    print(f"  Removed:   {len(removed_leads)} leads ({len(removed_leads)/max(len(leads),1)*100:.1f}%)")
    print(f"  Mode:      {'exclude' if args.exclude_maybe else 'include'} maybe-scored industries")
    print(f"{'='*50}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

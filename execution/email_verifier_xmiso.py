# [CLI] -- run via: py execution/email_verifier_xmiso.py --help
"""
Phase 4 of the backup Apollo pipeline.

Verifies a batch of emails via xmiso_scrapers/easy-bulk-email-validator on
Apify. This actor uses the MillionVerifier engine under the hood. Used as the
final quality gate to classify each email into one of:
  A  good / ok              -> safe to send
  B  risky / catch_all      -> domain accepts anything, send cautiously
  C  risky / unknown        -> SMTP check inconclusive
  D  bad / invalid          -> drop, will bounce

Apify actor: QM5YJIYftbZQiNpgN  (xmiso_scrapers/easy-bulk-email-validator)
Pricing: $1-1.7 per 1,000 emails
Input cap: 1,000 emails per call -- this script chunks automatically.

Output per email:
  email, email_quality (good/risky/bad), email_result (ok/catch_all/unknown/invalid),
  subresult, free (is free provider like gmail)

REQUIRES: APIFY_API_KEY in .env
"""
import argparse
import json
import os
import sys
import time
from collections import Counter

from apify_client import ApifyClient
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import log_ok, log_error, save_json  # type: ignore

load_dotenv()

XMISO_ACTOR = "QM5YJIYftbZQiNpgN"
CHUNK_SIZE = 1000


def verify(emails: list, timeout_per_email: int = 10) -> list:
    token = os.getenv("APIFY_API_KEY")
    if not token:
        log_error("APIFY_API_KEY missing from .env")
        sys.exit(1)
    if not emails:
        return []

    # Dedupe input
    unique_emails = list({(e or "").strip().lower() for e in emails if e and "@" in e})
    log_ok(f"Verifying {len(unique_emails)} unique emails via xmiso (MillionVerifier)")

    client = ApifyClient(token)
    all_results = []
    for i in range(0, len(unique_emails), CHUNK_SIZE):
        chunk = unique_emails[i:i + CHUNK_SIZE]
        log_ok(f"xmiso chunk {i // CHUNK_SIZE + 1}: {len(chunk)} emails")
        t0 = time.time()
        run = client.actor(XMISO_ACTOR).call(
            run_input={"emails": chunk, "timeout": timeout_per_email},
            timeout_secs=1800,
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        all_results.extend(items)
        log_ok(f"  -> {len(items)} results in {time.time()-t0:.0f}s")

    q = Counter(it.get("email_quality", "?") for it in all_results)
    r = Counter(it.get("email_result", "?") for it in all_results)
    log_ok(f"Quality distribution: {dict(q)}")
    log_ok(f"Result distribution:  {dict(r)}")
    return all_results


def main() -> None:
    p = argparse.ArgumentParser(description="Xmiso email verifier (Phase 4 of backup pipeline)")
    p.add_argument("--input", required=True, help="Path to JSON list of emails (strings) OR lead dicts with 'email' field")
    p.add_argument("--output", required=True, help="Path to write verification results JSON")
    p.add_argument("--timeout", type=int, default=10, help="Timeout per single SMTP check (seconds)")
    args = p.parse_args()

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    # Accept either list of strings or list of dicts with 'email' key
    if data and isinstance(data[0], dict):
        emails = [d.get("email") for d in data if d.get("email")]
    else:
        emails = [str(x) for x in data]

    results = verify(emails, timeout_per_email=args.timeout)
    save_json(results, args.output, mkdir=True)
    log_ok(f"Saved {len(results)} verifications to {args.output}")


if __name__ == "__main__":
    main()

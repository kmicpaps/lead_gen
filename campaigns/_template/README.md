# Campaign Template

Copy this folder to create a new client. Replace placeholder values in `client.json`.

## Structure

```
{client_id}/
├── client.json                    # Client metadata, ICP, campaign history
├── apollo_lists/                  # Apollo-sourced lead campaigns
│   └── {campaign_name_YYYYMMDD}/ # One folder per campaign
│       ├── *_leads.json          # Scraper output files
│       └── sheet_url.txt         # Google Sheet link for deliverable
├── google_maps_lists/            # Google Maps-sourced campaigns
│   └── {campaign_name_YYYYMMDD}/
│       ├── *.json
│       └── sheet_url.txt
├── reference_copies/             # Example emails/copy for this client's tone
│   └── emails.json
└── filter_learnings.json         # (auto-generated) Human filter decisions for AI feedback
```

## Required Files

- **`client.json`** — MUST exist. Fill in at minimum: `client_id`, `company_name`, `website`.
- **`apollo_lists/`** — Created on first Apollo campaign.
- **`google_maps_lists/`** — Created on first GMaps campaign.

## sheet_url.txt

Each campaign subfolder SHOULD contain a `sheet_url.txt` with the Google Sheet link
for the final deliverable. One URL per line. This lets future sessions find the Sheet
without re-exporting.

## Onboarding Files

- **`client_onboarding_form.md`** — Full 6-section form for thorough client intake
- **`client_onboarding_quick.md`** — Quick reference version
- **`sample_report_template.md`** — Template for demo deliverables

These are reference templates — they stay in `_template/` and are used during onboarding.

# Campaigns Directory

This directory contains all client-specific campaign data organized by client.

## Structure

```
campaigns/
├── client_name_1/
│   ├── client.json              # Client metadata
│   ├── apollo_lists/            # Apollo-based campaigns
│   │   └── campaign_name_YYYYMMDD/
│   │       ├── raw_leads.json
│   │       ├── enriched_leads.json
│   │       └── sheet_url.txt
│   └── google_maps_lists/       # Google Maps campaigns
│       └── campaign_name_YYYYMMDD/
│           ├── raw_leads.json
│           ├── enriched_leads.json
│           └── sheet_url.txt
└── client_name_2/
    └── ...
```

## Client Metadata Schema

Each client has a `client.json` file with the following structure:

```json
{
  "client_id": "unique_client_identifier",
  "company_name": "Client Company Name",
  "contact_email": "contact@client.com",
  "industry": "Technology",
  "product": "Product/Service Description",
  "icp": {
    "description": "Target customer profile description",
    "job_titles": ["Title 1", "Title 2"],
    "company_size": "50-500",
    "industries": ["Industry 1", "Industry 2"],
    "locations": ["Location 1", "Location 2"]
  },
  "created_at": "ISO 8601 timestamp",
  "updated_at": "ISO 8601 timestamp",
  "campaigns": [
    {
      "campaign_id": "campaign_name_20251205",
      "campaign_name": "Q4 Tech Leaders",
      "type": "apollo",
      "created_at": "ISO 8601 timestamp",
      "lead_count": 1042,
      "sheet_url": "https://docs.google.com/spreadsheets/d/..."
    }
  ]
}
```

## Campaign Organization

- **Apollo campaigns**: Go in `apollo_lists/` subfolder
- **Google Maps campaigns**: Go in `google_maps_lists/` subfolder
- Each campaign gets its own timestamped folder
- Campaign metadata is tracked in parent `client.json`

## Adding a New Client

Use the client management directive and execution script:

```bash
python execution/client_manager.py add
```

This will prompt for all required client information and create the folder structure automatically.

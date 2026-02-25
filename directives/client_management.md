# Client Management System

**Status:** Active as of Dec 5, 2025
**Purpose:** Organize campaigns by client, track client metadata, and maintain campaign history

---

## Overview

The client management system provides structured organization of lead generation campaigns by client. Each client has their own folder with metadata and segregated Apollo/Google Maps campaigns.

**Key Benefits:**
- Organize campaigns by client for easy tracking
- Store client ICP (Ideal Customer Profile) for campaign planning
- Maintain campaign history with metrics and deliverables
- Separate Apollo and Google Maps campaigns for clarity

---

## Directory Structure

```
campaigns/
├── client_name_1/
│   ├── client.json                    # Client metadata
│   ├── apollo_lists/                  # Apollo campaigns
│   │   └── campaign_name_20251205/
│   │       ├── raw_leads.json
│   │       ├── enriched_leads.json
│   │       └── sheet_url.txt
│   └── google_maps_lists/             # Google Maps campaigns
│       └── campaign_name_20251205/
│           ├── raw_leads.json
│           ├── enriched_leads.json
│           └── sheet_url.txt
└── client_name_2/
    └── ...
```

---

## Client Metadata Schema

Each client has a `client.json` file:

```json
{
  "client_id": "acme_corp",
  "company_name": "Acme Corporation",
  "contact_email": "contact@acme.com",
  "industry": "Technology",
  "product": "Enterprise SaaS Platform",
  "icp": {
    "description": "B2B SaaS companies with 100-1000 employees",
    "job_titles": ["CTO", "VP Engineering", "Head of Product"],
    "company_size": "100-1000",
    "industries": ["SaaS", "Technology"],
    "locations": ["United States", "Canada"]
  },
  "created_at": "2025-12-05T00:00:00Z",
  "updated_at": "2025-12-05T00:00:00Z",
  "campaigns": [
    {
      "campaign_id": "q4_tech_leaders_20251205",
      "campaign_name": "Q4 Tech Leaders",
      "type": "apollo",
      "created_at": "2025-12-05T10:30:00Z",
      "lead_count": 1042,
      "sheet_url": "https://docs.google.com/spreadsheets/d/..."
    }
  ]
}
```

---

## Workflow: Adding a New Client

### Tools Required
- `execution/client_manager.py`

### Steps

**1. Interactive Method (Recommended for first-time use)**

```bash
python execution/client_manager.py add
```

This will prompt for:
- Company name (required)
- Contact email (required)
- Industry (required)
- Product/service description (required)
- ICP details:
  - Description
  - Target job titles (comma-separated)
  - Company size range
  - Target industries (comma-separated)
  - Target locations (comma-separated)

**2. Programmatic Method (For AI orchestration)**

```python
from execution.client_manager import create_client

client_data = {
    "company_name": "Acme Corporation",
    "contact_email": "contact@acme.com",
    "industry": "Technology",
    "product": "Enterprise SaaS Platform",
    "icp": {
        "description": "B2B SaaS companies with 100-1000 employees",
        "job_titles": ["CTO", "VP Engineering"],
        "company_size": "100-1000",
        "industries": ["SaaS", "Technology"],
        "locations": ["United States", "Canada"]
    }
}

client_id = create_client(client_data)
print(f"Created client: {client_id}")
```

**Output:**
- Creates folder: `campaigns/acme_corp/`
- Creates subfolders: `apollo_lists/`, `google_maps_lists/`
- Creates metadata: `client.json`

---

## Workflow: Running a Campaign for a Client

### When to Use
Every time you run a lead generation campaign (Apollo or Google Maps), associate it with a client.

### Steps

**1. Identify the Client**

```bash
# List all clients
python execution/client_manager.py list

# Get specific client details
python execution/client_manager.py get acme_corp
```

**2. Run the Campaign (Apollo or Google Maps)**

Follow the existing directives:
- For Apollo: `directives/lead_generation_v5_optimized.md`
- For Google Maps: `directives/gmaps_lead_generation.md`

**3. Add Campaign to Client**

After campaign completes, register it:

```python
from execution.client_manager import add_campaign_to_client

campaign_data = {
    "campaign_name": "Q4 Tech Leaders",
    "type": "apollo",  # or "google_maps"
    "lead_count": 1042,
    "sheet_url": "https://docs.google.com/spreadsheets/d/..."
}

add_campaign_to_client("acme_corp", campaign_data)
```

**4. Store Campaign Files**

Move campaign outputs to the client folder:

```bash
# Determine the campaign folder
campaigns/acme_corp/apollo_lists/q4_tech_leaders_20251205/

# Copy final outputs
raw_leads.json          # Initial scraped leads
enriched_leads.json     # Fully enriched leads
sheet_url.txt           # Google Sheets URL
```

---

## Integration with Existing Workflows

### Apollo Lead Generation V4

**Modifications needed:**
1. At start: Ask which client this campaign is for
2. After export: Register campaign with `add_campaign_to_client()`
3. Store outputs in client's `apollo_lists/` folder

**Example integration:**

```python
# Step 0: Identify client
client_id = "acme_corp"
campaign_name = "Q4 Tech Leaders"

# Steps 1-8: Run Apollo V5 workflow (see lead_generation_v5_optimized.md)
# 1. Scrape with olympus (handle cookie renewal if needed)
# 2. Extract filters
# 3. Test with code_crafter (25 leads)
# 4. Validate 80% match
# 5. Full scrape with code_crafter
# 6. Scrape with peakydev
# 7. Handle peakydev failures
# 8. Merge & deduplicate
# 9-14. Email validation, enrichment, AI enrichment, export

# Step 15: Register campaign
from execution.client_manager import add_campaign_to_client

add_campaign_to_client(client_id, {
    "campaign_name": campaign_name,
    "type": "apollo",
    "lead_count": final_lead_count,
    "sheet_url": google_sheet_url
})

# Step 16: Store outputs
import shutil
campaign_dir = f"campaigns/{client_id}/apollo_lists/{campaign_name.lower().replace(' ', '_')}_{timestamp}"
shutil.copy("path/to/enriched_leads.json", f"{campaign_dir}/enriched_leads.json")
```

### Google Maps Lead Generation

**Modifications needed:**
1. At start: Ask which client this campaign is for
2. After export: Register campaign with `add_campaign_to_client()`
3. Store outputs in client's `google_maps_lists/` folder

**Example integration:**

```python
# Step 0: Identify client
client_id = "acme_corp"
campaign_name = "Bay Area Restaurants"

# Steps 1-4: Run Google Maps workflow as usual
# (scraping, enrichment, export)

# Step 5: Register campaign
from execution.client_manager import add_campaign_to_client

add_campaign_to_client(client_id, {
    "campaign_name": campaign_name,
    "type": "google_maps",
    "lead_count": final_lead_count,
    "sheet_url": google_sheet_url
})

# Step 6: Store outputs
import shutil
campaign_dir = f"campaigns/{client_id}/google_maps_lists/{campaign_name.lower().replace(' ', '_')}_{timestamp}"
shutil.copy("path/to/enriched_leads.json", f"{campaign_dir}/enriched_leads.json")
```

---

## Client Management Operations

### List All Clients

```bash
python execution/client_manager.py list
```

Output:
```
=== Clients (3) ===

Client ID: acme_corp
  Company: Acme Corporation
  Industry: Technology
  Contact: contact@acme.com
  Campaigns: 2

Client ID: beta_inc
  Company: Beta Inc
  Industry: Finance
  Contact: contact@beta.com
  Campaigns: 1
```

### Get Client Details

```bash
python execution/client_manager.py get acme_corp
```

Returns full JSON metadata including all campaigns.

### Update Client Information

```python
from execution.client_manager import update_client

updates = {
    "contact_email": "new_contact@acme.com",
    "product": "Updated product description"
}

update_client("acme_corp", updates)
```

---

## Best Practices

**1. Always Associate Campaigns with Clients**
- Don't run orphan campaigns without a client
- If it's a test, create a "test_client" or "internal_testing" client

**2. Use Descriptive Campaign Names**
- Good: "Q4 Tech Leaders", "Bay Area Restaurants", "EMEA Enterprise"
- Bad: "test1", "campaign_dec5", "list"

**3. Store Deliverable URLs**
- Always save the Google Sheets URL in campaign metadata
- This is the source of truth for deliverables

**4. Keep `.tmp/` Separate and Clean**
- Use `.tmp/` for processing (as usual)
- Copy final outputs to `campaigns/client_name/` at the end
- `.tmp/` remains regenerable and gitignored
- After a campaign is complete and data is saved in `campaigns/`, **delete the campaign-specific .tmp/ dirs** (e.g. `.tmp/codecrafter_example_training_hr_20260212/`)
- Standard output dirs (`b2b_finder/`, `codecrafter/`, `peakydev/`, `merged/`, etc.) stay -- they get overwritten by next scrape

**5. External CSV Imports**
- Place external CSV files (Google Sheets exports, cold email exports) in `.tmp/imports/`
- Update the README manifest in `.tmp/imports/` with origin and related campaign
- Never leave loose CSVs in the root directory

**6. Update Client ICP as Needed**
- If target audience changes, update the ICP in `client.json`
- This helps with planning future campaigns

---

## Error Handling

**Client Already Exists:**
```python
try:
    create_client(client_data)
except ValueError as e:
    print(f"Error: {e}")
    # Use update_client() instead
```

**Client Not Found:**
```python
client = get_client("nonexistent_client")
if not client:
    print("Client not found")
    # List available clients or create new one
```

**Invalid Campaign Type:**
```python
try:
    add_campaign_to_client(client_id, {"type": "invalid"})
except ValueError as e:
    print(f"Error: {e}")
    # Must be "apollo" or "google_maps"
```

---

## Migration from Existing Campaigns

If you have historical campaigns in `.tmp/` that you want to associate with clients:

**1. Create the client first**
```bash
python execution/client_manager.py add
```

**2. Manually register historical campaigns**
```python
from execution.client_manager import add_campaign_to_client
import json

# Load historical lead file
with open(".tmp/ai_enriched/cleaned_leads_20251204_090118_1039leads.json", "r") as f:
    leads = json.load(f)

# Register with client
add_campaign_to_client("acme_corp", {
    "campaign_name": "Historical Dec 4 Campaign",
    "type": "apollo",
    "lead_count": len(leads),
    "sheet_url": "https://docs.google.com/spreadsheets/d/..."  # If you have it
})
```

**3. Copy files to client folder**
```bash
# Find the campaign folder created
# Copy relevant files there
```

---

## Cost Tracking (Future Enhancement)

Campaign metadata can be extended to include cost tracking:

```json
{
  "campaign_id": "q4_tech_leaders_20251205",
  "lead_count": 1042,
  "costs": {
    "scraping": 15.00,
    "email_verification": 0.31,
    "email_enrichment": 1.04,
    "ai_enrichment": 0.42,
    "total": 16.77
  },
  "cost_per_lead": 0.016
}
```

This requires modifying `client_manager.py` to accept and store cost data.

---

## Summary

The client management system provides:
- ✓ Structured organization by client
- ✓ Campaign history and metrics
- ✓ ICP storage for targeting
- ✓ Separation of Apollo vs Google Maps campaigns
- ✓ Easy integration with existing workflows

**Tools:**
- `execution/client_manager.py` - All client operations
- `campaigns/` - Client folders and metadata

**Next Steps:**
1. Add your first client: `python execution/client_manager.py add`
2. Run a campaign using existing directives
3. Register campaign with client using `add_campaign_to_client()`
4. Store campaign outputs in client's folder

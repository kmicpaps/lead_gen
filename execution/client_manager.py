# [CLI] — run via: py execution/client_manager.py --help
"""
Client Management System

Handles client creation, metadata management, and campaign organization.
Supports both Apollo and Google Maps campaign types.

Usage:
    python client_manager.py add                           # Add new client (interactive)
    python client_manager.py list                          # List all clients
    python client_manager.py get <client_id>               # Get client details
    python client_manager.py update <client_id>            # Update client info
    python client_manager.py add-campaign <client_id>      # Add campaign to client

Functions for programmatic use:
    - create_client(client_data)
    - get_client(client_id)
    - update_client(client_id, updates)
    - add_campaign_to_client(client_id, campaign_data)
    - list_clients()
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_json, save_json

# Base directory
BASE_DIR = Path(__file__).parent.parent
CAMPAIGNS_DIR = BASE_DIR / "campaigns"


def normalize_client_id(company_name: str) -> str:
    """Convert company name to valid folder name (client_id)."""
    # Remove special chars, convert to lowercase, replace spaces with underscores
    client_id = company_name.lower()
    client_id = ''.join(c if c.isalnum() or c.isspace() else '' for c in client_id)
    client_id = '_'.join(client_id.split())
    return client_id


def create_client(client_data: Dict) -> str:
    """
    Create a new client with folder structure and metadata.

    Args:
        client_data: Dict with keys: company_name, contact_email, industry, product, icp

    Returns:
        client_id of created client

    Raises:
        ValueError if client already exists or required fields missing
    """
    required_fields = ['company_name', 'contact_email', 'industry', 'product', 'icp']
    missing = [f for f in required_fields if f not in client_data]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    client_id = normalize_client_id(client_data['company_name'])
    client_dir = CAMPAIGNS_DIR / client_id

    # Check if client already exists
    if client_dir.exists():
        raise ValueError(f"Client '{client_id}' already exists")

    # Create folder structure
    client_dir.mkdir(parents=True, exist_ok=True)
    (client_dir / "apollo_lists").mkdir(exist_ok=True)
    (client_dir / "google_maps_lists").mkdir(exist_ok=True)

    # Create client metadata
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    metadata = {
        "client_id": client_id,
        "company_name": client_data['company_name'],
        "contact_email": client_data['contact_email'],
        "industry": client_data['industry'],
        "product": client_data['product'],
        "icp": client_data['icp'],
        "created_at": now,
        "updated_at": now,
        "campaigns": []
    }

    # Write metadata file
    metadata_file = client_dir / "client.json"
    save_json(metadata, metadata_file)

    print(f"[OK] Created client '{client_id}'")
    print(f"  Directory: {client_dir}")
    print(f"  Metadata: {metadata_file}")

    return client_id


def get_client(client_id: str) -> Optional[Dict]:
    """
    Get client metadata.

    Args:
        client_id: Client identifier

    Returns:
        Client metadata dict or None if not found
    """
    client_file = CAMPAIGNS_DIR / client_id / "client.json"

    if not client_file.exists():
        return None

    return load_json(client_file)


def update_client(client_id: str, updates: Dict) -> bool:
    """
    Update client metadata.

    Args:
        client_id: Client identifier
        updates: Dict of fields to update

    Returns:
        True if successful, False if client not found
    """
    client = get_client(client_id)
    if not client:
        return False

    # Update fields
    for key, value in updates.items():
        if key not in ['client_id', 'created_at', 'campaigns']:  # Protect immutable fields
            client[key] = value

    client['updated_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Write back
    client_file = CAMPAIGNS_DIR / client_id / "client.json"
    save_json(client, client_file)

    print(f"[OK] Updated client '{client_id}'")
    return True


def add_campaign_to_client(client_id: str, campaign_data: Dict) -> bool:
    """
    Add a campaign to client's metadata and create campaign folder.

    Args:
        client_id: Client identifier
        campaign_data: Dict with keys: campaign_name, type (apollo/google_maps),
                       lead_count (optional), sheet_url (optional)

    Returns:
        True if successful, False if client not found

    Raises:
        ValueError if required fields missing or invalid type
    """
    client = get_client(client_id)
    if not client:
        return False

    # Validate campaign type
    campaign_type = campaign_data.get('type', 'apollo')
    if campaign_type not in ['apollo', 'google_maps']:
        raise ValueError(f"Invalid campaign type: {campaign_type}. Must be 'apollo' or 'google_maps'")

    # Generate campaign ID
    campaign_name = campaign_data.get('campaign_name', 'untitled')
    timestamp = datetime.now().strftime('%Y%m%d')
    campaign_id = f"{campaign_name.lower().replace(' ', '_')}_{timestamp}"

    # Create campaign folder
    list_folder = "apollo_lists" if campaign_type == "apollo" else "google_maps_lists"
    campaign_dir = CAMPAIGNS_DIR / client_id / list_folder / campaign_id
    campaign_dir.mkdir(parents=True, exist_ok=True)

    # Add to client metadata
    campaign_metadata = {
        "campaign_id": campaign_id,
        "campaign_name": campaign_data.get('campaign_name', 'Untitled Campaign'),
        "type": campaign_type,
        "created_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        "lead_count": campaign_data.get('lead_count', 0),
        "sheet_url": campaign_data.get('sheet_url', '')
    }

    client['campaigns'].append(campaign_metadata)
    client['updated_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Write back
    client_file = CAMPAIGNS_DIR / client_id / "client.json"
    save_json(client, client_file)

    print(f"[OK] Added campaign '{campaign_id}' to client '{client_id}'")
    print(f"  Campaign folder: {campaign_dir}")

    return True


def list_clients() -> List[Dict]:
    """
    List all clients.

    Returns:
        List of client metadata dicts
    """
    clients = []

    if not CAMPAIGNS_DIR.exists():
        return clients

    for client_dir in CAMPAIGNS_DIR.iterdir():
        if client_dir.is_dir() and (client_dir / "client.json").exists():
            client = get_client(client_dir.name)
            if client:
                clients.append(client)

    return clients


def interactive_add_client():
    """Interactive prompt to add a new client."""
    print("\n=== Add New Client ===\n")

    company_name = input("Company name: ").strip()
    if not company_name:
        print("Error: Company name is required")
        return

    contact_email = input("Contact email: ").strip()
    if not contact_email:
        print("Error: Contact email is required")
        return

    industry = input("Industry: ").strip()
    if not industry:
        print("Error: Industry is required")
        return

    product = input("Product/Service: ").strip()
    if not product:
        print("Error: Product is required")
        return

    print("\n--- ICP (Ideal Customer Profile) ---")
    icp_description = input("ICP description: ").strip()

    job_titles = input("Target job titles (comma-separated): ").strip()
    job_titles = [t.strip() for t in job_titles.split(',')] if job_titles else []

    company_size = input("Company size (e.g., 50-500): ").strip()

    industries = input("Target industries (comma-separated): ").strip()
    industries = [i.strip() for i in industries.split(',')] if industries else []

    locations = input("Target locations (comma-separated): ").strip()
    locations = [l.strip() for l in locations.split(',')] if locations else []

    icp = {
        "description": icp_description,
        "job_titles": job_titles,
        "company_size": company_size,
        "industries": industries,
        "locations": locations
    }

    client_data = {
        "company_name": company_name,
        "contact_email": contact_email,
        "industry": industry,
        "product": product,
        "icp": icp
    }

    try:
        client_id = create_client(client_data)
        print(f"\n[OK] Successfully created client: {client_id}")
    except ValueError as e:
        print(f"\nError: {e}")


def interactive_list_clients():
    """List all clients with summary info."""
    clients = list_clients()

    if not clients:
        print("\nNo clients found.")
        return

    print(f"\n=== Clients ({len(clients)}) ===\n")

    for client in clients:
        print(f"Client ID: {client['client_id']}")
        print(f"  Company: {client['company_name']}")
        print(f"  Industry: {client['industry']}")
        print(f"  Contact: {client['contact_email']}")
        print(f"  Campaigns: {len(client['campaigns'])}")
        print()


def interactive_get_client():
    """Get detailed info about a specific client."""
    client_id = input("\nClient ID: ").strip()

    client = get_client(client_id)
    if not client:
        print(f"Error: Client '{client_id}' not found")
        return

    print(f"\n=== Client: {client['company_name']} ===\n")
    print(json.dumps(client, indent=2))


def main():
    """CLI entry point."""
    CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python client_manager.py add                 # Add new client")
        print("  python client_manager.py list                # List all clients")
        print("  python client_manager.py get <client_id>     # Get client details")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "add":
        interactive_add_client()
    elif command == "list":
        interactive_list_clients()
    elif command == "get":
        if len(sys.argv) < 3:
            print("Error: client_id required")
            sys.exit(1)
        client_id = sys.argv[2]
        client = get_client(client_id)
        if not client:
            print(f"Error: Client '{client_id}' not found")
            sys.exit(1)
        print(json.dumps(client, indent=2))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()

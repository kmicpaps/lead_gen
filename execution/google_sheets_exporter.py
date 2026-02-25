# [CLI] — run via: py execution/google_sheets_exporter.py --help
"""
Script to upload leads to Google Sheets.
"""

import os
import sys
import json
import argparse
import csv
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']

def main():
    parser = argparse.ArgumentParser(description='Upload leads to Google Sheets')
    parser.add_argument('--input', required=True, help='Path to leads JSON file')
    parser.add_argument('--sheet-title', help='Custom title for Google Sheet (optional)')
    parser.add_argument('--sheet-id', help='Existing Google Sheet ID to update (instead of creating new)')
    parser.add_argument('--mode', choices=['create', 'append', 'replace'], default='create',
                        help='create: new sheet (default), append: add rows to existing, replace: clear & rewrite existing')

    args = parser.parse_args()
    
    try:
        # Load leads
        with open(args.input, 'r', encoding='utf-8') as f:
            leads = json.load(f)
            
        if not leads:
            print("No leads to upload.")
            return 0

        # Authenticate
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if os.path.exists('credentials.json'):
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                    # Save the credentials for the next run
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
                else:
                    print("Warning: credentials.json not found. Saving to CSV instead.")
                    save_to_csv(leads, args.input)
                    return 0

        try:
            service = build('sheets', 'v4', credentials=creds)

            # Determine sheet ID — create new or use existing
            if args.sheet_id:
                spreadsheet_id = args.sheet_id
                spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{args.sheet_id}/edit"
                print(f"Using existing Google Sheet: {spreadsheet_url}")
                print(f"Mode: {args.mode}")
            else:
                # Create a new spreadsheet
                if args.sheet_title:
                    sheet_title = args.sheet_title
                else:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                    sheet_title = f'Leads Export - {timestamp}'

                spreadsheet_body = {
                    'properties': {
                        'title': sheet_title
                    }
                }
                spreadsheet = service.spreadsheets().create(body=spreadsheet_body, fields='spreadsheetId,spreadsheetUrl').execute()
                spreadsheet_id = spreadsheet.get('spreadsheetId')
                spreadsheet_url = spreadsheet.get('spreadsheetUrl')

                print(f"Created Google Sheet: {spreadsheet_url}")

                # Share the sheet with anyone who has the link (editor access)
                try:
                    drive_service = build('drive', 'v3', credentials=creds)
                    permission = {
                        'type': 'anyone',
                        'role': 'writer'
                    }
                    drive_service.permissions().create(
                        fileId=spreadsheet_id,
                        body=permission
                    ).execute()
                    print(f"Sheet shared: Anyone with the link can edit")
                except HttpError as share_err:
                    print(f"Warning: Could not share sheet automatically: {share_err}")
                    print(f"You may need to share the sheet manually")

            # Prepare data - using standardized schema
            # Support both old schema and new flattened schema
            # Include AI enrichment fields and LinkedIn/Website enrichment
            headers = [
                'First Name', 'Last Name', 'Full Name', 'Job Title', 'Email', 'Email Status',
                'LinkedIn URL', 'City', 'Country', 'Company Name', 'Casual Company Name',
                'Company Website', 'Company LinkedIn', 'Company Phone', 'Company Domain',
                'Company Country', 'Industry', 'Company Summary', 'Icebreaker',
                # LinkedIn enrichment fields
                'LinkedIn Headline', 'LinkedIn Bio', 'LinkedIn Industry', 'LinkedIn Location',
                'LinkedIn Followers', 'LinkedIn Experience', 'LinkedIn Education',
                # Website enrichment
                'Website Content',
                'Source'
            ]

            values = [headers]
            for lead in leads:
                # Skip junk/log messages from scrapers
                name = lead.get('full_name', '') or lead.get('name', '')
                if name and ('👀' in name or '⏳' in name or 'Actor' in name or 'Scanning pages' in name):
                    continue

                # Handle nested org_name object (B2B finder format) vs flat company_name
                company_name = lead.get('company_name', '')
                company_website = lead.get('company_website', '')
                company_linkedin = lead.get('company_linkedin', '')
                company_phone = lead.get('company_phone', '') or lead.get('organization_phone', '')
                company_domain = lead.get('company_domain', '')

                # Handle org_name field (can be dict or string)
                if 'org_name' in lead:
                    org_name_value = lead.get('org_name', '')

                    if isinstance(org_name_value, dict):
                        # B2B Finder format: org_name is a dict with nested fields
                        if not company_name:
                            company_name = org_name_value.get('name', '')
                        if not company_website:
                            company_website = org_name_value.get('website_url', '')
                        if not company_linkedin:
                            company_linkedin = org_name_value.get('linkedin_url', '')
                        if not company_phone:
                            company_phone = org_name_value.get('phone', '')
                        if not company_domain:
                            company_domain = org_name_value.get('primary_domain', '')
                    elif isinstance(org_name_value, str) and org_name_value:
                        # CodeCrafter format: org_name is a string
                        if not company_name:
                            company_name = org_name_value
                        # Use flat fields for other data
                        if not company_website:
                            company_website = lead.get('website_url', '')
                        if not company_phone:
                            company_phone = lead.get('organization_phone', '')
                else:
                    # Fallback to flat fields if org_name doesn't exist
                    if not company_website:
                        company_website = lead.get('website_url', '')

                # Extract industry (AI-enriched field)
                industry = lead.get('industry', '')

                # Format LinkedIn experience as string
                experience_list = lead.get('linkedin_experience', [])
                if experience_list and isinstance(experience_list, list):
                    experience_str = ' | '.join([
                        f"{exp.get('title', '')} @ {exp.get('company', '')} ({exp.get('period', '')})"
                        for exp in experience_list[:3]  # Top 3 experiences
                    ])
                else:
                    experience_str = ''

                # Format LinkedIn education as string
                education_list = lead.get('linkedin_education', [])
                if education_list and isinstance(education_list, list):
                    education_str = ' | '.join([
                        f"{edu.get('degree', '')} @ {edu.get('school', '')}"
                        for edu in education_list[:2]  # Top 2 education entries
                    ])
                else:
                    education_str = ''

                # Truncate website content for spreadsheet (max 1000 chars)
                website_content = lead.get('website_content', '')
                if len(website_content) > 1000:
                    website_content = website_content[:1000] + '...'

                row = [
                    lead.get('first_name', ''),
                    lead.get('last_name', ''),
                    name,
                    lead.get('job_title', '') or lead.get('title', ''),  # Support both field names
                    lead.get('email', ''),
                    lead.get('email_status', ''),
                    lead.get('linkedin_url', ''),
                    lead.get('city', ''),
                    lead.get('country', ''),
                    company_name,
                    lead.get('casual_org_name', ''),  # AI-enriched casual company name
                    company_website,
                    company_linkedin,
                    company_phone,
                    company_domain,
                    lead.get('company_country', ''),
                    industry,  # AI-enriched industry categorization
                    lead.get('company_summary', ''),  # AI-generated company summary
                    lead.get('icebreaker', ''),  # AI-generated icebreaker
                    # LinkedIn enrichment fields
                    lead.get('linkedin_headline', ''),
                    lead.get('linkedin_bio', ''),
                    lead.get('linkedin_industry', ''),
                    lead.get('linkedin_location', ''),
                    lead.get('linkedin_followers', ''),
                    experience_str,
                    education_str,
                    # Website content
                    website_content,
                    lead.get('source', '')
                ]
                values.append(row)
            
            # Write data based on mode
            if args.sheet_id and args.mode == 'append':
                # Append mode: add rows after existing data (skip header row)
                body = {'values': values[1:]}
                result = service.spreadsheets().values().append(
                    spreadsheetId=spreadsheet_id, range="A1",
                    valueInputOption="RAW", insertDataOption="INSERT_ROWS",
                    body=body).execute()
                updated = result.get('updates', {}).get('updatedRows', 0)
                print(f"Appended {updated} rows to Google Sheet.")
            elif args.sheet_id and args.mode == 'replace':
                # Replace mode: clear all data then write fresh
                service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id, range="A:ZZ").execute()
                body = {'values': values}
                service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id, range="A1",
                    valueInputOption="RAW", body=body).execute()
                print(f"Replaced sheet data with {len(values) - 1} leads.")
            else:
                # Create mode (default): write to new sheet
                body = {'values': values}
                service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id, range="A1",
                    valueInputOption="RAW", body=body).execute()
                print(f"Successfully uploaded {len(leads)} leads to Google Sheet.")

            print(f"Link: {spreadsheet_url}")
            
        except HttpError as err:
            print(f"Google Sheets API Error: {err}")
            print("Falling back to CSV.")
            save_to_csv(leads, args.input)
            
    except Exception as e:
        print(f"Error uploading to Google Sheets: {e}", file=sys.stderr)
        return 1
        
    return 0

def save_to_csv(leads, input_path):
    """Fallback to CSV if Google Sheets fails."""
    csv_path = input_path.replace('.json', '.csv')

    headers = [
        'first_name', 'last_name', 'name', 'job_title', 'email', 'email_status',
        'linkedin_url', 'city', 'country', 'company_name', 'casual_org_name',
        'company_website', 'company_linkedin', 'company_phone', 'company_domain',
        'company_country', 'industry', 'company_summary', 'icebreaker', 'source'
    ]
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(leads)
        
    print(f"Saved leads to local CSV: {csv_path}")

if __name__ == "__main__":
    sys.exit(main())

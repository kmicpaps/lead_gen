# [CLI] — run via: py execution/fix_csv_name_diacritics.py --help
"""
Fix Name Diacritics in CSV Files

Processes a CSV file containing lead data and restores Latvian/Baltic
diacritical marks to names using LinkedIn URL slugs.

Usage:
    python execution/fix_csv_name_diacritics.py --input leads.csv --output leads_fixed.csv

Input CSV must have columns:
    - LinkedIn URL (required): 'LinkedIn URL', 'linkedin_url', or 'linkedinUrl'
    - First Name (optional): 'First Name', 'first_name', or 'firstName'
    - Last Name (optional): 'Last Name', 'last_name', or 'lastName'
    - Full Name (optional): 'Full Name', 'name', 'full_name', or 'fullName'

Output CSV will have the same columns with corrected names.
"""

import os
import sys
import csv
import argparse
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

# Fix Windows console encoding for Unicode output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from execution.name_diacritics_fixer import fix_lead_names, fix_name_from_linkedin
except ImportError:
    from name_diacritics_fixer import fix_lead_names, fix_name_from_linkedin


# Column name mappings (various formats that might be used)
LINKEDIN_URL_COLUMNS = ['LinkedIn URL', 'linkedin_url', 'linkedinUrl', 'LinkedIn', 'linkedin']
FIRST_NAME_COLUMNS = ['First Name', 'first_name', 'firstName', 'First_Name']
LAST_NAME_COLUMNS = ['Last Name', 'last_name', 'lastName', 'Last_Name']
FULL_NAME_COLUMNS = ['Full Name', 'full_name', 'fullName', 'name', 'Name', 'Full_Name']


def find_column(headers: List[str], possible_names: List[str]) -> Optional[str]:
    """Find the actual column name from a list of possibilities."""
    for name in possible_names:
        if name in headers:
            return name
    return None


def fix_csv_names(
    input_path: str,
    output_path: str,
    encoding: str = 'utf-8'
) -> Dict[str, Any]:
    """
    Process a CSV file and fix name diacritics.

    Args:
        input_path: Path to input CSV file
        output_path: Path to output CSV file
        encoding: File encoding (default: utf-8)

    Returns:
        Statistics dict with counts
    """
    stats = {
        'total_rows': 0,
        'rows_with_linkedin': 0,
        'names_fixed': 0,
        'names_unchanged': 0,
        'errors': 0
    }

    # Read input file
    try:
        with open(input_path, 'r', encoding=encoding, newline='') as f:
            # Try to detect delimiter
            sample = f.read(4096)
            f.seek(0)

            # Check for common delimiters
            if sample.count(';') > sample.count(','):
                delimiter = ';'
            else:
                delimiter = ','

            reader = csv.DictReader(f, delimiter=delimiter)
            headers = reader.fieldnames

            if not headers:
                print(f"Error: Could not read headers from {input_path}", file=sys.stderr)
                return stats

            # Find relevant columns
            linkedin_col = find_column(headers, LINKEDIN_URL_COLUMNS)
            first_name_col = find_column(headers, FIRST_NAME_COLUMNS)
            last_name_col = find_column(headers, LAST_NAME_COLUMNS)
            full_name_col = find_column(headers, FULL_NAME_COLUMNS)

            if not linkedin_col:
                print(f"Error: No LinkedIn URL column found in CSV", file=sys.stderr)
                print(f"Expected one of: {LINKEDIN_URL_COLUMNS}", file=sys.stderr)
                print(f"Found columns: {headers}", file=sys.stderr)
                return stats

            print(f"Input file: {input_path}")
            print(f"Detected columns:")
            print(f"  LinkedIn URL: {linkedin_col}")
            print(f"  First Name: {first_name_col or '(not found)'}")
            print(f"  Last Name: {last_name_col or '(not found)'}")
            print(f"  Full Name: {full_name_col or '(not found)'}")
            print()

            # Process rows
            rows = []
            changes = []

            for row in reader:
                stats['total_rows'] += 1

                linkedin_url = row.get(linkedin_col, '')
                if not linkedin_url:
                    rows.append(row)
                    continue

                stats['rows_with_linkedin'] += 1

                # Get current names
                first_name = row.get(first_name_col, '') if first_name_col else ''
                last_name = row.get(last_name_col, '') if last_name_col else ''
                full_name = row.get(full_name_col, '') if full_name_col else ''

                # Fix names
                try:
                    fixed = fix_name_from_linkedin(first_name, last_name, full_name, linkedin_url)

                    # Check if any changes were made
                    changed = False
                    change_details = []

                    if first_name_col and fixed['first_name'] != first_name:
                        row[first_name_col] = fixed['first_name']
                        changed = True
                        change_details.append(f"first: {first_name} -> {fixed['first_name']}")

                    if last_name_col and fixed['last_name'] != last_name:
                        row[last_name_col] = fixed['last_name']
                        changed = True
                        change_details.append(f"last: {last_name} -> {fixed['last_name']}")

                    if full_name_col and fixed['name'] != full_name:
                        row[full_name_col] = fixed['name']
                        changed = True
                        change_details.append(f"full: {full_name} -> {fixed['name']}")

                    if changed:
                        stats['names_fixed'] += 1
                        changes.append({
                            'row': stats['total_rows'],
                            'original': full_name or f"{first_name} {last_name}".strip(),
                            'fixed': fixed['name'],
                            'details': change_details
                        })
                    else:
                        stats['names_unchanged'] += 1

                except Exception as e:
                    stats['errors'] += 1
                    print(f"Warning: Error processing row {stats['total_rows']}: {e}", file=sys.stderr)

                rows.append(row)

    except UnicodeDecodeError:
        print(f"Error: Could not read file with {encoding} encoding.", file=sys.stderr)
        print("Try specifying a different encoding with --encoding", file=sys.stderr)
        return stats
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        return stats

    # Write output file
    try:
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        print(f"Output written to: {output_path}")

    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        return stats

    # Print summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total rows processed: {stats['total_rows']}")
    print(f"Rows with LinkedIn URL: {stats['rows_with_linkedin']}")
    print(f"Names fixed (diacritics restored): {stats['names_fixed']}")
    print(f"Names unchanged: {stats['names_unchanged']}")
    if stats['errors']:
        print(f"Errors: {stats['errors']}")
    print()

    # Show sample of changes
    if changes:
        print("Sample of changes made:")
        print("-" * 60)
        for change in changes[:10]:  # Show first 10 changes
            print(f"  Row {change['row']}: {change['original']} -> {change['fixed']}")
        if len(changes) > 10:
            print(f"  ... and {len(changes) - 10} more")
        print()

    return stats


def fix_json_names(
    input_path: str,
    output_path: str,
    encoding: str = 'utf-8'
) -> Dict[str, Any]:
    """
    Process a JSON file and fix name diacritics.

    Args:
        input_path: Path to input JSON file
        output_path: Path to output JSON file
        encoding: File encoding (default: utf-8)

    Returns:
        Statistics dict with counts
    """
    stats = {
        'total_leads': 0,
        'leads_with_linkedin': 0,
        'names_fixed': 0,
        'names_unchanged': 0,
        'errors': 0
    }

    try:
        with open(input_path, 'r', encoding=encoding) as f:
            leads = json.load(f)

        if not isinstance(leads, list):
            print(f"Error: JSON file must contain a list of leads", file=sys.stderr)
            return stats

        print(f"Input file: {input_path}")
        print(f"Total leads: {len(leads)}")
        print()

        changes = []

        for i, lead in enumerate(leads):
            stats['total_leads'] += 1

            linkedin_url = lead.get('linkedin_url', '') or lead.get('linkedinUrl', '')
            if not linkedin_url:
                continue

            stats['leads_with_linkedin'] += 1

            # Get original name
            original_name = lead.get('name', '') or lead.get('full_name', '') or lead.get('fullName', '')

            # Fix names
            try:
                fix_lead_names(lead)

                new_name = lead.get('name', '') or lead.get('full_name', '') or lead.get('fullName', '')

                if original_name != new_name:
                    stats['names_fixed'] += 1
                    changes.append({
                        'index': i,
                        'original': original_name,
                        'fixed': new_name
                    })
                else:
                    stats['names_unchanged'] += 1

            except Exception as e:
                stats['errors'] += 1
                print(f"Warning: Error processing lead {i}: {e}", file=sys.stderr)

        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(leads, f, indent=2, ensure_ascii=False)

        print(f"Output written to: {output_path}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return stats

    # Print summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total leads processed: {stats['total_leads']}")
    print(f"Leads with LinkedIn URL: {stats['leads_with_linkedin']}")
    print(f"Names fixed (diacritics restored): {stats['names_fixed']}")
    print(f"Names unchanged: {stats['names_unchanged']}")
    if stats['errors']:
        print(f"Errors: {stats['errors']}")
    print()

    # Show sample of changes
    if changes:
        print("Sample of changes made:")
        print("-" * 60)
        for change in changes[:10]:
            print(f"  Lead {change['index']}: {change['original']} -> {change['fixed']}")
        if len(changes) > 10:
            print(f"  ... and {len(changes) - 10} more")
        print()

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Fix name diacritics in CSV/JSON files using LinkedIn URLs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Fix CSV file
    python execution/fix_csv_name_diacritics.py --input leads.csv --output leads_fixed.csv

    # Fix JSON file
    python execution/fix_csv_name_diacritics.py --input leads.json --output leads_fixed.json

    # Specify encoding for non-UTF8 files
    python execution/fix_csv_name_diacritics.py --input leads.csv --output fixed.csv --encoding latin-1
        """
    )
    parser.add_argument('--input', '-i', required=True, help='Input CSV or JSON file')
    parser.add_argument('--output', '-o', help='Output file (default: input_fixed.csv/json)')
    parser.add_argument('--encoding', '-e', default='utf-8', help='Input file encoding (default: utf-8)')

    args = parser.parse_args()

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        base, ext = os.path.splitext(args.input)
        output_path = f"{base}_fixed{ext}"

    # Check input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1

    # Determine file type and process
    _, ext = os.path.splitext(args.input.lower())

    if ext == '.json':
        stats = fix_json_names(args.input, output_path, args.encoding)
    elif ext in ['.csv', '.tsv']:
        stats = fix_csv_names(args.input, output_path, args.encoding)
    else:
        # Try CSV by default
        print(f"Unknown file extension '{ext}', treating as CSV")
        stats = fix_csv_names(args.input, output_path, args.encoding)

    # Return success if any names were fixed or file was processed
    if stats.get('total_rows', 0) > 0 or stats.get('total_leads', 0) > 0:
        return 0
    return 1


if __name__ == '__main__':
    sys.exit(main())

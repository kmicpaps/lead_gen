# Fix Name Diacritics Directive

**Status:** Active
**Created:** January 15, 2026
**Purpose:** Restore Latvian/Baltic special characters to names in lead data

## Problem

Apollo's API returns personal names in ASCII-normalized form, stripping diacritical marks:
- `Artis Miezītis` → `Artis Miezitis`
- `Elīna Vulāne` → `Elina Vulane`
- `Anda Kalniņa` → `Anda Kalnina`

This affects Latvian characters: **ā, ē, ī, ū, ķ, ļ, ņ, š, ž, ģ, č**

## Solution

LinkedIn URLs preserve the original Unicode characters in URL-encoded form. We decode these URLs to restore proper names.

**Example:**
```
Apollo data:     "Artis Miezitis"
LinkedIn URL:    "http://linkedin.com/in/artis-miez%c4%abtis-33052036"
URL-decoded:     "artis-miezītis-33052036"
Fixed name:      "Artis Miezītis"
```

## Execution Scripts

### 1. Automatic Fix During Normalization

The `lead_normalizer.py` now automatically fixes diacritics when normalizing leads:

```python
from execution.lead_normalizer import normalize_leads_batch

# Diacritics are fixed by default
normalized = normalize_leads_batch(raw_leads, 'olympus')  # fix_diacritics=True by default

# Disable if needed
normalized = normalize_leads_batch(raw_leads, 'olympus', fix_diacritics=False)
```

### 2. Fix Existing CSV File

To fix an existing CSV file with leads:

```bash
python execution/fix_csv_name_diacritics.py \
    --input "path/to/leads.csv" \
    --output "path/to/leads_fixed.csv"
```

**Required CSV columns:**
- `LinkedIn URL` (or `linkedin_url`, `linkedinUrl`) - **Required**
- `First Name` (or `first_name`, `firstName`) - Optional
- `Last Name` (or `last_name`, `lastName`) - Optional
- `Full Name` (or `name`, `full_name`) - Optional

### 3. Fix Existing JSON File

```bash
python execution/fix_csv_name_diacritics.py \
    --input "path/to/leads.json" \
    --output "path/to/leads_fixed.json"
```

### 4. Direct API Usage

```python
from execution.name_diacritics_fixer import fix_lead_names, fix_name_from_linkedin

# Fix single lead (modifies in place)
lead = {
    'first_name': 'Artis',
    'last_name': 'Miezitis',
    'name': 'Artis Miezitis',
    'linkedin_url': 'http://www.linkedin.com/in/artis-miez%c4%abtis-33052036'
}
fix_lead_names(lead)
print(lead['name'])  # "Artis Miezītis"

# Fix names without modifying lead
fixed = fix_name_from_linkedin(
    first_name='Artis',
    last_name='Miezitis',
    full_name='Artis Miezitis',
    linkedin_url='http://www.linkedin.com/in/artis-miez%c4%abtis-33052036'
)
print(fixed)  # {'first_name': 'Artis', 'last_name': 'Miezītis', 'name': 'Artis Miezītis'}
```

## Workflow Integration

### New Leads (Automatic)

All scrapers now automatically fix diacritics during normalization:

1. Scraper fetches leads from Apollo/Apify
2. `lead_normalizer.py` normalizes field names
3. `name_diacritics_fixer.py` restores diacritics from LinkedIn URLs
4. Leads uploaded to Google Sheets with correct names

No additional steps needed - diacritics are fixed by default.

### Existing Data (Manual Fix)

For CSV files already exported:

```
1. User provides: Input CSV file path
2. Agent runs: python execution/fix_csv_name_diacritics.py --input "file.csv"
3. Output: file_fixed.csv with corrected names
4. Statistics: Shows how many names were fixed
```

## Supported Character Sets

The fixer supports diacritical marks from:
- **Latvian:** ā, ē, ī, ū, ķ, ļ, ņ, š, ž, ģ, č
- **Lithuanian:** ą, č, ę, ė, į, š, ų, ū, ž
- **Polish:** ą, ć, ę, ł, ń, ó, ś, ź, ż
- **Estonian:** ä, ö, ü, õ
- Other Latin-script languages with diacritics

## Limitations

1. **Requires LinkedIn URL:** Names can only be fixed if a LinkedIn URL is present
2. **Name matching:** The ASCII name must match the decoded LinkedIn slug (ignoring diacritics) for the fix to apply. This prevents incorrect replacements.
3. **Multi-part names:** Complex names like "Anna Maria van der Berg" may not parse perfectly from LinkedIn slugs
4. **URL-encoding variations:** Some special characters may use different encoding schemes

## Verification

After running the fix, verify results:

1. Check sample of fixed names in output file
2. Compare against LinkedIn profiles to confirm accuracy
3. Look for any obviously incorrect fixes (rare, but possible with unusual name formats)

## Error Handling

- If LinkedIn URL is missing → Name unchanged
- If URL parsing fails → Name unchanged
- If name doesn't match slug → Name unchanged (prevents false positives)
- Encoding errors → Script attempts UTF-8 first, falls back gracefully

## Example Output

```
Input file: leads.csv
Detected columns:
  LinkedIn URL: LinkedIn URL
  First Name: First Name
  Last Name: Last Name
  Full Name: Full Name

Output written to: leads_fixed.csv

============================================================
SUMMARY
============================================================
Total rows processed: 500
Rows with LinkedIn URL: 487
Names fixed (diacritics restored): 156
Names unchanged: 331

Sample of changes made:
------------------------------------------------------------
  Row 3: Agnese Blodniece -> Agnese Blodniece
  Row 8: Anda Kalnina -> Anda Kalniņa
  Row 19: Annija Oseniece -> Annija Ošeniece
  Row 34: Elina Vulane -> Elīna Vulāne
  Row 41: Inguna Smite -> Ingūna Šmite
  ... and 151 more
```

## Files

- `execution/name_diacritics_fixer.py` - Core fixer module
- `execution/fix_csv_name_diacritics.py` - CLI for CSV/JSON files
- `execution/lead_normalizer.py` - Updated to integrate fixer
- `directives/fix_name_diacritics.md` - This directive

## Self-Annealing Notes

- **2026-01-15:** Initial implementation based on analysis of Latvian leads. LinkedIn URL decoding confirmed as reliable source for proper names.
- Names are only replaced when they match (ignoring diacritics) to prevent false positives.
- Company names from Apollo typically already have correct diacritics (companies enter their own names).

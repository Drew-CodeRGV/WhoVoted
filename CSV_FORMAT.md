# CSV Upload Format Documentation

## Overview

This document describes the CSV format required for uploading voter data to the WhoVoted application.

## Required Columns

The following columns are **required** and must be present in every CSV file:

| Column Name | Description | Example |
|------------|-------------|---------|
| `ADDRESS` | Full street address of the voter | `700 Convention Center Blvd McAllen TX 78501` |
| `PRECINCT` | Voting precinct number | `101` |
| `BALLOT STYLE` | Ballot style code (typically party indicator) | `D`, `R`, or other code |

## Recommended Columns

The following columns are **recommended** and will be preserved in the output if present:

| Column Name | Description | Example |
|------------|-------------|---------|
| `VUID` | Voter Unique Identifier (10 digits) - Primary ID | `1234567890` |
| `CERT` | Certificate number - Used as VUID if VUID missing | `1054881450` |
| `ID` | Voter ID number (if 10 digits, treated as VUID) | `1001` or `1234567890` |
| `LASTNAME` | Voter's last name | `GARCIA` |
| `FIRSTNAME` | Voter's first name | `MARIA` |
| `MIDDLENAME` | Voter's middle name | `ELENA` |
| `SUFFIX` | Name suffix | `JR`, `SR`, `III` |
| `CHECK-IN` | Check-in timestamp | `2024-11-05 08:30:00` |
| `SITE` | Voting location name | `McAllen Convention Center` |
| `PARTY` | Party affiliation code | `D` (Democratic), `R` (Republican) |

## Important Notes

### VUID Fallback Logic
The system uses the following priority for determining the Voter Unique Identifier (VUID):

1. **VUID column** - If present, this is used as the primary identifier
2. **CERT column** - If VUID is missing, CERT is used as the VUID (most common case)
3. **ID column** - If both VUID and CERT are missing, and ID is 10 digits, it's used as VUID

This ensures cross-referencing works even when files use different column names for the voter identifier.

### CERT as VUID
- The `CERT` column is commonly used in Texas voter files as the unique voter identifier
- If your CSV has CERT but not VUID, the system will automatically use CERT as the VUID
- This allows cross-referencing voters across multiple uploads using their certificate number

### ID vs VUID Column
- If your CSV has an `ID` column with 10-digit values, it will be automatically treated as VUID
- If both `ID` and `VUID` columns exist, `VUID` takes precedence
- If VUID is missing but CERT exists, CERT takes precedence over ID
- This handles files where the ID column is actually the VUID

### VUID Column
- The `VUID` (or `CERT`) column is **strongly recommended** for cross-referencing voters across multiple uploads
- Without VUID or CERT, the system cannot track the same voter across different election cycles
- VUID/CERT should be a unique identifier (typically 10 digits)

### PARTY Field
- The `PARTY` column stores party affiliation codes
- Common codes:
  - `D` = Democratic
  - `R` = Republican
- The system automatically converts single-letter codes to full party names
- The raw party code is preserved in the `party` field
- The expanded party name is stored in `party_affiliation_current` field
- Example: `D` in CSV → `"party": "D"` and `"party_affiliation_current": "Democratic"` in output
### Name Fields
- If `FIRSTNAME`, `MIDDLENAME`, `LASTNAME`, and `SUFFIX` are provided, the system will automatically construct a full name
- Example: `MARIA ELENA GARCIA` or `JUAN CARLOS RODRIGUEZ JR`

### Address Format
- Addresses should include street number, street name, city, state, and ZIP code
- The system will automatically clean and normalize addresses
- Texas is added automatically if not present
- Common abbreviations (ST, AVE, RD, etc.) are standardized

### CHECK-IN Field
- If present, indicates the voter has voted in the current election
- Format: `YYYY-MM-DD HH:MM:SS`
- Used to determine `voted_in_current_election` status

### Empty Values
- Optional columns can be empty or omitted
- Empty values will not be included in the output JSON
- Only fields with actual data are preserved

## Example CSV

```csv
ID,CERT,LASTNAME,FIRSTNAME,MIDDLENAME,SUFFIX,ADDRESS,CHECK-IN,PRECINCT,SITE,BALLOT STYLE,PARTY
522471,1054881450,ABAD,ADELA,,,"1507 ANITA AVE, MISSION 78572",5/20/2024 17:42,128.01,EV-The Mansion,BS 2,D
522472,1054881451,GARCIA,MARIA,ELENA,,700 Convention Center Blvd McAllen TX 78501,5/20/2024 08:30:00,101,McAllen Convention Center,BS 1,D
522473,1054881452,RODRIGUEZ,JUAN,CARLOS,JR,1900 W Nolana Ave McAllen TX 78504,5/20/2024 09:15:00,102,Nolana Community Center,BS 3,R
```

## Output Format

The system will generate a GeoJSON file with all provided fields preserved in the `properties` object:

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [-98.2594316, 26.2006841]
  },
  "properties": {
    "address": "McAllen Convention Center, 700, Convention Center Boulevard...",
    "original_address": "700 Convention Center Blvd McAllen TX 78501",
    "precinct": "101",
    "ballot_style": "BS 1",
    "id": "522472",
    "cert": "1054881451",
    "lastname": "GARCIA",
    "firstname": "MARIA",
    "middlename": "ELENA",
    "check_in": "5/20/2024 08:30:00",
    "site": "McAllen Convention Center",
    "party": "D",
    "name": "MARIA ELENA GARCIA",
    "party_affiliation_current": "Democratic",
    "party_history": ["Democratic"],
    "has_switched_parties": false,
    "election_dates_participated": ["2024-05-20"],
    "voted_in_current_election": true,
    "is_registered": true,
    "household_voter_count": 1
  }
}
```

## Validation

The system performs the following validation checks:

1. **Required columns check**: Ensures ADDRESS, PRECINCT, and BALLOT STYLE are present
2. **Empty address check**: Rejects rows with empty or very short addresses
3. **PO Box warning**: Flags PO Box addresses as suspicious
4. **VUID/CERT check**: Logs info if VUID is missing but CERT is present (CERT will be used as VUID)
5. **Cross-referencing warning**: Logs warning if neither VUID, CERT, nor suitable ID column is found

## Processing Pipeline

1. **Upload**: CSV file is uploaded through the admin panel
2. **Validation**: System checks for required columns and validates data
3. **Cleaning**: Addresses are normalized and standardized
4. **Geocoding**: Addresses are converted to coordinates using Nominatim
5. **Output**: GeoJSON file is generated with all fields preserved
6. **Deployment**: Files are copied to the public directory for map display

## Troubleshooting

### Missing Required Columns
**Error**: "Missing required columns: ADDRESS, PRECINCT, BALLOT STYLE"
**Solution**: Ensure your CSV has all three required columns with exact names (case-sensitive)

### VUID Warning
**Warning**: "VUID column not found. Using CERT column as VUID for cross-referencing."
**Solution**: This is informational - the system will use CERT as the voter identifier. No action needed.

**Warning**: "VUID, CERT, and ID columns not found. Cross-referencing will not be available."
**Solution**: Add a VUID or CERT column to enable tracking voters across multiple uploads

### Geocoding Failures
**Issue**: Some addresses fail to geocode
**Solution**: Check the `processing_errors.csv` file in the data directory for failed addresses

### Empty Fields
**Issue**: Some fields are not appearing in the output
**Solution**: This is expected behavior - only fields with actual data are included in the output

## Best Practices

1. **Always include VUID or CERT** for cross-referencing across election cycles (CERT is most common in Texas voter files)
2. **Use consistent formatting** for addresses (include city, state, ZIP)
3. **Include CHECK-IN timestamps** to track who has voted
4. **Provide name components** (FIRSTNAME, LASTNAME, etc.) for better display
5. **Test with a small sample** before uploading large files
6. **Review the output** in the admin panel after processing

## Support

For questions or issues with CSV uploads, check the processing logs in the admin panel or review the `processing_errors.csv` file in the data directory.

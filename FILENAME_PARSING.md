# Automatic Filename Parsing

## Overview

The WhoVoted system automatically extracts election metadata from uploaded CSV filenames, reducing manual data entry and ensuring consistency across multiple uploads.

## Supported Filename Formats

The parser recognizes various filename patterns and extracts:
- Election year
- Election type (Primary, Runoff, General, Special)
- Party affiliation (Republican, Democratic, Libertarian, Green, Independent)
- Early voting indicator
- Cumulative data indicator
- County name
- Timestamp/date

## Example Filenames

### Format 1: Texas Standard Format
```
2024 Primary EV REP (Cumulative)_202403020808348828.csv
```
**Extracted:**
- Year: 2024
- Election Type: Primary
- Party: Republican
- Early Voting: Yes
- Cumulative: Yes
- Timestamp: 2024-03-02 08:08:34

### Format 2: Underscore Separated
```
2024_General_DEM_20241105.csv
```
**Extracted:**
- Year: 2024
- Election Type: General
- Party: Democratic
- Election Date: 2024-11-05

### Format 3: County Prefix
```
Hidalgo_2024_Primary_Republican_EarlyVoting.csv
```
**Extracted:**
- County: Hidalgo
- Year: 2024
- Election Type: Primary
- Party: Republican
- Early Voting: Yes

### Format 4: Full Description
```
Cameron_County_2024_Runoff_Democratic.csv
```
**Extracted:**
- County: Cameron
- Year: 2024
- Election Type: Runoff
- Party: Democratic

## Recognized Keywords

### Election Types
- `PRIMARY` → Primary election
- `RUNOFF` → Runoff election
- `GENERAL` → General election
- `SPECIAL` → Special election

### Early Voting Indicators
- `EV` → Early voting
- `EARLY VOTING` → Early voting
- `EARLYVOTING` → Early voting

### Party Affiliations
- `REP`, `REPUBLICAN` → Republican (red)
- `DEM`, `DEMOCRAT`, `DEMOCRATIC` → Democratic (blue)
- `LIB`, `LIBERTARIAN` → Libertarian (gold)
- `GRN`, `GREEN` → Green (green)
- `IND`, `INDEPENDENT` → Independent (purple)

### Data Type Indicators
- `CUMULATIVE` → Cumulative/aggregate data
- `CUMUL` → Cumulative data
- `TOTAL` → Total/aggregate data
- `AGGREGATE` → Aggregate data

### Recognized Texas Counties
The parser recognizes major Texas counties including:
- Hidalgo, Cameron, Harris, Dallas, Tarrant, Bexar
- Travis, Collin, Denton, El Paso, Fort Bend
- Montgomery, Williamson, Nueces, Galveston
- Brazoria, Webb

## Timestamp Formats

The parser can extract timestamps from the end of filenames:

### Format 1: Full Timestamp (20 digits)
```
202403020808348828
```
Parsed as: `2024-03-02 08:08:34` (YYYYMMDDHHMMSSssss)

### Format 2: Date and Time (14 digits)
```
20241105143000
```
Parsed as: `2024-11-05 14:30:00` (YYYYMMDDHHmmss)

### Format 3: Date Only (8 digits)
```
20241105
```
Parsed as: `2024-11-05` (YYYYMMDD)

## How It Works

### 1. Upload Process
When you upload a CSV file through the admin panel:

1. The filename is automatically parsed
2. Extracted metadata is displayed for confirmation
3. You can override any auto-detected values
4. Missing required fields (like county) will prompt for manual entry

### 2. Form Auto-Population
The upload form will automatically populate with detected values:
- County dropdown (if detected)
- Year field
- Election type dropdown
- Election date picker (if timestamp detected)

### 3. Override Capability
You can always override auto-detected values:
- Manual form entries take precedence over filename parsing
- Useful for correcting misdetected values
- Required for filenames that don't follow standard patterns

## Best Practices

### Recommended Filename Format
```
{County}_{Year}_{ElectionType}_{Party}_{Date}.csv
```

**Example:**
```
Hidalgo_2024_Primary_Republican_20240305.csv
```

### Tips for Consistent Parsing

1. **Include the year** early in the filename (not just in timestamp)
2. **Use standard abbreviations** (REP, DEM, EV, etc.)
3. **Separate components** with underscores or spaces
4. **Include county name** for multi-county systems
5. **Add timestamps** at the end for version tracking

### Good Examples
✓ `2024_Primary_EV_REP_Cumulative_20240302.csv`
✓ `Hidalgo_2024_General_Democratic.csv`
✓ `Cameron_2024_Runoff_REP_EarlyVoting.csv`

### Avoid
✗ `data.csv` (no metadata)
✗ `voters_march.csv` (ambiguous)
✗ `2024.csv` (insufficient information)

## API Response

When a file is uploaded, the API returns parsed metadata:

```json
{
  "success": true,
  "job_id": "abc-123-def",
  "county": "Hidalgo",
  "year": "2024",
  "election_type": "primary",
  "election_date": "2024-03-02",
  "parsed_from_filename": {
    "year": "2024",
    "county": "Hidalgo",
    "election_type": "primary",
    "party": "Republican",
    "is_early_voting": true,
    "is_cumulative": true,
    "description": "2024 Republican Primary Early Voting (Cumulative)"
  }
}
```

## Troubleshooting

### County Not Detected
**Issue:** Filename doesn't include a recognized county name
**Solution:** Manually select county from dropdown before upload

### Wrong Year Detected
**Issue:** Timestamp year overrides filename year
**Solution:** Place year early in filename (before timestamp)

### Party Not Detected
**Issue:** Non-standard party abbreviation used
**Solution:** Use standard abbreviations (REP, DEM, etc.) or manually select

### Election Type Not Detected
**Issue:** Ambiguous or non-standard election type
**Solution:** Use keywords (PRIMARY, GENERAL, RUNOFF, SPECIAL)

## Multi-Year Support

The system fully supports uploading files from different years:

```
2020_Primary_REP_EarlyVoting.csv
2022_General_DEM.csv
2024_Primary_REP_Cumulative.csv
2026_Runoff_DEM.csv
```

Each file's year is:
1. Extracted from the filename
2. Stored in the metadata
3. Used to organize data by election cycle
4. Displayed in the map interface for filtering

## Technical Details

### Parser Location
`backend/filename_parser.py`

### Integration Points
- `backend/upload.py` - Calls parser during file upload
- `backend/app.py` - Uses parsed metadata for processing jobs
- `backend/processor.py` - Stores metadata in output files

### Testing
Run the parser test suite:
```bash
cd WhoVoted
python backend/filename_parser.py
```

This will test various filename formats and display extracted metadata.

## Future Enhancements

Planned improvements:
- Machine learning for non-standard formats
- Support for additional states/counties
- Custom parsing rules per jurisdiction
- Batch upload with mixed formats
- Filename validation before upload

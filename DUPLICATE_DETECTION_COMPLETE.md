# Duplicate Detection Feature - COMPLETE ✅

## Overview

The WhoVoted admin dashboard now includes intelligent duplicate detection that prevents accidental re-uploads of the same dataset. When you try to upload a file that matches an existing dataset, you'll be prompted with three options.

## How It Works

### Detection Criteria

A file is considered a duplicate if it matches ALL of these characteristics with an existing dataset:
- **County** (e.g., "Hidalgo")
- **Year** (e.g., "2024")
- **Election Type** (e.g., "primary", "general", "runoff")
- **Election Date** (e.g., "2024-03-05")
- **Voting Method** (e.g., "early-voting" or "election-day")

### Upload Flow

```
1. User selects files and fills in form
2. User clicks "Upload and Process"
3. System checks for duplicates
4. If duplicates found:
   → Show warning modal with details
   → User chooses action (Skip, Replace, or Upload Anyway)
5. If no duplicates:
   → Upload proceeds normally
```

## User Options

When duplicates are detected, you get three choices:

### 1. Skip Duplicates ⏭️
- **What it does**: Skips the duplicate files, uploads only new files
- **Use when**: You accidentally selected files you've already uploaded
- **Result**: Duplicate files are not processed, others proceed normally

### 2. Replace Existing 🔄
- **What it does**: Deletes the old dataset and uploads the new one
- **Use when**: You have updated data for the same election
- **Result**: Old map_data and metadata files are deleted, new files are processed

### 3. Upload Anyway ⚠️
- **What it does**: Creates duplicate datasets (not recommended)
- **Use when**: You intentionally want multiple versions of the same data
- **Result**: Both old and new datasets exist (may cause confusion in the map)

## Implementation Details

### Backend Changes

#### New Endpoint: `/admin/check-duplicates`
```python
POST /admin/check-duplicates
Content-Type: application/json

Request:
{
  "files": [
    {
      "filename": "hidalgo_2024_primary_20240305.csv",
      "county": "Hidalgo",
      "year": "2024",
      "election_type": "primary",
      "election_date": "2024-03-05",
      "voting_method": "early-voting"
    }
  ]
}

Response:
{
  "success": true,
  "has_duplicates": true,
  "duplicates": [
    {
      "filename": "hidalgo_2024_primary_20240305.csv",
      "county": "Hidalgo",
      "year": "2024",
      "election_type": "primary",
      "election_date": "2024-03-05",
      "voting_method": "early-voting",
      "existing_filename": "hidalgo_primary_march.csv",
      "existing_metadata_file": "metadata_Hidalgo_2024_primary_20240305.json",
      "last_updated": "2026-02-20T15:30:00",
      "total_records": 45678
    }
  ]
}
```

#### Updated Endpoint: `/admin/upload`
Now accepts `duplicate_action` parameter:
- `skip` - Skip duplicate files
- `replace` - Delete existing and upload new
- `ignore` - Upload anyway (create duplicates)

### Frontend Changes

#### Duplicate Warning Modal
- Shows list of duplicate files with details
- Displays existing filename, last updated date, record count
- Three action buttons with clear descriptions
- Modal can be closed without action (cancels upload)

#### Upload Flow
1. Pre-upload duplicate check via `/admin/check-duplicates`
2. If duplicates found, show modal and wait for user choice
3. User selects action, modal closes
4. Upload proceeds with chosen `duplicate_action`
5. Success message shows skipped count if applicable

## Testing Instructions

### Test 1: Upload New File (No Duplicates)
1. Select a CSV file you haven't uploaded before
2. Fill in form fields
3. Click "Upload and Process"
4. **Expected**: Upload proceeds immediately, no modal shown

### Test 2: Upload Duplicate File
1. Upload a file successfully
2. Try to upload the same file again (same county, year, election type, date, voting method)
3. Click "Upload and Process"
4. **Expected**: Duplicate warning modal appears with file details

### Test 3: Skip Duplicates
1. Trigger duplicate warning (see Test 2)
2. Click "Skip Duplicates" button
3. **Expected**: 
   - Modal closes
   - Success message shows "0 file(s) uploaded (X skipped as duplicates)"
   - No new jobs created

### Test 4: Replace Existing
1. Trigger duplicate warning (see Test 2)
2. Click "Replace Existing" button
3. **Expected**:
   - Modal closes
   - Old dataset files are deleted
   - New file is processed
   - Upload history shows new upload with current timestamp

### Test 5: Upload Anyway
1. Trigger duplicate warning (see Test 2)
2. Click "Upload Anyway" button
3. **Expected**:
   - Modal closes
   - New file is processed
   - Both old and new datasets exist in upload history
   - Map may show duplicate data (not recommended)

### Test 6: Multiple Files with Some Duplicates
1. Select 3 files: 2 new, 1 duplicate
2. Fill in form and click "Upload and Process"
3. **Expected**: Duplicate warning shows only the 1 duplicate file
4. Choose "Skip Duplicates"
5. **Expected**: 2 new files upload, 1 skipped

### Test 7: Cancel Upload
1. Trigger duplicate warning
2. Click the X button or click outside modal
3. **Expected**: Modal closes, no upload happens, can try again

## Example Scenarios

### Scenario 1: Correcting Data
You uploaded Hidalgo County 2024 Primary data, but realized there were errors in the CSV.

**Solution**: 
1. Fix the CSV file
2. Upload again
3. Choose "Replace Existing"
4. Old data is deleted, new corrected data is uploaded

### Scenario 2: Accidental Re-selection
You're uploading multiple files and accidentally selected a file you already uploaded.

**Solution**:
1. Upload proceeds
2. Duplicate warning appears
3. Choose "Skip Duplicates"
4. Only new files are processed

### Scenario 3: Different Voting Methods
You have Early Voting and Election Day data for the same election.

**Result**: No duplicate warning! These are considered different datasets because voting_method differs.

## Technical Details

### Duplicate Detection Logic

```python
# A dataset is a duplicate if ALL these match:
existing.get('county') == county
existing.get('year') == year
existing.get('election_type') == election_type
existing.get('election_date') == election_date
existing.get('voting_method') == voting_method
```

### File Deletion (Replace Action)

When "Replace Existing" is chosen:
```python
# Both files are deleted:
metadata_Hidalgo_2024_primary_20240305.json  # Deleted
map_data_Hidalgo_2024_primary_20240305.json  # Deleted

# Then new files are created with same names
```

### Skip vs Ignore

**Skip** (recommended for duplicates):
- File is not uploaded
- No job is created
- Counted in "skipped" array
- Shown in success message

**Ignore** (not recommended):
- File is uploaded anyway
- Job is created
- Creates duplicate dataset
- May confuse users on the map

## Benefits

✅ **Prevents Accidents** - No more accidental duplicate uploads
✅ **User Control** - You decide what to do with duplicates
✅ **Data Integrity** - Easy to replace outdated data
✅ **Clear Feedback** - Shows exactly which files are duplicates
✅ **Batch Support** - Works with multi-file uploads
✅ **Smart Detection** - Only flags true duplicates (same characteristics)

## Files Modified

### Backend
- `WhoVoted/backend/app.py`
  - Added `/admin/check-duplicates` endpoint
  - Updated `/admin/upload` to handle `duplicate_action` parameter
  - Added duplicate detection logic
  - Added file deletion for replace action

### Frontend
- `WhoVoted/backend/admin/dashboard.html`
  - Added duplicate warning modal HTML
  - Added `showDuplicateWarning()` function
  - Added `closeDuplicateModal()` function
  - Added `handleDuplicateAction()` function
  - Updated upload button handler to check duplicates first
  - Added `performUpload()` function with duplicate_action parameter
  - Updated success messages to show skipped count

## Configuration

No configuration needed! The feature works automatically.

## Troubleshooting

### Modal doesn't appear
- Check browser console for JavaScript errors
- Verify `/admin/check-duplicates` endpoint is accessible
- Hard refresh browser (Ctrl+F5)

### "Replace" doesn't delete old files
- Check backend logs for permission errors
- Verify files exist in `WhoVoted/public/data/`
- Check file permissions

### False positives (not actually duplicates)
- Verify all 5 criteria match (county, year, election_type, election_date, voting_method)
- Check metadata files for correct values
- Different voting methods should NOT trigger duplicate warning

## Success Criteria

✅ Duplicate detection works for single file uploads
✅ Duplicate detection works for multi-file uploads
✅ Modal shows correct duplicate details
✅ "Skip" action prevents upload
✅ "Replace" action deletes old files and uploads new
✅ "Upload Anyway" creates duplicate datasets
✅ Non-duplicate files upload normally
✅ Success messages show skipped count
✅ Modal can be closed without action

## Next Steps

Consider adding:
1. **Filename comparison** - Also check if filename is similar
2. **Record count comparison** - Show if new file has more/fewer records
3. **Bulk replace** - Replace all duplicates at once
4. **Duplicate history** - Track when datasets were replaced
5. **Confirmation dialog** - Extra confirmation for "Replace" action

## Ready to Use! 🎉

The duplicate detection feature is fully implemented and ready to test. Try uploading a file twice to see it in action!

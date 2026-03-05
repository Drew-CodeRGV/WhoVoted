# Upload Monitoring - Ready

## Status
✅ Monitoring scripts deployed and ready
✅ Baseline established: 61,527 early-voting + 1,341 mail-in
✅ Waiting for election day upload

## Current State (Before Upload)
```
Early Voting:  61,527 voters (48,539 Dem + 12,988 Rep)
Mail-In:        1,341 voters (1,096 Dem + 245 Rep)
Election Day:       0 voters
─────────────────────────────────────────────────────
TOTAL:         62,868 voters
```

## Upload Instructions

### 1. Go to Admin Dashboard
https://politiquera.com/admin/dashboard.html

### 2. Upload Files
- Select your two election day CSV files:
  - `ED12026R25Hidalgo County - 2026 Primary - Republican.csv`
  - `ED12026P25Hidalgo County - 2026 Primary - Democratic.csv`

### 3. CRITICAL: Check Voting Method Dropdown
**BEFORE clicking upload, verify:**
- The "Voting Method" dropdown shows **"Election Day"**
- NOT "Early Voting" (which is the default)

The form has auto-detection that might set it based on filename, but please double-check!

### 4. Upload and Process

## After Upload - Verification

### Option 1: Run Check Script (Recommended)
```bash
ssh -i deploy/whovoted-key.pem ubuntu@politiquera.com "cd /opt/whovoted && source venv/bin/activate && python3 deploy/check_upload_result.py"
```

This will show:
- ✓ Success message if election-day records are found
- ⚠ Warning if records were tagged as early-voting instead

### Option 2: Check Manually
```bash
ssh -i deploy/whovoted-key.pem ubuntu@politiquera.com "cd /opt/whovoted && source venv/bin/activate && python3 deploy/check_hidalgo_2026.py"
```

## Expected Result

### If Upload is Correct
```
Early Voting:  61,527 voters
Election Day:  23,029 voters  ← NEW!
Mail-In:        1,341 voters
─────────────────────────────────────────────────────
TOTAL:         85,897 voters
```

### If Upload Has Wrong Tag
```
Early Voting:  84,556 voters  ← WRONG! (61,527 + 23,029)
Election Day:       0 voters  ← MISSING!
Mail-In:        1,341 voters
─────────────────────────────────────────────────────
TOTAL:         85,897 voters
```

## What to Do If Wrong Tag

If the upload was tagged as "early-voting" instead of "election-day":

### 1. Identify the Problem
The check script will show:
```
⚠ WARNING: No election-day records found!
⚠ Early voting count is 84,556 (expected 61,527)
⚠ This suggests the upload form had "Early Voting" selected!
```

### 2. Fix Options

**Option A: Delete and Re-upload**
1. Delete the incorrectly tagged records
2. Re-upload with correct "Election Day" selection

**Option B: Update Tags in Database**
1. Identify the specific records from today's upload
2. Update their voting_method to 'election-day'

I can help with either option if needed.

## Form Auto-Detection

The upload form tries to auto-detect voting method from filename:
- Files with "early" or "ev" → Early Voting
- Files with "election day" or "eday" → Election Day
- Files with "abbm" or "mail" → Mail-In

Your files start with "ED" which might not trigger the auto-detection, so the form might default to "Early Voting".

**That's why it's critical to manually verify the dropdown before uploading!**

## Monitoring Scripts Available

1. **check_upload_result.py** - Quick verification after upload
2. **check_hidalgo_2026.py** - Show current Hidalgo data breakdown
3. **monitor_upload.py** - Real-time monitoring (running in background)

## Frontend Updates

Once the upload is successful, the frontend will show:
- Combined dataset: "2026 Primary - Complete Election"
- Method breakdown: "Early: 61,527 | Mail-In: 1,341 | Election Day: 23,029"
- Individual datasets still available for drill-down

## Ready to Upload!

I'm monitoring and ready to help verify the upload. Please:
1. Double-check the voting method dropdown
2. Upload the files
3. Run the verification script
4. Let me know the result!

---
Date: March 5, 2026

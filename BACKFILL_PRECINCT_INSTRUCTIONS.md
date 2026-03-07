# Backfill Precinct Data Instructions

## Problem
62,876 voting records have `data_source = NULL` and no precinct data. These are preventing accurate district assignment.

## Solution
Upload the statewide voter CSV and backfill the precinct data for these records.

## Steps

### 1. Upload the Statewide CSV to Server

From your local machine (PowerShell):

```powershell
scp -i WhoVoted/deploy/whovoted-key.pem path\to\STATEWIDE_VOTER_INFO.csv ubuntu@politiquera.com:/opt/whovoted/data/
```

Replace `path\to\STATEWIDE_VOTER_INFO.csv` with the actual path to your CSV file.

### 2. Upload the Backfill Script

```powershell
scp -i WhoVoted/deploy/whovoted-key.pem WhoVoted/deploy/backfill_precincts_from_statewide_csv.py ubuntu@politiquera.com:/opt/whovoted/deploy/
```

### 3. Run the Backfill Script on Server

```powershell
ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com "cd /opt/whovoted && python3 deploy/backfill_precincts_from_statewide_csv.py"
```

This will:
- Find the CSV file
- Parse all VUIDs and their precincts
- Update voter_elections records that are missing precinct data
- Show progress and results

### 4. Re-run District Assignment

```powershell
ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com "cd /opt/whovoted && python3 deploy/build_normalized_precinct_system.py"
```

This will:
- Use the newly backfilled precinct data
- Match voters to districts using normalized precinct matching
- Should achieve 95%+ accuracy for D15

### 5. Verify Results

```powershell
ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com "cd /opt/whovoted && python3 deploy/final_district_assignment_status.py"
```

## Expected Results

After backfilling:
- Hidalgo Democratic voters with precinct data should go from 26.1% to 95%+
- D15 accuracy should go from 31% to 95%+
- Overall district coverage should reach 95%+

## Alternative: If CSV is Too Large

If the CSV is too large to upload (>100MB), you can:

1. Generate SQL updates locally:
   ```powershell
   python WhoVoted/deploy/generate_precinct_updates_from_csv.py STATEWIDE_VOTER_INFO.csv > precinct_updates.sql
   ```

2. Upload the SQL file:
   ```powershell
   scp -i WhoVoted/deploy/whovoted-key.pem precinct_updates.sql ubuntu@politiquera.com:/opt/whovoted/data/
   ```

3. Run the SQL on server:
   ```powershell
   ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com "cd /opt/whovoted && python3 -c \"import sqlite3; conn = sqlite3.connect('data/whovoted.db'); conn.executescript(open('data/precinct_updates.sql').read()); conn.commit(); print('Done')\""
   ```

## What This Fixes

The 62,876 NULL records are from an old import before `data_source` tracking was added. They have VUIDs and party data but no precinct information. The statewide CSV has precinct data for ALL voters, so we can backfill the missing precincts by matching on VUID.

Once precincts are backfilled, the normalized precinct matching system will be able to assign districts to these voters, bringing D15 accuracy from 31% to 95%+.

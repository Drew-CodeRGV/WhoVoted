# Upload District Reference Files - Simple Instructions

## What This Does

This script will:
1. Upload all 3 ZIP files to your server (~1.5GB total)
2. Extract them on the server (creates ~500 XLS files)
3. Run the parser to create 6 JSON files with all 219 districts
4. Verify everything worked

## How to Run

### Option 1: Using the PowerShell Script (Recommended)

```powershell
cd WhoVoted
.\UPLOAD_AND_EXTRACT.ps1 -ServerIP "your.server.ip"
```

Replace `your.server.ip` with your actual server IP address.

### Option 2: Manual Commands

If the script doesn't work, use these manual commands:

#### Step 1: Upload ZIP files
```powershell
cd WhoVoted\data\district_reference
scp planc2333_all_files_20251009.zip ubuntu@your.server.ip:/home/ubuntu/WhoVoted/data/district_reference/
scp plans2168_all_files_20250220.zip ubuntu@your.server.ip:/home/ubuntu/WhoVoted/data/district_reference/
scp planh2316_all_files_20250220.zip ubuntu@your.server.ip:/home/ubuntu/WhoVoted/data/district_reference/
```

#### Step 2: SSH to server
```powershell
ssh ubuntu@your.server.ip
```

#### Step 3: Extract files
```bash
cd /home/ubuntu/WhoVoted/data/district_reference
sudo apt-get install unzip -y
unzip -o planc2333_all_files_20251009.zip
unzip -o plans2168_all_files_20250220.zip
unzip -o planh2316_all_files_20250220.zip
```

#### Step 4: Run parser
```bash
cd /home/ubuntu/WhoVoted
pip install pandas xlrd openpyxl
python deploy/parse_district_files.py
```

#### Step 5: Verify
```bash
ls -lh data/district_reference/*.json
python3 -c "import json; f=open('data/district_reference/congressional_counties.json'); d=json.load(f); print('Congressional:', len(d), 'districts')"
python3 -c "import json; f=open('data/district_reference/state_senate_counties.json'); d=json.load(f); print('State Senate:', len(d), 'districts')"
python3 -c "import json; f=open('data/district_reference/state_house_counties.json'); d=json.load(f); print('State House:', len(d), 'districts')"
```

## Expected Results

After running, you should see:

### 6 JSON Files Created:
- `congressional_counties.json` (38 districts)
- `congressional_precincts.json` (38 districts)
- `state_senate_counties.json` (31 districts)
- `state_senate_precincts.json` (31 districts)
- `state_house_counties.json` (150 districts)
- `state_house_precincts.json` (150 districts)

### District Counts:
- Congressional: 38 districts
- State Senate: 31 districts
- State House: 150 districts
- **Total: 219 districts**

## What Gets Uploaded

| File | Size | Contains |
|------|------|----------|
| planc2333_all_files_20251009.zip | ~500MB | Congressional districts (38) |
| plans2168_all_files_20250220.zip | ~400MB | State Senate districts (31) |
| planh2316_all_files_20250220.zip | ~600MB | State House districts (150) |

## Troubleshooting

### "scp: command not found"
Install OpenSSH client for Windows or use WinSCP

### "Permission denied"
Make sure you have SSH access to the server

### "No such file or directory"
Make sure the remote directory exists:
```bash
ssh ubuntu@your.server.ip "mkdir -p /home/ubuntu/WhoVoted/data/district_reference"
```

### Parser fails
Make sure Python dependencies are installed:
```bash
pip install pandas xlrd openpyxl
```

## After Upload

Once complete, your system will be able to:
- Show accurate county counts for all 219 districts
- Display precinct information
- Calculate coverage percentages
- Validate uploaded data against official boundaries

Example:
```
"TX-15 covers 11 counties. We have data for 2 counties (18% coverage)"
```

# McAllen ISD Bond 2026 - Setup Complete

## Overview
Created a separate section at `/misdbond2026` for tracking the McAllen ISD Bond election (May 10, 2026).

## Live URL
https://politiquera.com/misdbond2026/

## Features
- Real-time early voting tracker
- Interactive map showing voter locations by precinct
- Statistics dashboard (total voters, precincts reporting, last update)
- Auto-refresh every 5 minutes
- Responsive design

## Files Created

### Frontend
- `public/misdbond2026/index.html` - Main page
- `public/misdbond2026/map.js` - Map and data visualization

### Backend
- `backend/app.py` - Added API routes:
  - `/api/misdbond2026/stats` - Overall statistics
  - `/api/misdbond2026/precinct/<id>` - Precinct details

### Import Script
- `deploy/import_misdbond2026_roster.py` - Downloads and imports early voting rosters

## Importing Rosters

### Manual Import
```bash
ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com
cd /opt/whovoted
python3 deploy/import_misdbond2026_roster.py
```

### Roster URLs
Update the `ROSTER_URLS` list in `import_misdbond2026_roster.py` as new rosters are published:
- Current: https://www.hidalgocounty.us/DocumentCenter/View/72488/EV-Roster-May-2-2026-Cumulative

### Automated Import (Optional)
Set up a cron job to check for new rosters:
```bash
# Check every hour during early voting period
0 * * * * cd /opt/whovoted && /opt/whovoted/venv/bin/python3 deploy/import_misdbond2026_roster.py >> /var/log/misdbond2026_import.log 2>&1
```

## Database Schema
Uses existing `voter_elections` table:
- `vuid` - Voter unique ID
- `election_date` - '2026-05-10'
- `voting_method` - 'early-voting'
- `data_source` - 'hidalgo-roster'
- `created_at` - Import timestamp

## API Response Format

### `/api/misdbond2026/stats`
```json
{
  "total_voters": 0,
  "precincts_count": 0,
  "precincts": [
    {
      "name": "001",
      "lat": 26.2034,
      "lng": -98.2300,
      "voters": 150
    }
  ],
  "last_update": "2026-05-02T10:30:00"
}
```

### `/api/misdbond2026/precinct/<id>`
```json
{
  "precinct": "001",
  "total_voters": 150,
  "early_voters": 150
}
```

## Maintenance

### Update Roster URLs
Edit `deploy/import_misdbond2026_roster.py` and add new URLs to the `ROSTER_URLS` list as they're published.

### Check Import Status
```bash
ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com
cd /opt/whovoted
python3 deploy/import_misdbond2026_roster.py
```

### View Current Data
```bash
curl https://politiquera.com/api/misdbond2026/stats | jq
```

## Notes
- The page uses the existing voter database, so voters must already be in the system
- Only voters with geocoded addresses (lat/lng) will appear on the map
- The import script skips duplicate records automatically
- Data refreshes automatically every 5 minutes on the frontend

## Future Enhancements
- Add election day results when available
- Show turnout by precinct
- Add historical comparison to previous bond elections
- Export data to CSV for analysis

# District 15 Dashboard Setup Guide

## Quick Start

The D15 dashboard is now ready to use! Here's what you need to know:

### 1. Upload the Campaign Logo

Upload the Bobby Pulido campaign logo to:
```
WhoVoted/public/assets/bobby-pulido-logo.png
```

Recommended specs:
- Format: PNG with transparent background
- Width: 280px (height will auto-scale)

### 2. Initialize with Sample Data (Optional)

The dashboard will work with empty data, but to test it with sample results:

**Option A: Use the upload interface**
1. Go to `https://politiquera.com/d15/upload.html`
2. Login with admin credentials
3. Upload `sample_results.csv`

**Option B: Run the initialization script (production only)**
```bash
cd WhoVoted/deploy
python init_d15_sample_data.py
```

### 3. Access the Dashboard

Navigate to: `https://politiquera.com/d15`

## Features

- **Real-time Updates**: Auto-refreshes every 30 seconds
- **Two Visualization Modes**:
  - **Solid**: Precincts filled with solid colors
  - **Heatmap**: Intensity-based visualization
- **Blue Outlines**: District and precinct boundaries in blue
- **No Red Colors**: Uses blue (Democratic) and orange (Republican)

## Uploading Election Night Results

### CSV Format

Your CSV file must have these columns:
```csv
county,precinct,dem_votes,rep_votes
Hidalgo,101,450,320
Cameron,201,610,450
```

### Upload Process

1. Prepare your CSV file with the latest results
2. Go to `/d15/upload.html`
3. Login (requires authentication)
4. Select and upload your CSV
5. Results appear on the dashboard immediately

### API Endpoints

- `GET /api/d15/results` - Fetch current results
- `POST /api/d15/upload` - Upload new results (auth required)

## Troubleshooting

### "No data available yet" message

This is normal when no results have been uploaded yet. The dashboard will show:
- 0 votes for both parties
- Empty county and precinct lists
- District boundary outline only

### 404 errors in console

If you see errors about missing files:
- Ensure `/data/districts.json` exists (should be auto-generated)
- Ensure `/data/precinct_boundaries_combined.json` exists
- Check that the logo file is uploaded

### Database errors

The backend will automatically create the `election_results` table on first access. If you see database errors:
1. Check that the backend is running
2. Verify database permissions
3. Check backend logs for details

## Color Scheme

- **Democratic**: Blue (#3b82f6)
- **Republican**: Orange (#f97316)
- **District Outline**: Blue dashed line (#3b82f6)
- **Precinct Borders**: Blue solid lines
- **Background**: Light gray (#f8f9fa)
- **Sidebar**: White (#ffffff)

## Technical Notes

- Built with Leaflet.js
- Uses CartoDB light basemap
- SQLite database backend
- Auto-creates tables on first use
- Supports multiple elections (by date)
- Shows most recent election data

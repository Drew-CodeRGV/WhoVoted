# District 15 Election Night Dashboard

Real-time election results dashboard for Texas Congressional District 15.

## Features

- **Live Results Display**: Shows Democratic vs Republican vote totals with percentages
- **County Breakdown**: Lists all counties in District 15 with vote tallies and margins
- **Top Precincts**: Displays the 10 precincts with the highest turnout
- **Interactive Map**: Visual representation of results by precinct
- **Two Visualization Modes**:
  - **Solid**: Precincts filled with solid colors (blue for Democratic, orange for Republican)
  - **Heatmap**: Intensity-based visualization showing margin strength
- **Blue District Outline**: District 15 boundary shown with dashed blue line
- **Auto-Refresh**: Updates every 30 seconds automatically
- **Manual Refresh**: Click the refresh button to update immediately

## Color Scheme

- **Democratic**: Blue (#3b82f6)
- **Republican**: Orange (#f97316) - avoiding red per request
- **District Boundary**: Blue dashed line
- **Precinct Outlines**: Blue borders

## Files

- `index.html` - Main dashboard page
- `dashboard.js` - Dashboard logic and map rendering
- `upload.html` - Admin interface for uploading results
- `sample_results.csv` - Example CSV format for testing

## Usage

### Viewing the Dashboard

Navigate to: `https://politiquera.com/d15`

### Uploading Results

1. Go to: `https://politiquera.com/d15/upload.html`
2. Login with admin credentials
3. Select a CSV file with the following format:

```csv
county,precinct,dem_votes,rep_votes
Hidalgo,101,450,320
Cameron,201,610,450
```

4. Click "Upload Results"
5. Results will appear on the dashboard immediately

## CSV Format

Required columns:
- `county` - County name (e.g., "Hidalgo", "Cameron", "Willacy")
- `precinct` - Precinct number (e.g., "101", "202")
- `dem_votes` - Democratic vote count (integer)
- `rep_votes` - Republican vote count (integer)

## API Endpoints

- `GET /api/d15/results` - Fetch current election results
- `POST /api/d15/upload` - Upload new results (requires authentication)

## Logo

The dashboard displays the Bobby Pulido for Congress campaign logo.
Upload the logo file as: `/assets/bobby-pulido-logo.png`

## Technical Details

- Built with Leaflet.js for mapping
- Uses light CartoDB basemap
- Precinct boundaries from `/data/precinct_boundaries_combined.json`
- District boundary from `/data/districts.json`
- Results stored in SQLite database (`election_results` table)

## Database Schema

```sql
CREATE TABLE election_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    election_date TEXT NOT NULL,
    district TEXT NOT NULL,
    county TEXT NOT NULL,
    precinct TEXT NOT NULL,
    dem_votes INTEGER DEFAULT 0,
    rep_votes INTEGER DEFAULT 0,
    updated_at TEXT,
    UNIQUE(election_date, district, county, precinct)
);
```

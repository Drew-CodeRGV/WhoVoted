# WhoVoted Modernization

Complete modernization of the WhoVoted civic application with OpenStreetMap, Nominatim geocoding, and an admin panel for data management.

## Features

- **Zero Google API Dependencies**: Uses OpenStreetMap tiles and Nominatim for geocoding
- **Admin Panel**: Secure web interface for uploading and processing voter roll CSV files
- **Automated Processing**: CSV validation, address cleaning, geocoding, and JSON generation
- **Real-time Progress**: Live status updates and processing logs
- **Intelligent Caching**: Minimizes API calls with persistent geocoding cache
- **Rate Limiting**: Respects Nominatim usage policy (1 request/second)
- **Hybrid Architecture**: Static frontend + minimal Flask backend

## Architecture

```
WhoVoted/
├── backend/              # Flask application
│   ├── app.py           # Main Flask app with routes
│   ├── auth.py          # Authentication module
│   ├── upload.py        # File upload handler
│   ├── processor.py     # Data processing pipeline
│   ├── geocoder.py      # Nominatim integration
│   ├── config.py        # Configuration management
│   ├── requirements.txt # Python dependencies
│   ├── .env            # Environment variables
│   └── admin/          # Admin panel HTML/JS
├── public/              # Static frontend
│   ├── index.html      # Main map page
│   ├── map.js          # Leaflet map management
│   ├── search.js       # Nominatim search
│   ├── data.js         # Data loading
│   ├── config.js       # Frontend config
│   └── styles.css      # Styles
├── data/               # Generated data files
│   ├── map_data.json   # Geocoded voter data
│   ├── metadata.json   # Processing metadata
│   └── geocoding_cache.json  # Persistent cache
└── uploads/            # Temporary CSV uploads
```

## Setup

### Prerequisites

- Python 3.8+
- pip

### Installation

1. **Clone the repository**
   ```bash
   cd WhoVoted
   ```

2. **Install Python dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and set SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
   ```

4. **Create required directories**
   ```bash
   mkdir -p ../data ../uploads ../logs ../public/data
   ```

5. **Initialize geocoding cache**
   ```bash
   echo "{}" > ../data/geocoding_cache.json
   ```

## Running Locally

### Start the backend server

```bash
cd backend
python app.py
```

The server will start on `http://localhost:5000`

### Access the application

- **Public Map**: http://localhost:5000/
- **Admin Panel**: http://localhost:5000/admin
  - Username: `admin`
  - Password: `admin2026!`

## Using the Admin Panel

1. **Login** at `/admin` with credentials: admin/admin2026!

2. **Upload CSV File**
   - Drag and drop or click to browse
   - File must be .csv format
   - Maximum size: 100MB
   - Required columns: ADDRESS, PRECINCT, BALLOT STYLE

3. **Monitor Processing**
   - Real-time progress bar
   - Live processing logs
   - Record counts and statistics

4. **Download Errors**
   - If geocoding errors occur, download error report
   - Review failed addresses and reasons

5. **View Results**
   - Processing automatically deploys to public map
   - Refresh public map page to see updated data

## CSV Format

Your voter roll CSV must include these columns:

```csv
ADDRESS,PRECINCT,BALLOT STYLE
123 Main St McAllen TX 78501,101,R
456 Oak Ave Brownsville TX 78520,202,D
```

## Deployment

### Backend (Railway/Heroku/VPS)

1. **Set environment variables**
   ```
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=admin2026!
   SECRET_KEY=<generate-secure-key>
   ```

2. **Deploy to Railway**
   - Connect GitHub repository
   - Railway auto-detects Python app
   - Set environment variables in dashboard
   - Deploy

3. **Deploy to Heroku**
   ```bash
   heroku create whovoted-backend
   heroku config:set SECRET_KEY=<your-secret-key>
   heroku config:set ADMIN_PASSWORD=admin2026!
   git push heroku main
   ```

### Frontend (GitHub Pages/Netlify)

The public/ directory can be deployed as a static site:

1. **GitHub Pages**
   - Push public/ contents to gh-pages branch
   - Enable GitHub Pages in repository settings

2. **Netlify**
   - Connect repository
   - Set build directory to `public/`
   - Deploy

## Configuration

### Backend (.env)

```bash
# Admin credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin2026!

# Session
SECRET_KEY=<generate-with-secrets.token_urlsafe(32)>
SESSION_TIMEOUT_HOURS=24

# Paths
UPLOAD_DIR=../uploads
DATA_DIR=../data
PUBLIC_DIR=../public

# Nominatim
NOMINATIM_ENDPOINT=https://nominatim.openstreetmap.org
NOMINATIM_USER_AGENT=WhoVoted/2.0 (civic voter turnout mapping)
NOMINATIM_RATE_LIMIT=1

# Processing
MAX_FILE_SIZE_MB=100
GEOCODING_CACHE_FILE=../data/geocoding_cache.json
```

### Frontend (config.js)

```javascript
const config = {
  MAP_CENTER: [26.2034, -98.2300],  // Hidalgo County
  MAP_ZOOM: 12,
  NOMINATIM_ENDPOINT: 'https://nominatim.openstreetmap.org',
  USER_AGENT: 'WhoVoted/2.0'
};
```

## API Endpoints

### Public
- `GET /` - Main map page
- `GET /<path>` - Static files

### Admin (requires authentication)
- `POST /admin/login` - Authenticate
- `POST /admin/logout` - Logout
- `GET /admin` - Dashboard
- `POST /admin/upload` - Upload CSV
- `GET /admin/status` - Processing status
- `GET /admin/download/errors` - Error report

## Troubleshooting

### "Invalid credentials" error
- Check ADMIN_USERNAME and ADMIN_PASSWORD in .env
- Default: admin/admin2026!

### "No file provided" error
- Ensure file is .csv format
- Check file size < 100MB

### Geocoding is slow
- First run geocodes all addresses (slow)
- Subsequent runs use cache (fast)
- Rate limited to 1 request/second (Nominatim policy)

### "Failed to load data" error
- Check data/map_data.json exists
- Verify file is valid JSON
- Check file permissions

## Security Notes

- Change default admin password in production
- Use HTTPS for admin panel
- Set secure SECRET_KEY
- Enable CORS only for trusted domains
- Review logs regularly

## License

Open source - see LICENSE file

## Credits

- OpenStreetMap contributors
- Nominatim geocoding service
- Leaflet.js mapping library
- Hidalgo County Elections Department
- Cameron County Elections Department

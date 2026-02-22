# WhoVoted - Quick Start Guide

## 🚀 Start the Server

```bash
cd WhoVoted
start.bat          # Windows
# or
./start.sh         # Linux/Mac
```

Server runs on: **http://localhost:5000**

## 🗺️ Access the Map

Open your browser: **http://localhost:5000/**

Features:
- View voter locations on OpenStreetMap
- Search for addresses
- Click geolocation button to find your location
- Zoom in/out to see individual markers

## 🔐 Admin Panel

URL: **http://localhost:5000/admin**

Credentials:
- Username: `admin`
- Password: `admin2026!`

## 📤 Upload Voter Data

1. Go to http://localhost:5000/admin
2. Log in
3. Drag & drop CSV file (or click to browse)
4. Wait for processing to complete
5. Check the public map for updated data

## 📋 CSV Format

```csv
ADDRESS,PRECINCT,BALLOT STYLE
700 Convention Center Blvd McAllen TX 78501,101,R
1900 W Nolana Ave McAllen TX 78504,102,D
2721 Pecan Blvd McAllen TX 78501,103,R
```

## ✅ Verify It's Working

Run the test:
```bash
cd WhoVoted
python test_complete_workflow.py
```

All tests should pass ✓

## 📁 Important Files

- `backend/.env` - Configuration
- `public/data/map_data.json` - Geocoded voter data
- `data/geocoding_cache.json` - Cached geocoding results
- `logs/app.log` - Server logs

## 🛠️ Troubleshooting

**Server won't start?**
```bash
pip install -r backend/requirements.txt
```

**Port 5000 in use?**
Edit `backend/app.py` and change the port number.

**CSV upload fails?**
Check `logs/app.log` for errors.

**Map doesn't show data?**
Refresh the page and check browser console (F12).

## 📞 Quick Commands

```bash
# Start server
cd WhoVoted && start.bat

# Run tests
cd WhoVoted && python test_complete_workflow.py

# Check logs
cd WhoVoted && type logs\app.log

# View cache
cd WhoVoted && type data\geocoding_cache.json
```

## 🎯 What's Working

✓ OpenStreetMap integration
✓ Nominatim geocoding
✓ Admin authentication
✓ CSV upload and processing
✓ Real-time progress tracking
✓ Intelligent caching
✓ Rate limiting
✓ Error reporting
✓ Responsive design
✓ Geolocation support

---

**Need more details?** See `COMPLETION_SUMMARY.md` or `README_MODERNIZATION.md`

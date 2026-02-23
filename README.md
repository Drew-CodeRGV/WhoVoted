# WhoVoted - Voter Turnout Mapping Application

A web-based application for visualizing voter turnout data on interactive maps with multi-dataset support and advanced geocoding capabilities.

![WhoVoted](public/assets/thumbnail.jpg)

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Drew-CodeRGV/WhoVoted.git
cd WhoVoted
```

2. **Install Python dependencies**
```bash
cd backend
pip install -r requirements.txt
```

3. **Configure environment** (optional)
```bash
cp .env.example .env
# Edit .env with your settings
```

4. **Start the application**

**Linux/Mac:**
```bash
./start.sh
```

**Windows:**
```bash
start.bat
```

Or manually:
```bash
python backend/app.py
```

5. **Access the application**
- **Public Map**: http://localhost:5000
- **Admin Dashboard**: http://localhost:5000/admin
  - Username: `admin`
  - Password: `admin2026!`

## 📋 Features

### Public Map Interface
- **Interactive Map**: Visualize voter locations on an interactive Leaflet map
- **Multi-Dataset Support**: Switch between multiple election datasets
- **Party Filtering**: Filter by Democratic, Republican, or All voters
- **Year Display**: Datasets show election year in the selector
- **Search**: Search for specific addresses or voters
- **Precinct Boundaries**: Optional precinct boundary overlays

### Admin Dashboard
- **File Upload**: Upload CSV/Excel voter roll files
- **Real-time Processing**: Monitor geocoding progress with two-color progress bar
  - Green: Previously cached addresses (instant)
  - Blue: Newly geocoded addresses (parallel processing)
- **Multi-File Upload**: Process multiple files simultaneously
- **Duplicate Detection**: Automatic detection and handling of duplicate datasets
- **Job Monitoring**: Track processing status and history
- **Error Handling**: Download error reports for failed geocoding

### Geocoding System
- **Multi-Provider Fallback**:
  1. Cache (77,000+ pre-geocoded addresses)
  2. AWS Location Service (Esri/HERE data)
  3. US Census Bureau
  4. Photon (OpenStreetMap)
  5. Nominatim (OpenStreetMap)
- **90%+ Cache Hit Rate**: Most addresses geocoded instantly
- **Parallel Processing**: Configurable worker count (default: 20)
- **Smart Caching**: Persistent cache across sessions

## 📁 Project Structure

```
WhoVoted/
├── backend/              # Flask backend
│   ├── app.py           # Main Flask application
│   ├── processor.py     # Data processing pipeline
│   ├── geocoder.py      # Multi-provider geocoding
│   ├── auth.py          # Authentication
│   ├── upload.py        # File upload handling
│   ├── config.py        # Configuration
│   ├── admin/           # Admin dashboard
│   │   ├── dashboard.html
│   │   └── dashboard.js
│   └── requirements.txt # Python dependencies
├── public/              # Frontend (served by Flask)
│   ├── index.html       # Main map interface
│   ├── map.js           # Map functionality
│   ├── ui.js            # UI components
│   ├── data.js          # Data loading
│   └── styles.css       # Styles
├── data/                # Backend data storage
│   ├── geocoded_addresses.json  # 77K+ cached addresses
│   ├── map_data*.json           # Processed datasets
│   └── metadata*.json           # Dataset metadata
├── uploads/             # Temporary upload storage
├── logs/                # Application logs
├── deprecated-v1/       # Old version (archived)
└── tests/               # Test suite
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password

# AWS Location Service (Optional)
AWS_LOCATION_PLACE_INDEX=WhoVotedPlaceIndex
AWS_DEFAULT_REGION=us-east-1

# Session Configuration
SECRET_KEY=your-secret-key-here
SESSION_TIMEOUT_HOURS=24

# Processing
MAX_FILE_SIZE_MB=100
```

### AWS Location Service (Optional)

For improved geocoding accuracy, configure AWS Location Service:

1. Create an AWS account
2. Set up AWS Location Service Place Index
3. Configure AWS credentials:
```bash
aws configure
```

See [AWS_LOCATION_SERVICE_SETUP.md](AWS_LOCATION_SERVICE_SETUP.md) for detailed instructions.

## 📊 Data Format

### CSV Upload Format

Required columns:
- `ADDRESS` - Street address
- `PRECINCT` - Precinct number
- `BALLOT STYLE` - Ballot style code

Optional columns:
- `VUID` - Voter Unique ID
- `CERT` - Certificate number
- `FIRSTNAME`, `LASTNAME`, `MIDDLENAME`, `SUFFIX` - Name components
- `PARTY` - Party affiliation (D/R)
- `CHECK-IN` - Check-in time
- `SITE` - Voting site

See [CSV_FORMAT.md](CSV_FORMAT.md) for detailed specifications.

## 🧪 Testing

Run the test suite:

```bash
npm test
```

Run specific tests:
```bash
npm test -- tests/unit/dataset-manager.test.js
```

## 📖 Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [QUICK_START_AWS.md](QUICK_START_AWS.md) - AWS setup guide
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - Complete documentation index
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [DEPRECATION_SUMMARY.md](DEPRECATION_SUMMARY.md) - v1.0 deprecation notice

## 🔐 Security

- Admin dashboard requires authentication
- Session-based authentication with configurable timeout
- File upload validation and size limits
- CORS configuration for production deployment
- Secure password hashing (change default password!)

## 🚀 Deployment

### Production Checklist

1. **Change default admin password** in `.env`
2. **Generate secure SECRET_KEY**:
```python
import secrets
print(secrets.token_urlsafe(32))
```
3. **Configure CORS_ORIGINS** for your domain
4. **Set up HTTPS** (required for production)
5. **Configure AWS credentials** (if using AWS Location Service)
6. **Set LOG_LEVEL=WARNING** for production

### Deployment Options

- **Traditional Server**: Run with gunicorn or uwsgi
- **Docker**: Create Dockerfile (see ARCHITECTURE.md)
- **Cloud**: Deploy to AWS, Google Cloud, or Azure
- **GitHub Pages**: Frontend only (requires separate backend)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Leaflet** - Interactive mapping library
- **OpenStreetMap** - Map tiles and geocoding data
- **AWS Location Service** - Enhanced geocoding accuracy
- **US Census Bureau** - Geocoding API
- **Flask** - Python web framework

## 📧 Contact

- **Repository**: https://github.com/Drew-CodeRGV/WhoVoted
- **Issues**: https://github.com/Drew-CodeRGV/WhoVoted/issues

## 🔄 Version History

### v2.0 (Current)
- Backend-driven architecture with Flask
- Admin dashboard with real-time processing
- Multi-dataset support with visual selector
- Advanced geocoding with 77K+ cached addresses
- Two-color progress bar (cached vs new)
- Parallel processing for performance

### v1.0 (Deprecated)
- Single-page application
- Client-side data loading
- Basic geocoding
- Archived in `deprecated-v1/`

---

**Made with ❤️ for civic engagement and voter transparency**

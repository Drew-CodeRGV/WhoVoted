"""Configuration module for WhoVoted backend."""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration."""
    
    # Admin credentials
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin2026!')
    
    # Session configuration
    SECRET_KEY = os.getenv('SECRET_KEY')
    SESSION_TIMEOUT_HOURS = int(os.getenv('SESSION_TIMEOUT_HOURS', '24'))
    
    # File paths
    BASE_DIR = Path(__file__).parent.parent.resolve()
    UPLOAD_DIR = BASE_DIR / 'uploads'
    DATA_DIR = BASE_DIR / 'data'
    PUBLIC_DIR = BASE_DIR / 'public'
    LOG_DIR = BASE_DIR / 'logs'
    
    # Nominatim configuration
    NOMINATIM_ENDPOINT = os.getenv('NOMINATIM_ENDPOINT', 'https://nominatim.openstreetmap.org')
    NOMINATIM_USER_AGENT = os.getenv('NOMINATIM_USER_AGENT', 'WhoVoted/2.0 (civic voter turnout mapping)')
    NOMINATIM_RATE_LIMIT = float(os.getenv('NOMINATIM_RATE_LIMIT', '1'))
    
    # Processing configuration
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '100'))
    GEOCODING_CACHE_FILE = BASE_DIR / 'data' / 'geocoded_addresses.json'
    
    # AWS Location Service configuration
    AWS_LOCATION_PLACE_INDEX = os.getenv('AWS_LOCATION_PLACE_INDEX', 'WhoVotedPlaceIndex')
    AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    
    # CORS configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:8080').split(',')
    
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = BASE_DIR / 'logs' / 'app.log'
    
    @classmethod
    def validate(cls):
        """Validate configuration on startup."""
        errors = []
        
        if not cls.SECRET_KEY:
            errors.append("SECRET_KEY environment variable is required")
        
        # Create directories if they don't exist
        for directory in [cls.UPLOAD_DIR, cls.DATA_DIR, cls.PUBLIC_DIR, cls.LOG_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True

def setup_logging():
    """Configure logging for the application."""
    Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Ensure log file exists
    Config.LOG_FILE.touch(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

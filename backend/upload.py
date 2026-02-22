"""File upload handler for WhoVoted admin panel."""
import os
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
from werkzeug.utils import secure_filename

from config import Config
from filename_parser import FilenameParser

logger = logging.getLogger(__name__)

def validate_file(file) -> tuple[bool, str]:
    """
    Validate uploaded file.
    
    Args:
        file: FileStorage object from Flask request
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if file exists
    if not file or not file.filename:
        return False, "No file provided"
    
    # Check file extension
    filename = file.filename.lower()
    if not (filename.endswith('.csv') or filename.endswith('.xls') or filename.endswith('.xlsx')):
        return False, "Only CSV and Excel files are accepted (.csv, .xls, .xlsx)"
    
    # Check file size (read first to get size)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    max_size_bytes = Config.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        return False, f"File size exceeds {Config.MAX_FILE_SIZE_MB}MB limit"
    
    if file_size == 0:
        return False, "File is empty"
    
    return True, ""

def save_upload(file) -> str:
    """
    Save uploaded file with unique identifier.
    
    Args:
        file: FileStorage object from Flask request
    
    Returns:
        Full path to saved file
    """
    # Generate unique file ID
    file_id = str(uuid.uuid4())
    
    # Secure the filename
    original_filename = secure_filename(file.filename)
    
    # Create filename with UUID prefix
    filename = f"{file_id}_{original_filename}"
    
    # Ensure upload directory exists
    Config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save file
    filepath = Config.UPLOAD_DIR / filename
    file.save(str(filepath))
    
    logger.info(f"Saved uploaded file: {filename} ({file.content_length} bytes)")
    
    return str(filepath)

def cleanup_old_uploads(days: int = 7):
    """
    Remove uploads older than specified days.
    
    Args:
        days: Number of days to retain uploads (default: 7)
    """
    if not Config.UPLOAD_DIR.exists():
        return
    
    cutoff_date = datetime.now() - timedelta(days=days)
    removed_count = 0
    
    for filepath in Config.UPLOAD_DIR.glob('*.csv'):
        # Get file modification time
        file_mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
        
        if file_mtime < cutoff_date:
            try:
                filepath.unlink()
                removed_count += 1
                logger.info(f"Removed old upload: {filepath.name}")
            except Exception as e:
                logger.error(f"Failed to remove old upload {filepath.name}: {e}")
    
    if removed_count > 0:
        logger.info(f"Cleaned up {removed_count} old upload(s)")

def get_file_info(file) -> dict:
    """
    Get metadata about uploaded file.
    
    Args:
        file: FileStorage object from Flask request
    
    Returns:
        Dictionary with file metadata including parsed election info
    """
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    # Parse filename for election metadata
    parsed_metadata = FilenameParser.parse_filename(file.filename)
    
    return {
        'filename': file.filename,
        'size_bytes': file_size,
        'size_mb': round(file_size / (1024 * 1024), 2),
        'content_type': file.content_type,
        # Add parsed metadata
        'year': parsed_metadata['year'],
        'election_type': parsed_metadata['election_type'],
        'party': parsed_metadata['party'],
        'is_early_voting': parsed_metadata['is_early_voting'],
        'is_cumulative': parsed_metadata['is_cumulative'],
        'county': parsed_metadata['county'],
        'election_date': parsed_metadata.get('election_date'),
        'description': FilenameParser.format_election_description(parsed_metadata),
        'party_color': FilenameParser.get_party_color(parsed_metadata['party'])
    }

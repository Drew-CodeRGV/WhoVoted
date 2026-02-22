"""Authentication module for WhoVoted admin panel."""
import secrets
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, redirect, jsonify

from config import Config

logger = logging.getLogger(__name__)

# In-memory session store (sufficient for single admin user)
sessions = {}

def authenticate(username: str, password: str) -> bool:
    """
    Validate admin credentials.
    
    Args:
        username: Username to validate
        password: Password to validate
    
    Returns:
        True if credentials are valid, False otherwise
    """
    is_valid = username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD
    
    if is_valid:
        logger.info(f"Successful authentication for user: {username}")
    else:
        logger.warning(f"Failed authentication attempt for user: {username}")
    
    return is_valid

def create_session(user_id: str) -> str:
    """
    Generate secure session token and store session data.
    
    Args:
        user_id: User identifier (e.g., 'admin')
    
    Returns:
        Secure session token
    """
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires_at = now + timedelta(hours=Config.SESSION_TIMEOUT_HOURS)
    
    sessions[token] = {
        'user_id': user_id,
        'created_at': now,
        'expires_at': expires_at
    }
    
    logger.info(f"Created session for user: {user_id}, expires at: {expires_at}")
    
    return token

def validate_session(token: str) -> bool:
    """
    Check if session token is valid and not expired.
    
    Args:
        token: Session token to validate
    
    Returns:
        True if session is valid and not expired, False otherwise
    """
    if not token or token not in sessions:
        return False
    
    session = sessions[token]
    now = datetime.now()
    
    if now > session['expires_at']:
        # Session expired, remove it
        del sessions[token]
        logger.info(f"Session expired for user: {session['user_id']}")
        return False
    
    return True

def invalidate_session(token: str):
    """
    Invalidate a session token (logout).
    
    Args:
        token: Session token to invalidate
    """
    if token in sessions:
        user_id = sessions[token]['user_id']
        del sessions[token]
        logger.info(f"Session invalidated for user: {user_id}")

def require_auth(func):
    """
    Decorator to protect admin routes.
    Requires valid session token in cookie.
    
    Usage:
        @app.route('/admin/dashboard')
        @require_auth
        def dashboard():
            return "Admin dashboard"
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.cookies.get('session_token')
        
        if not validate_session(token):
            # For API/data requests, return 401
            # Check for: /admin/api, /admin/upload, /admin/status, /admin/download, or JSON requests
            is_api_request = (
                request.path.startswith('/admin/api') or
                request.path.startswith('/admin/upload') or
                request.path.startswith('/admin/status') or
                request.path.startswith('/admin/download') or
                request.path.startswith('/admin/logout') or
                request.is_json or
                request.method in ['POST', 'PUT', 'DELETE', 'PATCH']
            )
            
            if is_api_request:
                return jsonify({'error': 'Unauthorized'}), 401
            # For page requests, redirect to login
            return redirect('/admin/login')
        
        return func(*args, **kwargs)
    
    return wrapper

def cleanup_expired_sessions():
    """
    Remove expired sessions from memory.
    Should be called periodically (e.g., every hour).
    """
    now = datetime.now()
    expired_tokens = [
        token for token, session in sessions.items()
        if now > session['expires_at']
    ]
    
    for token in expired_tokens:
        del sessions[token]
    
    if expired_tokens:
        logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")

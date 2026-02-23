"""Authentication module for WhoVoted admin panel."""
import secrets
import json
import logging
import fcntl
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from flask import request, redirect, jsonify

from config import Config

logger = logging.getLogger(__name__)

# File-based session store for multi-worker compatibility
SESSIONS_FILE = Config.DATA_DIR / 'sessions.json'


def _read_sessions() -> dict:
    """Read sessions from disk with file locking."""
    if not SESSIONS_FILE.exists():
        return {}
    try:
        with open(SESSIONS_FILE, 'r') as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                data = json.load(f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        return data
    except (json.JSONDecodeError, IOError):
        logger.warning("Could not read sessions file, returning empty sessions")
        return {}


def _write_sessions(sessions: dict):
    """Write sessions to disk with file locking."""
    try:
        Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(SESSIONS_FILE, 'w') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                json.dump(sessions, f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except IOError as e:
        logger.error(f"Could not write sessions file: {e}")


def authenticate(username: str, password: str) -> bool:
    """Validate admin credentials."""
    is_valid = username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD
    if is_valid:
        logger.info(f"Successful authentication for user: {username}")
    else:
        logger.warning(f"Failed authentication attempt for user: {username}")
    return is_valid


def create_session(user_id: str) -> str:
    """Generate secure session token and store in file-based session store."""
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires_at = now + timedelta(hours=Config.SESSION_TIMEOUT_HOURS)

    sessions = _read_sessions()
    sessions[token] = {
        'user_id': user_id,
        'created_at': now.isoformat(),
        'expires_at': expires_at.isoformat()
    }
    _write_sessions(sessions)

    logger.info(f"Created session for user: {user_id}, expires at: {expires_at}")
    return token


def validate_session(token: str) -> bool:
    """Check if session token is valid and not expired."""
    if not token:
        return False

    sessions = _read_sessions()
    if token not in sessions:
        return False

    session = sessions[token]
    now = datetime.now()
    expires_at = datetime.fromisoformat(session['expires_at'])

    if now > expires_at:
        del sessions[token]
        _write_sessions(sessions)
        logger.info(f"Session expired for user: {session['user_id']}")
        return False

    return True


def invalidate_session(token: str):
    """Invalidate a session token (logout)."""
    sessions = _read_sessions()
    if token in sessions:
        user_id = sessions[token]['user_id']
        del sessions[token]
        _write_sessions(sessions)
        logger.info(f"Session invalidated for user: {user_id}")


def require_auth(func):
    """Decorator to protect admin routes. Requires valid session token in cookie."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.cookies.get('session_token')

        if not validate_session(token):
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
            return redirect('/admin/login')

        return func(*args, **kwargs)

    return wrapper


def cleanup_expired_sessions():
    """Remove expired sessions from file store."""
    sessions = _read_sessions()
    now = datetime.now()
    expired_tokens = [
        token for token, session in sessions.items()
        if now > datetime.fromisoformat(session['expires_at'])
    ]

    for token in expired_tokens:
        del sessions[token]

    if expired_tokens:
        _write_sessions(sessions)
        logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")

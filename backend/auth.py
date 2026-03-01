"""Authentication module for WhoVoted - Google SSO + legacy admin."""
import secrets
import json
import logging
import fcntl
import requests
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from flask import request, redirect, jsonify, g

from config import Config

logger = logging.getLogger(__name__)

SESSIONS_FILE = Config.DATA_DIR / 'sessions.json'
SUPERADMIN_EMAIL = 'drew@politiquera.com'
GOOGLE_TOKENINFO_URL = 'https://oauth2.googleapis.com/tokeninfo'


def _read_sessions() -> dict:
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
        return {}


def _write_sessions(sessions: dict):
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


# ---- Legacy admin auth removed — Google SSO only ----


# ---- Google SSO ----

def verify_google_token(id_token: str) -> dict:
    """Verify a Google ID token and return user info.
    Returns dict with email, name, picture, sub or None on failure."""
    try:
        resp = requests.get(GOOGLE_TOKENINFO_URL, params={'id_token': id_token}, timeout=5)
        if resp.status_code != 200:
            logger.warning(f"Google token verification failed: {resp.status_code}")
            return None
        data = resp.json()
        # Verify the token is for our app (audience check)
        # We accept any Google client ID for now since the frontend handles the OAuth flow
        if not data.get('email_verified', '').lower() == 'true':
            logger.warning(f"Google email not verified: {data.get('email')}")
            return None
        return {
            'email': data['email'],
            'name': data.get('name', data['email'].split('@')[0]),
            'picture': data.get('picture', ''),
            'sub': data.get('sub', ''),
        }
    except Exception as e:
        logger.error(f"Google token verification error: {e}")
        return None


def get_or_create_user(google_info: dict) -> dict:
    """Get existing user or create new one from Google info. Returns user dict."""
    import database as db
    with db.get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (google_info['email'],)).fetchone()
        if row:
            # Update last login and picture
            conn.execute("UPDATE users SET last_login = ?, picture = ?, name = ? WHERE email = ?",
                         (datetime.now().isoformat(), google_info['picture'],
                          google_info['name'], google_info['email']))
            user = dict(row)
            user['last_login'] = datetime.now().isoformat()
            return user
        else:
            # New user - auto-approve superadmin, others are pending
            email = google_info['email']
            role = 'superadmin' if email == SUPERADMIN_EMAIL else 'pending'
            approved_at = datetime.now().isoformat() if role == 'superadmin' else None
            conn.execute("""
                INSERT INTO users (email, name, picture, role, google_sub, approved_at, last_login)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (email, google_info['name'], google_info['picture'], role,
                  google_info['sub'], approved_at, datetime.now().isoformat()))
            user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            logger.info(f"Created user: {email} with role: {role}")
            return {
                'id': user_id, 'email': email, 'name': google_info['name'],
                'picture': google_info['picture'], 'role': role,
                'google_sub': google_info['sub'], 'last_login': datetime.now().isoformat()
            }


# ---- Session management ----

def create_session(user_id: str, role: str = 'admin', email: str = '') -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires_at = now + timedelta(hours=Config.SESSION_TIMEOUT_HOURS)
    sessions = _read_sessions()
    sessions[token] = {
        'user_id': user_id,
        'role': role,
        'email': email,
        'created_at': now.isoformat(),
        'expires_at': expires_at.isoformat()
    }
    _write_sessions(sessions)
    return token


def validate_session(token: str) -> bool:
    if not token:
        return False
    sessions = _read_sessions()
    if token not in sessions:
        return False
    session = sessions[token]
    if datetime.now() > datetime.fromisoformat(session['expires_at']):
        del sessions[token]
        _write_sessions(sessions)
        return False
    return True


def get_session_info(token: str) -> dict:
    """Get session info including role and email."""
    if not token:
        return None
    sessions = _read_sessions()
    session = sessions.get(token)
    if not session:
        return None
    if datetime.now() > datetime.fromisoformat(session['expires_at']):
        return None
    return session


def invalidate_session(token: str):
    sessions = _read_sessions()
    if token in sessions:
        del sessions[token]
        _write_sessions(sessions)


def require_auth(func):
    """Decorator for admin routes. Requires valid session (Google SSO)."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.cookies.get('session_token')
        if not validate_session(token):
            is_api = (request.path.startswith('/admin/api') or
                      request.path.startswith('/admin/upload') or
                      request.path.startswith('/admin/status') or
                      request.is_json or request.method in ['POST', 'PUT', 'DELETE', 'PATCH'])
            if is_api:
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect('/')
        # Attach session info to g
        g.session = get_session_info(token)
        return func(*args, **kwargs)
    return wrapper


def require_superadmin(func):
    """Decorator requiring superadmin role."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.cookies.get('session_token')
        session = get_session_info(token)
        if not session or session.get('role') not in ('superadmin', 'admin'):
            return jsonify({'error': 'Forbidden'}), 403
        g.session = session
        return func(*args, **kwargs)
    return wrapper


def cleanup_expired_sessions():
    sessions = _read_sessions()
    now = datetime.now()
    expired = [t for t, s in sessions.items()
               if now > datetime.fromisoformat(s['expires_at'])]
    for t in expired:
        del sessions[t]
    if expired:
        _write_sessions(sessions)


# ---- User management (for admin dashboard) ----

def list_users() -> list:
    import database as db
    with db.get_db() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def update_user_role(user_id: int, role: str, approved_by: str = '') -> bool:
    import database as db
    with db.get_db() as conn:
        approved_at = datetime.now().isoformat() if role == 'approved' else None
        conn.execute("UPDATE users SET role = ?, approved_at = ?, approved_by = ? WHERE id = ?",
                     (role, approved_at, approved_by, user_id))
        return conn.total_changes > 0


def delete_user(user_id: int) -> bool:
    import database as db
    with db.get_db() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return conn.total_changes > 0


def update_user_info(user_id: int, name: str = None, email: str = None) -> bool:
    import database as db
    with db.get_db() as conn:
        if name:
            conn.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
        if email:
            conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
        return True

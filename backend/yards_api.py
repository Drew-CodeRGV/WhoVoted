"""
Yard Sign Tracker API — yards.politiquera.com
Handles photo uploads, AI identification, location matching, and rewards.
"""
from flask import Blueprint, request, jsonify, send_from_directory
import sqlite3
import os
import uuid
import json
from datetime import datetime, timedelta
from pathlib import Path

bp = Blueprint('yards', __name__, url_prefix='/api/yards')

DB_PATH = '/opt/whovoted/data/whovoted.db'
UPLOAD_DIR = '/opt/whovoted/uploads/yards'
MAX_DAILY_SUBMISSIONS = 50
REWARD_THRESHOLD = 20  # photos per free month


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@bp.route('/submit', methods=['POST'])
def submit_photo():
    """Receive a yard sign photo with GPS coordinates."""
    # Check auth
    from auth import get_session_info
    token = request.cookies.get('session_token')
    session = get_session_info(token) if token else None
    if not session:
        return jsonify({'error': 'Login required'}), 401

    user_id = session.get('user_id')

    # Rate limit
    conn = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    today_count = conn.execute(
        "SELECT COUNT(*) FROM yard_sign_photos WHERE user_id=? AND DATE(submitted_at)=?",
        (user_id, today)
    ).fetchone()[0]
    if today_count >= MAX_DAILY_SUBMISSIONS:
        conn.close()
        return jsonify({'error': f'Daily limit reached ({MAX_DAILY_SUBMISSIONS}/day)'}), 429

    # Get photo
    photo = request.files.get('photo')
    if not photo:
        conn.close()
        return jsonify({'error': 'No photo provided'}), 400

    # Get GPS
    lat = request.form.get('lat', type=float)
    lng = request.form.get('lng', type=float)
    accuracy = request.form.get('accuracy', type=float)
    timestamp = request.form.get('timestamp', '')

    if not lat or not lng:
        conn.close()
        return jsonify({'error': 'GPS coordinates required'}), 400

    # Save photo
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    photo_id = str(uuid.uuid4())
    filename = f"{photo_id}.jpg"
    filepath = os.path.join(UPLOAD_DIR, filename)
    photo.save(filepath)
    photo_url = f"/uploads/yards/{filename}"

    # Reverse geocode to get address
    address = reverse_geocode(lat, lng)

    # Match to voter
    matched_vuid = None
    if address:
        matched_vuid = match_address_to_voter(conn, address, lat, lng)

    # AI sign identification (async — for now just mark as pending)
    # In production: call Claude Vision API here
    candidate_identified = None
    confidence = 0

    # Try AI identification
    try:
        candidate_identified, confidence = identify_sign_ai(filepath)
    except Exception as e:
        pass  # Will be marked for manual review

    # Determine status
    status = 'pending'
    if candidate_identified and confidence >= 0.7 and matched_vuid:
        status = 'verified'
        # Insert into yard_signs table (feeds the maps)
        election_slug = get_election_for_candidate(candidate_identified)
        if election_slug:
            conn.execute("""
                INSERT OR REPLACE INTO yard_signs (vuid, election_slug, candidate, lat, lng, reported_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (matched_vuid, election_slug, candidate_identified, lat, lng))

    # Save submission
    conn.execute("""
        INSERT INTO yard_sign_photos (user_id, photo_url, device_lat, device_lng, photo_timestamp,
            candidate_identified, candidate_confidence, matched_address, matched_vuid, status, election_slug)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, photo_url, lat, lng, timestamp, candidate_identified, confidence,
          address, matched_vuid, status, get_election_for_candidate(candidate_identified) if candidate_identified else None))

    # Update credits
    update_credits(conn, user_id)

    conn.commit()

    # Get progress
    progress = get_progress(conn, user_id)
    conn.close()

    return jsonify({
        'success': True,
        'candidate': candidate_identified,
        'confidence': confidence,
        'address': address,
        'status': status,
        'message': 'Sign identified!' if candidate_identified else 'Submitted for review',
        'progress': progress,
    })


@bp.route('/my-progress')
def my_progress():
    """Get user's submission progress and recent history."""
    from auth import get_session_info
    token = request.cookies.get('session_token')
    session = get_session_info(token) if token else None
    if not session:
        return jsonify({'error': 'Login required'}), 401

    user_id = session.get('user_id')
    conn = get_db()

    progress = get_progress(conn, user_id)

    recent = conn.execute("""
        SELECT photo_url, candidate_identified as candidate, matched_address as address, status
        FROM yard_sign_photos WHERE user_id=? ORDER BY submitted_at DESC LIMIT 10
    """, (user_id,)).fetchall()

    conn.close()
    return jsonify({
        'progress': progress,
        'recent': [dict(r) for r in recent],
    })


# ── Helpers ──

def get_progress(conn, user_id):
    """Get user's credit progress."""
    verified = conn.execute(
        "SELECT COUNT(*) FROM yard_sign_photos WHERE user_id=? AND status='verified'",
        (user_id,)
    ).fetchone()[0]
    total = conn.execute(
        "SELECT COUNT(*) FROM yard_sign_photos WHERE user_id=?",
        (user_id,)
    ).fetchone()[0]
    credits = verified // REWARD_THRESHOLD
    return {'verified': verified % REWARD_THRESHOLD, 'total_submitted': total, 'credits_earned': credits}


def update_credits(conn, user_id):
    """Check if user earned a new credit."""
    verified = conn.execute(
        "SELECT COUNT(*) FROM yard_sign_photos WHERE user_id=? AND status='verified'",
        (user_id,)
    ).fetchone()[0]
    credits = verified // REWARD_THRESHOLD
    conn.execute("""
        INSERT OR REPLACE INTO yard_sign_credits (user_id, total_submitted, total_verified, credits_earned, last_credit_at)
        VALUES (?, (SELECT COUNT(*) FROM yard_sign_photos WHERE user_id=?), ?, ?, datetime('now'))
    """, (user_id, user_id, verified, credits))


def reverse_geocode(lat, lng):
    """Reverse geocode coordinates to an address."""
    try:
        import urllib.request
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json&addressdetails=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Politiquera/1.0'})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        return data.get('display_name', '')[:200]
    except:
        return None


def match_address_to_voter(conn, address, lat, lng):
    """Find the closest voter to these coordinates."""
    # Find voters within ~50m (roughly 0.0005 degrees)
    rows = conn.execute("""
        SELECT vuid, lat, lng, address FROM voters
        WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?
        AND lat IS NOT NULL
        LIMIT 5
    """, (lat - 0.0005, lat + 0.0005, lng - 0.0005, lng + 0.0005)).fetchall()

    if rows:
        # Return closest
        closest = min(rows, key=lambda r: abs(r['lat'] - lat) + abs(r['lng'] - lng))
        return closest['vuid']
    return None


def identify_sign_ai(filepath):
    """Use Claude Vision API to identify the yard sign candidate."""
    try:
        import anthropic
        import base64

        # Read and encode the image
        with open(filepath, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')

        # Known candidates for active elections in the area
        candidates_context = """
        Active elections in HD-41 / McAllen area:
        
        HD-41 Runoff (May 26, 2026):
        - Democratic: Victor "Seby" Haddad, Julio Salinas
        - Republican: Sergio Sanchez, Gary Groves
        
        McAllen City Commission District 5 (May 2, 2026):
        - Felida Villarreal, Mark Murray, Michael Fallek
        
        McAllen ISD Bond (May 10, 2026):
        - For/Against the bond
        """

        client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_data,
                        }
                    },
                    {
                        "type": "text",
                        "text": f"""Identify any political yard signs visible in this photo.

{candidates_context}

Respond in this exact JSON format only (no other text):
{{"candidate": "Full Candidate Name", "confidence": 0.95, "description": "brief description of sign"}}

If multiple signs, use the most prominent one.
If you cannot identify a political yard sign, respond:
{{"candidate": null, "confidence": 0, "description": "no sign identified"}}
"""
                    }
                ]
            }]
        )

        # Parse response
        text = response.content[0].text.strip()
        # Extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            candidate = result.get('candidate')
            confidence = result.get('confidence', 0)

            # Normalize candidate name to match our DB
            if candidate:
                candidate = normalize_candidate_name(candidate)

            return candidate, confidence

        return None, 0

    except ImportError:
        # anthropic package not installed
        return None, 0
    except Exception as e:
        print(f"AI Vision error: {e}")
        return None, 0


def normalize_candidate_name(name):
    """Normalize AI-detected candidate name to match our database format."""
    if not name:
        return None
    name_lower = name.lower()

    # HD-41 candidates
    if 'haddad' in name_lower or 'seby' in name_lower:
        return "Victor 'Seby' Haddad"
    if 'salinas' in name_lower or 'julio' in name_lower:
        return "Julio Salinas"
    if 'sanchez' in name_lower or 'sergio' in name_lower:
        return "Sergio Sanchez"
    if 'groves' in name_lower or 'gary' in name_lower:
        return "Gary Groves"

    # D5 candidates
    if 'villarreal' in name_lower or 'felida' in name_lower:
        return "Felida Villarreal"
    if 'murray' in name_lower or 'mark' in name_lower:
        return "Mark Murray"
    if 'fallek' in name_lower or 'michael' in name_lower:
        return "Michael Fallek"

    return name  # Return as-is if no match


def get_election_for_candidate(candidate):
    """Map a candidate name to their election slug."""
    if not candidate:
        return None
    candidate_elections = {
        "Victor 'Seby' Haddad": 'hd41',
        "Julio Salinas": 'hd41',
        "Sergio Sanchez": 'hd41',
        "Gary Groves": 'hd41',
        "Felida Villarreal": 'd5-2026',
        "Mark Murray": 'd5-2026',
        "Michael Fallek": 'd5-2026',
    }
    return candidate_elections.get(candidate)

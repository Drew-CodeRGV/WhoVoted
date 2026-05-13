# Design: Yard Sign Tracker PWA

## Architecture

```
┌─────────────────────────────────────────────┐
│  yards.politiquera.com (PWA)                │
│  - Camera capture + GPS                      │
│  - Offline queue (Service Worker)            │
│  - Progress tracker                          │
└──────────────────┬──────────────────────────┘
                   │ POST /api/yards/submit
                   ▼
┌─────────────────────────────────────────────┐
│  Backend (Flask)                             │
│  - Photo storage (S3 or /opt/whovoted/uploads/yards/) │
│  - AI Vision API call                        │
│  - Reverse geocoding                         │
│  - Voter DB lookup                           │
│  - Verification pipeline                     │
└──────────────────┬──────────────────────────┘
                   │ INSERT
                   ▼
┌─────────────────────────────────────────────┐
│  SQLite DB                                   │
│  - yard_sign_photos (submissions)            │
│  - yard_signs (verified, feeds maps)         │
│  - yard_sign_credits (rewards)               │
└─────────────────────────────────────────────┘
```

## PWA Flow

```
1. Open app → Login/Register (email or phone)
2. Home screen: "Snap a Sign" button + progress bar (12/20)
3. Tap → Camera opens (rear, full screen)
4. Take photo → Preview with GPS overlay
5. Confirm → Upload starts (show spinner)
6. Result: "✓ Seby Haddad sign identified at 123 Main St"
   or: "⚠️ Could not identify sign — submitted for review"
7. Counter increments → "13/20 toward free month!"
8. Repeat
```

## AI Vision Pipeline

```python
def identify_sign(photo_path):
    """Use Claude Vision to identify yard sign candidates."""
    # 1. Send photo to Claude Vision API
    # 2. Prompt: "Identify any political yard signs in this photo.
    #    Return the candidate name(s) and party if visible.
    #    Known candidates in this area: [list from active elections]"
    # 3. Parse response → candidate name, confidence
    # 4. Match against elections table
    return {
        'candidates': [{'name': 'Victor Haddad', 'party': 'Democratic', 'confidence': 0.95}],
        'sign_count': 1,
        'description': 'Blue yard sign with "SEBY HADDAD" text'
    }
```

## Address Matching Pipeline

```python
def match_to_voter(lat, lng):
    """Match GPS coordinates to a voter address."""
    # 1. Reverse geocode (lat, lng) → street address
    # 2. Search voters table for matching address
    # 3. If multiple voters at address, return all
    # 4. Return VUID(s) + voter info
    return {
        'address': '123 Main St, McAllen TX 78501',
        'voters': [{'vuid': '1054018499', 'name': 'John Smith', 'party': 'Democratic'}]
    }
```

## Database Schema

```sql
CREATE TABLE yard_sign_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    photo_url TEXT NOT NULL,
    device_lat REAL NOT NULL,
    device_lng REAL NOT NULL,
    exif_lat REAL,
    exif_lng REAL,
    photo_timestamp TEXT,
    submitted_at TEXT DEFAULT (datetime('now')),
    -- AI results
    candidate_identified TEXT,
    candidate_confidence REAL,
    sign_count INTEGER DEFAULT 1,
    ai_description TEXT,
    -- Address matching
    matched_address TEXT,
    matched_vuid TEXT,
    -- Verification
    status TEXT DEFAULT 'pending',  -- pending, verified, rejected, review
    rejection_reason TEXT,
    verified_at TEXT,
    -- Election context
    election_slug TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE yard_sign_credits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total_submitted INTEGER DEFAULT 0,
    total_verified INTEGER DEFAULT 0,
    credits_earned INTEGER DEFAULT 0,
    last_credit_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/yards/submit | User | Upload photo + GPS, returns AI result |
| GET | /api/yards/my-progress | User | Photos submitted, verified, credits |
| GET | /api/yards/recent | User | User's recent submissions |
| GET | /api/yards/leaderboard | Public | Top contributors |
| POST | /api/yards/review/:id | Admin | Approve/reject pending submission |
| GET | /admin/yards/queue | Admin | Pending review queue |

## Hosting

- Subdomain: `yards.politiquera.com`
- nginx proxy to a Flask blueprint on the same server
- Or: separate lightweight app on port 5002
- PWA manifest + service worker for installability

## AI Cost Estimate

- Claude Vision: ~$0.01-0.03 per image analysis
- At 1000 photos/month: $10-30/month
- ROI: each verified photo feeds campaign intelligence worth far more

## Files to Create

- `public/yards/` — PWA frontend (index.html, app.js, manifest.json, sw.js)
- `backend/yards_api.py` — Flask blueprint for the API
- `deploy/setup_yards.py` — DB table creation + nginx config

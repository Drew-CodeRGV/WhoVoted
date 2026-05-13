# Spec: Yard Sign Tracker PWA (yards.politiquera.com)

## Problem

Campaign intelligence requires knowing where yard signs are — which neighborhoods support which candidates. Currently this data is collected manually by canvassers marking individual voter records. There's no scalable way to crowdsource yard sign data with photo verification.

## Product

A standalone Progressive Web App at `yards.politiquera.com` where anyone with a phone can:
1. Take a photo of a house with a yard sign
2. The system identifies the candidate(s) on the sign using AI vision
3. GPS + EXIF data verifies the location
4. The system matches the address to a voter record
5. The yard sign data feeds into all Politiquera election trackers

## Users

- **Canvassers**: Campaign staff walking precincts, systematically photographing signs
- **Community members**: Anyone who wants to contribute data while driving/walking around
- **Campaign managers**: Consume the aggregated data in the election tracker maps

## Incentive Model

- Every 20 verified yard sign photos = 1 free month of Politiquera subscription
- Verification = photo + GPS match + sign identified + address matched
- Prevents gaming: duplicate addresses rejected, GPS must match photo EXIF, rate limiting

## Acceptance Criteria

### Photo Capture
1. User opens PWA, taps "Snap a Sign"
2. Camera opens (rear-facing, landscape encouraged)
3. Photo is captured with GPS coordinates from device
4. EXIF data extracted: lat/lng, timestamp, device info
5. Photo uploaded to server with metadata

### AI Sign Identification
1. System analyzes the photo using vision AI (Claude Vision or similar)
2. Identifies candidate name(s) on the sign
3. Matches against known candidate lists for active elections in the area
4. Returns: candidate name, party, election, confidence score
5. If multiple signs: identifies each one separately

### Location Verification
1. GPS from device at time of photo
2. EXIF GPS from photo metadata (if available)
3. Cross-reference: GPS must be within 50m of a registered voter address
4. Reverse geocode to get street address
5. Match address to voter rolls → get VUID

### Voter Association
1. Matched address → look up voter(s) at that address
2. Cross-reference party history: does the sign match their voting pattern?
3. Flag if sign is for opposing party (hostile sign)
4. Store: VUID, candidate, photo URL, GPS, timestamp, reporter

### Data Feed
1. Verified signs feed into the `yard_signs` table in the main DB
2. All election trackers (HD-41, bond, etc.) pick up the data automatically
3. Signs appear on maps with the 🪧/⚠️ icons as already implemented

### Reward System
1. Track photos per user
2. Every 20 verified photos → grant 1 month subscription credit
3. "Verified" = photo accepted + sign identified + address matched
4. Dashboard shows: photos submitted, verified, credits earned

### Anti-Gaming
1. Same address can only be submitted once per election cycle
2. GPS must be within 50m of the matched address
3. Photo timestamp must be within 1 hour of submission
4. Rate limit: max 50 submissions per day per user
5. AI confidence must be > 70% for auto-approval
6. Low-confidence submissions go to manual review queue

### Sign Lifecycle
1. All yard signs are assumed REMOVED after the election/runoff date passes
2. On election day + 1: all signs for that election are auto-expired (status → 'expired')
3. Expired signs no longer appear on maps or in targeting layers
4. Historical sign data is retained in the DB for analytics but not displayed as active
5. If a new election cycle starts, the same address can be submitted again
6. Signs for a runoff expire after the runoff date, not the original primary date

## Technical Architecture

### Frontend (PWA)
- Standalone app at `yards.politiquera.com`
- Service worker for offline photo queue
- Camera API with GPS overlay
- Simple UI: snap → confirm → submit → next
- Progress tracker: "12/20 toward your free month"

### Backend
- Flask blueprint or separate lightweight app
- Photo storage: S3 or local filesystem
- AI vision: Claude Vision API or OpenAI Vision
- Geocoding: Nominatim reverse geocode
- Voter matching: existing voter DB lookup by address

### Database
- `yard_sign_photos` table: id, user_id, photo_url, lat, lng, exif_lat, exif_lng, timestamp, candidate_identified, confidence, address_matched, vuid, status (pending/verified/rejected), created_at
- `yard_sign_credits` table: user_id, photos_verified, credits_earned, last_credit_at

## Out of Scope (v1)
- Video capture (photos only)
- Sign removal detection (only presence)
- Historical sign tracking (only current state)
- Multi-language sign detection

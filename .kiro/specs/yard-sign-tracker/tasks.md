# Tasks: Yard Sign Tracker PWA

## Phase 1: Core PWA + Photo Capture

- [ ] **1.1** Create `public/yards/index.html` — PWA shell with camera UI
- [ ] **1.2** Create `public/yards/app.js` — camera capture, GPS, upload logic
- [ ] **1.3** Create `public/yards/manifest.json` — PWA manifest for installability
- [ ] **1.4** Create `public/yards/sw.js` — service worker for offline photo queue
- [ ] **1.5** Create `public/yards/styles.css` — mobile-first UI
- [ ] **1.6** Add nginx config for `yards.politiquera.com` → same server

## Phase 2: Backend API

- [ ] **2.1** Create `backend/yards_api.py` — Flask blueprint
- [ ] **2.2** Implement `POST /api/yards/submit` — receive photo + GPS
- [ ] **2.3** Photo storage: save to `/opt/whovoted/uploads/yards/` with UUID filename
- [ ] **2.4** Create `yard_sign_photos` and `yard_sign_credits` tables
- [ ] **2.5** Register blueprint in `app.py`

## Phase 3: AI Vision Integration

- [ ] **3.1** Integrate Claude Vision API (or OpenAI Vision) for sign identification
- [ ] **3.2** Build candidate list context from active elections in the area
- [ ] **3.3** Parse AI response → candidate name, confidence score
- [ ] **3.4** Handle multi-sign photos (multiple candidates in one frame)
- [ ] **3.5** Fallback: if AI confidence < 70%, mark for manual review

## Phase 4: Location Verification

- [ ] **4.1** Extract EXIF GPS from uploaded photo
- [ ] **4.2** Compare device GPS vs EXIF GPS (must be within 50m)
- [ ] **4.3** Reverse geocode GPS → street address (Nominatim)
- [ ] **4.4** Match address to voter rolls → get VUID(s)
- [ ] **4.5** Validate: GPS within 50m of matched voter address

## Phase 5: Data Feed to Election Trackers

- [ ] **5.1** On verification: INSERT into `yard_signs` table (same table HD-41 uses)
- [ ] **5.2** Set election_slug based on which election the candidate belongs to
- [ ] **5.3** All existing map layers automatically pick up new signs
- [ ] **5.4** Real-time: new signs appear on maps within minutes of submission

## Phase 6: Reward System

- [ ] **6.1** Track submissions per user in `yard_sign_credits`
- [ ] **6.2** On every 20th verified photo: grant 1 month subscription credit
- [ ] **6.3** Progress UI in PWA: "12/20 toward your free month"
- [ ] **6.4** Credit applied to user's subscription automatically

## Phase 7: Admin Review Queue

- [ ] **7.1** Admin page: `/admin/yards/` — pending submissions
- [ ] **7.2** Show photo + AI result + GPS + matched address
- [ ] **7.3** Approve/reject buttons
- [ ] **7.4** Bulk approve for high-confidence submissions

## Phase 8: Anti-Gaming

- [ ] **8.1** Deduplicate: same address can only be submitted once per election
- [ ] **8.2** GPS validation: reject if device GPS is > 50m from address
- [ ] **8.3** Timestamp validation: photo must be < 1 hour old
- [ ] **8.4** Rate limit: max 50 per day per user
- [ ] **8.5** Flag suspicious patterns (same route, same time, bulk submissions)

## Status

**Overall**: [pending] — spec complete, ready to build.

## Priority Order

Build in this order for fastest time-to-value:
1. PWA + camera + GPS (Phase 1) — get photos flowing
2. Backend + storage (Phase 2) — save them
3. AI vision (Phase 3) — identify signs automatically
4. Location matching (Phase 4) — connect to voter data
5. Data feed (Phase 5) — light up the maps
6. Rewards (Phase 6) — incentivize contributors
7. Admin (Phase 7) — quality control
8. Anti-gaming (Phase 8) — prevent abuse

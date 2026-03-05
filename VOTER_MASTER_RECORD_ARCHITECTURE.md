# Voter Master Record Architecture

## Vision
Build a comprehensive, VUID-centric data warehouse that provides a **360-degree view** of every voter by combining:
- **Political Data** (Politiquera): Voting history, party affiliation, district assignments
- **Physical Engagement** (Crowdsurfer): Event attendance, physical presence verification
- **Demographics & Enrichments**: Census data, propensity scores, contact history

This enables advanced analytics, cross-referencing, and insights that weren't possible before - from "who voted" to "who shows up" to "who can we mobilize."

## Core Principles

### 1. VUID is the Universal Key
Every voter has one immutable identifier (VUID) that ties together all their data across multiple dimensions and time periods.

### 2. Immutable vs Mutable Data Separation
- **IMMUTABLE** (rarely changes): VUID, birth year, sex - stored in master record
- **MUTABLE** (changes over time): Address, party affiliation, district assignments, event attendance - stored in timestamped history tables

### 3. Extensibility First
New data sources (Crowdsurfer events, census data, ML scores) are added as separate tables with VUID as FK, never modifying the core schema.

## Current State (What We Have)

### voters Table (Master Record)
```sql
CREATE TABLE voters (
    vuid TEXT PRIMARY KEY,
    -- Identity
    lastname TEXT,
    firstname TEXT,
    middlename TEXT,
    suffix TEXT,
    
    -- Demographics
    birth_year INTEGER,
    sex TEXT,
    
    -- Location
    address TEXT,
    city TEXT,
    zip TEXT,
    county TEXT,
    lat REAL,
    lng REAL,
    geocoded INTEGER,
    
    -- Political Geography (Current - 2026 Map)
    precinct TEXT,
    congressional_district TEXT,
    state_house_district TEXT,
    commissioner_district TEXT,
    
    -- Political Geography (Historical - 2022-2024 Map)
    old_congressional_district TEXT,
    
    -- Party Affiliation
    registered_party TEXT,
    current_party TEXT,  -- Most recent primary voted in
    
    -- Metadata
    registration_date TEXT,
    source TEXT,
    updated_at TEXT
)
```

### voter_elections Table (Event History)
```sql
CREATE TABLE voter_elections (
    id INTEGER PRIMARY KEY,
    vuid TEXT,  -- FK to voters
    election_date TEXT,
    election_year TEXT,
    election_type TEXT,
    voting_method TEXT,
    party_voted TEXT,
    is_new_voter INTEGER,  -- Computed flag
    created_at TEXT,
    FOREIGN KEY (vuid) REFERENCES voters(vuid)
)
```

## Proposed Architecture: Modular Enrichment Tables

### 1. Core Master Record (voters table)
Keep this lean with only **IMMUTABLE or slowly-changing data**:
- **IMMUTABLE**: VUID, birth_year, sex
- **SLOWLY CHANGING**: Name (marriage), current address (moves)
- **CURRENT STATE ONLY**: Latest geocoding, current district assignments

**Philosophy**: This table answers "Who is this person RIGHT NOW?"

### 2. History Tables (Track Changes Over Time)

#### voter_address_history
Track address changes (moves):
```sql
CREATE TABLE voter_address_history (
    vuid TEXT,
    effective_date TEXT,  -- When they moved here
    address TEXT,
    city TEXT,
    zip TEXT,
    county TEXT,
    lat REAL,
    lng REAL,
    source TEXT,  -- 'voter_file', 'usps', 'manual'
    PRIMARY KEY (vuid, effective_date)
)
```

#### voter_geography_history
Track district assignments over time as boundaries change:
```sql
CREATE TABLE voter_geography_history (
    vuid TEXT,
    effective_date TEXT,  -- When this map became active
    map_plan TEXT,  -- e.g., 'PlanC2333', 'PlanC2193'
    congressional_district TEXT,
    state_house_district TEXT,
    state_senate_district TEXT,
    commissioner_district TEXT,
    school_district TEXT,
    precinct TEXT,
    PRIMARY KEY (vuid, effective_date, map_plan)
)
```

**Philosophy**: These tables answer "Where has this person lived?" and "Which districts have they been in?"

### 3. Enrichment Tables (External Data Sources)

#### voter_demographics_enriched
Additional demographic data from external sources:
```sql
CREATE TABLE voter_demographics_enriched (
    vuid TEXT PRIMARY KEY,
    estimated_income_bracket TEXT,  -- From census block group
    education_level TEXT,  -- From census data
    homeowner_status TEXT,  -- From property records
    household_size INTEGER,  -- From census
    ethnicity TEXT,  -- From surname analysis or census
    language_preference TEXT,  -- From voter file or census
    updated_at TEXT,
    source TEXT  -- Where this data came from
)
```

#### voter_contact_history
Track outreach attempts:
```sql
CREATE TABLE voter_contact_history (
    id INTEGER PRIMARY KEY,
    vuid TEXT,
    contact_date TEXT,
    contact_type TEXT,  -- 'door_knock', 'phone', 'text', 'mail'
    campaign_id TEXT,
    result TEXT,  -- 'answered', 'not_home', 'refused', etc.
    notes TEXT,
    contacted_by TEXT
)
```

#### voter_propensity_scores
ML-generated scores for targeting:
```sql
CREATE TABLE voter_propensity_scores (
    vuid TEXT PRIMARY KEY,
    turnout_score REAL,  -- 0-100: likelihood to vote
    persuasion_score REAL,  -- 0-100: likelihood to be persuaded
    support_score REAL,  -- 0-100: current support level
    volunteer_score REAL,  -- 0-100: likelihood to volunteer
    donor_score REAL,  -- 0-100: likelihood to donate
    model_version TEXT,
    computed_at TEXT
)
```

#### voter_social_network
Household and social connections:
```sql
CREATE TABLE voter_social_network (
    vuid TEXT,
    related_vuid TEXT,
    relationship_type TEXT,  -- 'household', 'family', 'neighbor'
    confidence REAL,  -- 0-1: how confident we are
    PRIMARY KEY (vuid, related_vuid)
)
```

#### voter_issues
Issue positions from surveys/canvassing:
```sql
CREATE TABLE voter_issues (
    vuid TEXT,
    issue_tag TEXT,  -- 'healthcare', 'immigration', 'economy'
    position TEXT,  -- 'support', 'oppose', 'neutral'
    intensity INTEGER,  -- 1-5: how strongly they feel
    source TEXT,  -- 'survey', 'canvass', 'social_media'
    recorded_at TEXT,
    PRIMARY KEY (vuid, issue_tag)
)
```

#### voter_media_consumption
Media habits for targeting:
```sql
CREATE TABLE voter_media_consumption (
    vuid TEXT,
    platform TEXT,  -- 'facebook', 'twitter', 'tv', 'radio'
    frequency TEXT,  -- 'daily', 'weekly', 'rarely'
    source TEXT,
    updated_at TEXT,
    PRIMARY KEY (vuid, platform)
)
```

### 4. Crowdsurfer Integration (Physical Engagement)

#### voter_event_registrations
Track event sign-ups:
```sql
CREATE TABLE voter_event_registrations (
    id INTEGER PRIMARY KEY,
    vuid TEXT,
    event_id TEXT,  -- FK to Crowdsurfer events
    registered_at TEXT,
    registration_source TEXT,  -- 'web', 'mobile', 'canvass'
    confirmed INTEGER,  -- 0 or 1
    FOREIGN KEY (vuid) REFERENCES voters(vuid)
)
```

#### voter_event_attendance
Track verified physical presence:
```sql
CREATE TABLE voter_event_attendance (
    id INTEGER PRIMARY KEY,
    vuid TEXT,
    event_id TEXT,
    check_in_time TEXT,
    check_in_method TEXT,  -- 'qr_code', 'nfc', 'manual', 'bluetooth_beacon'
    device_id TEXT,  -- Device used for check-in
    location_verified INTEGER,  -- GPS/beacon confirmed they were there
    lat REAL,  -- Check-in location
    lng REAL,
    duration_minutes INTEGER,  -- How long they stayed
    FOREIGN KEY (vuid) REFERENCES voters(vuid)
)
```

#### voter_engagement_summary
Aggregated engagement metrics (computed periodically):
```sql
CREATE TABLE voter_engagement_summary (
    vuid TEXT PRIMARY KEY,
    total_events_registered INTEGER,
    total_events_attended INTEGER,
    attendance_rate REAL,  -- attended / registered
    last_event_date TEXT,
    favorite_event_type TEXT,  -- 'rally', 'town_hall', 'canvass', etc.
    avg_event_duration_minutes INTEGER,
    is_super_volunteer INTEGER,  -- Attended 5+ events
    computed_at TEXT
)
```

**Philosophy**: These tables answer "How engaged is this person?" and "Do they show up when they say they will?"

## Data Ingestion Pipeline

### On File Upload (processor.py)
```python
def process_voter_record(vuid, record_data):
    # 1. Upsert to voters table (master record)
    upsert_voter_master(vuid, {
        'name': record_data['name'],
        'address': record_data['address'],
        'birth_year': record_data['birth_year'],
        # ... core fields
    })
    
    # 2. Geocode if needed
    if not has_geocoding(vuid):
        lat, lng = geocode_address(record_data['address'])
        update_geocoding(vuid, lat, lng)
    
    # 3. Assign political geography
    if has_geocoding(vuid):
        assign_districts(vuid, lat, lng, current_map='PlanC2333')
        # Also assign to historical maps for comparison
        assign_districts(vuid, lat, lng, current_map='PlanC2193', 
                        table='voter_geography_history')
    
    # 4. Record election participation
    if record_data.get('election_date'):
        insert_voter_election(vuid, {
            'election_date': record_data['election_date'],
            'party_voted': record_data['party_voted'],
            'voting_method': record_data['voting_method']
        })
    
    # 5. Trigger enrichment jobs (async)
    queue_enrichment_job(vuid, ['demographics', 'propensity'])
```

### Enrichment Jobs (Background Workers)
```python
# Run periodically or on-demand
def enrich_voter_demographics(vuid):
    voter = get_voter(vuid)
    
    # Census block group lookup
    census_data = lookup_census_block(voter.lat, voter.lng)
    
    # Property records
    property_data = lookup_property_records(voter.address)
    
    # Update enrichment table
    upsert_voter_demographics_enriched(vuid, {
        'estimated_income_bracket': census_data.income_bracket,
        'homeowner_status': property_data.owner_status,
        'education_level': census_data.education,
        'source': 'census_2020,property_records'
    })
```

## Advanced Analytics Queries

### 360-Degree Voter Profile
```sql
-- Complete profile: voting + engagement + demographics
SELECT 
    v.vuid, v.firstname, v.lastname, v.birth_year,
    v.congressional_district,
    -- Voting behavior
    COUNT(DISTINCT ve.election_date) as elections_voted,
    ve_latest.party_voted as last_party_voted,
    -- Physical engagement
    ves.total_events_attended,
    ves.attendance_rate,
    ves.is_super_volunteer,
    -- Demographics
    vde.estimated_income_bracket,
    vde.homeowner_status,
    -- Propensity
    vps.turnout_score,
    vps.volunteer_score
FROM voters v
LEFT JOIN voter_elections ve ON v.vuid = ve.vuid
LEFT JOIN voter_elections ve_latest ON v.vuid = ve_latest.vuid 
    AND ve_latest.election_date = (SELECT MAX(election_date) FROM voter_elections WHERE vuid = v.vuid)
LEFT JOIN voter_engagement_summary ves ON v.vuid = ves.vuid
LEFT JOIN voter_demographics_enriched vde ON v.vuid = vde.vuid
LEFT JOIN voter_propensity_scores vps ON v.vuid = vps.vuid
WHERE v.congressional_district = 'TX-15'
GROUP BY v.vuid;
```

### Identify Super Activists
```sql
-- Voters who both vote consistently AND attend events
SELECT v.vuid, v.name, v.address,
       COUNT(DISTINCT ve.election_date) as elections_voted,
       ves.total_events_attended,
       ves.attendance_rate
FROM voters v
JOIN voter_elections ve ON v.vuid = ve.vuid
JOIN voter_engagement_summary ves ON v.vuid = ves.vuid
WHERE ves.total_events_attended >= 3
  AND ves.attendance_rate > 0.8  -- Shows up when they register
  AND v.congressional_district = 'TX-15'
GROUP BY v.vuid
HAVING COUNT(DISTINCT ve.election_date) >= 3
ORDER BY ves.total_events_attended DESC, elections_voted DESC;
```

### Event Attendance Predicts Turnout
```sql
-- Do people who attend events actually vote?
SELECT 
    CASE 
        WHEN ves.total_events_attended = 0 THEN 'No Events'
        WHEN ves.total_events_attended BETWEEN 1 AND 2 THEN '1-2 Events'
        WHEN ves.total_events_attended >= 3 THEN '3+ Events'
    END as engagement_level,
    COUNT(DISTINCT v.vuid) as total_voters,
    COUNT(DISTINCT CASE WHEN ve.election_date = '2026-03-03' THEN v.vuid END) as voted_2026,
    ROUND(COUNT(DISTINCT CASE WHEN ve.election_date = '2026-03-03' THEN v.vuid END) * 100.0 / COUNT(DISTINCT v.vuid), 1) as turnout_rate
FROM voters v
LEFT JOIN voter_engagement_summary ves ON v.vuid = ves.vuid
LEFT JOIN voter_elections ve ON v.vuid = ve.vuid
WHERE v.congressional_district = 'TX-15'
GROUP BY engagement_level
ORDER BY engagement_level;
```

### Flaky Registrants (Register but Don't Show)
```sql
-- Find people who register for events but never attend
SELECT v.vuid, v.name, v.address, v.phone,
       COUNT(DISTINCT ver.event_id) as registered_events,
       COUNT(DISTINCT vea.event_id) as attended_events,
       ROUND(COUNT(DISTINCT vea.event_id) * 100.0 / COUNT(DISTINCT ver.event_id), 1) as attendance_rate
FROM voters v
JOIN voter_event_registrations ver ON v.vuid = ver.vuid
LEFT JOIN voter_event_attendance vea ON v.vuid = vea.vuid AND ver.event_id = vea.event_id
WHERE v.congressional_district = 'TX-15'
GROUP BY v.vuid
HAVING COUNT(DISTINCT ver.event_id) >= 3
   AND attendance_rate < 50
ORDER BY registered_events DESC;
```

### Geographic Mobility Analysis
```sql
-- Voters who moved between districts
SELECT v.vuid, v.name,
       vah_old.address as old_address,
       vah_old.congressional_district as old_district,
       v.address as current_address,
       v.congressional_district as new_district,
       vah_old.effective_date as moved_date
FROM voters v
JOIN voter_address_history vah_old ON v.vuid = vah_old.vuid
WHERE vah_old.congressional_district != v.congressional_district
  AND vah_old.effective_date >= '2024-01-01'
ORDER BY vah_old.effective_date DESC;
```

## Benefits

1. **360-Degree View**: Combine voting behavior + physical engagement + demographics
2. **Immutable Core**: VUID, birth_year, sex never change - reliable identifiers
3. **Historical Tracking**: Track changes over time (moves, redistricting, engagement)
4. **Predictive Power**: Event attendance predicts turnout; identify super activists
5. **Separation of Concerns**: Core voter data separate from enrichments
6. **Incremental Enrichment**: Add Crowdsurfer data without touching voting tables
7. **Fast Queries**: Indexed by VUID for instant lookups
8. **Scalable**: Add new enrichment tables as needed
9. **Privacy-Aware**: Sensitive data in separate tables with access controls
10. **Campaign Integration**: Know who to invite, who will show up, who will vote

## Real-World Use Cases

### Use Case 1: Event Targeting
**Question**: "Who should we invite to our next rally?"

**Answer**: High-propensity voters who attend events but haven't been to one recently
```sql
SELECT v.vuid, v.name, v.phone, v.email,
       vps.turnout_score,
       ves.total_events_attended,
       ves.last_event_date
FROM voters v
JOIN voter_propensity_scores vps ON v.vuid = vps.vuid
LEFT JOIN voter_engagement_summary ves ON v.vuid = ves.vuid
WHERE v.congressional_district = 'TX-15'
  AND vps.turnout_score > 70
  AND (ves.total_events_attended >= 1 OR vps.volunteer_score > 60)
  AND (ves.last_event_date < '2026-01-01' OR ves.last_event_date IS NULL)
ORDER BY vps.turnout_score DESC, ves.total_events_attended DESC
LIMIT 500;
```

### Use Case 2: Volunteer Recruitment
**Question**: "Who are our most reliable activists?"

**Answer**: People who show up to events AND vote consistently
```sql
SELECT v.vuid, v.name, v.phone,
       ves.total_events_attended,
       ves.attendance_rate,
       COUNT(DISTINCT ve.election_date) as elections_voted
FROM voters v
JOIN voter_engagement_summary ves ON v.vuid = ves.vuid
JOIN voter_elections ve ON v.vuid = ve.vuid
WHERE ves.attendance_rate > 0.8
  AND ves.total_events_attended >= 3
GROUP BY v.vuid
HAVING elections_voted >= 3
ORDER BY ves.total_events_attended DESC;
```

### Use Case 3: Turnout Prediction
**Question**: "Will this person vote in the next election?"

**Answer**: ML model trained on voting history + event attendance + demographics
```python
# Feature engineering for ML model
features = {
    'elections_voted_last_4_years': count_elections(vuid, since='2022-01-01'),
    'events_attended_last_year': count_events(vuid, since='2025-01-01'),
    'attendance_rate': get_attendance_rate(vuid),
    'is_super_volunteer': is_super_volunteer(vuid),
    'age': 2026 - birth_year,
    'income_bracket': get_income_bracket(vuid),
    'homeowner': is_homeowner(vuid),
    'days_since_last_contact': days_since_contact(vuid)
}
turnout_probability = model.predict(features)
```

## Next Steps

### Phase 1: Foundation (Current)
- ✅ Core `voters` table with VUID as primary key
- ✅ `voter_elections` table for voting history
- ✅ District assignments (current + old for redistricting)
- ✅ Geocoding for all voters

### Phase 2: Crowdsurfer Integration (Next)
1. Create `voter_event_registrations` table
2. Create `voter_event_attendance` table with device verification
3. Build Crowdsurfer → Politiquera sync pipeline
4. Implement VUID matching (email, phone, name+address)
5. Create `voter_engagement_summary` computed table

### Phase 3: Enrichment (Short-term)
1. Add `voter_address_history` for move tracking
2. Add `voter_geography_history` for all historical maps
3. Add `voter_demographics_enriched` with census data
4. Build background enrichment workers

### Phase 4: ML & Predictions (Medium-term)
1. Build propensity score models (turnout, volunteer, donor)
2. Create `voter_propensity_scores` table
3. Train models on voting history + event attendance
4. Real-time score updates after each event/election

### Phase 5: Advanced Features (Long-term)
1. Social network analysis (household, neighbors)
2. Issue position tracking from surveys
3. Media consumption patterns
4. Integration with VAN/NGP campaign tools

## Data Sources to Integrate

- **Census Bureau**: Income, education, household size by block group
- **Property Records**: Homeownership, property value
- **Voter File Vendors**: Enhanced demographics, consumer data
- **Social Media**: Issue positions, media consumption (with consent)
- **Campaign Tools**: Contact history, survey responses
- **Public Records**: Donor history, business ownership
- **Geographic Data**: School districts, municipal boundaries

This architecture positions the system as a **comprehensive voter intelligence platform** rather than just a turnout tracker.

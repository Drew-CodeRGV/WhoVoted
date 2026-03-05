# Combined Election Datasets - Implementation Summary

## Overview

The system now provides BOTH combined and individual election datasets, giving users flexibility to view:

1. **Combined "Complete Election" datasets** (DEFAULT) - Shows early voting + election day together
2. **Individual datasets** - Separate "Early Voting" and "Election Day" for drill-down analysis

## How It Works

### Backend Changes (`backend/app.py`)

#### 1. `/api/elections` Endpoint

The API now returns BOTH types of datasets:

**Combined Datasets:**
- Created by grouping data by `election_date` only (ignoring `voting_method`)
- Marked with `votingMethod: 'combined'`
- Includes `votingMethods` array showing which methods are included (e.g., ['early-voting', 'election-day'])
- Includes `methodBreakdown` object with stats per voting method
- **Only created if election has multiple voting methods** (no point in "combining" a single method)

**Individual Datasets:**
- Created by grouping data by `(election_date, voting_method)`
- Marked with specific `votingMethod` (e.g., 'early-voting', 'election-day')
- Allows users to drill down into specific voting periods

**Sorting:**
- Most recent elections first
- Combined datasets appear BEFORE individual datasets
- Within same date: combined → early-voting → election-day

**Example Response:**
```json
{
  "success": true,
  "elections": [
    {
      "electionDate": "2026-03-03",
      "electionYear": "2026",
      "electionType": "primary",
      "votingMethod": "combined",
      "votingMethods": ["early-voting", "election-day"],
      "totalVoters": 150000,
      "methodBreakdown": {
        "early-voting": {"totalVoters": 60000, "geocodedCount": 58000},
        "election-day": {"totalVoters": 90000, "geocodedCount": 87000}
      },
      "parties": ["Democratic", "Republican"],
      "counties": ["Hidalgo"],
      ...
    },
    {
      "electionDate": "2026-03-03",
      "electionYear": "2026",
      "electionType": "primary",
      "votingMethod": "early-voting",
      "totalVoters": 60000,
      ...
    },
    {
      "electionDate": "2026-03-03",
      "electionYear": "2026",
      "electionType": "primary",
      "votingMethod": "election-day",
      "totalVoters": 90000,
      ...
    }
  ]
}
```

#### 2. `/api/voters/heatmap` Endpoint

Updated to handle `voting_method='combined'`:
- When `votingMethod` is 'combined', converts it to `None`
- `None` means "fetch all voting methods" in the database query
- Returns all voters regardless of how they voted (early or election day)

#### 3. `/api/election-stats` Endpoint

Updated to handle `voting_method='combined'`:
- When `votingMethod` is 'combined', converts it to `None`
- Returns aggregate stats across all voting methods
- Includes total voters, party breakdown, flips, new voters, etc.

### Frontend Changes (`public/ui.js`)

#### DatasetSelector Class Updates

**1. `populateDropdown()` Method:**
- Detects `votingMethod === 'combined'`
- Displays as "Complete Election" when both early and election day are present
- Shows breakdown in tooltip/label: "(150,000 voters)"

**2. `updateDatasetInfo()` Method:**
- Handles combined datasets in the info display
- Shows "Complete Election" instead of just voting method
- Provides context about what's included

**Display Labels:**
- `votingMethod === 'combined'` + both methods → "Complete Election"
- `votingMethod === 'combined'` + early only → "Early Voting"
- `votingMethod === 'combined'` + election day only → "Election Day"
- `votingMethod === 'early-voting'` → "Early Voting"
- `votingMethod === 'election-day'` → "Election Day"

### Data Flow

```
User opens map
    ↓
Frontend calls /api/elections
    ↓
Backend returns:
  - 2026 Primary - Complete Election (150K voters) ← DEFAULT
  - 2026 Primary - Early Voting (60K voters)
  - 2026 Primary - Election Day (90K voters)
    ↓
User selects "Complete Election" (default)
    ↓
Frontend calls /api/voters/heatmap?voting_method=combined
    ↓
Backend fetches ALL voters (early + election day)
    ↓
Map displays all 150K voters
```

## Benefits

### 1. Complete Picture by Default
Users see the full election results immediately without needing to understand the difference between early voting and election day.

### 2. Granular Analysis Available
Power users can still drill down into specific voting periods to analyze:
- Early voting trends
- Election day turnout
- Differences in demographics between voting methods

### 3. Backward Compatible
- Individual datasets still exist
- Old bookmarks/links still work
- No breaking changes to existing functionality

### 4. Automatic for All Elections
- Works for any election with multiple voting methods
- No manual configuration needed
- Automatically combines when you upload election day data

## User Experience

### Dropdown Display

```
┌─────────────────────────────────────────────────────────┐
│ Hidalgo 2026 Primary - Complete Election (150,000)  ▼  │
├─────────────────────────────────────────────────────────┤
│ Hidalgo 2026 Primary - Complete Election (150,000)     │ ← DEFAULT
│ Hidalgo 2026 Primary - Early Voting (60,000)           │
│ Hidalgo 2026 Primary - Election Day (90,000)           │
│ Hidalgo 2024 Primary - Complete Election (140,000)     │
│ Hidalgo 2024 Primary - Early Voting (55,000)           │
│ Hidalgo 2024 Primary - Election Day (85,000)           │
└─────────────────────────────────────────────────────────┘
```

### Info Display

```
┌─────────────────────────────────────┐
│ County: Hidalgo                     │
│ Year: 2026                          │
│ Type: Primary - Complete Election   │
│ Voters: 150,000                     │
└─────────────────────────────────────┘
```

## Database Queries

The system uses the SAME database queries - just with different `voting_method` filters:

**Combined Dataset:**
```sql
SELECT * FROM voter_elections 
WHERE election_date = '2026-03-03'
-- No voting_method filter = all methods
```

**Individual Dataset:**
```sql
SELECT * FROM voter_elections 
WHERE election_date = '2026-03-03' 
AND voting_method = 'early-voting'
```

## Cache Handling

Cache keys include the voting method:
- `heatmap:Hidalgo:2026-03-03:all` (combined)
- `heatmap:Hidalgo:2026-03-03:early-voting` (individual)
- `heatmap:Hidalgo:2026-03-03:election-day` (individual)

This ensures correct data is served for each dataset type.

## Testing

### Verify Combined Datasets Appear

1. Open https://politiquera.com
2. Check dataset dropdown
3. Should see "Complete Election" as first option for 2026
4. Should also see individual "Early Voting" and "Election Day" options

### Verify Data Loads Correctly

1. Select "Complete Election"
2. Map should show ALL voters (early + election day)
3. Stats box should show combined totals
4. Select "Early Voting"
5. Map should show ONLY early voters
6. Stats should reflect early voting only

### Verify Stats Are Accurate

```bash
# On server
cd /opt/whovoted
source venv/bin/activate
python3 deploy/check_2026_data.py
```

Should show:
- Total voters by voting method
- Combined totals match sum of individual methods

## Future Enhancements

### 1. Method Breakdown in Stats Box
Show breakdown of early vs election day within combined view:
```
Total: 150,000
  Early Voting: 60,000 (40%)
  Election Day: 90,000 (60%)
```

### 2. Toggle Between Methods
Add button to switch between early/election day without changing dataset:
```
[Early] [Election Day] [Both]
```

### 3. Visual Distinction
Use different marker styles to distinguish early vs election day voters on combined map.

## Troubleshooting

### Issue: Combined dataset not appearing

**Cause:** Election only has one voting method (e.g., only early voting data uploaded)

**Solution:** Combined datasets only appear when election has 2+ voting methods. Upload election day data to see combined view.

### Issue: Wrong voter count in combined dataset

**Cause:** Cache not cleared after uploading new data

**Solution:** 
```bash
# On server
cd /opt/whovoted/backend
source ../venv/bin/activate
python3 -c "from app import cache_invalidate; cache_invalidate()"
```

### Issue: Individual datasets missing

**Cause:** Code error in grouping logic

**Solution:** Check backend logs:
```bash
tail -100 /opt/whovoted/logs/gunicorn.log
```

## Summary

The system now provides the best of both worlds:
- **Default view** shows complete election picture (early + election day combined)
- **Drill-down view** allows analysis of specific voting periods
- **Automatic** - works for all elections without manual configuration
- **Backward compatible** - existing functionality preserved

Users get the full story by default, with the option to dig deeper when needed.


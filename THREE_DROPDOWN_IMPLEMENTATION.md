# Three Dropdown Implementation Plan

## New UI Structure
Instead of one complex "Election" dropdown, we now have three simple dropdowns:

1. **County** - Select which county to view (Hidalgo, Cameron, etc.)
2. **Year** - Select election year (2026, 2024, 2022, etc.)
3. **Voting Method** - Select data type:
   - Complete Election (combined: early + election day + mail-in)
   - Early Voting
   - Election Day  
   - Mail-In

## Implementation Steps

### 1. HTML Changes ✓
- Replaced single "Election" dropdown with three dropdowns
- Added year-selector and voting-method-selector elements
- Kept county dropdown as-is

### 2. JavaScript Changes (TODO)
Need to rewrite DatasetSelector class to:
- Populate year dropdown from available datasets
- Populate voting method dropdown based on selected county + year
- Handle cascading changes (county change → update years → update methods)
- Load correct dataset when any dropdown changes
- Default to "Complete Election" when available

### 3. Data Flow
```
User selects County (Hidalgo)
  ↓
Load all datasets for Hidalgo
  ↓
Extract unique years → populate Year dropdown (2026, 2024, 2022...)
  ↓
User selects Year (2026)
  ↓
Filter datasets to 2026 only
  ↓
Extract available methods → populate Voting Method dropdown
  - Complete Election (if combined dataset exists)
  - Early Voting
  - Election Day
  - Mail-In
  ↓
User selects Voting Method (Complete Election)
  ↓
Load that specific dataset
```

### 4. Benefits
- Much simpler UX
- Clear separation of concerns
- Easy to understand what you're viewing
- No more scrolling through long lists
- Automatic filtering based on what's available

## Next: Implement JavaScript logic

---
inclusion: auto
---

# Data Integrity — Absolute Accuracy Standard

## Core Principle

Politiquera is a campaign intelligence tool. Campaign managers make resource allocation decisions — where to send canvassers, which precincts to target, how to spend limited dollars — based on what this tool shows them. **Wrong data costs campaigns elections.**

## The Standard

Every number displayed on the platform must be:
1. **Real** — sourced from an official record (voter rolls, certified results, county elections office)
2. **Verifiable** — traceable to a specific source document or database query
3. **Current** — reflects the most recent available data, with the date clearly shown
4. **Unambiguous** — if data is incomplete or uncertain, say so explicitly rather than filling gaps with estimates

## Rules

### NEVER:
- Display estimated or proportionally allocated data as if it were real
- Fill in missing precinct-level data with district-wide averages
- Show candidate-level results unless sourced from official certified canvass reports
- Assume a precinct belongs to a district without geometric verification
- Display a boundary that hasn't been verified against the authoritative source (TLC for state districts, Census for federal)
- Round numbers in ways that obscure the actual count
- Show "0" when the real answer is "no data available"

### ALWAYS:
- Show the data source and last-updated timestamp
- Distinguish between "zero votes" and "no data for this precinct"
- Use the official certified results when available, not election-night unofficial totals
- Verify precinct boundaries geometrically (centroid must be inside the district polygon)
- Aggregate sub-precinct splits to their parent precinct when individual split boundaries aren't available
- Label any data limitation clearly in the UI (e.g., "35 of 48 precincts have boundary outlines")
- Prefer showing nothing over showing wrong data

### Data Sources (in order of authority):
1. **County Elections Office** — certified canvass reports, official rosters, precinct-by-precinct results
2. **Texas Secretary of State** — certified statewide results, election returns
3. **Texas Legislative Council** — district boundaries (PLANH2316, PLANS2168, PLANC2333), VTD shapefiles
4. **Voter rolls** — per-voter party ballot pulled (which party's primary they voted in)
5. **Census Bureau** — VTD boundaries, demographic data (use TLC over Census when they conflict)

### What We CAN Show (Real Data):
- Per-precinct: how many pulled Democratic ballots, how many pulled Republican ballots (from voter rolls — exact)
- Per-precinct: total registered voters (from voter rolls — exact)
- Per-precinct: turnout percentage (voted / registered — exact)
- Per-precinct: which party won, by how many votes, margin percentage (exact)
- District-wide: certified candidate totals from SOS (exact)
- Voter history: which elections each voter participated in, which party (exact)
- Geographic: voter locations from geocoded addresses (accurate to address level)

### What We CANNOT Show (Without Official Canvass):
- Per-precinct candidate results (e.g., "Salinas got 45 votes in Precinct 72") — requires county canvass report
- Individual voter's candidate choice (secret ballot — we only know party, not candidate)
- Precinct boundaries for sub-splits (e.g., "081.01") — only parent precinct has a polygon

### When Data Is Missing:
- Show the precinct in the report card with its real numbers but mark it as "no boundary available"
- Do NOT draw a circle or dot as a substitute for a real polygon
- Do NOT estimate what the missing data might be
- Show a clear count: "Showing 35 of 48 precincts with boundary data"

## Application to Campaign Strategy

A campaign manager using this tool should be able to:
1. See exactly which precincts their party won/lost and by how much
2. Identify the highest-volume precincts (where the most votes are)
3. Identify battleground precincts (where the margin is smallest)
4. See registered voter counts to estimate untapped potential
5. Cross-reference with voter history to find mobilization targets

They should NOT be able to:
- See which candidate won each precinct (unless we have the official canvass)
- See estimated splits that look real but are proportional allocations
- Make decisions based on data that might be wrong

## Implementation Checklist

When building any new election tracker:
- [ ] Verify district boundary source is authoritative (TLC for state, Census for federal)
- [ ] Verify all precincts are geometrically inside the district
- [ ] Use only real per-precinct data from voter rolls
- [ ] Do not display candidate-level precinct data without official canvass
- [ ] Show data source and timestamp in the UI
- [ ] Show coverage stats ("X of Y precincts displayed")
- [ ] Test: can every number on screen be traced to a specific DB query?

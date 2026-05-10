# Design: Deploy Directory Cleanup

## Approach

Manual review + git rm. No automated tooling — the risk of accidentally deleting a needed script is too high.

## Categorization

### Category A: Keep (cron / documented workflows)
Scripts listed in requirements.md. Move to a `deploy/scripts/` subdirectory if desired, but keeping flat is fine.

### Category B: Keep (active election support)
Any `cache_misdbond2026_*.py`, `cache_elsa2026_*.py`, `import_misdbond2026_*.py`, `import_elsa*.py` — these support live elections.

### Category C: Archive (may be needed for reference)
Scripts that implement complex logic that might be needed again but aren't currently active. Move to `deploy/archive/` rather than deleting.

Candidates:
- `build_precinct_district_mapping.py` — the precinct→district algorithm is documented in steering, but the script itself may be useful
- `build_district_reference_data.py` — reference data builder
- `assign_districts_using_shapefiles.py` — shapefile-based district assignment

### Category D: Delete (one-off diagnostics)
All `check_*.py`, `verify_*.py`, `diagnose_*.py`, `debug_*.py`, `test_*.py` scripts that were clearly one-off investigations. Estimated ~200 scripts.

Exception: keep `test_email_registration.py`, `test_webhook_live.py`, `test_sms.py` — these are integration tests that may be rerun.

### Category E: Delete (superseded fixes)
All `fix_*.py` scripts where the fix is confirmed resolved. Estimated ~40 scripts.

## Naming Convention Going Forward

- `cache_<election>_<data>.py` — cache builders for specific elections
- `import_<source>.py` — data importers
- `build_<thing>.py` — one-time builders that produce persistent artifacts
- `check_<thing>.py` — diagnostic scripts (acceptable, but delete after use)
- `test_<thing>.py` — integration tests (keep if reusable)

## Process

1. Create `deploy/archive/` directory
2. Move Category C scripts to archive
3. `git rm` all Category D and E scripts
4. Update `deploy/README.md` with surviving scripts
5. Commit with message: "chore: clean up one-off deploy scripts"

## Risk

- Low: All deleted scripts are diagnostic/fix scripts. The actual application code is in `backend/`.
- Mitigation: Review git log before deleting anything that touched production data.

## Files Touched

- `deploy/*.py` — mass deletion
- `deploy/README.md` — update with surviving scripts
- `deploy/archive/` — new directory for archived scripts

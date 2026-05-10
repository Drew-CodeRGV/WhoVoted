# Spec: Deploy Directory Cleanup

## Problem

`deploy/` contains ~300+ Python scripts accumulated over many Kiro sessions. Most are one-off diagnostic, fix, or verification scripts that were run once and never needed again. They clutter the repo, make it hard to find reusable tools, and slow down `git status` / `git diff`. A mass deletion is staged but not committed.

## Goals

1. Identify which scripts are genuinely reusable (should stay).
2. Identify which scripts are one-off session artifacts (should be deleted).
3. Commit the cleanup with a clear rationale.
4. Prevent future accumulation with a naming convention.

## Acceptance Criteria

1. `deploy/` contains only scripts that are either: (a) run by cron, (b) run manually as part of documented workflows, or (c) reusable utilities referenced in steering docs.
2. All deleted scripts are gone from git history (or at minimum from HEAD).
3. A `deploy/README.md` documents what each surviving script does and when to run it.
4. Scripts that should survive are listed explicitly in this spec.

## Scripts That Must Survive

| Script | Reason |
|--------|--------|
| `evr_scraper.py` | Cron job — EVR data |
| `import_may2_roster.py` | Cron job — May 2 election roster |
| `election_day_scraper.py` | Run manually on election day |
| `import_official_rosters.py` | Reusable roster import |
| `import_election_history.py` | Reusable history import |
| `geocode_registry.py` | Reusable geocoding utility |
| `batch_geocode_aws.py` | Reusable AWS geocoding |
| `cache_misdbond2026_*.py` | Active election cache builders |
| `cache_elsa2026_*.py` | Active election cache builders |
| `refresh_misdbond2026_all.py` | Active election refresh |
| `refresh_elsa_caches.py` | Active election refresh |
| `generate_statewide_gazette_cache.py` | Gazette cache builder |
| `seed_elections.py` | DB seeding utility |
| `migrate_users_table.py` | DB migration utility |
| `setup_misdbond2026.sh` | Election setup |
| `nginx-whovoted.conf` | nginx config reference |
| `d15-nginx.conf` | d15 nginx config reference |
| `lightsail-setup.sh` | Server setup reference |
| `whovoted-key.pem` | SSH key (already gitignored?) |

## Criteria for Deletion

A script should be deleted if:
- Name starts with `check_`, `verify_`, `diagnose_`, `test_`, `fix_`, `find_`, `debug_` AND it was clearly a one-off investigation
- Name contains a specific date or version that has passed (e.g., `regenerate_tx15_with_timestamp.py`)
- It duplicates functionality of another script (e.g., `check_db_status.py`, `check_db_status2.py`, `check_db_status3.py`)
- It was created to fix a specific bug that is now resolved

## Out of Scope

- Cleaning up `*.md` files in repo root (separate concern)
- Cleaning up `public/` or `backend/` directories

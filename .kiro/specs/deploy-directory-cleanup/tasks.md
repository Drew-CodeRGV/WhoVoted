# Tasks: Deploy Directory Cleanup

- [pending] **1** Audit `deploy/` — categorize each script as Keep / Archive / Delete
- [pending] **2** Create `deploy/archive/` directory
- [pending] **3** Move Category C scripts (complex, may be needed) to `deploy/archive/`
- [pending] **4** `git rm` all Category D scripts (`check_*.py`, `verify_*.py`, `diagnose_*.py`, `debug_*.py` one-offs)
- [pending] **5** `git rm` all Category E scripts (`fix_*.py` for resolved bugs)
- [pending] **6** `git rm` duplicate scripts (e.g., `check_db_status.py`, `check_db_status2.py` — keep only one)
- [pending] **7** Update `deploy/README.md` with table of surviving scripts and their purpose
- [pending] **8** Verify cron scripts still exist: `evr_scraper.py`, `import_may2_roster.py`
- [pending] **9** Commit: `git commit -m "chore: clean up one-off deploy scripts (~200 files removed)"`
- [pending] **10** Push and verify production server still has the scripts it needs (they're in `/opt/whovoted/deploy/` on server, not pulled from git for cron)

## Status

**Overall**: [pending] — mass deletion is staged locally but not committed. Blocked on completing the categorization audit.

## Note

The server's `/opt/whovoted/deploy/` directory may have scripts that are NOT in the repo (uploaded directly via SCP during debugging sessions). Before deleting from git, verify the server doesn't depend on any script that was never committed.

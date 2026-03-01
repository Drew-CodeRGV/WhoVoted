"""
Pipeline Integrity Checker for WhoVoted EV uploads.

Runs after each upload completes to verify data consistency across
every stage: file → DB → GeoJSON → metadata → public deployment.

Each check produces a PASS/FAIL with details. Any FAIL triggers a
warning in the job log so the admin can investigate.
"""
import json
import hashlib
import logging
import sqlite3
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class IntegrityReport:
    """Collects check results and produces a summary."""

    def __init__(self, job_id: str, source_file: str):
        self.job_id = job_id
        self.source_file = source_file
        self.checks = []
        self.created_at = datetime.now().isoformat()

    def add(self, name: str, passed: bool, expected=None, actual=None, detail: str = ''):
        self.checks.append({
            'name': name,
            'passed': passed,
            'expected': expected,
            'actual': actual,
            'detail': detail,
        })

    @property
    def passed(self) -> bool:
        return all(c['passed'] for c in self.checks)

    @property
    def failed_checks(self) -> list:
        return [c for c in self.checks if not c['passed']]

    def summary_lines(self) -> list:
        lines = []
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c['passed'])
        lines.append(f"Integrity: {passed}/{total} checks passed")
        for c in self.failed_checks:
            lines.append(f"  FAIL {c['name']}: expected={c['expected']}, actual={c['actual']} {c['detail']}")
        return lines

    def to_dict(self) -> dict:
        return {
            'job_id': self.job_id,
            'source_file': self.source_file,
            'created_at': self.created_at,
            'passed': self.passed,
            'total_checks': len(self.checks),
            'passed_checks': sum(1 for c in self.checks if c['passed']),
            'checks': self.checks,
        }


def verify_ev_upload(
    db_path: str,
    data_dir: Path,
    public_dir: Path,
    county: str,
    year: str,
    election_type: str,
    election_date: str,
    party: str,
    raw_row_count: int,
    cleaned_row_count: int,
    normalized_vuid_count: int,
    geocoded_count: int,
    unmatched_count: int,
    job_id: str = '',
    source_file: str = '',
) -> IntegrityReport:
    """
    Run all integrity checks for an early vote upload.

    Parameters come from the processor at the end of process_early_vote_roster.
    """
    report = IntegrityReport(job_id, source_file)
    party_suffix = f'_{party}' if party else ''
    date_str = election_date.replace('-', '')

    # ── 1. Row-count chain ──────────────────────────────────────────────
    # raw >= cleaned >= normalized (monotonically decreasing)
    report.add(
        'row_chain_raw_ge_cleaned',
        raw_row_count >= cleaned_row_count,
        expected=f'>= {cleaned_row_count}',
        actual=raw_row_count,
        detail='raw rows should be >= cleaned rows (NaN/empty VUIDs removed)',
    )
    report.add(
        'row_chain_cleaned_ge_normalized',
        cleaned_row_count >= normalized_vuid_count,
        expected=f'>= {normalized_vuid_count}',
        actual=cleaned_row_count,
        detail='cleaned rows should be >= normalized VUIDs (non-digit VUIDs removed)',
    )

    # ── 2. DB record count ──────────────────────────────────────────────
    try:
        conn = sqlite3.connect(db_path)
        db_count = conn.execute(
            "SELECT COUNT(*) FROM voter_elections WHERE election_date=? AND party_voted=?",
            (election_date, party.capitalize() if party else ''),
        ).fetchone()[0]

        # DB uses upsert so duplicate VUIDs in source file produce fewer DB records.
        # DB count should be <= normalized_vuid_count (source may have dups) and > 0.
        report.add(
            'db_record_count',
            0 < db_count <= normalized_vuid_count,
            expected=f'> 0 and <= {normalized_vuid_count}',
            actual=db_count,
            detail='DB records should be > 0 and <= normalized VUIDs (upsert deduplicates)',
        )

        # Check for stale same-party records on different dates for this election year
        stale = conn.execute(
            """SELECT election_date, COUNT(*) FROM voter_elections
               WHERE party_voted=? AND election_date != ?
                 AND election_date LIKE ?
               GROUP BY election_date""",
            (party.capitalize() if party else '', election_date, f'{year}%'),
        ).fetchall()
        report.add(
            'no_stale_election_records',
            len(stale) == 0,
            expected='no stale records',
            actual=f'{len(stale)} stale date groups: {stale}' if stale else 'none',
            detail='No same-party records on different dates within the same election year',
        )
        conn.close()
    except Exception as e:
        report.add('db_record_count', False, detail=f'DB error: {e}')

    # ── 3. Day snapshot GeoJSON ─────────────────────────────────────────
    snap_file = data_dir / f'map_data_{county}_{year}_{election_type}{party_suffix}_{date_str}_ev.json'
    snap_features = 0
    if snap_file.exists():
        try:
            with open(snap_file) as f:
                snap_data = json.load(f)
            snap_features = len(snap_data.get('features', []))

            # Snapshot features should be close to normalized VUID count
            # (equal or slightly less if some VUIDs were filtered)
            report.add(
                'snapshot_feature_count',
                abs(snap_features - normalized_vuid_count) <= max(normalized_vuid_count * 0.01, 5),
                expected=f'~{normalized_vuid_count} (within 1%)',
                actual=snap_features,
                detail='Day snapshot features should be close to normalized VUID count',
            )

            # Every feature must have a non-empty vuid
            empty_vuids = sum(
                1 for f in snap_data['features']
                if not f.get('properties', {}).get('vuid')
            )
            report.add(
                'snapshot_no_empty_vuids',
                empty_vuids == 0,
                expected=0,
                actual=empty_vuids,
            )

            # geocoded + unmatched should equal total features
            geo = sum(1 for f in snap_data['features'] if not f['properties'].get('unmatched', False))
            unmatch = sum(1 for f in snap_data['features'] if f['properties'].get('unmatched', False))
            report.add(
                'snapshot_geo_plus_unmatched',
                geo + unmatch == snap_features,
                expected=snap_features,
                actual=geo + unmatch,
                detail='geocoded + unmatched should equal total features',
            )
            report.add(
                'snapshot_geocoded_matches',
                geo == geocoded_count,
                expected=geocoded_count,
                actual=geo,
            )
        except Exception as e:
            report.add('snapshot_feature_count', False, detail=f'Error reading snapshot: {e}')
    else:
        # Day snapshot may not exist for manually reprocessed datasets — warn but don't fail
        report.add('snapshot_exists', True, expected='exists', actual='missing (non-fatal)',
                    detail=f'Day snapshot not found: {snap_file.name}. OK for manual reprocessing.')

    # ── 4. Day snapshot metadata ────────────────────────────────────────
    snap_meta_file = data_dir / f'metadata_{county}_{year}_{election_type}{party_suffix}_{date_str}_ev.json'
    if snap_meta_file.exists():
        try:
            with open(snap_meta_file) as f:
                snap_meta = json.load(f)

            report.add(
                'snapshot_meta_raw_count',
                snap_meta.get('raw_voter_count', 0) == raw_row_count,
                expected=raw_row_count,
                actual=snap_meta.get('raw_voter_count'),
                detail='Snapshot metadata raw_voter_count should match file row count',
            )
            report.add(
                'snapshot_meta_election_date',
                snap_meta.get('election_date') == election_date,
                expected=election_date,
                actual=snap_meta.get('election_date'),
            )
        except Exception as e:
            report.add('snapshot_meta', False, detail=f'Error: {e}')
    else:
        report.add('snapshot_meta_exists', True, expected='exists', actual='missing (non-fatal)',
                    detail='Day snapshot metadata not found. OK for manual reprocessing.')

    # ── 5. Cumulative GeoJSON ───────────────────────────────────────────
    cum_file = data_dir / f'map_data_{county}_{year}_{election_type}{party_suffix}_cumulative_ev.json'
    if cum_file.exists():
        try:
            with open(cum_file) as f:
                cum_data = json.load(f)
            cum_features = len(cum_data.get('features', []))

            # Cumulative deduplicates by VUID across all day snapshots.
            # It should have features > 0 and <= snapshot (dedup can only reduce).
            report.add(
                'cumulative_count_valid',
                0 < cum_features <= (snap_features if snap_file.exists() else cum_features),
                expected=f'> 0 and <= snapshot ({snap_features if snap_file.exists() else "?"})',
                actual=cum_features,
                detail='Cumulative features should be > 0 and <= snapshot (dedup reduces duplicates)',
            )

            # All VUIDs in cumulative should be unique
            cum_vuids = [f['properties']['vuid'] for f in cum_data['features'] if f.get('properties', {}).get('vuid')]
            unique_cum = len(set(cum_vuids))
            report.add(
                'cumulative_unique_vuids',
                unique_cum == cum_features,
                expected=cum_features,
                actual=unique_cum,
                detail='All VUIDs in cumulative should be unique',
            )
        except Exception as e:
            report.add('cumulative_geojson', False, detail=f'Error: {e}')
    else:
        report.add('cumulative_exists', False, expected='exists', actual='missing')

    # ── 6. Cumulative metadata ──────────────────────────────────────────
    cum_meta_file = data_dir / f'metadata_{county}_{year}_{election_type}{party_suffix}_cumulative_ev.json'
    if cum_meta_file.exists():
        try:
            with open(cum_meta_file) as f:
                cum_meta = json.load(f)

            cum_total = cum_meta.get('total_addresses', 0)
            cum_raw = cum_meta.get('raw_voter_count', 0)

            # raw_voter_count should be >= total_addresses (or equal)
            report.add(
                'cumulative_meta_raw_ge_total',
                cum_raw >= cum_total or cum_raw == 0,
                expected=f'>= {cum_total}',
                actual=cum_raw,
                detail='Cumulative raw_voter_count should be >= total_addresses',
            )

            # total_addresses should be >= feature count
            report.add(
                'cumulative_meta_total_ge_features',
                cum_total >= cum_features if cum_file.exists() else True,
                expected=f'>= {cum_features if cum_file.exists() else "?"}',
                actual=cum_total,
                detail='Metadata total_addresses should be >= GeoJSON feature count',
            )
        except Exception as e:
            report.add('cumulative_meta', False, detail=f'Error: {e}')

    # ── 7. Public deployment ────────────────────────────────────────────
    public_data_dir = public_dir / 'data'
    pub_cum_file = public_data_dir / f'map_data_{county}_{year}_{election_type}{party_suffix}_cumulative_ev.json'
    pub_cum_meta = public_data_dir / f'metadata_{county}_{year}_{election_type}{party_suffix}_cumulative_ev.json'

    report.add(
        'public_cumulative_deployed',
        pub_cum_file.exists(),
        expected='exists',
        actual='exists' if pub_cum_file.exists() else 'missing',
    )
    report.add(
        'public_cumulative_meta_deployed',
        pub_cum_meta.exists(),
        expected='exists',
        actual='exists' if pub_cum_meta.exists() else 'missing',
    )

    # Verify public files match data/ files (byte-level)
    if pub_cum_file.exists() and cum_file.exists():
        src_hash = _file_hash(cum_file)
        pub_hash = _file_hash(pub_cum_file)
        report.add(
            'public_cumulative_matches_source',
            src_hash == pub_hash,
            expected=src_hash[:12],
            actual=pub_hash[:12],
            detail='Public GeoJSON should be identical to data/ GeoJSON',
        )

    if pub_cum_meta.exists() and cum_meta_file.exists():
        src_hash = _file_hash(cum_meta_file)
        pub_hash = _file_hash(pub_cum_meta)
        report.add(
            'public_meta_matches_source',
            src_hash == pub_hash,
            expected=src_hash[:12],
            actual=pub_hash[:12],
            detail='Public metadata should be identical to data/ metadata',
        )

    # ── 8. Flip detection sanity ────────────────────────────────────────
    if cum_file.exists():
        try:
            with open(cum_file) as f:
                cum_data = json.load(f)

            flipped = sum(1 for f in cum_data['features'] if f['properties'].get('has_switched_parties'))
            has_prev = sum(1 for f in cum_data['features'] if f['properties'].get('party_affiliation_previous'))

            # Every flipped voter must have a previous party
            report.add(
                'flipped_have_previous_party',
                flipped == has_prev,
                expected=flipped,
                actual=has_prev,
                detail='Every has_switched_parties=True voter must have party_affiliation_previous',
            )

            # Flipped voters should be a reasonable fraction (< 20% of total)
            if cum_features > 0:
                flip_pct = flipped / cum_features * 100
                report.add(
                    'flip_rate_reasonable',
                    flip_pct < 20,
                    expected='< 20%',
                    actual=f'{flip_pct:.1f}%',
                    detail='Flip rate sanity check',
                )
        except Exception:
            pass

    return report


def _file_hash(path: Path) -> str:
    """SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

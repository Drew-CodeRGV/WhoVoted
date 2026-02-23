"""
Reprocess existing GeoJSON map_data files to add party_affiliation_previous field.
Checks against ALL earlier datasets (both Dem and Rep) to catch flips in both directions.

Usage: python reprocess_flipped_voters.py
Run from the WhoVoted directory.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import json
import logging
from pathlib import Path
from config import Config
from processor import CrossReferenceEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reprocess():
    data_dir = Config.DATA_DIR
    public_data_dir = Config.PUBLIC_DIR / 'data'

    metadata_files = sorted(data_dir.glob('metadata_*.json'))
    logger.info(f"Found {len(metadata_files)} metadata files in {data_dir}")

    for meta_path in metadata_files:
        try:
            with open(meta_path) as f:
                meta = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Skipping {meta_path.name}: {e}")
            continue

        try:
            county = meta.get('county', '')
            election_date = meta.get('election_date', '')
            if not county or not election_date:
                logger.warning(f"Skipping {meta_path.name}: missing county or election_date")
                continue

            map_data_name = 'map_data_' + meta_path.name[len('metadata_'):]
            map_data_path = data_dir / map_data_name

            if not map_data_path.exists():
                logger.warning(f"Map data file not found: {map_data_path}")
                continue

            logger.info(f"\nProcessing: {map_data_name}")
            logger.info(f"  County: {county}, Election Date: {election_date}")

            with open(map_data_path) as f:
                geojson = json.load(f)

            features = geojson.get('features', [])
            if not features:
                logger.info(f"  No features, skipping")
                continue

            engine = CrossReferenceEngine(county, election_date, data_dir)
            earlier = engine.find_earlier_datasets()

            if not earlier:
                logger.info(f"  No earlier datasets found for {county} before {election_date}")
                for feature in features:
                    feature['properties']['party_affiliation_previous'] = ''
            else:
                # Merge lookups from ALL earlier datasets (both Dem and Rep)
                merged_vuid = {}
                merged_name_coord = {}
                for ds in earlier:
                    if not ds['map_data_path'].exists():
                        continue
                    logger.info(f"  Loading earlier dataset: {ds['map_data_path'].name} (date={ds['election_date']})")
                    lookups = engine.load_voter_lookup(ds['map_data_path'])
                    # Earlier entries don't overwrite — first match wins (most recent date first)
                    for k, v in lookups['vuid_lookup'].items():
                        if k not in merged_vuid:
                            merged_vuid[k] = v
                    for k, v in lookups['name_coord_lookup'].items():
                        if k not in merged_name_coord:
                            merged_name_coord[k] = v

                logger.info(f"  Merged lookups: {len(merged_vuid)} VUIDs, {len(merged_name_coord)} name+coords")

                dem_to_rep = 0
                rep_to_dem = 0
                for feature in features:
                    props = feature['properties']
                    coords = feature.get('geometry', {}).get('coordinates', [])

                    voter_row = {
                        'vuid': str(props.get('vuid', '')),
                        'lastname': str(props.get('lastname', '')),
                        'firstname': str(props.get('firstname', '')),
                        'lat': coords[1] if len(coords) >= 2 else 0,
                        'lng': coords[0] if len(coords) >= 2 else 0,
                        'party_affiliation_current': props.get('party_affiliation_current', ''),
                        'ballot_style': props.get('ballot_style', ''),
                        'party': props.get('party', ''),
                    }

                    prev_party = engine.get_previous_party(voter_row, merged_vuid, merged_name_coord)
                    props['party_affiliation_previous'] = prev_party

                    if prev_party:
                        current = props.get('party_affiliation_current', '').lower()
                        prev = prev_party.lower()
                        is_cur_dem = 'democrat' in current or 'dem' in current
                        is_cur_rep = 'republican' in current or 'rep' in current
                        is_prev_dem = 'democrat' in prev or 'dem' in prev
                        is_prev_rep = 'republican' in prev or 'rep' in prev

                        if is_prev_dem and is_cur_rep:
                            dem_to_rep += 1
                        elif is_prev_rep and is_cur_dem:
                            rep_to_dem += 1

                total_flipped = dem_to_rep + rep_to_dem
                logger.info(f"  RESULTS: {total_flipped} flipped voters out of {len(features)}")
                logger.info(f"    Dem → Rep (Flipped Red/Maroon): {dem_to_rep}")
                logger.info(f"    Rep → Dem (Flipped Blue/Purple): {rep_to_dem}")

            # Save updated GeoJSON
            with open(map_data_path, 'w') as f:
                json.dump(geojson, f, indent=2)
            logger.info(f"  Updated: {map_data_path}")

            public_map_data = public_data_dir / map_data_name
            if public_map_data.exists():
                with open(public_map_data, 'w') as f:
                    json.dump(geojson, f, indent=2)
                logger.info(f"  Updated: {public_map_data}")

        except Exception as e:
            logger.error(f"Error processing {meta_path.name}: {e}")
            continue

    logger.info("\nDone! Refresh the browser to see flipped voters.")

if __name__ == '__main__':
    reprocess()

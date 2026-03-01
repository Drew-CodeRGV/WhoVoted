#!/usr/bin/env python3
"""
Batch geocode all ungeocoded Hidalgo County voter addresses using AWS Location Service.
Usage: python3 batch_geocode_aws.py [--workers 20] [--batch-size 500] [--dry-run]
"""
import os, sys, time, json, sqlite3, logging, argparse, threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted')
from dotenv import load_dotenv
load_dotenv('/opt/whovoted/.env')

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

DB_PATH = '/opt/whovoted/data/whovoted.db'
STATUS_FILE = '/opt/whovoted/data/batch_geocode_status.json'
PLACE_INDEX = os.environ.get('AWS_LOCATION_PLACE_INDEX', 'WhoVotedPlaceIndex')
REGION = os.environ.get('AWS_REGION', os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
COUNTY = 'Hidalgo'

os.makedirs('/opt/whovoted/logs', exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.FileHandler('/opt/whovoted/logs/batch_geocode.log'), logging.StreamHandler()])
log = logging.getLogger('batch_geocode')

def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn

def ensure_tables(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS voter_addresses (
            vuid TEXT NOT NULL, address_key TEXT NOT NULL, address_raw TEXT,
            created_at TEXT DEFAULT (datetime('now')), PRIMARY KEY (vuid));
        CREATE INDEX IF NOT EXISTS idx_va_address_key ON voter_addresses(address_key);
    """)
    conn.commit()

def normalize_address(addr):
    return addr.strip().upper()

def write_status(status):
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception:
        pass

class AWSBatchGeocoder:
    def __init__(self, max_workers=20):
        self.max_workers = max_workers
        cfg = BotoConfig(max_pool_connections=max_workers + 5,
                         retries={'max_attempts': 3, 'mode': 'adaptive'})
        self.client = boto3.client('location', region_name=REGION, config=cfg)
        self.place_index = PLACE_INDEX
        self.stats = {'api_calls': 0, 'successes': 0, 'failures': 0, 'throttles': 0}
        self._lock = threading.Lock()

    def geocode_one(self, address):
        try:
            with self._lock:
                self.stats['api_calls'] += 1
            resp = self.client.search_place_index_for_text(
                IndexName=self.place_index, Text=address, MaxResults=1, FilterCountries=['USA'])
            if resp.get('Results'):
                place = resp['Results'][0]['Place']
                coords = place['Geometry']['Point']
                with self._lock:
                    self.stats['successes'] += 1
                return normalize_address(address), {
                    'lat': float(coords[1]), 'lng': float(coords[0]),
                    'display_name': place.get('Label', address), 'source': 'aws_batch',
                    'relevance': resp['Results'][0].get('Relevance', 0)}
            else:
                with self._lock:
                    self.stats['failures'] += 1
                return normalize_address(address), None
        except ClientError as e:
            code = e.response['Error']['Code']
            with self._lock:
                if code == 'ThrottlingException':
                    self.stats['throttles'] += 1
                else:
                    self.stats['failures'] += 1
            if code == 'ThrottlingException':
                time.sleep(2)
                try:
                    resp = self.client.search_place_index_for_text(
                        IndexName=self.place_index, Text=address, MaxResults=1, FilterCountries=['USA'])
                    if resp.get('Results'):
                        place = resp['Results'][0]['Place']
                        coords = place['Geometry']['Point']
                        with self._lock:
                            self.stats['successes'] += 1
                        return normalize_address(address), {
                            'lat': float(coords[1]), 'lng': float(coords[0]),
                            'display_name': place.get('Label', address), 'source': 'aws_batch_retry',
                            'relevance': resp['Results'][0].get('Relevance', 0)}
                except Exception:
                    pass
            return normalize_address(address), None
        except Exception:
            with self._lock:
                self.stats['failures'] += 1
            return normalize_address(address), None

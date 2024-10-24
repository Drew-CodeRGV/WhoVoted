import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import threading
import logging
import re
import time
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ThreadSafeCounter:
    def __init__(self):
        self.value = 0
        self.lock = Lock()

    def increment(self):
        with self.lock:
            self.value += 1
            return self.value


class GoogleGeocoder:
    def __init__(self, api_key, max_workers=4):
        self.api_key = api_key
        self.max_workers = max_workers
        self.cache = {}
        self.cache_lock = Lock()
        self.request_lock = Lock()
        self.last_request_time = 0
        self.min_delay = 0.1  # 100ms between requests to respect rate limits

    def geocode_address(self, address):
        # Check cache first
        with self.cache_lock:
            if address in self.cache:
                return address, self.cache[address]

        # Rate limiting
        with self.request_lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_delay:
                time.sleep(self.min_delay - time_since_last)
            self.last_request_time = time.time()

        try:
            base_url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {"address": address, "key": self.api_key}

            response = requests.get(base_url, params=params, timeout=10)
            data = response.json()

            if data["status"] == "OK":
                result = data["results"][0]
                location = result["geometry"]["location"]

                location_data = {
                    "latitude": location["lat"],
                    "longitude": location["lng"],
                    "formatted_address": result["formatted_address"],
                    "place_id": result["place_id"],
                }

                # Update cache
                with self.cache_lock:
                    self.cache[address] = location_data

                return address, location_data
            else:
                logger.debug(
                    f"Geocoding failed with status: {data['status']} for address: {address}"
                )
                if "error_message" in data:
                    logger.debug(f"Error message: {data['error_message']}")
                return address, None

        except Exception as e:
            logger.debug(f"Error geocoding address {address}: {str(e)}")
            return address, None


def ensure_directory(directory):
    """Create directory if it doesn't exist and verify it's writable"""
    try:
        os.makedirs(directory, exist_ok=True)
        # Test if directory is writable
        test_file = Path(directory) / ".write_test"
        test_file.touch()
        test_file.unlink()
        return True
    except Exception as e:
        logger.error(f"Error creating/accessing directory {directory}: {str(e)}")
        return False


def save_json_file(data, filepath, backup=True):
    """Save JSON data with error handling and backup"""
    filepath = Path(filepath)
    try:
        if backup and filepath.exists():
            # Create backup with timestamp to avoid conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = filepath.with_name(f"{filepath.stem}_{timestamp}.json.bak")
            try:
                os.replace(filepath, backup_path)
            except Exception as e:
                logger.warning(f"Could not create backup, proceeding without: {str(e)}")

        # Save new data
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Successfully saved data to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving file {filepath}: {str(e)}")
        return False


def save_progress_atomic(data, filepath):
    """Save progress data atomically using a temporary file"""
    filepath = Path(filepath)
    temp_path = filepath.with_name(f"{filepath.stem}_temp.json")
    try:
        # Write to temporary file first
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2)

        # Then rename it to the target file (atomic operation)
        os.replace(temp_path, filepath)
        return True
    except Exception as e:
        logger.error(f"Error saving progress: {str(e)}")
        if temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass
        return False


def load_existing_geocoded_data(map_data_file):
    """Load existing geocoded addresses from map data file"""
    try:
        if map_data_file.exists():
            with open(map_data_file, "r") as f:
                existing_data = json.load(f)

            # Create a dictionary of existing geocoded addresses
            geocoded_addresses = {}
            for feature in existing_data.get("features", []):
                props = feature.get("properties", {})
                original_address = props.get("original_address")
                if original_address:
                    geocoded_addresses[original_address] = {
                        "location_data": {
                            "latitude": feature["geometry"]["coordinates"][1],
                            "longitude": feature["geometry"]["coordinates"][0],
                            "formatted_address": props.get("address"),
                            "place_id": props.get("place_id"),
                        },
                        "feature": feature,
                    }

            logger.info(f"Loaded {len(geocoded_addresses)} existing geocoded addresses")
            return existing_data, geocoded_addresses
        else:
            return {"type": "FeatureCollection", "features": []}, {}
    except Exception as e:
        logger.warning(f"Error loading existing geocoded data: {str(e)}")
        return {"type": "FeatureCollection", "features": []}, {}


def fetch_csv(url):
    """
    Fetch CSV data from URL and return as pandas DataFrame.
    """
    try:
        logger.info(f"Fetching data from {url}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        temp_file = Path("temp_data.csv")
        with open(temp_file, "wb") as f:
            f.write(response.content)

        df = pd.read_csv(temp_file)
        temp_file.unlink()

        logger.info(f"Successfully fetched {len(df)} records")
        return df

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching CSV: {str(e)}")
        raise


def clean_address(address):
    if pd.isna(address):
        return None

    address = re.sub(r"[^a-zA-Z0-9\s,.]", " ", address)

    replacements = {
        r"\bST\b": "STREET",
        r"\bAVE\b": "AVENUE",
        r"\bRD\b": "ROAD",
        r"\bDR\b": "DRIVE",
        r"\bLN\b": "LANE",
        r"\bCT\b": "COURT",
        r"\bAPT\b": "APARTMENT",
        r"\bN\b": "NORTH",
        r"\bS\b": "SOUTH",
        r"\bE\b": "EAST",
        r"\bW\b": "WEST",
        r"\bBLVD\b": "BOULEVARD",
        r"\bCIR\b": "CIRCLE",
    }

    for pattern, replacement in replacements.items():
        address = re.sub(pattern, replacement, address.upper())

    if "TX" not in address.upper():
        address = f"{address}, TEXAS"

    return " ".join(address.split())


def process_data(url, api_key, output_dir="data", max_workers=4):
    """
    Fetch and process CSV data with parallel geocoding using Google's API.
    """
    # Ensure output directory exists and is writable
    if not ensure_directory(output_dir):
        raise RuntimeError(f"Cannot access or create output directory: {output_dir}")

    output_dir = Path(output_dir)
    map_data_file = output_dir / "map_data.json"
    progress_file = output_dir / "progress.json"

    try:
        # Load existing geocoded data
        geojson_data, geocoded_addresses = load_existing_geocoded_data(map_data_file)

        # Fetch CSV data from URL
        df = fetch_csv(url)

        # Clean addresses
        logger.info("Cleaning addresses...")
        df["cleaned_address"] = df["ADDRESS"].apply(clean_address)
        df = df.dropna(subset=["cleaned_address"])

        # Load existing progress
        processed_addresses = set()
        if progress_file.exists():
            try:
                with open(progress_file, "r") as f:
                    processed_addresses = set(json.load(f))
            except json.JSONDecodeError:
                logger.warning("Could not read progress file, starting fresh")

        # Initialize geocoder and results
        geocoder = GoogleGeocoder(api_key, max_workers=max_workers)
        failed_addresses = []

        # Create progress counter
        counter = ThreadSafeCounter()
        total_addresses = len(df)
        save_lock = Lock()  # Add lock for file saving
        geocoded_cache_lock = Lock()  # Add lock for geocoded addresses cache

        def process_chunk(chunk):
            results = []
            local_failed = []

            for _, row in chunk.iterrows():
                address = row["cleaned_address"]
                if address in processed_addresses:
                    continue

                # Check if address is already geocoded
                with geocoded_cache_lock:
                    existing_data = geocoded_addresses.get(address)

                if existing_data:
                    # Use existing geocoded data
                    results.append(existing_data["feature"])
                    count = counter.increment()
                    if count % 10 == 0:
                        logger.info(
                            f"Processed {count}/{total_addresses} addresses (cache hit)..."
                        )
                else:
                    # Geocode new address
                    address, location = geocoder.geocode_address(address)
                    count = counter.increment()

                    if count % 10 == 0:
                        logger.info(f"Processed {count}/{total_addresses} addresses...")

                    if location:
                        feature = {
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [
                                    location["longitude"],
                                    location["latitude"],
                                ],
                            },
                            "properties": {
                                "address": location["formatted_address"],
                                "original_address": address,
                                "precinct": row["PRECINCT"],
                                "ballot_style": row["BALLOT STYLE"],
                                "place_id": location["place_id"],
                            },
                        }
                        results.append(feature)

                        # Add to cache
                        with geocoded_cache_lock:
                            geocoded_addresses[address] = {
                                "location_data": location,
                                "feature": feature,
                            }
                    else:
                        local_failed.append(address)

            return results, local_failed

        # Split data into chunks for parallel processing
        chunk_size = max(1, len(df) // (max_workers * 4))
        chunks = [df[i : i + chunk_size] for i in range(0, len(df), chunk_size)]

        logger.info(f"Starting parallel geocoding with {max_workers} workers...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk = {
                executor.submit(process_chunk, chunk): i
                for i, chunk in enumerate(chunks)
            }

            for future in as_completed(future_to_chunk):
                chunk_results, chunk_failed = future.result()
                with save_lock:  # Use lock when updating shared data
                    # Only append new results (avoid duplicates)
                    existing_features = set(
                        f["properties"]["original_address"]
                        for f in geojson_data["features"]
                    )
                    new_features = [
                        f
                        for f in chunk_results
                        if f["properties"]["original_address"] not in existing_features
                    ]

                    geojson_data["features"].extend(new_features)
                    failed_addresses.extend(chunk_failed)
                    new_processed = processed_addresses.union(set(chunk_failed))

                    # Save intermediate results atomically
                    if new_features and save_json_file(
                        geojson_data, map_data_file, backup=False
                    ):
                        save_progress_atomic(list(new_processed), progress_file)
                        processed_addresses = new_processed

        # Save final results with backup
        if not save_json_file(geojson_data, map_data_file, backup=True):
            raise RuntimeError("Failed to save final results")

        # Save failed addresses
        if failed_addresses:
            try:
                with open(output_dir / "failed_addresses.txt", "w") as f:
                    for addr in failed_addresses:
                        f.write(f"{addr}\n")
            except Exception as e:
                logger.error(f"Error saving failed addresses: {str(e)}")

        # Save metadata
        metadata = {
            "last_updated": datetime.now().isoformat(),
            "source_url": url,
            "total_addresses": total_addresses,
            "successfully_geocoded": len(geojson_data["features"]),
            "failed_addresses": len(failed_addresses),
            "cache_hits": len(geocoded_addresses),
        }

        save_json_file(metadata, output_dir / "metadata.json", backup=False)

        logger.info("Processing complete:")
        logger.info(
            f"Successfully geocoded: {len(geojson_data['features'])}/{total_addresses}"
        )
        logger.info(f"Cache hits: {len(geocoded_addresses)}")
        logger.info(f"Failed addresses: {len(failed_addresses)}")

    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        raise


if __name__ == "__main__":
    # Replace with your CSV URL and Google API key
    CSV_URL = "http://localhost:8081/voters_test.csv"
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # Adjust max_workers based on your CPU and memory
    process_data(CSV_URL, GOOGLE_API_KEY, max_workers=4)

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

    # def clean_address(address):
    #     if pd.isna(address):
    #         return None
    #
    #     address = re.sub(r"[^a-zA-Z0-9\s,.]", " ", address)
    #
    #     replacements = {
    #         r"\bST\b": "STREET",
    #         r"\bAVE\b": "AVENUE",
    #         r"\bRD\b": "ROAD",
    #         r"\bDR\b": "DRIVE",
    #         r"\bLN\b": "LANE",
    #         r"\bCT\b": "COURT",
    #         r"\bAPT\b": "APARTMENT",
    #         r"\bN\b": "NORTH",
    #         r"\bS\b": "SOUTH",
    #         r"\bE\b": "EAST",
    #         r"\bW\b": "WEST",
    #         r"\bBLVD\b": "BOULEVARD",
    #         r"\bCIR\b": "CIRCLE",
    #     }
    #
    # for pattern, replacement in replacements.items():
    #     address = re.sub(pattern, replacement, address.upper())
    #
    # if "TX" not in address.upper():
    #     address = f"{address}, TEXAS"
    #
    # return " ".join(address.split())


def process_data(url, api_key, output_dir="public/data", max_workers=4):
    """
    Fetch and process CSV data with parallel geocoding using Google's API.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    try:
        # Fetch CSV data from URL
        df = fetch_csv(url)

        # Clean addresses
        # logger.info("Cleaning addresses...")
        # df["cleaned_address"] = df["ADDRESS"].apply(clean_address)
        # df = df.dropna(subset=["cleaned_address"])

        # Load existing progress
        progress_file = Path(output_dir) / "progress.json"
        processed_addresses = set()
        if progress_file.exists():
            with open(progress_file, "r") as f:
                processed_addresses = set(json.load(f))

        # Initialize geocoder and results
        geocoder = GoogleGeocoder(api_key, max_workers=max_workers)
        geojson_data = {"type": "FeatureCollection", "features": []}
        failed_addresses = []

        # Create progress counter
        counter = ThreadSafeCounter()
        total_addresses = len(df)

        def process_chunk(chunk):
            results = []
            local_failed = []

            for _, row in chunk.iterrows():
                address = row["ADDRESS"]
                if address in processed_addresses:
                    continue

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
                geojson_data["features"].extend(chunk_results)
                failed_addresses.extend(chunk_failed)

                # Save intermediate results
                with open(Path(output_dir) / "map_data.json", "w") as f:
                    json.dump(geojson_data, f)

                # Update progress
                with open(progress_file, "w") as f:
                    json.dump(list(processed_addresses.union(set(chunk_failed))), f)

        # Save final results
        with open(Path(output_dir) / "map_data.json", "w") as f:
            json.dump(geojson_data, f)

        # Save failed addresses
        if failed_addresses:
            with open(Path(output_dir) / "failed_addresses.txt", "w") as f:
                for addr in failed_addresses:
                    f.write(f"{addr}\n")

        # Save metadata
        metadata = {
            "last_updated": datetime.now().isoformat(),
            "source_url": url,
            "total_addresses": total_addresses,
            "successfully_geocoded": len(geojson_data["features"]),
            "failed_addresses": len(failed_addresses),
        }

        with open(Path(output_dir) / "metadata.json", "w") as f:
            json.dump(metadata, f)

        logger.info("Processing complete:")
        logger.info(
            f"Successfully geocoded: {len(geojson_data['features'])}/{total_addresses}"
        )
        logger.info(f"Failed addresses: {len(failed_addresses)}")

    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        raise


if __name__ == "__main__":
    # Replace with your CSV URL and Google API key
    CSV_URL = "https://www.hidalgocounty.us/DocumentCenter/View/68887/EV-Roster-November-5-2024-Cumulative"
    GOOGLE_API_KEY = "AIzaSyC0sJxE0fpGMzbaEsa4ocjv7kVJFtwlqrE"

    # Adjust max_workers based on your CPU and memory
    process_data(CSV_URL, GOOGLE_API_KEY, max_workers=4)

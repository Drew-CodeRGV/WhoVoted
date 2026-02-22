"""Geocoding service with Nominatim integration, caching, and rate limiting."""
import json
import time
import logging
import re
import requests
from pathlib import Path
from typing import Optional
from datetime import datetime

from config import Config

logger = logging.getLogger(__name__)

# Try to import boto3 for AWS Location Service (optional)
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    logger.info("boto3 not installed - AWS Location Service will be unavailable")

class GeocodingCache:
    """Persistent cache for geocoding results with thread-safe operations."""
    
    def __init__(self, cache_file: str):
        """
        Initialize geocoding cache.
        
        Args:
            cache_file: Path to JSON cache file
        """
        import threading
        self.cache_file = Path(cache_file)
        self.cache = self.load_cache()
        self.lock = threading.Lock()  # Thread-safe lock
    
    def load_cache(self) -> dict:
        """Load cache from JSON file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                logger.info(f"Loaded {len(cache)} entries from geocoding cache")
                return cache
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
                return {}
        return {}
    
    def save_cache(self):
        """Save cache to JSON file (must be called with lock held)."""
        try:
            # Ensure directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temp file first, then rename (atomic operation)
            temp_file = self.cache_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
            
            temp_file.replace(self.cache_file)
            logger.debug(f"Saved {len(self.cache)} entries to geocoding cache")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def normalize_address(self, address: str) -> str:
        """
        Normalize address for consistent cache keys.
        
        Args:
            address: Raw address string
        
        Returns:
            Normalized address string
        """
        if not address:
            return ""
        
        # Convert to uppercase
        normalized = address.upper()
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        # Standardize common abbreviations
        replacements = {
            r'\bST\b': 'STREET',
            r'\bAVE\b': 'AVENUE',
            r'\bRD\b': 'ROAD',
            r'\bDR\b': 'DRIVE',
            r'\bLN\b': 'LANE',
            r'\bCT\b': 'COURT',
            r'\bAPT\b': 'APARTMENT',
            r'\bN\b': 'NORTH',
            r'\bS\b': 'SOUTH',
            r'\bE\b': 'EAST',
            r'\bW\b': 'WEST',
            r'\bBLVD\b': 'BOULEVARD',
            r'\bCIR\b': 'CIRCLE',
            r'\bPKWY\b': 'PARKWAY',
            r'\bHWY\b': 'HIGHWAY',
            r'\bTX\b': 'TEXAS',  # Normalize TX to TEXAS for cache consistency
        }
        
        for pattern, replacement in replacements.items():
            normalized = re.sub(pattern, replacement, normalized)
        
        return normalized
    
    def get(self, address: str) -> Optional[dict]:
        """
        Retrieve cached geocoding result (thread-safe).
        
        Args:
            address: Address to look up
        
        Returns:
            Cached result dict or None if not found
        """
        normalized = self.normalize_address(address)
        with self.lock:
            # Try normalized version first (with TEXAS)
            result = self.cache.get(normalized)
            if result:
                return result
            
            # If not found, try with TX instead of TEXAS (for backward compatibility)
            normalized_tx = normalized.replace(' TEXAS ', ' TX ')
            result = self.cache.get(normalized_tx)
            if result:
                return result
            
            # Also try the original address as-is
            return self.cache.get(address)
    
    def set(self, address: str, result: dict):
        """
        Store geocoding result in cache (thread-safe).
        
        Args:
            address: Address that was geocoded
            result: Geocoding result dict with lat, lng, display_name
        """
        normalized = self.normalize_address(address)
        
        # Add metadata
        result['cached_at'] = datetime.now().isoformat()
        if 'source' not in result:
            result['source'] = 'unknown'
        
        with self.lock:
            self.cache[normalized] = result
            self.save_cache()
    
    def size(self) -> int:
        """Get number of entries in cache."""
        with self.lock:
            return len(self.cache)
    
    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.cache = {}
            self.save_cache()
            logger.info("Geocoding cache cleared")


class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, max_requests: int, period: float):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in period
            period: Time period in seconds
        """
        self.max_requests = max_requests
        self.period = period
        self.requests = []
    
    def wait(self):
        """Block until rate limit allows next request."""
        now = time.time()
        
        # Remove requests older than period
        self.requests = [r for r in self.requests if now - r < self.period]
        
        # If at limit, wait until oldest request expires
        if len(self.requests) >= self.max_requests:
            sleep_time = self.period - (now - self.requests[0])
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, waiting {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        # Record this request
        self.requests.append(time.time())


class CensusGeocoder:
    """Geocoder using US Census Bureau Geocoding API."""
    
    def __init__(self):
        """Initialize Census geocoder."""
        self.endpoint = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
        self.stats = {
            'api_calls': 0,
            'failures': 0
        }
    
    def geocode(self, address: str) -> Optional[dict]:
        """
        Geocode address using Census Bureau API.
        
        Args:
            address: Address to geocode
        
        Returns:
            Dict with lat, lng, display_name or None if failed
        """
        params = {
            'address': address,
            'benchmark': 'Public_AR_Current',
            'format': 'json'
        }
        
        try:
            self.stats['api_calls'] += 1
            logger.debug(f"Calling Census API for address: {address}")
            
            response = requests.get(
                self.endpoint,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Census API error {response.status_code}: {response.text}")
                self.stats['failures'] += 1
                return None
            
            data = response.json()
            
            # Check if we got results
            if data.get('result', {}).get('addressMatches'):
                match = data['result']['addressMatches'][0]
                coords = match['coordinates']
                
                return {
                    'lat': float(coords['y']),
                    'lng': float(coords['x']),
                    'display_name': match.get('matchedAddress', address),
                    'source': 'census'
                }
            else:
                logger.warning(f"Census API: No results found for address: {address}")
                self.stats['failures'] += 1
                return None
        
        except requests.exceptions.Timeout:
            logger.error(f"Census API timeout for address: {address}")
            self.stats['failures'] += 1
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Census API request error for address: {address} - {e}")
            self.stats['failures'] += 1
            return None
        except Exception as e:
            logger.error(f"Census API unexpected error for address: {address} - {e}")
            self.stats['failures'] += 1
            return None
    
    def get_stats(self) -> dict:
        """Get geocoding statistics."""
        return {
            'api_calls': self.stats['api_calls'],
            'failures': self.stats['failures']
        }


class AWSLocationGeocoder:
    """Geocoder using AWS Location Service (Esri/HERE data)."""
    
    def __init__(self, place_index: str = None, region: str = 'us-east-1'):
        """
        Initialize AWS Location Service geocoder.
        
        Args:
            place_index: Name of the Place Index in AWS Location Service
            region: AWS region (default: us-east-1)
        """
        self.place_index = place_index or (Config.AWS_LOCATION_PLACE_INDEX if hasattr(Config, 'AWS_LOCATION_PLACE_INDEX') else None)
        self.region = region
        self.stats = {
            'api_calls': 0,
            'failures': 0
        }
        
        if not HAS_BOTO3:
            logger.warning("boto3 not installed. Install with: pip install boto3")
            self.client = None
            return
        
        if not self.place_index:
            logger.warning("AWS Location Service Place Index not configured. Set AWS_LOCATION_PLACE_INDEX in config.")
            self.client = None
            return
        
        try:
            # Initialize AWS Location Service client with increased connection pool
            from botocore.config import Config as BotoConfig
            boto_config = BotoConfig(
                max_pool_connections=50  # Support up to 50 parallel connections
            )
            self.client = boto3.client('location', region_name=self.region, config=boto_config)
            logger.info(f"AWS Location Service initialized with Place Index: {self.place_index} (max 50 parallel connections)")
        except NoCredentialsError:
            logger.warning("AWS credentials not found. Configure AWS credentials to use Location Service.")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize AWS Location Service: {e}")
            self.client = None
    
    def geocode(self, address: str) -> Optional[dict]:
        """
        Geocode address using AWS Location Service.
        
        Args:
            address: Address to geocode
        
        Returns:
            Dict with lat, lng, display_name or None if failed
        """
        if not self.client:
            return None
        
        try:
            self.stats['api_calls'] += 1
            logger.debug(f"Calling AWS Location Service for address: {address}")
            
            response = self.client.search_place_index_for_text(
                IndexName=self.place_index,
                Text=address,
                MaxResults=1,
                FilterCountries=['USA']  # Limit to USA for better accuracy
            )
            
            # Check if we got results
            if response.get('Results'):
                result = response['Results'][0]
                place = result['Place']
                coords = place['Geometry']['Point']
                
                # Build display name from place components
                label = place.get('Label', address)
                
                return {
                    'lat': float(coords[1]),  # AWS returns [lng, lat]
                    'lng': float(coords[0]),
                    'display_name': label,
                    'source': 'aws_location',
                    'relevance': result.get('Relevance', 0)  # Confidence score
                }
            else:
                logger.warning(f"AWS Location Service: No results found for address: {address}")
                self.stats['failures'] += 1
                return None
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.error(f"AWS Location Service: Place Index '{self.place_index}' not found")
            else:
                logger.error(f"AWS Location Service error: {e}")
            self.stats['failures'] += 1
            return None
        except Exception as e:
            logger.error(f"AWS Location Service unexpected error for address: {address} - {e}")
            self.stats['failures'] += 1
            return None
    
    def get_stats(self) -> dict:
        """Get geocoding statistics."""
        return {
            'api_calls': self.stats['api_calls'],
            'failures': self.stats['failures']
        }


class PhotonGeocoder:
    """Geocoder using Photon API (OpenStreetMap-based, free, unlimited)."""
    
    def __init__(self):
        """Initialize Photon geocoder."""
        self.endpoint = "https://photon.komoot.io/api/"
        self.stats = {
            'api_calls': 0,
            'failures': 0
        }
    
    def geocode(self, address: str) -> Optional[dict]:
        """
        Geocode address using Photon API.
        
        Args:
            address: Address to geocode
        
        Returns:
            Dict with lat, lng, display_name or None if failed
        """
        params = {
            'q': address,
            'limit': 1,
            'osm_tag': 'place:house',  # Prefer house-level results
            'layer': 'house'  # Focus on building/house layer
        }
        
        try:
            self.stats['api_calls'] += 1
            logger.debug(f"Calling Photon API for address: {address}")
            
            response = requests.get(
                self.endpoint,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Photon API error {response.status_code}: {response.text}")
                self.stats['failures'] += 1
                return None
            
            data = response.json()
            
            # Check if we got results
            if data.get('features'):
                feature = data['features'][0]
                coords = feature['geometry']['coordinates']
                props = feature.get('properties', {})
                
                # Build display name from properties
                name_parts = []
                if props.get('housenumber'):
                    name_parts.append(props['housenumber'])
                if props.get('street'):
                    name_parts.append(props['street'])
                if props.get('city'):
                    name_parts.append(props['city'])
                if props.get('state'):
                    name_parts.append(props['state'])
                if props.get('postcode'):
                    name_parts.append(props['postcode'])
                
                display_name = ', '.join(name_parts) if name_parts else props.get('name', address)
                
                return {
                    'lat': float(coords[1]),
                    'lng': float(coords[0]),
                    'display_name': display_name,
                    'source': 'photon'
                }
            else:
                logger.warning(f"Photon API: No results found for address: {address}")
                self.stats['failures'] += 1
                return None
        
        except requests.exceptions.Timeout:
            logger.error(f"Photon API timeout for address: {address}")
            self.stats['failures'] += 1
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Photon API request error for address: {address} - {e}")
            self.stats['failures'] += 1
            return None
        except Exception as e:
            logger.error(f"Photon API unexpected error for address: {address} - {e}")
            self.stats['failures'] += 1
            return None
    
    def get_stats(self) -> dict:
        """Get geocoding statistics."""
        return {
            'api_calls': self.stats['api_calls'],
            'failures': self.stats['failures']
        }


class BingMapsGeocoder:
    """Geocoder using Bing Maps Location API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Bing Maps geocoder.
        
        Args:
            api_key: Bing Maps API key (optional, will use from config if not provided)
        """
        self.api_key = api_key or Config.BING_MAPS_API_KEY if hasattr(Config, 'BING_MAPS_API_KEY') else None
        self.endpoint = "http://dev.virtualearth.net/REST/v1/Locations"
        self.stats = {
            'api_calls': 0,
            'failures': 0
        }
        
        if not self.api_key:
            logger.warning("Bing Maps API key not configured. Bing geocoding will be skipped.")
    
    def geocode(self, address: str) -> Optional[dict]:
        """
        Geocode address using Bing Maps API.
        
        Args:
            address: Address to geocode
        
        Returns:
            Dict with lat, lng, display_name or None if failed
        """
        if not self.api_key:
            return None
        
        params = {
            'query': address,
            'key': self.api_key,
            'maxResults': 1
        }
        
        try:
            self.stats['api_calls'] += 1
            logger.debug(f"Calling Bing Maps API for address: {address}")
            
            response = requests.get(
                self.endpoint,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Bing Maps API error {response.status_code}: {response.text}")
                self.stats['failures'] += 1
                return None
            
            data = response.json()
            
            # Check if we got results
            if data.get('resourceSets') and data['resourceSets'][0].get('resources'):
                resource = data['resourceSets'][0]['resources'][0]
                coords = resource['point']['coordinates']
                
                return {
                    'lat': float(coords[0]),
                    'lng': float(coords[1]),
                    'display_name': resource.get('name', address),
                    'source': 'bing'
                }
            else:
                logger.warning(f"Bing Maps API: No results found for address: {address}")
                self.stats['failures'] += 1
                return None
        
        except requests.exceptions.Timeout:
            logger.error(f"Bing Maps API timeout for address: {address}")
            self.stats['failures'] += 1
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Bing Maps API request error for address: {address} - {e}")
            self.stats['failures'] += 1
            return None
        except Exception as e:
            logger.error(f"Bing Maps API unexpected error for address: {address} - {e}")
            self.stats['failures'] += 1
            return None
    
    def get_stats(self) -> dict:
        """Get geocoding statistics."""
        return {
            'api_calls': self.stats['api_calls'],
            'failures': self.stats['failures']
        }

    class PhotonGeocoder:
        """Geocoder using Photon API (OpenStreetMap-based, free, unlimited)."""

        def __init__(self):
            """Initialize Photon geocoder."""
            self.endpoint = "https://photon.komoot.io/api/"
            self.stats = {
                'api_calls': 0,
                'failures': 0
            }

        def geocode(self, address: str) -> Optional[dict]:
            """
            Geocode address using Photon API.

            Args:
                address: Address to geocode

            Returns:
                Dict with lat, lng, display_name or None if failed
            """
            params = {
                'q': address,
                'limit': 1,
                'osm_tag': 'place:house',  # Prefer house-level results
                'layer': 'house'  # Focus on building/house layer
            }

            try:
                self.stats['api_calls'] += 1
                logger.debug(f"Calling Photon API for address: {address}")

                response = requests.get(
                    self.endpoint,
                    params=params,
                    timeout=10
                )

                if response.status_code != 200:
                    logger.error(f"Photon API error {response.status_code}: {response.text}")
                    self.stats['failures'] += 1
                    return None

                data = response.json()

                # Check if we got results
                if data.get('features'):
                    feature = data['features'][0]
                    coords = feature['geometry']['coordinates']
                    props = feature.get('properties', {})

                    # Build display name from properties
                    name_parts = []
                    if props.get('housenumber'):
                        name_parts.append(props['housenumber'])
                    if props.get('street'):
                        name_parts.append(props['street'])
                    if props.get('city'):
                        name_parts.append(props['city'])
                    if props.get('state'):
                        name_parts.append(props['state'])
                    if props.get('postcode'):
                        name_parts.append(props['postcode'])

                    display_name = ', '.join(name_parts) if name_parts else props.get('name', address)

                    return {
                        'lat': float(coords[1]),
                        'lng': float(coords[0]),
                        'display_name': display_name,
                        'source': 'photon'
                    }
                else:
                    logger.warning(f"Photon API: No results found for address: {address}")
                    self.stats['failures'] += 1
                    return None

            except requests.exceptions.Timeout:
                logger.error(f"Photon API timeout for address: {address}")
                self.stats['failures'] += 1
                return None
            except requests.exceptions.RequestException as e:
                logger.error(f"Photon API request error for address: {address} - {e}")
                self.stats['failures'] += 1
                return None
            except Exception as e:
                logger.error(f"Photon API unexpected error for address: {address} - {e}")
                self.stats['failures'] += 1
                return None

        def get_stats(self) -> dict:
            """Get geocoding statistics."""
            return {
                'api_calls': self.stats['api_calls'],
                'failures': self.stats['failures']
            }


class NominatimGeocoder:
    """Multi-provider geocoder with fallback chain: Cache → AWS Location → Census → Photon → Nominatim."""
    
    def __init__(self, cache: GeocodingCache, bing_api_key: Optional[str] = None, 
                 aws_place_index: Optional[str] = None, aws_region: str = 'us-east-1'):
        """
        Initialize multi-provider geocoder.
        
        Args:
            cache: GeocodingCache instance
            bing_api_key: Optional Bing Maps API key (deprecated, kept for compatibility)
            aws_place_index: Optional AWS Location Service Place Index name
            aws_region: AWS region for Location Service (default: us-east-1)
        """
        self.cache = cache
        self.aws_geocoder = AWSLocationGeocoder(aws_place_index, aws_region)
        self.census_geocoder = CensusGeocoder()
        self.photon_geocoder = PhotonGeocoder()
        self.bing_geocoder = BingMapsGeocoder(bing_api_key)
        self.rate_limiter = RateLimiter(
            max_requests=int(Config.NOMINATIM_RATE_LIMIT),
            period=1.0
        )
        self.endpoint = f"{Config.NOMINATIM_ENDPOINT}/search"
        self.user_agent = Config.NOMINATIM_USER_AGENT
        self.stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'failures': 0,
            'aws_success': 0,
            'census_success': 0,
            'photon_success': 0,
            'bing_success': 0,
            'nominatim_success': 0,
            'zip_fallback_success': 0
        }
    
    def geocode(self, address: str) -> Optional[dict]:
        """
        Geocode address with multi-provider fallback chain.
        
        Fallback order:
        1. Cache (persistent across deletions)
        2. AWS Location Service (if configured - Esri/HERE data, excellent accuracy, NO RATE LIMIT)
        3. US Census Bureau (free, NO RATE LIMIT, good US coverage)
        4. Photon (free, unlimited, OpenStreetMap-based, good for addresses, NO RATE LIMIT)
        5. Nominatim (OpenStreetMap, RATE LIMITED to 1 req/sec)
        6. ZIP code fallback (try with just ZIP if address fails)
        
        Args:
            address: Address to geocode
        
        Returns:
            Dict with lat, lng, display_name, source or None if all providers failed
        """
        # 1. Check cache first (persistent across deletions)
        cached = self.cache.get(address)
        if cached:
            self.stats['cache_hits'] += 1
            logger.debug(f"Cache hit for address: {address} (source: {cached.get('source', 'unknown')})")
            return cached
        
        result = None
        
        # 2. Try AWS Location Service first (if configured - best accuracy, NO RATE LIMIT)
        if self.aws_geocoder.client:
            result = self.aws_geocoder.geocode(address)
            if result:
                self.stats['aws_success'] += 1
                logger.info(f"AWS Location Service success for: {address}")
                self.cache.set(address, result)
                return result
        
        # 3. Try Census geocoder (free, NO RATE LIMIT, best for US addresses)
        result = self.census_geocoder.geocode(address)
        if result:
            self.stats['census_success'] += 1
            logger.info(f"Census geocoder success for: {address}")
            self.cache.set(address, result)
            return result
        
        # 4. Try Photon geocoder (free, unlimited, NO RATE LIMIT, good for street-level)
        result = self.photon_geocoder.geocode(address)
        if result:
            self.stats['photon_success'] += 1
            logger.info(f"Photon geocoder success for: {address}")
            self.cache.set(address, result)
            return result
        
        # 5. Try Nominatim (RATE LIMITED - only apply rate limiting here)
        self.rate_limiter.wait()
        result = self._call_nominatim(address)
        if result:
            self.stats['nominatim_success'] += 1
            result['source'] = 'nominatim'
            self.cache.set(address, result)
            return result
        
        # 6. ZIP code fallback - try all providers with just ZIP (NO RATE LIMIT for AWS/Census/Photon)
        zip_match = re.search(r'\b(\d{5})\b', address)
        if zip_match:
            zip_code = zip_match.group(1)
            logger.info(f"Trying ZIP code fallback for: {address}")
            zip_address = f"{zip_code}, Texas, USA"
            
            # Try AWS with ZIP first (NO RATE LIMIT)
            if self.aws_geocoder.client:
                result = self.aws_geocoder.geocode(zip_address)
            
            # Try Census with ZIP (NO RATE LIMIT)
            if not result:
                result = self.census_geocoder.geocode(zip_address)
            
            # Try Photon with ZIP (NO RATE LIMIT)
            if not result:
                result = self.photon_geocoder.geocode(zip_address)
            
            # Try Nominatim with ZIP (RATE LIMITED - only apply rate limiting here)
            if not result:
                self.rate_limiter.wait()
                result = self._call_nominatim(zip_address)
                if result:
                    result['source'] = 'nominatim'
            
            if result:
                self.stats['zip_fallback_success'] += 1
                result['fallback'] = 'zip_code'
                result['original_address'] = address
                self.cache.set(address, result)
                return result
        
        # All providers failed
        self.stats['failures'] += 1
        logger.error(f"All geocoding providers failed for address: {address}")
        return None
    
    def _call_nominatim(self, address: str, retry_count: int = 0) -> Optional[dict]:
        """
        Make HTTP request to Nominatim API.
        
        Args:
            address: Address to geocode
            retry_count: Current retry attempt number
        
        Returns:
            Dict with lat, lng, display_name or None if failed
        """
        params = {
            'q': address,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'us'
        }
        headers = {'User-Agent': self.user_agent}
        
        try:
            self.stats['api_calls'] += 1
            logger.debug(f"Calling Nominatim API for address: {address}")
            
            response = requests.get(
                self.endpoint,
                params=params,
                headers=headers,
                timeout=10
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                if retry_count < 3:
                    wait_time = (2 ** retry_count) * 2  # Exponential backoff: 2s, 4s, 8s
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                    return self._call_nominatim(address, retry_count + 1)
                else:
                    logger.error(f"Rate limit exceeded after {retry_count} retries")
                    return None
            
            # Handle other errors
            if response.status_code != 200:
                logger.error(f"Nominatim API error {response.status_code}: {response.text}")
                return None
            
            results = response.json()
            
            if results:
                result = results[0]
                return {
                    'lat': float(result['lat']),
                    'lng': float(result['lon']),
                    'display_name': result['display_name']
                }
            else:
                logger.warning(f"No results found for address: {address}")
                return None
        
        except requests.exceptions.Timeout:
            logger.error(f"Timeout geocoding address: {address}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error geocoding address: {address} - {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error geocoding address: {address} - {e}")
            return None
    
    def get_stats(self) -> dict:
        """Get geocoding statistics from all providers."""
        total_requests = self.stats['api_calls'] + self.stats['cache_hits']
        cache_hit_rate = (
            self.stats['cache_hits'] / total_requests
            if total_requests > 0 else 0
        )
        
        stats = {
            'total_requests': total_requests,
            'api_calls': self.stats['api_calls'],
            'cache_hits': self.stats['cache_hits'],
            'cache_hit_rate': round(cache_hit_rate, 3),
            'failures': self.stats['failures'],
            'cache_size': self.cache.size(),
            'nominatim_success': self.stats['nominatim_success'],
            'zip_fallback_success': self.stats['zip_fallback_success']
        }
        
        # Add AWS Location Service stats if configured
        if self.aws_geocoder.client:
            aws_stats = self.aws_geocoder.get_stats()
            stats['aws_success'] = self.stats['aws_success']
            stats['aws_api_calls'] = aws_stats['api_calls']
            stats['aws_failures'] = aws_stats['failures']
        
        # Add Census stats
        census_stats = self.census_geocoder.get_stats()
        stats['census_success'] = self.stats['census_success']
        stats['census_api_calls'] = census_stats['api_calls']
        stats['census_failures'] = census_stats['failures']
        
        # Add Photon stats
        photon_stats = self.photon_geocoder.get_stats()
        stats['photon_success'] = self.stats['photon_success']
        stats['photon_api_calls'] = photon_stats['api_calls']
        stats['photon_failures'] = photon_stats['failures']
        
        # Add Bing stats if configured (kept for compatibility)
        if self.bing_geocoder.api_key:
            bing_stats = self.bing_geocoder.get_stats()
            stats['bing_success'] = self.stats['bing_success']
            stats['bing_api_calls'] = bing_stats['api_calls']
            stats['bing_failures'] = bing_stats['failures']
        
        return stats

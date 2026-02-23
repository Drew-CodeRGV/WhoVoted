// Map initialization and management
let map, markerClusterGroup, heatmapLayer, heatmapLayerDemocratic, heatmapLayerRepublican, flippedHeatmapLayer;
let yearLayers = {}; // Store layers by year
let activeYears = new Set(); // Track which years are active
let precinctBoundariesLayer = null; // Precinct boundaries layer
let precinctLabelsLayer = null; // Precinct number labels layer
let countyOutlinesLayer = null; // County outlines layer (separate from precincts)
let pollingPlacesLayer = null; // Polling places layer
let layerControlPanel = null; // Layer control panel instance
let datasetSelector = null; // Dataset selector instance
let partyFilter = null; // Party filter instance
let flippedVotersFilter = 'none'; // Track flipped voters filter: 'none', 'to-blue', 'to-red'

function initMap() {
    // Initialize Leaflet map with OpenStreetMap tiles and Canvas renderer for performance
    map = L.map('map', {
        renderer: L.canvas({ 
            tolerance: 5,
            padding: 0.1
        }),
        preferCanvas: true
    }).setView(config.MAP_CENTER, config.MAP_ZOOM);
    
    // Add CartoDB Positron tile layer (cleaner, less cluttered than default OSM)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors, © CARTO',
        subdomains: 'abcd'
    }).addTo(map);
    
    // Initialize marker cluster group with optimized settings
    markerClusterGroup = L.markerClusterGroup({
        disableClusteringAtZoom: 17,
        spiderfyOnMaxZoom: true,
        maxClusterRadius: 50,
        showCoverageOnHover: false,
        chunkedLoading: true,        // Load markers in chunks for better performance
        chunkInterval: 200,           // Milliseconds between chunk loads
        chunkDelay: 50                // Delay before starting chunk loading
    });
    
    // Initialize heatmap layers
    // Traditional heatmap (single color)
    heatmapLayer = L.heatLayer([], {
        radius: 25,
        blur: 35,
        maxZoom: config.HEATMAP_MAX_ZOOM,
        max: 1.0,
        minOpacity: 0.3,
        maxOpacity: 0.8
    });
    
    // Party-colored heatmaps
    heatmapLayerDemocratic = L.heatLayer([], {
        radius: 25,
        blur: 35,
        maxZoom: config.HEATMAP_MAX_ZOOM,
        max: 1.0,
        minOpacity: 0.3,
        maxOpacity: 0.8,
        gradient: {
            0.0: 'rgba(30, 144, 255, 0)',      // Transparent blue
            0.2: 'rgba(30, 144, 255, 0.3)',    // Light blue
            0.5: 'rgba(30, 144, 255, 0.6)',    // Medium blue
            0.8: 'rgba(30, 144, 255, 0.8)',    // Strong blue
            1.0: 'rgba(30, 144, 255, 1.0)'     // Full blue
        }
    });
    
    heatmapLayerRepublican = L.heatLayer([], {
        radius: 25,
        blur: 35,
        maxZoom: config.HEATMAP_MAX_ZOOM,
        max: 1.0,
        minOpacity: 0.3,
        maxOpacity: 0.8,
        gradient: {
            0.0: 'rgba(220, 20, 60, 0)',       // Transparent red
            0.2: 'rgba(220, 20, 60, 0.3)',     // Light red
            0.5: 'rgba(220, 20, 60, 0.6)',     // Medium red
            0.8: 'rgba(220, 20, 60, 0.8)',     // Strong red
            1.0: 'rgba(220, 20, 60, 1.0)'      // Full red
        }
    });
    
    // Flipped voters heatmap layer
    flippedHeatmapLayer = L.heatLayer([], {
        radius: 25,
        blur: 35,
        maxZoom: config.HEATMAP_MAX_ZOOM,
        max: 1.0,
        minOpacity: 0.3,
        maxOpacity: 0.8,
        gradient: { 0.4: '#9370DB', 0.65: '#9370DB', 1: '#9370DB' }
    });

    // Track which heatmap mode is active
    window.heatmapMode = 'traditional'; // 'traditional' or 'party'
    
    // Set willReadFrequently on the canvas for better performance
    // This needs to be done after the layer is added to the map
    map.on('layeradd', function(e) {
        if (e.layer === heatmapLayer) {
            const canvas = heatmapLayer._canvas;
            if (canvas) {
                const ctx = canvas.getContext('2d', { willReadFrequently: true });
            }
        }
    });
    
    // Add geolocation control
    addGeolocationControl();
    
    // Initialize layer control - DISABLED (using dataset selector instead)
    // initLayerControl();
    
    // Load precinct boundaries and polling places
    loadAdditionalLayers();
    
    // Initialize dataset selector and party filter
    initializeDatasetControls();
    
    // Load data
    loadMapData();
}

async function loadAdditionalLayers() {
    try {
        console.log('Loading additional layers...');
        
        // Load precinct boundaries
        precinctBoundariesLayer = await loadPrecinctBoundaries();
        console.log('Precinct boundaries loaded:', precinctBoundariesLayer ? 'success' : 'failed');
        
        // Load county outlines (separate layer)
        countyOutlinesLayer = await loadCountyOutlines();
        console.log('County outlines loaded:', countyOutlinesLayer ? 'success' : 'failed');
        
        // Load polling places
        pollingPlacesLayer = await loadPollingPlaces();
        console.log('Polling places loaded:', pollingPlacesLayer ? 'success' : 'failed');
        
        // Initialize layer control panel with all layers
        const layers = {
            voterMarkers: markerClusterGroup,
            heatmap: heatmapLayer,
            precincts: precinctBoundariesLayer,
            pollingPlaces: pollingPlacesLayer
        };
        
        console.log('Initializing LayerControlPanel with layers:', Object.keys(layers));
        layerControlPanel = new LayerControlPanel(map, layers);
        
        // Initialize color legend
        console.log('Initializing ColorLegend');
        new ColorLegend();
        
    } catch (error) {
        console.error('Error loading additional layers:', error);
    }
}

function addGeolocationControl() {
    const geolocationButton = document.getElementById('geolocation-button');
    if (geolocationButton) {
        geolocationButton.addEventListener('click', centerMapOnUserLocation);
    }
}

function centerMapOnUserLocation() {
    if ("geolocation" in navigator) {
        const geolocationButton = document.getElementById('geolocation-button');
        geolocationButton.classList.add('loading');
        geolocationButton.disabled = true;

        navigator.geolocation.getCurrentPosition(function(position) {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            map.setView([lat, lng], 16);

            const userLocationMarker = L.marker([lat, lng], {
                icon: L.divIcon({
                    className: 'user-location-marker',
                    html: '<div style="background-color: #4285F4; width: 16px; height: 16px; border-radius: 50%; border: 3px solid white;"></div>',
                    iconSize: [22, 22],
                    iconAnchor: [11, 11]
                })
            }).addTo(map);

            userLocationMarker.bindPopup("You are here").openPopup();

            // Reverse geocode to get address
            reverseGeocode(lat, lng);

            geolocationButton.classList.remove('loading');
            geolocationButton.disabled = false;
        }, function(error) {
            console.error("Error getting user location:", error);
            alert("Unable to get your location. Please make sure you've granted permission to access your location.");

            geolocationButton.classList.remove('loading');
            geolocationButton.disabled = false;
        }, {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        });
    } else {
        alert("Geolocation is not supported by your browser.");
    }
}

function updateMapView() {
    const currentZoom = map.getZoom();
    console.log('updateMapView called, zoom:', currentZoom, 'threshold:', config.HEATMAP_MAX_ZOOM);
    console.log('Current heatmap mode:', window.heatmapMode);
    
    // Get current party filter
    const datasetManager = getDatasetManager();
    const partyFilter = datasetManager.getPartyFilter();
    console.log('Current party filter:', partyFilter);
    
    if (currentZoom > config.HEATMAP_MAX_ZOOM) {
        // Show markers at high zoom
        // Remove all heatmap layers
        if (map.hasLayer(heatmapLayer)) {
            map.removeLayer(heatmapLayer);
        }
        if (map.hasLayer(heatmapLayerDemocratic)) {
            map.removeLayer(heatmapLayerDemocratic);
        }
        if (map.hasLayer(heatmapLayerRepublican)) {
            map.removeLayer(heatmapLayerRepublican);
        }
        if (flippedHeatmapLayer && map.hasLayer(flippedHeatmapLayer)) {
            map.removeLayer(flippedHeatmapLayer);
        }
        
        if (!map.hasLayer(markerClusterGroup)) {
            map.addLayer(markerClusterGroup);
        }
        console.log('Showing markers, cluster has', markerClusterGroup.getLayers().length, 'markers');
    } else {
        // Flipped voters mode: show flipped heatmap at low zoom
        if (flippedVotersFilter !== 'none') {
            // Remove all standard heatmap layers
            if (map.hasLayer(heatmapLayer)) {
                map.removeLayer(heatmapLayer);
            }
            if (map.hasLayer(heatmapLayerDemocratic)) {
                map.removeLayer(heatmapLayerDemocratic);
            }
            if (map.hasLayer(heatmapLayerRepublican)) {
                map.removeLayer(heatmapLayerRepublican);
            }
            
            // Remove markers at low zoom
            if (map.hasLayer(markerClusterGroup)) {
                map.removeLayer(markerClusterGroup);
            }
            
            // Show flipped heatmap layer
            if (flippedHeatmapLayer && !map.hasLayer(flippedHeatmapLayer)) {
                map.addLayer(flippedHeatmapLayer);
            }
            console.log('Flipped voters mode: showing flipped heatmap');
            return;
        }
        
        // Ensure flipped heatmap is removed when not in flipped mode
        if (flippedHeatmapLayer && map.hasLayer(flippedHeatmapLayer)) {
            map.removeLayer(flippedHeatmapLayer);
        }
        
        // Show heatmap at low zoom
        if (map.hasLayer(markerClusterGroup)) {
            map.removeLayer(markerClusterGroup);
        }
        
        // Show appropriate heatmap based on mode
        if (window.heatmapMode === 'party') {
            // Party-colored heatmaps
            if (map.hasLayer(heatmapLayer)) {
                map.removeLayer(heatmapLayer);
            }
            
            // Show heatmaps based on party filter
            if (partyFilter === 'all' || !partyFilter) {
                // Show both party heatmaps
                if (!map.hasLayer(heatmapLayerDemocratic)) {
                    map.addLayer(heatmapLayerDemocratic);
                    console.log('Added Democratic heatmap layer to map');
                }
                if (!map.hasLayer(heatmapLayerRepublican)) {
                    map.addLayer(heatmapLayerRepublican);
                    console.log('Added Republican heatmap layer to map');
                }
                console.log('Showing both party-colored heatmaps');
            } else if (partyFilter === 'democratic') {
                // Show only Democratic heatmap
                if (map.hasLayer(heatmapLayerRepublican)) {
                    map.removeLayer(heatmapLayerRepublican);
                    console.log('Removed Republican heatmap layer from map');
                }
                if (!map.hasLayer(heatmapLayerDemocratic)) {
                    map.addLayer(heatmapLayerDemocratic);
                    console.log('Added Democratic heatmap layer to map');
                }
                console.log('Showing Democratic heatmap only');
            } else if (partyFilter === 'republican') {
                // Show only Republican heatmap
                if (map.hasLayer(heatmapLayerDemocratic)) {
                    map.removeLayer(heatmapLayerDemocratic);
                    console.log('Removed Democratic heatmap layer from map');
                }
                if (!map.hasLayer(heatmapLayerRepublican)) {
                    map.addLayer(heatmapLayerRepublican);
                    console.log('Added Republican heatmap layer to map');
                }
                console.log('Showing Republican heatmap only');
            }
        } else {
            // Traditional heatmap
            if (map.hasLayer(heatmapLayerDemocratic)) {
                map.removeLayer(heatmapLayerDemocratic);
            }
            if (map.hasLayer(heatmapLayerRepublican)) {
                map.removeLayer(heatmapLayerRepublican);
            }
            if (!map.hasLayer(heatmapLayer)) {
                map.addLayer(heatmapLayer);
            }
            const heatmapPoints = heatmapLayer._latlngs || [];
            console.log('Showing traditional heatmap, has', heatmapPoints.length, 'points');
        }
    }
}

function addCustomMarker(latlng) {
    const customPinIcon = L.divIcon({
        className: 'custom-pin-icon',
        html: `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#007bff">
                <path d="M12 0C7.31 0 3.5 3.81 3.5 8.5C3.5 14.88 12 24 12 24S20.5 14.88 20.5 8.5C20.5 3.81 16.69 0 12 0ZM12 13C9.79 13 8 11.21 8 9C8 6.79 9.79 5 12 5C14.21 5 16 6.79 16 9C16 11.21 14.21 13 12 13Z"/>
            </svg>
        `,
        iconSize: [40, 40],
        iconAnchor: [20, 40],
        popupAnchor: [0, -40]
    });

    return L.marker(latlng, { icon: customPinIcon }).addTo(map);
}

/**
 * Initialize dataset selector and party filter controls
 * Creates instances and sets up callbacks for dataset changes
 */
async function initializeDatasetControls() {
    try {
        console.log('Initializing dataset controls...');
        
        // Get the DatasetManager instance
        const datasetManager = getDatasetManager();
        
        // Create DatasetSelector instance with onDatasetChange callback
        datasetSelector = new DatasetSelector(map, async (dataset, datasetIndex) => {
            console.log('Dataset changed:', dataset);
            
            // Update DatasetManager state
            datasetManager.setCurrentDataset(dataset);
            datasetManager.setSelectedDatasetIndex(datasetIndex);
            datasetManager.saveState();
            
            // Show loading indicator
            const loadingIndicator = document.getElementById('map-loading-indicator');
            if (loadingIndicator) {
                loadingIndicator.style.display = 'flex';
            }
            
            // Clear existing map markers
            if (markerClusterGroup) {
                markerClusterGroup.clearLayers();
            }
            // Clear heatmap layers - remove from map first to avoid errors
            if (heatmapLayer && map.hasLayer(heatmapLayer)) {
                map.removeLayer(heatmapLayer);
            }
            if (heatmapLayerDemocratic && map.hasLayer(heatmapLayerDemocratic)) {
                map.removeLayer(heatmapLayerDemocratic);
            }
            if (heatmapLayerRepublican && map.hasLayer(heatmapLayerRepublican)) {
                map.removeLayer(heatmapLayerRepublican);
            }
            
            // Load new dataset
            try {
                await loadDataset(dataset);
                
                // Initialize time-lapse if early vote dataset
                if (typeof initTimeLapse === 'function' && datasetSelector.datasets) {
                    await initTimeLapse(dataset, datasetSelector.datasets);
                }
                
                // Update party filter visibility based on election type
                if (partyFilter) {
                    const isPrimary = datasetManager.isPrimaryElection();
                    partyFilter.setVisible(isPrimary);
                    
                    // If it's a primary election, apply the saved filter
                    if (isPrimary) {
                        const currentFilter = datasetManager.getPartyFilter();
                        // Trigger filter application by calling the filter change handler
                        if (currentFilter !== 'all') {
                            partyFilter.handleFilterChange(currentFilter);
                        }
                    }
                }
            } catch (error) {
                console.error('Error loading dataset:', error);
            } finally {
                // Hide loading indicator
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
            }
        });
        
        // Initialize DatasetSelector (loads datasets and restores selection)
        await datasetSelector.initialize();
        
        // Create PartyFilter instance with onFilterChange callback
        partyFilter = new PartyFilter(map, (filterValue) => {
            console.log('Party filter changed:', filterValue);
            
            // Update DatasetManager state
            datasetManager.setPartyFilter(filterValue);
            datasetManager.saveState();
            
            // Re-filter the current data WITHOUT reloading
            // The data is already loaded in window.mapData
            if (window.mapData && window.mapData.features) {
                initializeDataLayers();
            }
        });
        
        // Initialize PartyFilter (restores saved filter)
        partyFilter.initialize();
        
        console.log('Dataset controls initialized successfully');
        
    } catch (error) {
        console.error('Error initializing dataset controls:', error);
    }
}

// Initialize map when DOM is loaded
document.addEventListener('DOMContentLoaded', initMap);

// ============================================================================
// PERFORMANCE UTILITIES
// ============================================================================

/**
 * Debounce function to limit how often a function can fire
 * @param {Function} func - Function to debounce
 * @param {number} wait - Milliseconds to wait
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Viewport culling - only render markers within visible bounds
 * @param {Array} allMarkers - All marker data
 * @param {L.LatLngBounds} bounds - Current map bounds
 * @returns {Array} Filtered markers within bounds
 */
function cullMarkersToViewport(allMarkers, bounds) {
    return allMarkers.filter(marker => {
        if (!marker.lat || !marker.lng) return false;
        return bounds.contains([marker.lat, marker.lng]);
    });
}

/**
 * Lazy loads marker data in chunks for better performance
 * @param {Array} markers - Array of marker data
 * @param {number} chunkSize - Number of markers per chunk
 * @param {Function} processChunk - Function to process each chunk
 */
async function lazyLoadMarkers(markers, chunkSize, processChunk) {
    for (let i = 0; i < markers.length; i += chunkSize) {
        const chunk = markers.slice(i, i + chunkSize);
        await processChunk(chunk);
        
        // Allow UI to update between chunks
        await new Promise(resolve => setTimeout(resolve, 10));
    }
}

// ============================================================================
// PARTY AFFILIATION VISUALIZATION SYSTEM
// ============================================================================

/**
 * Determines the marker color based on voter's party affiliation and voting history
 * @param {Object} voterData - Voter data object containing party affiliation and history
 * @returns {string} Color code: 'red', 'blue', 'purple', 'maroon', 'green'
 */
function determineMarkerColor(voterData) {
    // Handle missing or incomplete data
    if (!voterData || !voterData.party_affiliation_current) {
        return 'green'; // Unknown affiliation
    }

    const currentParty = voterData.party_affiliation_current.toLowerCase();
    
    // Check for party flip if flipped voters filter is active
    if (flippedVotersFilter !== 'none' && voterData.party_affiliation_previous) {
        const previousParty = voterData.party_affiliation_previous.toLowerCase();
        
        const isCurrentRep = currentParty.includes('republican') || currentParty.includes('rep');
        const isCurrentDem = currentParty.includes('democrat') || currentParty.includes('dem');
        const isPreviousRep = previousParty.includes('republican') || previousParty.includes('rep');
        const isPreviousDem = previousParty.includes('democrat') || previousParty.includes('dem');
        
        // Red to Blue (Republican to Democratic) = Purple
        if (isPreviousRep && isCurrentDem) {
            // If filtering for "to-red" only, skip this voter
            if (flippedVotersFilter === 'to-red') {
                return null; // Skip this voter
            }
            return 'purple';
        }
        
        // Blue to Red (Democratic to Republican) = Maroon
        if (isPreviousDem && isCurrentRep) {
            // If filtering for "to-blue" only, skip this voter
            if (flippedVotersFilter === 'to-blue') {
                return null; // Skip this voter
            }
            return 'maroon';
        }
        
        // If flipped voters filter is active but voter didn't flip, skip them
        if (flippedVotersFilter !== 'none') {
            return null; // Skip non-flipped voters when filter is active
        }
    } else if (flippedVotersFilter !== 'none') {
        // If flipped voters filter is active but no previous party data, skip this voter
        return null;
    }

    // Republican - red
    if (currentParty.includes('republican') || currentParty.includes('rep')) {
        return 'red';
    }

    // Democratic - blue
    if (currentParty.includes('democrat') || currentParty.includes('dem')) {
        return 'blue';
    }

    // Unknown or other party
    return 'green';
}


/**
 * Determines the marker style based on whether voter has voted and registration status
 * @param {Object} voterData - Voter data object containing voting and registration status
 * @returns {string} Style code: 'filled', 'hollow-red', 'hollow-blue', 'hollow-gray', 'hollow-black'
 */
function determineMarkerStyle(voterData) {
    // Handle missing data
    if (!voterData) {
        return 'hollow-black'; // Unregistered/no data
    }
    
    const hasVoted = voterData.voted_in_current_election || false;
    const isRegistered = voterData.is_registered !== false; // Default to true if not specified
    
    // Voter has voted in current election - use filled circle
    if (hasVoted) {
        return 'filled';
    }
    
    // Voter is not registered
    if (!isRegistered) {
        return 'hollow-black';
    }
    
    // Registered voter who hasn't voted - determine outline color by party
    const partyAffiliation = voterData.party_affiliation_current || '';
    
    if (partyAffiliation.toLowerCase().includes('republican') || 
        partyAffiliation.toLowerCase().includes('rep')) {
        return 'hollow-red'; // Registered Republican who hasn't voted
    }
    
    if (partyAffiliation.toLowerCase().includes('democrat') || 
        partyAffiliation.toLowerCase().includes('dem')) {
        return 'hollow-blue'; // Registered Democrat who hasn't voted
    }
    
    // Registered voter with unknown party who hasn't voted
    return 'hollow-gray';
}

/**
 * Groups voters by their exact address coordinates
 * @param {Array} voters - Array of voter data objects with lat/lng
 * @returns {Object} Map of coordinate keys to arrays of voters
 */
function groupVotersByAddress(voters) {
    const grouped = {};
    
    voters.forEach(voter => {
        if (!voter.lat || !voter.lng) return;
        
        // Create a key from coordinates (rounded to 6 decimal places for exact matching)
        const key = `${voter.lat.toFixed(6)},${voter.lng.toFixed(6)}`;
        
        if (!grouped[key]) {
            grouped[key] = [];
        }
        
        grouped[key].push(voter);
    });
    
    return grouped;
}

/**
 * Calculates party distribution for a household
 * @param {Array} voters - Array of voters at the same address
 * @returns {Object} Party distribution with counts per party color
 */
function calculateHouseholdPartyDistribution(voters) {
    const distribution = {
        red: 0,
        blue: 0,
        purple: 0,
        maroon: 0,
        green: 0
    };
    
    voters.forEach(voter => {
        const color = determineMarkerColor(voter);
        if (color && distribution.hasOwnProperty(color)) {
            distribution[color]++;
        }
    });
    
    return distribution;
}

/**
 * Determines if a household should show a numeric badge (same party)
 * @param {Object} distribution - Party distribution object
 * @returns {boolean} True if all voters are same party
 */
function shouldShowNumericBadge(distribution) {
    const nonZeroParties = Object.values(distribution).filter(count => count > 0);
    return nonZeroParties.length === 1 && nonZeroParties[0] > 1;
}

/**
 * Determines if a household should show multiple markers (different parties)
 * @param {Object} distribution - Party distribution object
 * @returns {boolean} True if voters have different parties
 */
function shouldShowMultipleMarkers(distribution) {
    const nonZeroParties = Object.values(distribution).filter(count => count > 0);
    return nonZeroParties.length > 1;
}

/**
 * Creates offset positions for stacking multiple markers
 * @param {number} lat - Base latitude
 * @param {number} lng - Base longitude
 * @param {number} index - Marker index
 * @param {number} total - Total number of markers
 * @returns {Array} [lat, lng] with offset applied
 */
function offsetMarkerPosition(lat, lng, index, total) {
    // Limit to maximum 5 visible markers
    const maxVisible = Math.min(total, 5);
    
    if (maxVisible === 1) {
        return [lat, lng];
    }
    
    // Create circular offset pattern
    const angle = (index / maxVisible) * 2 * Math.PI;
    const offsetDistance = 0.00005; // Small offset in degrees (~5 meters)
    
    const offsetLat = lat + (Math.cos(angle) * offsetDistance);
    const offsetLng = lng + (Math.sin(angle) * offsetDistance);
    
    return [offsetLat, offsetLng];
}

// ============================================================================
// ZOOM-DEPENDENT RENDERING
// ============================================================================

/**
 * ZoomDependentRenderer class manages switching between markers and heatmap
 */
class ZoomDependentRenderer {
    constructor(map, markerLayer, heatmapLayer) {
        this.map = map;
        this.markerLayer = markerLayer;
        this.heatmapLayer = heatmapLayer;
        this.currentMode = null;
        this.ZOOM_THRESHOLD = 16; // Zoom 16+ shows markers, 15- shows heatmap
        
        // Listen for zoom events
        this.map.on('zoomend', () => this.updateVisualization());
        
        // Initial update
        this.updateVisualization();
    }
    
    updateVisualization() {
        const currentZoom = this.map.getZoom();
        const newMode = currentZoom >= this.ZOOM_THRESHOLD ? 'markers' : 'heatmap';
        
        // Only update if mode changed
        if (newMode === this.currentMode) {
            return;
        }
        
        this.currentMode = newMode;
        
        if (newMode === 'markers') {
            this.showMarkers();
        } else {
            this.showHeatmap();
        }
    }
    
    showMarkers() {
        // Remove heatmap, add markers
        if (this.map.hasLayer(this.heatmapLayer)) {
            this.map.removeLayer(this.heatmapLayer);
        }
        if (!this.map.hasLayer(this.markerLayer)) {
            this.map.addLayer(this.markerLayer);
        }
    }
    
    showHeatmap() {
        // Remove markers, add heatmap
        if (this.map.hasLayer(this.markerLayer)) {
            this.map.removeLayer(this.markerLayer);
        }
        if (!this.map.hasLayer(this.heatmapLayer)) {
            this.map.addLayer(this.heatmapLayer);
        }
    }
    
    getCurrentMode() {
        return this.currentMode;
    }
}

/**
 * Filters voters to include ONLY those who have voted (for heatmap)
 * Excludes registered non-voters and unregistered addresses
 * @param {Array} voters - Array of all voter data
 * @returns {Array} Array of [lat, lng, intensity] for heatmap
 */
function filterVotersForHeatmap(voters) {
    const heatmapData = [];
    
    voters.forEach(voter => {
        // Only include voters who have actually voted
        if (voter.voted_in_current_election && voter.lat && voter.lng) {
            heatmapData.push([voter.lat, voter.lng, 1]);
        }
    });
    
    return heatmapData;
}

// ============================================================================
// PRECINCT BOUNDARIES
// ============================================================================

/**
 * Loads and displays precinct boundary polygons
 * @param {string} dataUrl - URL to precinct_boundaries.json
 * @returns {L.GeoJSON} Leaflet GeoJSON layer
 */
async function loadPrecinctBoundaries(dataUrl = 'data/precinct_boundaries_combined.json') {
    try {
        const response = await fetch(dataUrl);
        if (!response.ok) {
            console.warn('Precinct boundaries data not available');
            return null;
        }
        
        const geojsonData = await response.json();
        
        // Create labels layer for precinct numbers
        precinctLabelsLayer = L.layerGroup();
        
        // Store label metadata for zoom-responsive resizing
        const precinctLabelData = [];
        
        const precinctLayer = L.geoJSON(geojsonData, {
            style: function(feature) {
                return {
                    color: '#333',
                    weight: 2,
                    opacity: 0.6,
                    fillColor: 'transparent',
                    fillOpacity: 0,
                    dashArray: '5, 5'
                };
            },
            onEachFeature: function(feature, layer) {
                // Create a label at the centroid of each precinct
                const props = feature.properties;
                const precinctId = props.precinct_id || props.precinct || '';
                // Strip leading zeros for cleaner display
                const labelText = precinctId.replace(/^0+/, '') || precinctId;
                
                if (labelText && layer.getBounds) {
                    const center = layer.getBounds().getCenter();
                    const bounds = layer.getBounds();
                    
                    const label = L.marker(center, {
                        icon: L.divIcon({
                            className: 'precinct-label',
                            html: `<div>${labelText}</div>`,
                            iconSize: [10, 10],
                            iconAnchor: [5, 5]
                        }),
                        interactive: false,
                        zIndexOffset: -1000
                    });
                    
                    // Store bounds so we can compute pixel width on zoom
                    precinctLabelData.push({ label, bounds, text: labelText });
                    precinctLabelsLayer.addLayer(label);
                }
                
                // Add click handler to show precinct info
                layer.on('click', function(e) {
                    const turnoutPct = props.turnout_percentage || 'N/A';
                    const totalVoters = props.total_voters || 'N/A';
                    const votedCount = props.voted_count || 'N/A';
                    
                    const popupContent = `
                        <div class="precinct-popup">
                            <h4>Precinct ${precinctId}</h4>
                            <p><strong>Total Registered:</strong> ${totalVoters}</p>
                            <p><strong>Voted:</strong> ${votedCount}</p>
                            <p><strong>Turnout:</strong> ${turnoutPct}%</p>
                        </div>
                    `;
                    
                    layer.bindPopup(popupContent).openPopup();
                });
            }
        });
        
        console.log('Created', precinctLabelData.length, 'precinct labels');
        
        // Zoom-responsive label sizing
        function updatePrecinctLabelSizes() {
            if (!map || !map.hasLayer(precinctLabelsLayer)) return;
            
            precinctLabelData.forEach(({ label, bounds, text }) => {
                // Convert precinct bounds to pixel coordinates
                const nw = map.latLngToContainerPoint(bounds.getNorthWest());
                const se = map.latLngToContainerPoint(bounds.getSouthEast());
                const pixelWidth = Math.abs(se.x - nw.x);
                const pixelHeight = Math.abs(se.y - nw.y);
                
                // Font size = fraction of the precinct's pixel width, capped
                // Use ~40% of the smaller dimension so text fits inside
                const charCount = text.length;
                const maxByWidth = (pixelWidth * 0.7) / (charCount * 0.6);
                const maxByHeight = pixelHeight * 0.5;
                const fontSize = Math.max(0, Math.min(60, Math.floor(Math.min(maxByWidth, maxByHeight))));
                
                // Hide labels that would be too small to read
                const iconW = Math.max(fontSize * charCount * 0.7, 10);
                const iconH = Math.max(fontSize * 1.2, 10);
                
                label.setIcon(L.divIcon({
                    className: 'precinct-label',
                    html: `<div style="font-size:${fontSize}px;${fontSize < 8 ? 'display:none;' : ''}">${text}</div>`,
                    iconSize: [iconW, iconH],
                    iconAnchor: [iconW / 2, iconH / 2]
                }));
            });
        }
        
        // Update on zoom and when layer is added
        map.on('zoomend', updatePrecinctLabelSizes);
        map.on('layeradd', function(e) {
            if (e.layer === precinctLabelsLayer) {
                updatePrecinctLabelSizes();
            }
        });
        
        // Initial sizing
        updatePrecinctLabelSizes();
        
        return precinctLayer;
        
    } catch (error) {
        console.error('Error loading precinct boundaries:', error);
        return null;
    }
}

/**
 * Loads county outline as fallback for precinct boundaries
 * @returns {L.GeoJSON} Leaflet GeoJSON layer
 */
async function loadCountyOutlines() {
    try {
        console.log('Loading county outlines as fallback...');
        const response = await fetch('../data/tx-county-outlines.json');
        if (!response.ok) {
            console.warn('County outlines not available');
            return null;
        }
        
        const geojsonData = await response.json();
        
        // Filter for Hidalgo County (FIPS 215) and Cameron County (FIPS 61)
        const filteredFeatures = geojsonData.features.filter(feature => {
            const fips = feature.properties.FIPS_ST_CNTY_CD;
            return fips === '48215' || fips === '48061'; // Hidalgo or Cameron
        });
        
        const countyLayer = L.geoJSON({
            type: 'FeatureCollection',
            features: filteredFeatures
        }, {
            style: function(feature) {
                return {
                    color: '#333',
                    weight: 2,
                    opacity: 0.6,
                    fillColor: 'transparent',
                    fillOpacity: 0,
                    dashArray: '5, 5'
                };
            },
            onEachFeature: function(feature, layer) {
                layer.on('click', function(e) {
                    const countyName = feature.properties.CNTY_NM || 'Unknown';
                    const popupContent = `
                        <div class="precinct-popup">
                            <h4>${countyName} County</h4>
                            <p><em>Precinct boundaries not loaded</em></p>
                            <p>See PRECINCT_DATA_INSTRUCTIONS.md for setup</p>
                        </div>
                    `;
                    layer.bindPopup(popupContent).openPopup();
                });
            }
        });
        
        return countyLayer;
        
    } catch (error) {
        console.error('Error loading county outlines:', error);
        return null;
    }
}

// ============================================================================
// POLLING PLACES
// ============================================================================

/**
 * Creates a custom polling place icon (ballot box)
 * @returns {L.DivIcon} Leaflet icon for polling places
 */
function createPollingPlaceIcon() {
    return L.divIcon({
        className: 'polling-place-icon',
        html: `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32">
                <path fill="#4A90E2" d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-8 14H9v-2h2v2zm0-4H9V7h2v6zm6 4h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                <rect fill="#4A90E2" x="7" y="1" width="10" height="2" rx="1"/>
            </svg>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
    });
}

/**
 * Loads and displays polling place markers
 * @param {string} dataUrl - URL to voting_locations.json
 * @returns {L.LayerGroup} Leaflet layer group with polling place markers
 */
async function loadPollingPlaces(dataUrl = 'data/voting_locations.json') {
    try {
        const response = await fetch(dataUrl);
        if (!response.ok) {
            console.warn('Polling places data not available');
            return null;
        }
        
        const data = await response.json();
        const pollingPlaceLayer = L.layerGroup();
        const icon = createPollingPlaceIcon();
        
        if (data.locations && Array.isArray(data.locations)) {
            data.locations.forEach(location => {
                if (location.lat && location.lng) {
                    const marker = L.marker([location.lat, location.lng], { icon: icon });
                    
                    const popupContent = `
                        <div class="polling-place-popup">
                            <h4>${location.name || 'Polling Place'}</h4>
                            <p><strong>Address:</strong><br>${location.address || 'N/A'}</p>
                            <p><strong>Hours:</strong> ${location.hours || 'N/A'}</p>
                            <p><strong>Dates:</strong> ${location.dates || 'N/A'}</p>
                            ${location.type ? `<p><strong>Type:</strong> ${location.type}</p>` : ''}
                        </div>
                    `;
                    
                    marker.bindPopup(popupContent);
                    pollingPlaceLayer.addLayer(marker);
                }
            });
        }
        
        return pollingPlaceLayer;
        
    } catch (error) {
        console.error('Error loading polling places:', error);
        return null;
    }
}

// ============================================================================
// MARKER RENDERING
// ============================================================================

/**
 * Gets the fill color for a marker based on party color code
 * @param {string} colorCode - Color code from determineMarkerColor()
 * @returns {string} Hex color code
 */
function getMarkerFillColor(colorCode) {
    const colors = {
        'red': '#DC143C',      // Republican
        'blue': '#1E90FF',     // Democratic
        'purple': '#9370DB',   // Flipped: Republican → Democratic
        'maroon': '#800000',   // Flipped: Democratic → Republican
        'green': '#32CD32'     // Unknown/Other
    };

    return colors[colorCode] || colors['green'];
}


/**
 * Renders a voter marker with appropriate style
 * @param {Object} voterData - Voter data object
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @param {number} badge - Optional numeric badge for household count
 * @returns {L.CircleMarker} Leaflet circle marker
 */
function renderVoterMarker(voterData, lat, lng, badge = null) {
    const colorCode = determineMarkerColor(voterData);
    
    // Skip this voter if color is null (filtered out)
    if (!colorCode) {
        return null;
    }
    
    const styleCode = determineMarkerStyle(voterData);
    const fillColor = getMarkerFillColor(colorCode);
    
    // Determine if filled or hollow
    const isFilled = styleCode === 'filled';
    
    // Create marker options
    const markerOptions = {
        radius: 8,
        fillColor: fillColor,
        color: fillColor,
        weight: 2,
        opacity: 1,
        fillOpacity: isFilled ? 0.8 : 0  // Filled or hollow
    };
    
    const marker = L.circleMarker([lat, lng], markerOptions);
    
    // Add numeric badge if provided
    if (badge && badge > 1) {
        const badgeHtml = `
            <div class="marker-badge" style="
                position: absolute;
                top: -8px;
                right: -8px;
                background: rgba(0, 0, 0, 0.7);
                color: white;
                border-radius: 50%;
                width: 18px;
                height: 18px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 11px;
                font-weight: bold;
                border: 1px solid white;
            ">${badge > 5 ? '+5' : badge}</div>
        `;
        
        // Note: Badge rendering would need custom implementation with Leaflet divIcon
        // For now, we'll include badge info in the popup
    }
    
    return marker;
}

/**
 * Creates popup content for a household with multiple voters
 * @param {Array} voters - Array of voter objects at the same address
 * @returns {string} HTML content for popup
 */
function createHouseholdPopup(voters) {
    const count = voters.length;
    const address = voters[0].address || 'Unknown address';
    
    let html = `
        <div class="household-popup">
            <h4>${count} Voter${count > 1 ? 's' : ''} at this Address</h4>
            <p class="address">${address}</p>
            <div class="voter-list">
    `;
    
    voters.forEach((voter, index) => {
        const colorCode = determineMarkerColor(voter);
        
        // Skip filtered voters
        if (!colorCode) {
            return;
        }
        
        const styleCode = determineMarkerStyle(voter);
        const votedStatus = voter.voted_in_current_election ? 'Voted' : 'Not Voted';
        const partyLabel = voter.party_affiliation_current || 'Unknown';
        const markerColor = getMarkerFillColor(colorCode);
        
        html += `
            <div class="voter-item">
                <span class="voter-marker-indicator" style="
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    background-color: ${styleCode === 'filled' ? markerColor : 'transparent'};
                    border: 2px solid ${markerColor};
                    margin-right: 8px;
                "></span>
                <span class="voter-info">
                    <strong>${voter.name || 'Voter ' + (index + 1)}</strong><br>
                    <small>${partyLabel} - ${votedStatus}</small>
                </span>
            </div>
        `;
    });
    
    html += `
            </div>
        </div>
    `;
    
    return html;
}

// ============================================================================
// MAP CLEARING FUNCTIONALITY
// ============================================================================

/**
 * Clears all markers and heatmap data from the map
 * Should be called before loading a new dataset
 */
function clearMapMarkers() {
    console.log('Clearing all map markers and heatmap data');
    
    // Clear marker cluster group
    if (markerClusterGroup) {
        markerClusterGroup.clearLayers();
        console.log('Cleared marker cluster group');
    }
    
    // Clear heatmap layer
    if (heatmapLayer) {
        heatmapLayer.setLatLngs([]);
        console.log('Cleared heatmap layer');
    }
    
    // Clear year layers if they exist
    if (yearLayers && Object.keys(yearLayers).length > 0) {
        Object.keys(yearLayers).forEach(year => {
            yearLayers[year] = null;
        });
        yearLayers = {};
        activeYears.clear();
        console.log('Cleared year layers');
    }
}

// ============================================================================
// LOADING INDICATOR
// ============================================================================

/**
 * Shows the loading indicator overlay during map updates
 * Should be called before starting data loading operations
 */
function showLoadingIndicator() {
    const indicator = document.getElementById('map-loading-indicator');
    if (indicator) {
        indicator.style.display = 'flex';
        console.log('Loading indicator shown');
    }
}

/**
 * Hides the loading indicator overlay after map updates complete
 * Should be called after data loading and rendering is finished
 */
function hideLoadingIndicator() {
    const indicator = document.getElementById('map-loading-indicator');
    if (indicator) {
        indicator.style.display = 'none';
        console.log('Loading indicator hidden');
    }
}

// Layer control functionality
function initLayerControl() {
    // Create layer control panel
    const layerControl = document.createElement('div');
    layerControl.className = 'layer-control';
    layerControl.innerHTML = `
        <div class="layer-control-header">
            <h3>Election Years</h3>
            <button class="layer-control-toggle" onclick="toggleLayerControl()">
                <i class="fas fa-layer-group"></i>
            </button>
        </div>
        <div class="layer-control-content" id="layerControlContent">
            <div class="layer-control-loading">Loading available years...</div>
        </div>
    `;
    
    document.body.appendChild(layerControl);
}

function toggleLayerControl() {
    const content = document.getElementById('layerControlContent');
    const control = document.querySelector('.layer-control');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        control.classList.add('expanded');
    } else {
        content.style.display = 'none';
        control.classList.remove('expanded');
    }
}

function updateLayerControl(availableYears) {
    const content = document.getElementById('layerControlContent');
    
    if (!availableYears || availableYears.length === 0) {
        content.innerHTML = '<div class="layer-control-empty">No election data available</div>';
        return;
    }
    
    // Sort years in descending order (newest first)
    availableYears.sort((a, b) => b - a);
    
    let html = '<div class="layer-list">';
    
    availableYears.forEach(year => {
        const isActive = activeYears.has(year);
        const color = getYearColor(year);
        
        html += `
            <div class="layer-item">
                <label class="layer-checkbox">
                    <input type="checkbox" 
                           id="layer-${year}" 
                           ${isActive ? 'checked' : ''} 
                           onchange="toggleYearLayer(${year})">
                    <span class="layer-color" style="background-color: ${color}"></span>
                    <span class="layer-label">${year}</span>
                </label>
                <span class="layer-count" id="count-${year}">0</span>
            </div>
        `;
    });
    
    html += '</div>';
    html += `
        <div class="layer-actions">
            <button onclick="toggleAllLayers(true)" class="layer-btn">Show All</button>
            <button onclick="toggleAllLayers(false)" class="layer-btn">Hide All</button>
        </div>
    `;
    
    content.innerHTML = html;
}

function getYearColor(year) {
    // Generate distinct colors for different years
    const colors = [
        '#e74c3c', // Red
        '#3498db', // Blue
        '#2ecc71', // Green
        '#f39c12', // Orange
        '#9b59b6', // Purple
        '#1abc9c', // Turquoise
        '#e67e22', // Carrot
        '#34495e', // Dark gray
    ];
    
    const index = (year - 2020) % colors.length;
    return colors[index];
}

function toggleYearLayer(year) {
    const checkbox = document.getElementById(`layer-${year}`);
    
    if (checkbox.checked) {
        activeYears.add(year);
        if (yearLayers[year]) {
            showYearLayer(year);
        } else {
            loadYearData(year);
        }
    } else {
        activeYears.delete(year);
        hideYearLayer(year);
    }
}

function toggleAllLayers(show) {
    const checkboxes = document.querySelectorAll('.layer-checkbox input[type="checkbox"]');
    
    checkboxes.forEach(checkbox => {
        const year = parseInt(checkbox.id.replace('layer-', ''));
        checkbox.checked = show;
        
        if (show) {
            activeYears.add(year);
            if (yearLayers[year]) {
                showYearLayer(year);
            } else {
                loadYearData(year);
            }
        } else {
            activeYears.delete(year);
            hideYearLayer(year);
        }
    });
}

function showYearLayer(year) {
    console.log('showYearLayer called for year:', year);
    if (!yearLayers[year]) {
        console.warn('No layer data for year:', year);
        return;
    }
    
    const layer = yearLayers[year];
    console.log('Layer has', layer.markers ? layer.markers.length : 0, 'markers and', layer.heatmapData ? layer.heatmapData.length : 0, 'heatmap points');
    
    // Add markers to cluster group
    if (layer.markers) {
        layer.markers.forEach(marker => {
            markerClusterGroup.addLayer(marker);
        });
        console.log('Added markers to cluster group, total now:', markerClusterGroup.getLayers().length);
    }
    
    // Add to heatmap
    if (layer.heatmapData && layer.heatmapData.length > 0) {
        const currentData = heatmapLayer._latlngs || [];
        const newData = [...currentData, ...layer.heatmapData];
        heatmapLayer.setLatLngs(newData);
        console.log('Updated heatmap, total points now:', newData.length);
    }
    
    updateMapView();
}

function hideYearLayer(year) {
    if (!yearLayers[year]) return;
    
    const layer = yearLayers[year];
    
    // Remove markers from cluster group
    if (layer.markers) {
        layer.markers.forEach(marker => {
            markerClusterGroup.removeLayer(marker);
        });
    }
    
    // Rebuild heatmap without this year's data
    rebuildHeatmap();
    
    updateMapView();
}

function rebuildHeatmap() {
    const allHeatmapData = [];
    
    activeYears.forEach(year => {
        if (yearLayers[year] && yearLayers[year].heatmapData) {
            allHeatmapData.push(...yearLayers[year].heatmapData);
        }
    });
    
    heatmapLayer.setLatLngs(allHeatmapData);
}

async function loadYearData(year) {
    try {
        const response = await fetch(`data/map_data_${year}.json`);
        
        if (!response.ok) {
            console.warn(`No data available for year ${year}`);
            return;
        }
        
        const data = await response.json();
        processYearData(year, data);
        
    } catch (error) {
        console.error(`Error loading data for year ${year}:`, error);
    }
}

function processYearData(year, mapData) {
    if (!mapData || !mapData.features) {
        console.error(`Invalid map data format for year ${year}`);
        return;
    }
    
    const markers = [];
    const heatmapData = [];
    const color = getYearColor(year);
    
    mapData.features.forEach(feature => {
        try {
            const coords = feature.geometry.coordinates;
            const props = feature.properties;
            
            // Validate coordinates
            if (!coords || coords.length !== 2 || 
                isNaN(coords[0]) || isNaN(coords[1])) {
                return;
            }
            
            const lat = coords[1];
            const lng = coords[0];
            
            // Add to heatmap
            heatmapData.push([lat, lng, 1]);
            
            // Create marker with year-specific color
            const marker = L.circleMarker([lat, lng], {
                radius: 8,
                fillColor: color,
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.7
            });
            
            // Create popup content
            const popupContent = `
                <div class="info-box">
                    <strong>Year:</strong> ${year}<br>
                    <strong>Address:</strong> ${props.address || 'N/A'}<br>
                    <strong>Precinct:</strong> ${props.precinct || 'N/A'}<br>
                    <strong>Ballot Style:</strong> ${props.ballot_style || 'N/A'}
                </div>
            `;
            
            marker.bindPopup(popupContent);
            markers.push(marker);
            
        } catch (error) {
            console.warn('Error processing feature:', error);
        }
    });
    
    // Store layer data
    yearLayers[year] = {
        markers: markers,
        heatmapData: heatmapData,
        count: markers.length
    };
    
    // Update count display
    const countElement = document.getElementById(`count-${year}`);
    if (countElement) {
        countElement.textContent = markers.length.toLocaleString();
    }
    
    // Show layer if it's active
    if (activeYears.has(year)) {
        showYearLayer(year);
    }
    
    console.log(`Loaded ${markers.length} records for year ${year}`);
}


// Heatmap mode toggle functionality
function initializeHeatmapModeToggle() {
    const buttons = document.querySelectorAll('.heatmap-toggle-btn');
    
    buttons.forEach(button => {
        button.addEventListener('click', () => {
            const mode = button.getAttribute('data-mode');
            
            // Update active state
            buttons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Update global heatmap mode
            window.heatmapMode = mode;
            
            // Update map view to show appropriate heatmap
            updateMapView();
            
            console.log('Heatmap mode changed to:', mode);
        });
    });
}

// Call this after map initialization
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeHeatmapModeToggle);
} else {
    initializeHeatmapModeToggle();
}

// ============================================================================
// MAP OPTIONS PANEL
// ============================================================================

/**
 * Initialize Map Options Panel
 * Handles all map display options including heatmap type, layers, and overlays
 */
function initializeMapOptionsPanel() {
    console.log('Initializing Map Options Panel...');
    
    // Icon button toggle
    const mapIconBtn = document.getElementById('mapIconBtn');
    const mapPopup = document.getElementById('mapOptionsPopup');
    const mapClose = document.getElementById('mapOptionsClose');
    
    if (mapIconBtn && mapPopup) {
        mapIconBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = mapPopup.classList.toggle('open');
            mapIconBtn.classList.toggle('active', isOpen);
            // Close data popup if open
            const dataPopup = document.getElementById('dataOptionsPopup');
            const dataBtn = document.getElementById('dataIconBtn');
            if (dataPopup && dataPopup.classList.contains('open')) {
                dataPopup.classList.remove('open');
                if (dataBtn) dataBtn.classList.remove('active');
            }
        });
        
        if (mapClose) {
            mapClose.addEventListener('click', () => {
                mapPopup.classList.remove('open');
                mapIconBtn.classList.remove('active');
            });
        }
        
        mapPopup.addEventListener('click', (e) => e.stopPropagation());
    }
    
    // Heatmap type buttons
    const heatmapButtons = document.querySelectorAll('.map-option-btn[data-option="heatmap"]');
    heatmapButtons.forEach(button => {
        button.addEventListener('click', () => {
            const value = button.getAttribute('data-value');
            
            // Update active state - remove inline styles and use classes
            heatmapButtons.forEach(btn => {
                btn.classList.remove('active');
                // Remove inline styles that override CSS
                btn.style.background = '';
                btn.style.color = '';
                btn.style.border = '';
            });
            button.classList.add('active');
            
            // Update global heatmap mode
            window.heatmapMode = value;
            
            // Update map view
            updateMapView();
            
            console.log('Heatmap type changed to:', value);
        });
    });
    
    // Numeric displays toggle
    const numericToggle = document.getElementById('numericDisplayToggle');
    if (numericToggle) {
        numericToggle.addEventListener('change', (e) => {
            window.showNumericBadges = e.target.checked;
            console.log('Numeric badges:', e.target.checked ? 'enabled' : 'disabled');
            
            // Reload markers to apply change
            if (window.mapData && window.mapData.features) {
                initializeDataLayers();
            }
        });
    }
    
    // Precinct lines toggle
    const precinctToggle = document.getElementById('precinctLinesToggle');
    if (precinctToggle) {
        precinctToggle.addEventListener('change', (e) => {
            if (precinctBoundariesLayer) {
                if (e.target.checked) {
                    if (!map.hasLayer(precinctBoundariesLayer)) {
                        map.addLayer(precinctBoundariesLayer);
                    }
                    if (precinctLabelsLayer && !map.hasLayer(precinctLabelsLayer)) {
                        map.addLayer(precinctLabelsLayer);
                    }
                    console.log('Precinct boundaries and labels shown');
                } else {
                    if (map.hasLayer(precinctBoundariesLayer)) {
                        map.removeLayer(precinctBoundariesLayer);
                    }
                    if (precinctLabelsLayer && map.hasLayer(precinctLabelsLayer)) {
                        map.removeLayer(precinctLabelsLayer);
                    }
                    console.log('Precinct boundaries and labels hidden');
                }
            } else {
                console.warn('Precinct boundaries layer not available');
            }
        });
    }
    
    // Polling locations toggle
    const pollingToggle = document.getElementById('pollingLocationsToggle');
    if (pollingToggle) {
        pollingToggle.addEventListener('change', (e) => {
            if (pollingPlacesLayer) {
                if (e.target.checked) {
                    if (!map.hasLayer(pollingPlacesLayer)) {
                        map.addLayer(pollingPlacesLayer);
                        console.log('Polling locations shown');
                    }
                } else {
                    if (map.hasLayer(pollingPlacesLayer)) {
                        map.removeLayer(pollingPlacesLayer);
                        console.log('Polling locations hidden');
                    }
                }
            } else {
                console.warn('Polling places layer not available');
            }
        });
    }
    
    // County boundaries toggle
    const countyToggle = document.getElementById('countyBoundariesToggle');
    if (countyToggle) {
        countyToggle.addEventListener('change', (e) => {
            if (countyOutlinesLayer) {
                if (e.target.checked) {
                    if (!map.hasLayer(countyOutlinesLayer)) {
                        map.addLayer(countyOutlinesLayer);
                        console.log('County boundaries shown');
                    }
                } else {
                    if (map.hasLayer(countyOutlinesLayer)) {
                        map.removeLayer(countyOutlinesLayer);
                        console.log('County boundaries hidden');
                    }
                }
            } else {
                console.warn('County boundaries layer not available');
            }
        });
    }
    
    // Flipped voters buttons
    const flippedButtons = document.querySelectorAll('.flipped-voters-btn');
    flippedButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            const flipValue = e.currentTarget.dataset.flip;
            flippedVotersFilter = flipValue;
            console.log('Flipped voters filter:', flipValue);
            
            // Update active state
            flippedButtons.forEach(btn => btn.classList.remove('active'));
            e.currentTarget.classList.add('active');
            
            // Reload markers to apply change
            if (window.mapData && window.mapData.features) {
                initializeDataLayers();
            }
        });
    });
    
    // Initialize global flag for numeric badges
    window.showNumericBadges = numericToggle ? numericToggle.checked : true;
    
    console.log('Map Options Panel initialized successfully');
}

// ============================================================================
// PANEL POPUP CLOSE ON OUTSIDE CLICK (REMOVED - panels are now persistent)
// Panels stay open until user clicks the X button or toggles the icon button
// ============================================================================

// ============================================================================
// DATA OPTIONS PANEL
// ============================================================================

/**
 * Initialize Data Options Panel
 * Handles dataset selection and party filtering in a unified panel
 */
function initializeDataOptionsPanel() {
    console.log('Initializing Data Options Panel...');
    
    // Icon button toggle
    const dataIconBtn = document.getElementById('dataIconBtn');
    const dataPopup = document.getElementById('dataOptionsPopup');
    const dataClose = document.getElementById('dataOptionsClose');
    
    if (dataIconBtn && dataPopup) {
        dataIconBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = dataPopup.classList.toggle('open');
            dataIconBtn.classList.toggle('active', isOpen);
            // Close map popup if open
            const mapPopup = document.getElementById('mapOptionsPopup');
            const mapBtn = document.getElementById('mapIconBtn');
            if (mapPopup && mapPopup.classList.contains('open')) {
                mapPopup.classList.remove('open');
                if (mapBtn) mapBtn.classList.remove('active');
            }
        });
        
        if (dataClose) {
            dataClose.addEventListener('click', () => {
                dataPopup.classList.remove('open');
                dataIconBtn.classList.remove('active');
            });
        }
        
        dataPopup.addEventListener('click', (e) => e.stopPropagation());
    }
    
    // Initialize inline dataset selector
    initializeInlineDatasetSelector();
    
    // Initialize inline party filter
    initializeInlinePartyFilter();
    
    console.log('Data Options Panel initialized successfully');
}

/**
 * Initialize inline dataset selector in Data Options panel
 */
function initializeInlineDatasetSelector() {
    const select = document.getElementById('dataset-selector-inline');
    const originalSelect = document.getElementById('dataset-selector');
    
    if (!select) {
        console.warn('Inline dataset selector not found');
        return;
    }
    
    if (!originalSelect) {
        console.warn('Original dataset selector not found');
        return;
    }
    
    // Copy options from the original dataset selector
    if (originalSelect.options.length > 0) {
        select.innerHTML = originalSelect.innerHTML;
        select.selectedIndex = originalSelect.selectedIndex;
        
        // Update info badges
        updateInlineDatasetInfo();
    }
    
    // Listen for changes on inline selector
    select.addEventListener('change', async (e) => {
        const selectedIndex = e.target.selectedIndex;
        
        // Sync with original selector
        originalSelect.selectedIndex = selectedIndex;
        // Trigger change event on original selector
        const event = new Event('change', { bubbles: true });
        originalSelect.dispatchEvent(event);
        
        // Update info badges
        updateInlineDatasetInfo();
    });
    
    // Listen for changes on original selector to sync back
    originalSelect.addEventListener('change', () => {
        if (select.selectedIndex !== originalSelect.selectedIndex) {
            select.selectedIndex = originalSelect.selectedIndex;
            updateInlineDatasetInfo();
        }
    });
    
    console.log('Inline dataset selector initialized');
}

/**
 * Update inline dataset info badges
 */
function updateInlineDatasetInfo() {
    const select = document.getElementById('dataset-selector-inline');
    const countySpan = document.getElementById('dataset-county-inline');
    const yearSpan = document.getElementById('dataset-year-inline');
    const typeSpan = document.getElementById('dataset-type-inline');
    
    if (!select || !countySpan || !yearSpan || !typeSpan) return;
    
    const selectedOption = select.options[select.selectedIndex];
    if (!selectedOption || !selectedOption.value) {
        countySpan.textContent = '';
        yearSpan.textContent = '';
        typeSpan.textContent = '';
        return;
    }
    
    // Parse dataset info from option text or data attributes
    const text = selectedOption.textContent;
    const parts = text.split(' - ');
    
    if (parts.length >= 3) {
        countySpan.textContent = parts[0]; // County
        yearSpan.textContent = parts[1];   // Year
        typeSpan.textContent = parts[2];   // Type
    }
}

/**
 * Initialize inline party filter in Data Options panel
 */
function initializeInlinePartyFilter() {
    const section = document.getElementById('partyFilterSection');
    const buttons = document.querySelectorAll('.party-filter-btn-inline');
    
    if (!section || buttons.length === 0) {
        console.warn('Inline party filter not found');
        return;
    }
    
    // Add click handlers
    buttons.forEach(button => {
        button.addEventListener('click', () => {
            const filterValue = button.getAttribute('data-filter');
            
            // Update inline button states FIRST
            buttons.forEach(btn => {
                if (btn.getAttribute('data-filter') === filterValue) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
            
            // Trigger the original party filter buttons (hidden)
            const originalButtons = document.querySelectorAll('.party-filter-btn');
            originalButtons.forEach(btn => {
                if (btn.getAttribute('data-filter') === filterValue) {
                    btn.click();
                }
            });
            
            console.log('Inline party filter changed to:', filterValue);
        });
    });
    
    console.log('Inline party filter initialized');
}

/**
 * Show/hide inline party filter based on election type
 * @param {boolean} show - Whether to show the party filter
 */
function setInlinePartyFilterVisibility(show) {
    const section = document.getElementById('partyFilterSection');
    if (section) {
        section.style.display = show ? 'block' : 'none';
        console.log('Inline party filter visibility:', show ? 'visible' : 'hidden');
    }
}

/**
 * Sync inline dataset selector with main selector
 * Called when datasets are loaded or selection changes
 */
function syncInlineDatasetSelector() {
    const originalSelect = document.getElementById('dataset-selector');
    const inlineSelect = document.getElementById('dataset-selector-inline');
    
    if (originalSelect && inlineSelect) {
        inlineSelect.innerHTML = originalSelect.innerHTML;
        inlineSelect.selectedIndex = originalSelect.selectedIndex;
        updateInlineDatasetInfo();
    }
}

/**
 * Sync inline party filter with main filter
 * Called when party filter state changes
 * @param {string} filterValue - The active filter value ('all', 'republican', 'democratic')
 */
function syncInlinePartyFilter(filterValue) {
    const buttons = document.querySelectorAll('.party-filter-btn-inline');
    buttons.forEach(btn => {
        if (btn.getAttribute('data-filter') === filterValue) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// Initialize Data Options Panel after DOM loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeDataOptionsPanel);
} else {
    initializeDataOptionsPanel();
}

// Initialize Map Options Panel after DOM loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeMapOptionsPanel);
} else {
    initializeMapOptionsPanel();
}

// ============================================================================
// SCREENSHOT FEATURE
// ============================================================================

/**
 * Capture the current map view as a 1920x1080 screenshot with watermark
 */
async function captureScreenshot() {
    const btn = document.getElementById('screenshotBtn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }

    try {
        // Capture the entire document body (includes logo, stats box, map, everything)
        const capture = await html2canvas(document.body, {
            useCORS: true,
            allowTaint: true,
            logging: false,
            scale: 1,
            width: window.innerWidth,
            height: window.innerHeight,
            backgroundColor: '#f0f0f0'
        });

        const W = capture.width;
        const H = capture.height;

        // Create final canvas with room for bottom bar
        const barH = 44;
        const canvas = document.createElement('canvas');
        canvas.width = W;
        canvas.height = H + barH;
        const ctx = canvas.getContext('2d');

        // Draw captured page
        ctx.drawImage(capture, 0, 0);

        // Large centered logo watermark (semi-transparent)
        const logo = new Image();
        logo.crossOrigin = 'anonymous';
        logo.src = 'assets/politiquera.png';

        await new Promise((resolve) => {
            logo.onload = resolve;
            logo.onerror = () => resolve();
        });

        if (logo.naturalWidth) {
            const logoMaxW = Math.min(W * 0.4, 500);
            const aspect = logo.naturalWidth / logo.naturalHeight;
            const logoW = logoMaxW;
            const logoH = logoW / aspect;
            const logoX = (W - logoW) / 2;
            const logoY = (H - logoH) / 2;
            ctx.globalAlpha = 0.2;
            ctx.drawImage(logo, logoX, logoY, logoW, logoH);
            ctx.globalAlpha = 1.0;
        }

        // Black bar at bottom with text
        ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
        ctx.fillRect(0, H, W, barH);

        const text = 'Data Visualizations by Politiquera.com';
        ctx.font = '600 18px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#ffffff';
        ctx.fillText(text, W / 2, H + barH / 2);

        // Convert to blob and trigger download
        canvas.toBlob(blob => {
            if (!blob) {
                alert('Failed to generate screenshot');
                return;
            }
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const ds = window.currentDataset || currentDataset;
            const datePart = new Date().toISOString().slice(0, 10);
            const nameParts = [];
            if (ds) {
                if (ds.county) nameParts.push(ds.county);
                if (ds.year) nameParts.push(ds.year);
                if (ds.electionType) nameParts.push(ds.electionType);
            }
            nameParts.push(datePart);
            a.download = `Politiquera_${nameParts.join('_')}.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 'image/png');

    } catch (err) {
        console.error('Screenshot failed:', err);
        alert('Screenshot failed: ' + err.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-camera"></i>';
        }
    }
}

// Initialize screenshot button
function initializeScreenshotButton() {
    const btn = document.getElementById('screenshotBtn');
    if (btn) {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            captureScreenshot();
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeScreenshotButton);
} else {
    initializeScreenshotButton();
}

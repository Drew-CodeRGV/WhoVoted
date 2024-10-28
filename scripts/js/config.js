// config.js
const config = {
    // Map center coordinates (McAllen, TX)
    MAP_CENTER: [26.2034, -98.2300],
    
    // Default zoom level
    MAP_ZOOM: 13,
    
    // Minimum and maximum zoom levels
    MIN_ZOOM: 10,
    MAX_ZOOM: 18,
    
    // Heatmap configuration
    HEATMAP_RADIUS: 25,
    HEATMAP_BLUR: 15,
    HEATMAP_MAX_ZOOM: 15,
    HEATMAP_MIN_OPACITY: 0.1,
    HEATMAP_MAX_OPACITY: 0.6,
    
    // Cluster configuration
    CLUSTER_DISTANCE: 20,
    CLUSTER_MAX_ZOOM: 17,
    
    // District style configuration
    DISTRICT_STYLES: {
        'McAllen District 1': {
            color: '#FF0000',
            weight: 2,
            opacity: 0.7,
            fillOpacity: 0.2,
            fillColor: '#FF0000'
        },
        'McAllen District 2': {
            color: '#00FF00',
            weight: 2,
            opacity: 0.7,
            fillOpacity: 0.2,
            fillColor: '#00FF00'
        },
        'McAllen District 3': {
            color: '#808080',
            weight: 2,
            opacity: 0.7,
            fillOpacity: 0.2,
            fillColor: '#808080'
        },
        'McAllen District 4': {
            color: '#0000FF',
            weight: 2,
            opacity: 0.7,
            fillOpacity: 0.2,
            fillColor: '#0000FF'
        },
        'McAllen District 5': {
            color: '#800080',
            weight: 2,
            opacity: 0.7,
            fillOpacity: 0.2,
            fillColor: '#800080'
        },
        'McAllen District 6': {
            color: '#FFFF00',
            weight: 2,
            opacity: 0.7,
            fillOpacity: 0.2,
            fillColor: '#FFFF00'
        }
    },

    // Popup configuration
    POPUP_OPTIONS: {
        maxWidth: 300,
        minWidth: 200,
        closeButton: true,
        closeOnClick: true,
        autoClose: true
    },

    // Marker configuration
    MARKER_OPTIONS: {
        radius: 8,
        fillColor: "#2196F3",
        color: "#fff",
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8
    },

    // Search configuration
    SEARCH_OPTIONS: {
        position: 'topright',
        zoom: 16,
        placeholder: 'Search for an address',
        showMarker: true,
        showPopup: true,
        autocomplete: true
    },

    // Geolocation configuration
    GEOLOCATION_OPTIONS: {
        position: 'topright',
        setView: true,
        maxZoom: 16,
        timeout: 10000,
        enableHighAccuracy: true
    },

    // Data URLs
    URLS: {
        VOTING_LOCATIONS: 'data/voting_locations.json',
        DISTRICT_BOUNDARIES: 'data/district_boundaries.json'
    },

    // Layer visibility defaults
    LAYER_DEFAULTS: {
        showVotingLocations: true,
        showDistricts: false,
        showHeatmap: true
    },

    // District boundary coordinates
    DISTRICT_COORDINATES: {
        'McAllen District 1': [
            [-98.2235, 26.2815],
            [-98.2392, 26.2814],
            [-98.2392, 26.2627],
            [-98.2235, 26.2627],
            [-98.2235, 26.2815]
        ],
        'McAllen District 2': [
            [-98.2392, 26.2814],
            [-98.2571, 26.2814],
            [-98.2571, 26.2734],
            [-98.2392, 26.2734],
            [-98.2392, 26.2814]
        ],
        'McAllen District 3': [
            [-98.2235, 26.2627],
            [-98.2392, 26.2627],
            [-98.2392, 26.1896],
            [-98.2235, 26.1896],
            [-98.2235, 26.2627]
        ],
        'McAllen District 4': [
            [-98.2392, 26.2165],
            [-98.2701, 26.2165],
            [-98.2701, 26.1896],
            [-98.2392, 26.1896],
            [-98.2392, 26.2165]
        ],
        'McAllen District 5': [
            [-98.2483, 26.2734],
            [-98.2571, 26.2734],
            [-98.2571, 26.2165],
            [-98.2483, 26.2165],
            [-98.2483, 26.2734]
        ],
        'McAllen District 6': [
            [-98.2392, 26.2627],
            [-98.2483, 26.2627],
            [-98.2483, 26.2165],
            [-98.2392, 26.2165],
            [-98.2392, 26.2627]
        ]
    },

    // Control panel configuration
    CONTROLS: {
        position: 'topright',
        collapsed: false,
        autoZIndex: true
    },

    // Custom icon configuration
    CUSTOM_ICON: {
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32],
        className: 'custom-div-icon'
    }
};

// Export the config object
if (typeof module !== 'undefined' && module.exports) {
    module.exports = config;
}

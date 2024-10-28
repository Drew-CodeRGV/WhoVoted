// config.js
const config = {
    // Map base settings (your specified values)
    MAP_CENTER: [26.2034, -98.2300],
    MAP_ZOOM: 12,
    HEATMAP_RADIUS: 15,
    HEATMAP_BLUR: 15,
    HEATMAP_MAX_ZOOM: 16,
    NEARBY_RADIUS: 1000, // 1km

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
    }
};

// Export the config object
if (typeof module !== 'undefined' && module.exports) {
    module.exports = config;
}

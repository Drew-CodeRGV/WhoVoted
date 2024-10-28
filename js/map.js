// map.js
let map, markerClusterGroup, heatmapLayer, votingLocationsLayer, votingLocationsControl, districtLayer;

function initMap() {
    // Initialize map with config settings
    map = L.map('map').setView(config.MAP_CENTER, config.MAP_ZOOM);

    // Create custom icon using Font Awesome
    var customIcon = L.divIcon({
        html: '<i class="fa-solid fa-flag-usa"></i>',
        iconSize: [32, 32],
        className: 'custom-div-icon'
    });

    // Set as default icon for all markers
    L.Marker.prototype.options.icon = customIcon;

    // Add base tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '© OpenStreetMap contributors | DL-R23'
    }).addTo(map);

    // Initialize layers
    initializeLayers();

    // Initialize district controls and layers
    initializeDistrictControls();

    // Add event listeners
    map.on('zoomend', updateMapView);
    addGeolocationControl();

    // Load map data and voting locations
    loadMapData();
}

function initializeLayers() {
    // Initialize marker cluster group
    markerClusterGroup = L.markerClusterGroup({
        disableClusteringAtZoom: 17,
        spiderfyOnMaxZoom: true,
        maxClusterRadius: 20,
        chunkedLoading: true,
        zoomToBoundsOnClick: true,
        showCoverageOnHover: false,
        removeOutsideVisibleBounds: true,
        animate: false,
        spiderfyDistanceMultiplier: 2.0,
        singleMarkerMode: true,
        iconCreateFunction: function(cluster) {
            var childCount = cluster.getChildCount();
            var c = ' marker-cluster-';
            if (childCount < 5) {
                c += 'small';
            } else if (childCount < 25) {
                c += 'medium';
            } else {
                c += 'large';
            }
            return new L.DivIcon({
                html: '<div><span>' + childCount + '</span></div>',
                className: 'marker-cluster' + c,
                iconSize: new L.Point(40, 40)
            });
        }
    });

    // Initialize heatmap layer
    heatmapLayer = L.heatLayer([], {
        radius: config.HEATMAP_RADIUS,
        blur: config.HEATMAP_BLUR,
        maxZoom: config.HEATMAP_MAX_ZOOM,
        max: 1.0,
        minOpacity: 0.1,
        maxOpacity: 0.6,
    });

    // Initialize voting locations layer
    votingLocationsLayer = L.layerGroup();

    // Initialize district layer
    districtLayer = L.layerGroup();
}

function initializeDistrictControls() {
    // Create district control div
    const controlDiv = document.createElement('div');
    controlDiv.className = 'district-control';
    controlDiv.innerHTML = `
        <div class="layer-control-box">
            <h4>District Boundaries</h4>
            <div class="control-toggle">
                <label class="switch">
                    <input type="checkbox" id="district-toggle">
                    <span class="slider round"></span>
                </label>
                <span>Show/Hide Districts</span>
            </div>
            <div class="opacity-control">
                <label for="district-opacity">Opacity: </label>
                <input type="range" id="district-opacity" min="0" max="100" value="70">
                <span id="opacity-value">70%</span>
            </div>
        </div>
    `;

    // Add custom control to map
    const LayerControl = L.Control.extend({
        options: { position: 'topright' },
        onAdd: function() {
            return controlDiv;
        }
    });

    map.addControl(new LayerControl());

    // Add districts to map
    addDistrictsToMap();

    // Add event listeners for controls
    document.getElementById('district-toggle').addEventListener('change', function(e) {
        if (e.target.checked) {
            districtLayer.addTo(map);
        } else {
            districtLayer.remove();
        }
    });

    document.getElementById('district-opacity').addEventListener('input', function(e) {
        const opacity = e.target.value / 100;
        document.getElementById('opacity-value').textContent = e.target.value + '%';
        
        districtLayer.eachLayer(function(layer) {
            layer.setStyle({
                fillOpacity: opacity * 0.2,
                opacity: opacity
            });
        });
    });
}

function addDistrictsToMap() {
    Object.entries(config.DISTRICT_COORDINATES).forEach(([name, coordinates]) => {
        const style = config.DISTRICT_STYLES[name];
        const polygon = L.polygon(coordinates, style)
            .bindPopup(name);
        districtLayer.addLayer(polygon);
    });
}

function updateMapView() {
    let currentZoom = map.getZoom();
    if (currentZoom > config.HEATMAP_MAX_ZOOM) {
        map.removeLayer(heatmapLayer);
        map.addLayer(markerClusterGroup);
    } else {
        map.removeLayer(markerClusterGroup);
        map.addLayer(heatmapLayer);
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

            showNearbyLocations([lat, lng]);
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

function loadMapData() {
    // Load voting locations
    fetch('data/voting_locations.json')
        .then(response => response.json())
        .then(data => {
            data.locations.forEach(location => {
                const marker = L.marker([location.latitude, location.longitude])
                    .bindPopup(`
                        <strong>${location.location}</strong><br>
                        Address: ${location.address}<br>
                        City: ${location.city}<br>
                        Voting Area: ${location.voting_area}<br>
                        Total Votes: ${location.total_votes}
                    `);
                votingLocationsLayer.addLayer(marker);
            });
            votingLocationsLayer.addTo(map);
        })
        .catch(error => console.error('Error loading voting locations:', error));
}

// Initialize map when DOM is loaded
document.addEventListener('DOMContentLoaded', initMap);

// Export for global access
window.initMap = initMap;

// map.js
let map, markerClusterGroup, heatmapLayer;

function initMap() {
    map = L.map('map').setView(config.MAP_CENTER, config.MAP_ZOOM);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    markerClusterGroup = L.markerClusterGroup();
    heatmapLayer = L.heatLayer([], {
        radius: config.HEATMAP_RADIUS,
        blur: config.HEATMAP_BLUR,
        maxZoom: config.HEATMAP_MAX_ZOOM
    });

    map.on('zoomend', updateMapView);
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

initMap();

let map = L.map('map').setView([39.8283, -98.5795], 4);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Create a marker cluster group
let markerClusterGroup = L.markerClusterGroup();

// Create an array to store heatmap data
let heatmapData = [];

// Fetch voter data and add markers
fetch('voters.json')
    .then(response => response.json())
    .then(data => {
        data.forEach(voter => {
            let marker = L.marker([voter.latitude, voter.longitude]);
            marker.bindPopup(`Voter ID: ${voter.id}<br>Party: ${voter.party}`);
            markerClusterGroup.addLayer(marker);

            // Add data point for heatmap
            heatmapData.push([voter.latitude, voter.longitude, 1]);
        });

        // Add the marker cluster group to the map
        map.addLayer(markerClusterGroup);

        // Create and add the heatmap layer
        let heatmapLayer = L.heatLayer(heatmapData, {
            radius: 20,
            blur: 15,
            maxZoom: 10 // Adjust this value to set when to switch from heatmap to markers
        }).addTo(map);

        // Function to toggle between heatmap and markers based on zoom level
        function updateMapView() {
            let currentZoom = map.getZoom();
            if (currentZoom > 10) { // Adjust this value to match maxZoom in heatmapLayer options
                map.removeLayer(heatmapLayer);
                map.addLayer(markerClusterGroup);
            } else {
                map.removeLayer(markerClusterGroup);
                map.addLayer(heatmapLayer);
            }
        }

        // Listen for zoom events
        map.on('zoomend', updateMapView);

        // Initial call to set the correct view
        updateMapView();
    });


async function loadMapData() {
    try {
        const response = await fetch('data/map_data.json');
        const data = await response.json();
        
        L.geoJSON(data, {
            pointToLayer: function(feature, latlng) {
                heatmapLayer.addLatLng(latlng);
                return L.circleMarker(latlng, {
                    radius: 6,
                    fillColor: "#007bff",
                    color: "#fff",
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8
                });
            },
            onEachFeature: function(feature, layer) {
                let popupContent = `
                    <div class="info-box">
                        <strong>Address:</strong> ${feature.properties.address}<br>
                        <strong>Precinct:</strong> ${feature.properties.precinct}<br>
                        <strong>Ballot Style:</strong> ${feature.properties.ballot_style}
                    </div>
                `;
                layer.bindPopup(popupContent);
            }
        }).addTo(markerClusterGroup);

        updateMapView();
    } catch (error) {
        console.error('Error loading map data:', error);
        alert('Error loading map data. Please try again later.');
    }
}

function showNearbyLocations(center) {
    markerClusterGroup.eachLayer(function(layer) {
        if (layer.feature) {
            const distance = map.distance(
                center,
                [layer.feature.geometry.coordinates[1], layer.feature.geometry.coordinates[0]]
            );
            if (distance <= config.NEARBY_RADIUS) {
                layer.setStyle({
                    fillColor: '#28a745',
                    radius: 8
                });
            } else {
                layer.setStyle({
                    fillColor: '#007bff',
                    radius: 6
                });
            }
        }
    });
}

loadMapData();

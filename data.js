async function loadMapData() {
    try {
        const [mapDataResponse, votingLocationsResponse] = await Promise.all([
            fetch('data/map_data.json'),
            fetch('data/voting_locations.json')
        ]);

        const mapData = await mapDataResponse.json();
        const votingLocations = await votingLocationsResponse.json();
        
        // Load map data
        L.geoJSON(mapData, {
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

        // Load voting locations
        loadVotingLocations(votingLocations);

        updateMapView();
    } catch (error) {
        console.error('Error loading data:', error);
        alert('Error loading data. Please try again later.');
    }
}

function loadVotingLocations(locations) {
    const votingLocationIcon = L.divIcon({
        html: '<i class="fas fa-house-user voting-location-icon"></i>',
        iconSize: [32, 32],
        className: 'voting-location-icon'
    });

    locations.forEach(location => {
        const marker = L.marker([parseFloat(location.latitude), parseFloat(location.longitude)], { icon: votingLocationIcon })
            .bindPopup(`
                <strong>${location.location}</strong><br>
                Address: ${location.address}<br>
                City: ${location.city}<br>
                Voting Area: ${location.voting_area}
            `);
        votingLocationsLayer.addLayer(marker);
    });

    // Add the voting locations layer to the map
    map.addLayer(votingLocationsLayer);
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

// map.js
let map, markerClusterGroup, heatmapLayer, votingLocationsLayer, votingLocationsControl;

function initMap() {
  map = L.map('map').setView(config.MAP_CENTER, config.MAP_ZOOM);

  // Create custom icon using Font Awesome - ADD THIS NEW CODE
  var customIcon = L.divIcon({
    html: '<i class="fa-solid fa-flag-usa"></i>',
    iconSize: [32, 32],
    className: 'custom-div-icon'
  });

  // Set as default icon for all markers - ADD THIS NEW CODE
  L.Marker.prototype.options.icon = customIcon;

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '© OpenStreetMap contributors | DL-R23'
  }).addTo(map);

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
    iconCreateFunction: function (cluster) {
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

  
  heatmapLayer = L.heatLayer([], {
    radius: config.HEATMAP_RADIUS,
    blur: config.HEATMAP_BLUR,
    maxZoom: config.HEATMAP_MAX_ZOOM,
    max: 1.0,
    minOpacity: 0.1,
    maxOpacity: 0.6,  // Adjust this value between 0 and 1 (default is 0.6)
  });

  // Create a new layer group for voting locations
  votingLocationsLayer = L.layerGroup();

  // Add control panel for toggling voting locations
  votingLocationsControl = L.control.layers(null, { "Voting Locations": votingLocationsLayer }, { collapsed: false });
  votingLocationsControl.addTo(map);

  map.on('zoomend', updateMapView);

  // Add geolocation control
  addGeolocationControl();

  // Load map data and voting locations
  loadMapData();
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

function addGeolocationControl() {
  const geolocationButton = document.getElementById('geolocation-button');
  if (geolocationButton) {
    geolocationButton.addEventListener('click', centerMapOnUserLocation);
  } else {
    console.error("Geolocation button not found");
  }
}

function centerMapOnUserLocation() {
  if ("geolocation" in navigator) {
    const geolocationButton = document.getElementById('geolocation-button');
    geolocationButton.classList.add('loading');
    geolocationButton.disabled = true;

    navigator.geolocation.getCurrentPosition(function (position) {
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
    }, function (error) {
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

function reverseGeocode(lat, lng) {
  const geocoder = new google.maps.Geocoder();
  const latlng = { lat: lat, lng: lng };

  geocoder.geocode({ location: latlng }, (results, status) => {
    if (status === "OK") {
      if (results[0]) {
        const address = results[0].formatted_address;
        document.getElementById('search-input').value = address;
      } else {
        console.log("No results found");
      }
    } else {
      console.log("Geocoder failed due to: " + status);
    }
  });
}

function loadVotingLocations(icon) {
  fetch('data/voting_locations.json')
    .then(response => response.json())
    .then(data => {
      data.forEach(location => {
        const marker = L.marker([location.latitude, location.longitude], { icon: icon })
          .bindPopup(`
            <strong>${location.location}</strong><br>
            Address: ${location.address}<br>
            City: ${location.city}<br>
            Voting Area: ${location.voting_area}
          `);
        votingLocationsLayer.addLayer(marker);
      });
      votingLocationsLayer.addTo(map);
    })
    .catch(error => console.error('Error loading voting locations:', error));
}

// Make sure to export the initMap function
window.initMap = initMap;

// Call initMap when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', initMap);

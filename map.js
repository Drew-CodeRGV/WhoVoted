// map.js
let map, markerClusterGroup, heatmapLayer, votingLocationsLayer, votingLocationsControl, districtLayer;

// Initialize map configurations
const mapConfig = {
  center: config.MAP_CENTER,
  zoom: config.MAP_ZOOM,
  maxZoom: 18,
  minZoom: 5
};

// District data configuration
const districtData = {
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "McAllen District 1",
        "style": { "color": "#FF0000", "weight": 2, "opacity": 0.7, "fillOpacity": 0.2 }
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-98.2235, 26.2815], [-98.2392, 26.2814], [-98.2392, 26.2627], [-98.2235, 26.2627], [-98.2235, 26.2815]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "McAllen District 2",
        "style": { "color": "#00FF00", "weight": 2, "opacity": 0.7, "fillOpacity": 0.2 }
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-98.2392, 26.2814], [-98.2571, 26.2814], [-98.2571, 26.2734], [-98.2392, 26.2734], [-98.2392, 26.2814]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "McAllen District 3",
        "style": { "color": "#808080", "weight": 2, "opacity": 0.7, "fillOpacity": 0.2 }
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-98.2235, 26.2627], [-98.2392, 26.2627], [-98.2392, 26.1896], [-98.2235, 26.1896], [-98.2235, 26.2627]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "McAllen District 4",
        "style": { "color": "#0000FF", "weight": 2, "opacity": 0.7, "fillOpacity": 0.2 }
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-98.2392, 26.2165], [-98.2701, 26.2165], [-98.2701, 26.1896], [-98.2392, 26.1896], [-98.2392, 26.2165]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "McAllen District 5",
        "style": { "color": "#800080", "weight": 2, "opacity": 0.7, "fillOpacity": 0.2 }
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-98.2483, 26.2734], [-98.2571, 26.2734], [-98.2571, 26.2165], [-98.2483, 26.2165], [-98.2483, 26.2734]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "McAllen District 6",
        "style": { "color": "#FFFF00", "weight": 2, "opacity": 0.7, "fillOpacity": 0.2 }
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-98.2392, 26.2627], [-98.2483, 26.2627], [-98.2483, 26.2165], [-98.2392, 26.2165], [-98.2392, 26.2627]]]
      }
    }
  ]
};

function initMap() {
  // Initialize map
  map = L.map('map', mapConfig);

  // Add base tile layer
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '© OpenStreetMap contributors | DL-R23'
  }).addTo(map);

  // Initialize layers
  initializeLayers();
  
  // Add controls
  addControls();
  
  // Add event listeners
  addEventListeners();
  
  // Load data
  loadData();
}

function initializeLayers() {
  // Create marker cluster group
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
    iconCreateFunction: createClusterIcon
  });

  // Initialize heatmap layer
  heatmapLayer = L.heatLayer([], {
    radius: config.HEATMAP_RADIUS,
    blur: config.HEATMAP_BLUR,
    maxZoom: config.HEATMAP_MAX_ZOOM,
    max: 1.0,
    minOpacity: 0.1,
    maxOpacity: 0.6
  });

  // Initialize voting locations layer
  votingLocationsLayer = L.layerGroup();
  
  // Initialize district layer
  districtLayer = L.layerGroup();
}

function addControls() {
  // Add district control
  const districtControl = createDistrictControl();
  map.addControl(districtControl);

  // Add layer control
  votingLocationsControl = L.control.layers(null, {
    "Voting Locations": votingLocationsLayer
  }, { collapsed: false });
  votingLocationsControl.addTo(map);

  // Add geolocation control
  addGeolocationControl();
}

function createDistrictControl() {
  const LayerControl = L.Control.extend({
    options: { position: 'topright' },
    onAdd: function() {
      const container = L.DomUtil.create('div', 'district-control');
      container.innerHTML = `
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
      return container;
    }
  });
  return new LayerControl();
}

function addEventListeners() {
  // Map zoom event
  map.on('zoomend', updateMapView);

  // District controls
  document.getElementById('district-toggle')?.addEventListener('change', toggleDistricts);
  document.getElementById('district-opacity')?.addEventListener('input', updateDistrictOpacity);
}

function loadData() {
  // Add districts to map
  addDistrictsToMap();
  
  // Load voting locations
  loadVotingLocations();
}

function addDistrictsToMap() {
  L.geoJSON(districtData, {
    style: feature => feature.properties.style,
    onEachFeature: (feature, layer) => {
      layer.bindPopup(feature.properties.name);
      districtLayer.addLayer(layer);
    }
  });
}

function toggleDistricts(e) {
  if (e.target.checked) {
    districtLayer.addTo(map);
  } else {
    districtLayer.remove();
  }
}

function updateDistrictOpacity(e) {
  const opacity = e.target.value / 100;
  document.getElementById('opacity-value').textContent = e.target.value + '%';
  
  districtLayer.eachLayer(layer => {
    layer.setStyle({
      fillOpacity: opacity * 0.2,
      opacity: opacity
    });
  });
}

function updateMapView() {
  const currentZoom = map.getZoom();
  if (currentZoom > config.HEATMAP_MAX_ZOOM) {
    map.removeLayer(heatmapLayer);
    map.addLayer(markerClusterGroup);
  } else {
    map.removeLayer(markerClusterGroup);
    map.addLayer(heatmapLayer);
  }
}

function loadVotingLocations() {
  fetch('data/voting_locations.json')
    .then(response => response.json())
    .then(data => {
      data.forEach(location => {
        const marker = L.marker([location.latitude, location.longitude])
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

function createClusterIcon(cluster) {
  const childCount = cluster.getChildCount();
  let c = ' marker-cluster-';
  c += childCount < 5 ? 'small' : childCount < 25 ? 'medium' : 'large';
  
  return new L.DivIcon({
    html: '<div><span>' + childCount + '</span></div>',
    className: 'marker-cluster' + c,
    iconSize: new L.Point(40, 40)
  });
}

// Initialize map when DOM is loaded
document.addEventListener('DOMContentLoaded', initMap);

// Export for global access
window.initMap = initMap;

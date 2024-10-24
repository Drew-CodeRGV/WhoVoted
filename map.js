// map.js
let map, markerClusterGroup, heatmapLayer;

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
    attribution: '© OpenStreetMap contributors | DL-R22'
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

  // Rest of your code remains the same...

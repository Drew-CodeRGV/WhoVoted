// map.js
let map;
let markers = [];
const dataPoints = [];

async function initMap() {
  // Initialize the map centered on Hidalgo County
  map = L.map('map').setView([26.3017, -98.1634], 11);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(map);

  // Load map data
  try {
    const response = await fetch('data/map_data.json');
    const data = await response.json();
    data.features.forEach(feature => {
      const marker = L.marker([
        feature.geometry.coordinates[1],
        feature.geometry.coordinates[0]
      ]);

      marker.bindPopup(`
                <strong>Address:</strong> ${feature.properties.address}<br>
                <strong>Precinct:</strong> ${feature.properties.precinct}<br>
                <strong>Ballot Style:</strong> ${feature.properties.ballot_style}
            `);

      dataPoints.push({
        marker: marker,
        coords: [feature.geometry.coordinates[1], feature.geometry.coordinates[0]]
      });
    });
  } catch (error) {
    console.error('Error loading map data:', error);
  }
}

function showNearbyPoints(lat, lng, radius = 0.01) {
  // Clear existing markers
  markers.forEach(marker => map.removeLayer(marker));
  markers = [];

  // Show points within radius
  dataPoints.forEach(point => {
    const distance = Math.sqrt(
      Math.pow(point.coords[0] - lat, 2) +
      Math.pow(point.coords[1] - lng, 2)
    );

    if (distance <= radius) {
      point.marker.addTo(map);
      markers.push(point.marker);
    }
  });
}

// Initialize map
initMap();

// search.js
const searchInput = document.getElementById('search-input');
const suggestionsContainer = document.getElementById('suggestions-container');
let debounceTimer;

searchInput.addEventListener('input', function (e) {
  clearTimeout(debounceTimer);
  const query = e.target.value.trim();

  if (query.length < 3) {
    suggestionsContainer.style.display = 'none';
    return;
  }

  debounceTimer = setTimeout(() => {
    fetchAddressSuggestions(query);
  }, 300);
});

async function fetchAddressSuggestions(query) {
  searchInput.classList.add('loading');
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&countrycodes=us&limit=5`
    );
    const data = await response.json();

    displaySuggestions(data);
  } catch (error) {
    console.error('Error fetching suggestions:', error);
  } finally {
    searchInput.classList.remove('loading');
  }
}

function displaySuggestions(suggestions) {
  suggestionsContainer.innerHTML = '';

  if (suggestions.length === 0) {
    suggestionsContainer.style.display = 'none';
    return;
  }

  suggestions.forEach(suggestion => {
    const div = document.createElement('div');
    div.className = 'suggestion-item';
    div.textContent = suggestion.display_name;

    div.addEventListener('click', () => {
      searchInput.value = suggestion.display_name;
      suggestionsContainer.style.display = 'none';

      // Center map on selected location
      map.setView([suggestion.lat, suggestion.lon], 15);
      showNearbyPoints(suggestion.lat, suggestion.lon);
    });

    suggestionsContainer.appendChild(div);
  });

  suggestionsContainer.style.display = 'block';
}

// Close suggestions when clicking outside
document.addEventListener('click', function (e) {
  if (!suggestionsContainer.contains(e.target) && e.target !== searchInput) {
    suggestionsContainer.style.display = 'none';
  }
});

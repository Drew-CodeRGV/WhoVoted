// Search functionality using Nominatim
let searchTimeout = null;

const searchInput = document.getElementById('search-input');
const searchButton = document.getElementById('search-button');

// Create search results dropdown
const searchResults = document.createElement('div');
searchResults.className = 'search-results';
searchInput.parentElement.appendChild(searchResults);
searchInput.parentElement.style.position = 'relative';

// Search input handler with debouncing
searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    const query = e.target.value.trim();
    
    if (query.length < 3) {
        searchResults.classList.remove('show');
        return;
    }
    
    searchTimeout = setTimeout(() => {
        searchAddress(query);
    }, 300);
});

// Search button handler
searchButton.addEventListener('click', () => {
    const query = searchInput.value.trim();
    if (query) {
        searchAddress(query);
    }
});

// Enter key handler
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        const query = searchInput.value.trim();
        if (query) {
            searchAddress(query);
        }
    }
});

// Search address using Nominatim
async function searchAddress(query) {
    try {
        const params = new URLSearchParams({
            q: query,
            format: 'json',
            limit: 5,
            countrycodes: 'us',
            bounded: 1,
            viewbox: '-98.5,26.5,-97.5,25.5' // Hidalgo/Cameron County bounds
        });
        
        const response = await fetch(`${config.NOMINATIM_ENDPOINT}/search?${params}`, {
            headers: {
                'User-Agent': config.USER_AGENT
            }
        });
        
        if (!response.ok) {
            throw new Error('Search failed');
        }
        
        const results = await response.json();
        displaySearchResults(results);
    } catch (error) {
        console.error('Search error:', error);
        searchResults.innerHTML = '<div class="search-result-item">Search temporarily unavailable</div>';
        searchResults.classList.add('show');
    }
}

// Display search results
function displaySearchResults(results) {
    if (results.length === 0) {
        searchResults.innerHTML = '<div class="search-result-item">No results found</div>';
        searchResults.classList.add('show');
        return;
    }
    
    searchResults.innerHTML = results.map(result => `
        <div class="search-result-item" data-lat="${result.lat}" data-lng="${result.lon}">
            ${result.display_name}
        </div>
    `).join('');
    
    searchResults.classList.add('show');
    
    // Add click handlers to results
    searchResults.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
            const lat = parseFloat(item.dataset.lat);
            const lng = parseFloat(item.dataset.lng);
            selectAddress(lat, lng, item.textContent);
        });
    });
}

// Handle address selection
function selectAddress(lat, lng, address) {
    map.setView([lat, lng], 16);
    addCustomMarker([lat, lng]).bindPopup(address).openPopup();
    searchResults.classList.remove('show');
    searchInput.value = address;
}

// Reverse geocode coordinates to address
async function reverseGeocode(lat, lng) {
    try {
        const params = new URLSearchParams({
            lat: lat,
            lon: lng,
            format: 'json'
        });
        
        const response = await fetch(`${config.NOMINATIM_ENDPOINT}/reverse?${params}`, {
            headers: {
                'User-Agent': config.USER_AGENT
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.display_name) {
                searchInput.value = data.display_name;
            }
        }
    } catch (error) {
        console.error('Reverse geocoding error:', error);
    }
}

// Close search results when clicking outside
document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
        searchResults.classList.remove('show');
    }
});

// Search functionality using Nominatim - Bottom-left icon + popup
let searchTimeout = null;

// Create geolocation icon button (standalone, next to info and search icons)
const geoIconBtn = document.createElement('button');
geoIconBtn.className = 'geo-icon-btn';
geoIconBtn.id = 'geolocation-button';
geoIconBtn.title = 'Find my location';
geoIconBtn.innerHTML = '<i class="fas fa-crosshairs"></i>';
document.body.appendChild(geoIconBtn);

// Create search icon button
const searchIconBtn = document.createElement('button');
searchIconBtn.className = 'search-icon-btn';
searchIconBtn.title = 'Search Address';
searchIconBtn.innerHTML = '<i class="fas fa-search"></i>';
document.body.appendChild(searchIconBtn);

// Create search popup
const searchPopup = document.createElement('div');
searchPopup.className = 'search-popup';
searchPopup.innerHTML = `
    <div class="search-popup-inner">
        <input id="search-input" type="text" placeholder="Search for an address">
        <button class="search-popup-btn" id="search-button">Search</button>
    </div>
`;
document.body.appendChild(searchPopup);

// Get references to new elements
const searchInput = document.getElementById('search-input');
const searchButton = document.getElementById('search-button');
let isSearchOpen = false;

// Create search results dropdown inside popup
const searchResults = document.createElement('div');
searchResults.className = 'search-results';
searchPopup.querySelector('.search-popup-inner').appendChild(searchResults);

// Toggle search popup on icon click
searchIconBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    isSearchOpen = !isSearchOpen;
    searchPopup.classList.toggle('open', isSearchOpen);
    searchIconBtn.classList.toggle('active', isSearchOpen);
    if (isSearchOpen) {
        searchInput.focus();
    }
});

// Close search popup when clicking outside
document.addEventListener('click', (e) => {
    if (isSearchOpen && !searchPopup.contains(e.target) && !searchIconBtn.contains(e.target)) {
        isSearchOpen = false;
        searchPopup.classList.remove('open');
        searchIconBtn.classList.remove('active');
        searchResults.classList.remove('show');
    }
});

// Prevent popup clicks from closing it
searchPopup.addEventListener('click', (e) => e.stopPropagation());

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
            viewbox: '-98.5,26.5,-97.5,25.5'
        });
        
        const response = await fetch(`${config.NOMINATIM_ENDPOINT}/search?${params}`, {
            headers: { 'User-Agent': config.USER_AGENT }
        });
        
        if (!response.ok) throw new Error('Search failed');
        
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
    
    searchResults.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
            const lat = parseFloat(item.dataset.lat);
            const lng = parseFloat(item.dataset.lng);
            selectAddress(lat, lng, item.textContent.trim());
        });
    });
}

// Handle address selection
function selectAddress(lat, lng, address) {
    map.setView([lat, lng], 16);
    addCustomMarker([lat, lng]).bindPopup(address).openPopup();
    searchResults.classList.remove('show');
    searchInput.value = address;
    // Close popup after selection
    isSearchOpen = false;
    searchPopup.classList.remove('open');
    searchIconBtn.classList.remove('active');
}

// Reverse geocode coordinates to address
async function reverseGeocode(lat, lng) {
    try {
        const params = new URLSearchParams({ lat, lon: lng, format: 'json' });
        const response = await fetch(`${config.NOMINATIM_ENDPOINT}/reverse?${params}`, {
            headers: { 'User-Agent': config.USER_AGENT }
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

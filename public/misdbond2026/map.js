// McAllen ISD Bond 2026 - Map and Data Visualization

let map;
let markerClusterGroup = null;
let heatLayer = null;
let allVotersData = null;
let mcallenOnly = true;

// Fun loading messages
const loadingMessages = [
    "Loading scantron cards...",
    "Sharpening pencils...",
    "Counting ballots...",
    "Checking voter rolls...",
    "Organizing precinct maps...",
    "Brewing coffee for poll workers...",
    "Printing voter guides...",
    "Setting up voting booths...",
    "Calibrating ballot scanners...",
    "Preparing election results..."
];

let currentMessageIndex = 0;
let loadingStartTime = 0;

// Show loading screen
function showLoading() {
    loadingStartTime = Date.now();
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'loading-screen';
    loadingDiv.innerHTML = `
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                    background: rgba(255,255,255,0.95); z-index: 10000; 
                    display: flex; flex-direction: column; align-items: center; justify-content: center;">
            <div style="text-align: center;">
                <div style="width: 80px; height: 80px; margin: 0 auto 20px;">
                    <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="50" cy="50" r="45" fill="none" stroke="#e0e0e0" stroke-width="8"/>
                        <circle cx="50" cy="50" r="45" fill="none" stroke="#0066cc" stroke-width="8" 
                                stroke-dasharray="283" stroke-dashoffset="283" 
                                stroke-linecap="round" transform="rotate(-90 50 50)">
                            <animate attributeName="stroke-dashoffset" from="283" to="0" 
                                     dur="3s" repeatCount="indefinite"/>
                        </circle>
                    </svg>
                </div>
                <div style="font-size: 24px; font-weight: 600; color: #333; margin-bottom: 10px;">
                    Loading Voter Data
                </div>
                <div id="loading-message" style="font-size: 14px; color: #666; font-style: italic; min-height: 20px;">
                    ${loadingMessages[0]}
                </div>
                <div id="loading-progress" style="margin-top: 15px; font-size: 12px; color: #999;">
                    <span id="loading-time">0.0s</span> elapsed
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(loadingDiv);
    
    // Rotate messages every 1.5 seconds
    const messageInterval = setInterval(() => {
        currentMessageIndex = (currentMessageIndex + 1) % loadingMessages.length;
        const msgEl = document.getElementById('loading-message');
        if (msgEl) {
            msgEl.textContent = loadingMessages[currentMessageIndex];
        } else {
            clearInterval(messageInterval);
        }
    }, 1500);
    
    // Update elapsed time
    const timeInterval = setInterval(() => {
        const elapsed = (Date.now() - loadingStartTime) / 1000;
        const timeEl = document.getElementById('loading-time');
        if (timeEl) {
            timeEl.textContent = elapsed.toFixed(1) + 's';
        } else {
            clearInterval(timeInterval);
        }
    }, 100);
}

// Hide loading screen
function hideLoading() {
    const loadingDiv = document.getElementById('loading-screen');
    if (loadingDiv) {
        const elapsed = (Date.now() - loadingStartTime) / 1000;
        console.log(`Data loaded in ${elapsed.toFixed(2)}s`);
        loadingDiv.remove();
    }
}

// Initialize map
function initMap() {
    // Center on McAllen - centered on the heatmap mass
    map = L.map('map').setView([26.2300, -98.2350], 12);
    
    // Use same tile layer as main politiquera.com
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);
    
    // Initialize marker cluster group - invisible clusters (no circles, no numbers)
    markerClusterGroup = L.markerClusterGroup({
        maxClusterRadius: 50,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        iconCreateFunction: function(cluster) {
            // Completely invisible cluster icon - no circle, no number
            return L.divIcon({
                html: '',
                className: 'invisible-cluster',
                iconSize: L.point(1, 1)
            });
        }
    });
    
    map.addLayer(markerClusterGroup);
    
    // Setup event listeners
    setupEventListeners();
    
    loadData();
}

// Setup event listeners
function setupEventListeners() {
    // Search functionality
    const searchInput = document.getElementById('search-input');
    searchInput.addEventListener('input', handleSearch);
    
    // GPS location button
    const locationBtn = document.getElementById('location-btn');
    locationBtn.addEventListener('click', zoomToUserLocation);
    
    // McAllen filter checkbox
    const mcallenFilter = document.getElementById('mcallen-filter');
    mcallenFilter.addEventListener('change', handleFilterChange);
}

// Handle search - show live results dropdown
function handleSearch(e) {
    const query = e.target.value.toLowerCase().trim();
    const resultsDiv = document.getElementById('search-results');
    
    if (!query || query.length < 2 || !allVotersData) {
        resultsDiv.classList.remove('visible');
        resultsDiv.innerHTML = '';
        return;
    }
    
    // Search through mapped voters
    const mappedResults = allVotersData.voters.filter(voter => {
        const name = voter.name.toLowerCase();
        const address = (voter.address || '').toLowerCase();
        return name.includes(query) || address.includes(query);
    }).slice(0, 6);
    
    // Search through unmapped voters
    const unmappedResults = (allVotersData.unmapped || []).filter(voter => {
        const name = voter.name.toLowerCase();
        return name.includes(query);
    }).slice(0, 4);
    
    const allResults = [...mappedResults, ...unmappedResults];
    
    if (allResults.length === 0) {
        resultsDiv.innerHTML = '<div class="search-result-item" style="color:#999;cursor:default;">No results found</div>';
        resultsDiv.classList.add('visible');
        return;
    }
    
    resultsDiv.innerHTML = allResults.map((voter, i) => {
        const isUnmapped = voter.unmapped;
        const badge = isUnmapped ? '<span style="background:#f0ad4e;color:white;font-size:9px;padding:1px 5px;border-radius:3px;margin-left:6px;">Voted, but unmapped</span>' : '';
        const address = isUnmapped ? (voter.precinct ? 'Precinct ' + voter.precinct : 'No address on file') : (voter.address || 'No address');
        return `<div class="search-result-item" data-index="${i}" data-unmapped="${isUnmapped ? '1' : '0'}">
            <div class="search-result-name">${voter.name}${badge}</div>
            <div class="search-result-address">${address}</div>
        </div>`;
    }).join('');
    resultsDiv.classList.add('visible');
    
    // Click handler for each result
    resultsDiv.querySelectorAll('.search-result-item[data-index]').forEach(item => {
        item.addEventListener('click', () => {
            const idx = parseInt(item.dataset.index);
            const isUnmapped = item.dataset.unmapped === '1';
            
            if (isUnmapped) {
                // Can't zoom to unmapped voter - just show their name
                document.getElementById('search-input').value = allResults[idx].name;
                resultsDiv.classList.remove('visible');
                return;
            }
            
            const voter = allResults[idx];
            if (!voter || !voter.lat) return;
            
            resultsDiv.classList.remove('visible');
            document.getElementById('search-input').value = voter.name;
            
            // Zoom to voter
            map.setView([voter.lat, voter.lng], 17);
            markerClusterGroup.eachLayer(marker => {
                const latlng = marker.getLatLng();
                if (Math.abs(latlng.lat - voter.lat) < 0.0001 && Math.abs(latlng.lng - voter.lng) < 0.0001) {
                    markerClusterGroup.zoomToShowLayer(marker, () => {
                        marker.openPopup();
                    });
                }
            });
        });
    });
}

// Close search results when clicking outside
document.addEventListener('click', function(e) {
    const resultsDiv = document.getElementById('search-results');
    const searchInput = document.getElementById('search-input');
    if (resultsDiv && !resultsDiv.contains(e.target) && e.target !== searchInput) {
        resultsDiv.classList.remove('visible');
    }
});

// Zoom to user's GPS location
function zoomToUserLocation() {
    if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser');
        return;
    }
    
    const locationBtn = document.getElementById('location-btn');
    locationBtn.disabled = true;
    locationBtn.innerHTML = 'Locating...';
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            
            map.setView([lat, lng], 15);
            
            // Add temporary marker
            const userMarker = L.marker([lat, lng], {
                icon: L.divIcon({
                    className: 'user-location-marker',
                    html: '<div style="background: #0066cc; width: 16px; height: 16px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 8px rgba(0,0,0,0.3);"></div>',
                    iconSize: [16, 16]
                })
            }).addTo(map);
            
            userMarker.bindPopup('You are here').openPopup();
            
            setTimeout(() => map.removeLayer(userMarker), 5000);
            
            locationBtn.disabled = false;
            locationBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>My Location';
        },
        (error) => {
            let errorMsg = 'Unable to get your location';
            if (error.code === error.PERMISSION_DENIED) {
                errorMsg = 'Location permission denied. Please enable location services in your browser settings.';
            } else if (error.code === error.POSITION_UNAVAILABLE) {
                errorMsg = 'Location information unavailable.';
            } else if (error.code === error.TIMEOUT) {
                errorMsg = 'Location request timed out.';
            }
            alert(errorMsg);
            locationBtn.disabled = false;
            locationBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>My Location';
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
}

// Handle filter change
async function handleFilterChange(e) {
    mcallenOnly = e.target.checked;
    
    // For now, just reload from cache (McAllen only)
    // TODO: Add support for all voters when needed
    showLoading();
    
    try {
        const cacheResponse = await fetch('/cache/misdbond2026_voters.json');
        
        if (!cacheResponse.ok) {
            throw new Error('Cache file not found');
        }
        
        const voters = await cacheResponse.json();
        allVotersData = voters;
        
        // Get last update time from cache file headers
        const lastModified = cacheResponse.headers.get('Last-Modified');
        const lastUpdate = lastModified ? new Date(lastModified).toISOString() : new Date().toISOString();
        
        const totalVoters = voters.count || (voters.voters ? voters.voters.length : 0);
        const totalVoted = voters.total_voted || totalVoters;
        updateStats({ 
            total_voters: totalVoters,
            total_voted: totalVoted,
            last_update: lastUpdate
        });
        updateMap({}, voters);
        
        hideLoading();
    } catch (error) {
        hideLoading();
        console.error('Error reloading data:', error);
    }
}
// Load voter data
async function loadData() {
    showLoading();
    
    try {
        // Load from static cache (fast and reliable)
        const cacheResponse = await fetch('/cache/misdbond2026_voters.json');
        
        if (!cacheResponse.ok) {
            throw new Error('Cache file not found');
        }
        
        const voters = await cacheResponse.json();
        console.log('Loaded from cache:', voters.count, 'voters');
        
        allVotersData = voters;
        
        // Get last update time from cache file headers
        const lastModified = cacheResponse.headers.get('Last-Modified');
        const lastUpdate = lastModified ? new Date(lastModified).toISOString() : new Date().toISOString();
        
        // Use cached count for stats
        const totalVoters = voters.count || (voters.voters ? voters.voters.length : 0);
        const totalVoted = voters.total_voted || totalVoters;
        updateStats({ 
            total_voters: totalVoters,
            total_voted: totalVoted,
            last_update: lastUpdate,
            method_breakdown: voters.method_breakdown
        });
        
        // Update map
        updateMap({}, voters);
        
        hideLoading();
        
        // Show banner 3 seconds after data is fully loaded
        showBannerAfterDelay();
    } catch (error) {
        hideLoading();
        console.error('Error loading data:', error);
        document.querySelector('.header-bar').insertAdjacentHTML('afterend', 
            '<div style="position: fixed; top: 70px; left: 50%; transform: translateX(-50%); background: #f44336; color: white; padding: 10px 20px; border-radius: 4px; z-index: 10001;">Unable to load data. Please try again later.</div>');
    }
}

// Show banner after data is loaded
let bannerTimeout = null;

function showBannerAfterDelay() {
    setTimeout(() => {
        const banner = document.getElementById('sliding-banner');
        if (banner) {
            banner.classList.remove('hidden');
            
            // Auto-hide after 5 seconds
            bannerTimeout = setTimeout(hideBanner, 5000);
            
            // Hide on any tap/click anywhere
            document.addEventListener('click', hideBannerOnTap, { once: true });
            document.addEventListener('touchstart', hideBannerOnTap, { once: true });
        }
    }, 7000);
}

function hideBanner() {
    const banner = document.getElementById('sliding-banner');
    const tab = document.getElementById('banner-tab');
    if (banner) banner.classList.add('hidden');
    if (tab) tab.classList.add('visible');
    if (bannerTimeout) { clearTimeout(bannerTimeout); bannerTimeout = null; }
}

function hideBannerOnTap(e) {
    // Don't hide if they clicked the banner link itself
    const banner = document.getElementById('sliding-banner');
    if (banner && banner.contains(e.target)) return;
    hideBanner();
    // Remove the other listener too
    document.removeEventListener('click', hideBannerOnTap);
    document.removeEventListener('touchstart', hideBannerOnTap);
}

// Update statistics
function updateStats(data) {
    // Show total_voted (mapped + unmapped) if available
    const totalVoted = data.total_voted || data.total_voters;
    const el = document.getElementById('total-voters');
    el.textContent = totalVoted.toLocaleString();
    el.style.cursor = 'pointer';
    el.title = 'Click for breakdown';
    
    // Store method breakdown for click handler
    if (data.method_breakdown) {
        el.onclick = function() {
            const mb = data.method_breakdown;
            const early = mb['early-voting'] || 0;
            const mailin = mb['mail-in'] || 0;
            const eday = mb['election-day'] || 0;
            const other = totalVoted - early - mailin - eday;
            let msg = '🗳️ Voting Method Breakdown\n\n';
            msg += '🏫 In-Person Early: ' + early.toLocaleString() + '\n';
            msg += '📬 Mail-In: ' + mailin.toLocaleString() + '\n';
            if (eday > 0) msg += '📍 Election Day: ' + eday.toLocaleString() + '\n';
            if (other > 0) msg += '❓ Unmapped: ' + other.toLocaleString() + '\n';
            msg += '\n📊 Total: ' + totalVoted.toLocaleString();
            alert(msg);
        };
    }
    
    // Update last update time from cache file metadata
    const lastUpdateEl = document.getElementById('last-update');
    if (lastUpdateEl && data.last_update) {
        const updateDate = new Date(data.last_update);
        const timeStr = updateDate.toLocaleString('en-US', { 
            month: 'short', 
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
        lastUpdateEl.textContent = timeStr;
    }
}

// Build voter card matching politiquera.com style
function buildVoterCard(voter) {
    const name = voter.name || 'Unknown';
    const party = voter.party_voted || voter.current_party || '';
    const pColor = party.toLowerCase().includes('democrat') ? '#1E90FF'
                 : party.toLowerCase().includes('republican') ? '#DC143C' : '#888';
    const gender = voter.sex === 'F' ? 'Female' : voter.sex === 'M' ? 'Male' : '';
    const currentYear = new Date().getFullYear();
    const age = voter.birth_year && voter.birth_year > 1900 ? (currentYear - voter.birth_year) : '';
    const ageStr = age ? `Age ${age}` : '';
    
    let html = '';
    // Name row with party dot
    html += `<div style="display:flex;align-items:center;gap:6px;margin-bottom:2px;">`;
    html += `<span style="width:10px;height:10px;border-radius:50%;background:${pColor};flex-shrink:0;"></span>`;
    html += `<span style="font-weight:600;font-size:13px;">${name}</span>`;
    html += `</div>`;
    
    // Details line: party · gender · age · precinct
    const details = [party, gender, ageStr, voter.precinct ? 'Pct ' + voter.precinct : ''].filter(Boolean).join(' · ');
    if (details) {
        html += `<div style="font-size:11px;color:#666;margin-bottom:3px;">${details}</div>`;
    }
    
    // Voting method badge
    const votingMethod = voter.voting_method || 'early-voting';
    if (votingMethod === 'early-voting') {
        html += `<div style="color:#2E7D32;font-size:11px;font-weight:600;margin-bottom:2px;">✓ Early Voter</div>`;
    }
    
    return html;
}

// Update map with voter locations
function updateMap(stats, voters) {
    // Clear existing markers
    if (markerClusterGroup) {
        markerClusterGroup.clearLayers();
    }
    
    if (heatLayer) {
        map.removeLayer(heatLayer);
    }
    
    // Create heat map data from individual voters
    const heatData = [];
    
    // Group voters by address for multi-voter households
    const addressGroups = {};
    if (voters && voters.voters) {
        voters.voters.forEach(voter => {
            if (voter.lat && voter.lng) {
                const key = `${voter.lat.toFixed(5)},${voter.lng.toFixed(5)}`;
                if (!addressGroups[key]) {
                    addressGroups[key] = [];
                }
                addressGroups[key].push(voter);
            }
        });
    }
    
    // Add individual voter markers with clustering
    Object.entries(addressGroups).forEach(([key, votersAtAddress]) => {
        const firstVoter = votersAtAddress[0];
        const lat = firstVoter.lat;
        const lng = firstVoter.lng;
        
        // Add to heat map
        heatData.push([lat, lng, votersAtAddress.length]);
        
        // Determine marker color based on party
        let markerColor = '#888';
        if (votersAtAddress.length === 1) {
            const party = votersAtAddress[0].party_voted || votersAtAddress[0].current_party || '';
            if (party.toLowerCase().includes('democrat')) {
                markerColor = '#1E90FF';
            } else if (party.toLowerCase().includes('republican')) {
                markerColor = '#DC143C';
            }
        } else {
            // Multi-voter household - use blue
            markerColor = '#0066cc';
        }
        
        // Create circle marker
        const marker = L.circleMarker([lat, lng], {
            radius: 6,
            fillColor: markerColor,
            color: '#ffffff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        });
        
        // Build popup content
        let popupHtml = `<div style="max-width:380px;">`;
        popupHtml += `<div style="font-size:11px;color:#888;margin-bottom:2px;">${firstVoter.address || 'N/A'}</div>`;
        
        if (votersAtAddress.length > 1) {
            popupHtml += `<div style="font-weight:700;font-size:13px;margin-bottom:6px;">${votersAtAddress.length} voters at this address</div>`;
        }
        
        votersAtAddress.forEach((voter, i) => {
            if (i > 0) {
                popupHtml += `<hr style="margin:6px 0;border:none;border-top:1px dashed #ddd;">`;
            }
            popupHtml += buildVoterCard(voter);
        });
        
        popupHtml += `</div>`;
        
        marker.bindPopup(popupHtml);
        markerClusterGroup.addLayer(marker);
    });
    
    // Add heat layer with politiquera.com colors - clean gradient
    if (heatData.length > 0) {
        heatLayer = L.heatLayer(heatData, {
            radius: 20,
            blur: 25,
            maxZoom: 15,
            max: 1.0,
            minOpacity: 0.3,
            gradient: {
                0.0: 'rgba(0, 0, 255, 0)',
                0.2: 'rgba(0, 0, 255, 0.4)',
                0.4: 'rgba(0, 255, 255, 0.5)',
                0.6: 'rgba(0, 255, 0, 0.6)',
                0.8: 'rgba(255, 255, 0, 0.7)',
                1.0: 'rgba(255, 0, 0, 0.8)'
            }
        }).addTo(map);
    }
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initMap);

// Auto-refresh every 5 minutes
setInterval(loadData, 5 * 60 * 1000);

// ── Heatmap mode toggle (voters vs opportunity vs non-voters) ──
let nonVoterHeatLayer = null;
let nonVoterDataCache = null;
let opportunityDataCache = null;
let districtBoundaryLayer = null;
let studentHeatLayer = null;
let studentElemLayer = null;
let studentMidLayer = null;
let studentHighLayer = null;
let studentDataCache = null;

async function setHeatmapMode(mode) {
    // Remove all overlay layers first
    if (nonVoterHeatLayer) map.removeLayer(nonVoterHeatLayer);
    if (studentHeatLayer) map.removeLayer(studentHeatLayer);
    if (studentElemLayer) map.removeLayer(studentElemLayer);
    if (studentMidLayer) map.removeLayer(studentMidLayer);
    if (studentHighLayer) map.removeLayer(studentHighLayer);
    if (oppRegularLayer) map.removeLayer(oppRegularLayer);
    if (oppOccasionalLayer) map.removeLayer(oppOccasionalLayer);
    if (oppNeverLayer) map.removeLayer(oppNeverLayer);
    document.getElementById('opp-type-select').style.display = 'none';
    document.getElementById('opp-type-mobile-row').style.display = 'none';
    document.getElementById('student-filters').style.display = 'none';
    
    if (mode === 'voters') {
        if (heatLayer) heatLayer.addTo(map);
        if (markerClusterGroup) map.addLayer(markerClusterGroup);
    } else {
        // Hide voter layers for non-voter modes
        if (heatLayer) map.removeLayer(heatLayer);
        if (markerClusterGroup) map.removeLayer(markerClusterGroup);
        
        if (mode === 'opportunity') {
            // Ensure voter layers are fully removed
            if (heatLayer) map.removeLayer(heatLayer);
            if (markerClusterGroup) map.removeLayer(markerClusterGroup);
            // Show the opportunity type dropdown
            document.getElementById('opp-type-select').style.display = '';
            document.getElementById('opp-type-mobile-row').style.display = '';
            await loadOpportunityLayers();
            applyOpportunityType(document.getElementById('opp-type-select').value);
        } else if (mode === 'students') {
            document.getElementById('student-filters').style.display = 'block';
            if (!studentElemLayer) {
                try {
                    const resp = await fetch('/cache/misdbond2026_students.json');
                    studentDataCache = await resp.json();
                    const maxVal = Math.max(...studentDataCache.tracts.map(t => t.total));
                    
                    // Elementary = Red
                    studentElemLayer = L.heatLayer(
                        studentDataCache.tracts.filter(t=>t.elem>0).map(t=>[t.lat,t.lng,t.elem]),
                        {radius:40, blur:20, maxZoom:16, max:maxVal*0.4, minOpacity:0.3,
                         gradient:{0:'rgba(220,0,0,0)',0.3:'rgba(220,0,0,0.4)',0.6:'rgba(200,0,0,0.65)',1:'rgba(160,0,0,0.85)'}});
                    // Middle = Yellow
                    studentMidLayer = L.heatLayer(
                        studentDataCache.tracts.filter(t=>t.middle>0).map(t=>[t.lat,t.lng,t.middle]),
                        {radius:40, blur:20, maxZoom:16, max:maxVal*0.4, minOpacity:0.3,
                         gradient:{0:'rgba(220,200,0,0)',0.3:'rgba(220,200,0,0.4)',0.6:'rgba(200,180,0,0.65)',1:'rgba(160,140,0,0.85)'}});
                    // High = Green
                    studentHighLayer = L.heatLayer(
                        studentDataCache.tracts.filter(t=>t.high>0).map(t=>[t.lat,t.lng,t.high]),
                        {radius:40, blur:20, maxZoom:16, max:maxVal*0.4, minOpacity:0.3,
                         gradient:{0:'rgba(0,160,0,0)',0.3:'rgba(0,160,0,0.4)',0.6:'rgba(0,140,0,0.65)',1:'rgba(0,110,0,0.85)'}});
                } catch(err) { console.error('Failed to load student data:', err); return; }
            }
            refreshStudentLayers();
        } else if (mode === 'nonvoters') {
            if (!nonVoterHeatLayer) {
                try {
                    if (!nonVoterDataCache) {
                        const resp = await fetch('/cache/misdbond2026_nonvoters.json');
                        nonVoterDataCache = await resp.json();
                    }
                    const heatData = nonVoterDataCache.points.map(p => [p[0], p[1], 0.5]);
                    nonVoterHeatLayer = L.heatLayer(heatData, {
                        radius: 12,
                        blur: 18,
                        maxZoom: 15,
                        max: 1.0,
                        minOpacity: 0.15,
                        gradient: {
                            0.0: 'rgba(100,149,237,0)',
                            0.3: 'rgba(100,149,237,0.15)',
                            0.5: 'rgba(65,105,225,0.25)',
                            0.7: 'rgba(30,80,200,0.35)',
                            1.0: 'rgba(0,50,160,0.45)'
                        }
                    });
                } catch(err) { console.error('Failed to load non-voter data:', err); return; }
            }
            nonVoterHeatLayer.addTo(map);
        }
    }
}

// ── Opportunity layer management ──
let oppRegularLayer = null;
let oppOccasionalLayer = null;
let oppNeverLayer = null;

async function loadOpportunityLayers() {
    if (!opportunityDataCache) {
        const resp = await fetch('/cache/misdbond2026_opportunity.json');
        opportunityDataCache = await resp.json();
    }
    
    if (!oppRegularLayer) {
        const regular = [], occasional = [], never = [];
        opportunityDataCache.households.forEach(hh => {
            const pt = [hh.la, hh.ln, Math.min(hh.v, 5)];
            if (hh.t === 'r') regular.push(pt);
            else if (hh.t === 'o') occasional.push(pt);
            else never.push(pt);
        });
        
        oppRegularLayer = L.heatLayer(regular, {
            radius: 25, blur: 15, maxZoom: 17, max: 5.0, minOpacity: 0.2,
            gradient: {0:'rgba(255,0,0,0)', 0.3:'rgba(255,50,0,0.4)', 0.6:'rgba(255,0,0,0.6)', 1:'rgba(180,0,0,0.85)'}
        });
        oppOccasionalLayer = L.heatLayer(occasional, {
            radius: 25, blur: 15, maxZoom: 17, max: 5.0, minOpacity: 0.2,
            gradient: {0:'rgba(255,165,0,0)', 0.3:'rgba(255,180,0,0.35)', 0.6:'rgba(255,140,0,0.55)', 1:'rgba(200,100,0,0.75)'}
        });
        oppNeverLayer = L.heatLayer(never, {
            radius: 20, blur: 18, maxZoom: 17, max: 5.0, minOpacity: 0.1,
            gradient: {0:'rgba(100,100,200,0)', 0.3:'rgba(100,100,200,0.2)', 0.6:'rgba(80,80,180,0.35)', 1:'rgba(60,60,150,0.5)'}
        });
    }
}

function applyOpportunityType(type) {
    if (oppRegularLayer) map.removeLayer(oppRegularLayer);
    if (oppOccasionalLayer) map.removeLayer(oppOccasionalLayer);
    if (oppNeverLayer) map.removeLayer(oppNeverLayer);
    
    if ((type === 'regular' || type === 'regular_occasional' || type === 'all') && oppRegularLayer) oppRegularLayer.addTo(map);
    if ((type === 'occasional' || type === 'regular_occasional' || type === 'all') && oppOccasionalLayer) oppOccasionalLayer.addTo(map);
    if ((type === 'never' || type === 'all') && oppNeverLayer) oppNeverLayer.addTo(map);
}

document.getElementById('opp-type-select').addEventListener('change', function(e) {
    applyOpportunityType(e.target.value);
});

document.getElementById('opp-type-select-mobile').addEventListener('change', function(e) {
    document.getElementById('opp-type-select').value = e.target.value;
    applyOpportunityType(e.target.value);
});

// District boundary toggle
const districtColors = {1:'#e74c3c',2:'#27ae60',3:'#8e44ad',4:'#2980b9',5:'#f1c40f',6:'#95a5a6'};

function refreshStudentLayers() {
    if (studentElemLayer) map.removeLayer(studentElemLayer);
    if (studentMidLayer) map.removeLayer(studentMidLayer);
    if (studentHighLayer) map.removeLayer(studentHighLayer);
    if (document.getElementById('stu-elem').checked && studentElemLayer) studentElemLayer.addTo(map);
    if (document.getElementById('stu-mid').checked && studentMidLayer) studentMidLayer.addTo(map);
    if (document.getElementById('stu-high').checked && studentHighLayer) studentHighLayer.addTo(map);
}
let schoolZoneLayer = null;

async function toggleDistrictBoundaries(show) {
    if (show && !districtBoundaryLayer) {
        try {
            const resp = await fetch('/data/mcallen_smd.json');
            const data = await resp.json();
            districtBoundaryLayer = L.geoJSON(data, {
                style: function(feature) {
                    const num = parseInt(feature.properties.NAME.replace('District ', ''));
                    return {
                        color: districtColors[num] || '#666',
                        weight: 3,
                        fillOpacity: 0.08,
                        dashArray: '6,4'
                    };
                },
                onEachFeature: function(feature, layer) {
                    const p = feature.properties;
                    layer.bindTooltip(p.NAME + (p.REPNAME ? '<br>' + p.REPNAME : ''), {
                        permanent: false, direction: 'center',
                        className: 'district-tooltip'
                    });
                }
            });
        } catch(err) { console.error('Failed to load district boundaries:', err); return; }
    }
    if (show && districtBoundaryLayer) {
        districtBoundaryLayer.addTo(map);
    } else if (!show && districtBoundaryLayer) {
        map.removeLayer(districtBoundaryLayer);
    }
}

const schoolZoneColors = ['#e67e22','#16a085','#8e44ad','#2980b9','#c0392b','#27ae60'];

async function toggleSchoolZones(show) {
    if (show && !schoolZoneLayer) {
        try {
            const resp = await fetch('/data/mcallen_ms_zones.json');
            const data = await resp.json();
            let i = 0;
            schoolZoneLayer = L.geoJSON(data, {
                style: function() {
                    const color = schoolZoneColors[i++ % schoolZoneColors.length];
                    return { color: color, weight: 2, fillOpacity: 0.06, dashArray: '4,6' };
                },
                onEachFeature: function(feature, layer) {
                    layer.bindTooltip(feature.properties.NAME, {
                        permanent: false, direction: 'center',
                        className: 'district-tooltip'
                    });
                }
            });
        } catch(err) { console.error('Failed to load school zones:', err); return; }
    }
    if (show && schoolZoneLayer) {
        schoolZoneLayer.addTo(map);
    } else if (!show && schoolZoneLayer) {
        map.removeLayer(schoolZoneLayer);
    }
}

document.getElementById('heatmap-mode').addEventListener('change', function(e) {
    setHeatmapMode(e.target.value);
});

document.getElementById('show-city-districts').addEventListener('change', function(e) {
    toggleDistrictBoundaries(e.target.checked);
});

document.getElementById('show-school-zones').addEventListener('change', function(e) {
    toggleSchoolZones(e.target.checked);
});

let hsZoneLayer = null;
const hsZoneColors = ['#1abc9c','#9b59b6','#e74c3c'];

async function toggleHsZones(show) {
    if (show && !hsZoneLayer) {
        try {
            const resp = await fetch('/data/mcallen_hs_zones.json');
            const data = await resp.json();
            let i = 0;
            hsZoneLayer = L.geoJSON(data, {
                style: function() {
                    const color = hsZoneColors[i++ % hsZoneColors.length];
                    return { color: color, weight: 3, fillOpacity: 0.05, dashArray: '8,4' };
                },
                onEachFeature: function(feature, layer) {
                    layer.bindTooltip(feature.properties.NAME, {
                        permanent: false, direction: 'center', className: 'district-tooltip'
                    });
                }
            });
        } catch(err) { console.error('Failed to load HS zones:', err); return; }
    }
    if (show && hsZoneLayer) hsZoneLayer.addTo(map);
    else if (!show && hsZoneLayer) map.removeLayer(hsZoneLayer);
}

document.getElementById('show-hs-zones').addEventListener('change', function(e) {
    toggleHsZones(e.target.checked);
});

// ── Report Card ──
let reportCardCache = {};

document.getElementById('reportcard-btn').addEventListener('click', async function() {
    const panel = document.getElementById('reportcard-panel');
    if (panel.classList.contains('visible')) {
        panel.classList.remove('visible');
        return;
    }
    panel.classList.add('visible');
    // Random fun quip
    const quips = [
        '🗳️ Brought to you by your neighborhood',
        '📊 Because democracy needs a report card too',
        '🎓 Grading politicians since 2026',
        '🏫 Your vote is your homework — turn it in!',
        '✏️ No extra credit for not voting',
        '📝 The only test where everyone should pass',
        '🗳️ Making civic data fun since forever',
        '🎒 School is in session — go vote!'
    ];
    const quipEl = document.getElementById('footer-quip');
    if (quipEl) quipEl.textContent = quips[Math.floor(Math.random() * quips.length)];
    switchReportTab('districts');
});

document.getElementById('reportcard-close').addEventListener('click', function() {
    document.getElementById('reportcard-panel').classList.remove('visible');
});

async function switchReportTab(tab) {
    document.querySelectorAll('.rc-tab').forEach(t => t.classList.remove('active'));
    document.getElementById('rc-tab-' + tab).classList.add('active');
    
    if (tab === 'demo') {
        if (!reportCardCache.demo) {
            try {
                const resp = await fetch('/cache/misdbond2026_demographics.json?t=' + Date.now());
                reportCardCache.demo = await resp.json();
            } catch(err) { console.error('Failed to load demographics:', err); return; }
        }
        renderDemographics(reportCardCache.demo);
        return;
    }
    
    if (tab === 'staff') {
        if (!reportCardCache.staff) {
            try {
                const resp = await fetch('/cache/misdbond2026_staff.json?t=' + Date.now());
                reportCardCache.staff = await resp.json();
            } catch(err) { console.error('Failed to load staff data:', err); return; }
        }
        renderStaffReport(reportCardCache.staff);
        return;
    }
    
    const urls = {
        districts: '/cache/misdbond2026_reportcard.json?t=' + Date.now(),
        campuses: '/cache/misdbond2026_campus_reportcard.json?t=' + Date.now(),
        hs: '/cache/misdbond2026_hs_reportcard.json?t=' + Date.now(),
        elem: '/cache/misdbond2026_elem_reportcard.json?t=' + Date.now()
    };
    const keys = {
        districts: 'districts',
        campuses: 'campuses',
        hs: 'campuses',
        elem: 'campuses'
    };
    
    // Always re-fetch report card data (never cache stale)
    delete reportCardCache[tab];
    try {
        const resp = await fetch(urls[tab]);
        reportCardCache[tab] = await resp.json();
    } catch(err) {
        console.error('Failed to load report card:', err);
        return;
    }
    renderReportCard(reportCardCache[tab], keys[tab], tab);
}

function renderDemographics(data) {
    const font = "font-family:'Patrick Hand',cursive;";
    const summary = document.getElementById('reportcard-summary');
    const list = document.getElementById('reportcard-list');
    
    // Build zone filter dropdown
    let filterHtml = '<select id="demo-zone-filter" style="width:100%;padding:6px 8px;border:1px solid #d4a853;border-radius:4px;font-size:13px;margin-top:6px;' + font + '">';
    filterHtml += '<option value="all">🌎 All McAllen</option>';
    console.log('zone_groups:', data.zone_groups, 'zones:', data.zones ? Object.keys(data.zones).length : 0);
    if (data.zone_groups) {
        for (const [group, zones] of Object.entries(data.zone_groups)) {
            filterHtml += '<optgroup label="' + group + '">';
            zones.forEach(z => { filterHtml += '<option value="' + z + '">' + z + '</option>'; });
            filterHtml += '</optgroup>';
        }
    }
    filterHtml += '</select>';
    
    summary.innerHTML = `
        <div style="text-align:center;${font}">
            <div style="font-size:18px;font-weight:700;color:#333;">📊 Voter Demographics</div>
        </div>
        ${filterHtml}
    `;
    
    // Wire up filter
    document.getElementById('demo-zone-filter').addEventListener('change', function(e) {
        const zone = e.target.value;
        const d = (zone === 'all') ? data.all : (data.zones[zone] || data.all);
        renderDemoContent(d, list, font);
    });
    
    // Initial render
    renderDemoContent(data.all, list, font);
}

function renderDemoContent(dd, list, font) {
    let html = '';
    html += '<div style="text-align:center;padding:6px 18px;font-size:13px;color:#666;' + font + '">' + dd.total_voted.toLocaleString() + ' voted of ' + dd.total_registered.toLocaleString() + ' registered</div>';
    
    // Daily pace
    if (dd.daily && dd.daily.length > 0) {
        html += '<div style="padding:10px 18px;border-bottom:2px solid #d4a853;">';
        html += '<div style="font-size:14px;font-weight:700;color:#333;' + font + '">📅 Daily Voting Pace</div>';
        const maxNew = Math.max(...dd.daily.map(x => x.new));
        dd.daily.forEach(x => {
            const pct = Math.round(x.new / maxNew * 100);
            const dateStr = new Date(x.date + 'T12:00:00').toLocaleDateString('en-US', {weekday:'short', month:'short', day:'numeric'});
            html += '<div style="display:flex;align-items:center;gap:8px;padding:3px 0;' + font + '">';
            html += '<span style="width:90px;font-size:12px;color:#666;">' + dateStr + '</span>';
            html += '<div style="flex:1;height:16px;background:#eee;border-radius:3px;overflow:hidden;">';
            html += '<div style="width:' + pct + '%;height:100%;background:#3498db;border-radius:3px;"></div></div>';
            html += '<span style="font-size:12px;font-weight:600;width:40px;text-align:right;">+' + x.new + '</span>';
            html += '<span style="font-size:11px;color:#999;width:45px;text-align:right;">' + x.total + '</span>';
            html += '</div>';
        });
        html += '</div>';
    }
    
    // Age breakdown
    html += '<div style="padding:10px 18px;border-bottom:2px solid #d4a853;">';
    html += '<div style="font-size:14px;font-weight:700;color:#333;' + font + '">👤 Age Group Turnout</div>';
    const maxAge = Math.max(...dd.age.map(a => a.turnout_pct), 0.01);
    dd.age.forEach(a => {
        const pct = Math.round(a.turnout_pct / maxAge * 100);
        const color = a.turnout_pct >= 2 ? '#27ae60' : a.turnout_pct >= 1 ? '#f39c12' : '#e74c3c';
        html += '<div style="display:flex;align-items:center;gap:8px;padding:3px 0;' + font + '">';
        html += '<span style="width:50px;font-size:13px;font-weight:600;">' + a.group + '</span>';
        html += '<div style="flex:1;height:18px;background:#eee;border-radius:3px;overflow:hidden;">';
        html += '<div style="width:' + pct + '%;height:100%;background:' + color + ';border-radius:3px;"></div></div>';
        html += '<span style="font-size:12px;font-weight:600;width:45px;text-align:right;">' + a.turnout_pct + '%</span>';
        html += '<span style="font-size:11px;color:#999;width:60px;text-align:right;">' + a.voted + '/' + a.registered.toLocaleString() + '</span>';
        html += '</div>';
    });
    html += '</div>';
    
    // Gender gap
    html += '<div style="padding:10px 18px;border-bottom:2px solid #d4a853;">';
    html += '<div style="font-size:14px;font-weight:700;color:#333;' + font + '">⚤ Gender Gap</div>';
    dd.gender.forEach(g => {
        const icon = g.group === 'Women' ? '👩' : '👨';
        const clr = g.group === 'Women' ? '#e91e63' : '#2196f3';
        const barW = Math.round(g.turnout_pct / 3 * 100);
        html += '<div style="display:flex;align-items:center;gap:8px;padding:4px 0;' + font + '">';
        html += '<span style="font-size:16px;">' + icon + '</span>';
        html += '<span style="width:55px;font-size:13px;font-weight:600;">' + g.group + '</span>';
        html += '<div style="flex:1;height:20px;background:#eee;border-radius:3px;overflow:hidden;">';
        html += '<div style="width:' + barW + '%;height:100%;background:' + clr + ';border-radius:3px;"></div></div>';
        html += '<span style="font-size:13px;font-weight:700;width:45px;text-align:right;">' + g.turnout_pct + '%</span>';
        html += '<span style="font-size:11px;color:#999;width:55px;text-align:right;">' + g.voted + '</span>';
        html += '</div>';
    });
    html += '</div>';
    
    // Party breakdown
    html += '<div style="padding:10px 18px;">';
    html += '<div style="font-size:14px;font-weight:700;color:#333;' + font + '">🗳️ Party Breakdown</div>';
    const total = dd.party.Democratic + dd.party.Republican + dd.party.Other;
    if (total > 0) {
        const demPct = Math.round(dd.party.Democratic / total * 100);
        const repPct = Math.round(dd.party.Republican / total * 100);
        const othPct = 100 - demPct - repPct;
        html += '<div style="display:flex;height:28px;border-radius:4px;overflow:hidden;margin:6px 0;">';
        html += '<div style="width:' + demPct + '%;background:#1E90FF;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:700;">' + demPct + '%</div>';
        html += '<div style="width:' + repPct + '%;background:#DC143C;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:700;">' + repPct + '%</div>';
        html += '<div style="width:' + othPct + '%;background:#95a5a6;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:700;">' + othPct + '%</div>';
        html += '</div>';
    }
    html += '<div style="display:flex;justify-content:space-between;font-size:12px;' + font + '">';
    html += '<span>🔵 Dem: ' + dd.party.Democratic + '</span>';
    html += '<span>🔴 Rep: ' + dd.party.Republican + '</span>';
    html += '<span>⚪ Other: ' + dd.party.Other + '</span>';
    html += '</div></div>';
    
    list.innerHTML = html;
}

function renderStaffReport(d) {
    const font = "font-family:'Patrick Hand',cursive;";
    const summary = document.getElementById('reportcard-summary');
    const list = document.getElementById('reportcard-list');
    
    const grade = d.turnout_pct >= 20 ? 'A' : d.turnout_pct >= 15 ? 'B' : d.turnout_pct >= 10 ? 'C' : d.turnout_pct >= 5 ? 'D' : 'F';
    const gradeColor = {A:'#27ae60',B:'#2ecc71',C:'#f39c12',D:'#e67e22',F:'#e74c3c'};
    const gradeEmoji = {A:'⭐',B:'👍',C:'😐',D:'😬',F:'😱'};
    
    summary.innerHTML = '<div style="text-align:center;margin-bottom:4px;">' +
        '<div style="font-size:12px;color:#999;' + font + '">McAllen ISD Staff</div>' +
        '<div style="font-size:18px;font-weight:700;' + font + 'color:#333;">👩‍🏫 Staff Turnout</div>' +
        '</div>' +
        '<div style="display:flex;align-items:center;justify-content:center;gap:14px;">' +
        '<div class="rc-grade rc-grade-' + grade + '" style="width:56px;height:56px;font-size:28px;transform:rotate(-5deg);">' + grade + '</div>' +
        '<div style="text-align:left;">' +
        '<div style="font-size:18px;font-weight:700;color:#333;' + font + '">' + d.turnout_pct + '% of staff voted ' + gradeEmoji[grade] + '</div>' +
        '<div style="font-size:13px;color:#666;' + font + '">✅ ' + d.voted + ' voted · 🪑 ' + d.not_voted + ' didn\'t</div>' +
        '<div style="font-size:13px;color:#888;' + font + '">📋 ' + d.matched_to_voters + ' found in voter rolls of ' + d.total_staff + ' staff</div>' +
        '<div style="font-size:11px;color:#aaa;' + font + '">🔍 ' + d.not_found + ' staff not found (may live outside McAllen)</div>' +
        '</div></div>';
    
    let html = '';
    
    // Narrative blurb
    html += '<div style="padding:10px 18px;border-bottom:2px solid #d4a853;background:#fff3e0;">';
    html += '<div style="font-size:12px;color:#555;line-height:1.5;' + font + '">';
    html += '📝 Of ' + d.total_staff.toLocaleString() + ' MISD staff listed on mcallenisd.org, ' + d.matched_to_voters + ' were found in McAllen voter rolls. ';
    html += 'Only <b>' + d.voted + '</b> (' + d.turnout_pct + '%) have voted in the bond that would directly fund their schools and workplaces. ';
    if (d.roles && d.roles.length > 0) {
        const instr = d.roles.find(r => r.role === 'Instructional');
        const fac = d.roles.find(r => r.role === 'Facilities & Operations');
        if (instr && fac && fac.turnout_pct > 0) {
            html += 'Teachers and instructional staff lead at ' + instr.turnout_pct + '% turnout — ';
            html += Math.round(instr.turnout_pct / fac.turnout_pct) + 'x the rate of facilities and operations staff (' + fac.turnout_pct + '%). ';
        }
        const subs = d.roles.find(r => r.role === 'Substitute');
        if (subs) {
            html += 'Substitutes make up half the staff directory but vote at just ' + subs.turnout_pct + '%.';
        }
    }
    html += '</div></div>';
    
    // Role breakdown (if available)
    if (d.roles && d.roles.length > 0) {
        html += '<div style="padding:10px 18px;border-bottom:2px solid #d4a853;">';
        html += '<div style="font-size:14px;font-weight:700;color:#333;' + font + '">🏫 Turnout by Role</div>';
        d.roles.forEach(function(r) {
            const barW = Math.min(Math.round(r.turnout_pct / 25 * 100), 100);
            const color = r.turnout_pct >= 20 ? '#27ae60' : r.turnout_pct >= 10 ? '#f39c12' : '#e74c3c';
            html += '<div style="display:flex;align-items:center;gap:8px;padding:4px 0;' + font + '">';
            html += '<span style="font-size:14px;">' + (r.icon || '') + '</span>';
            html += '<span style="width:100px;font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="' + r.role + '">' + r.role + '</span>';
            html += '<div style="flex:1;height:18px;background:#eee;border-radius:3px;overflow:hidden;">';
            html += '<div style="width:' + barW + '%;height:100%;background:' + color + ';border-radius:3px;"></div></div>';
            html += '<span style="font-size:12px;font-weight:600;width:40px;text-align:right;">' + r.turnout_pct + '%</span>';
            html += '<span style="font-size:10px;color:#999;width:70px;text-align:right;">' + r.voted + '/' + r.matched + ' of ' + r.total + '</span>';
            html += '</div>';
        });
        html += '</div>';
    }
    
    // Age breakdown
    html += '<div style="padding:10px 18px;border-bottom:2px solid #d4a853;">';
    html += '<div style="font-size:14px;font-weight:700;color:#333;' + font + '">👤 Staff Turnout by Age</div>';
    const maxAge = Math.max(...d.age.map(a => a.turnout_pct), 0.01);
    d.age.forEach(function(a) {
        const pct = Math.round(a.turnout_pct / maxAge * 100);
        const color = a.turnout_pct >= 20 ? '#27ae60' : a.turnout_pct >= 10 ? '#f39c12' : '#e74c3c';
        html += '<div style="display:flex;align-items:center;gap:8px;padding:3px 0;' + font + '">';
        html += '<span style="width:50px;font-size:13px;font-weight:600;">' + a.group + '</span>';
        html += '<div style="flex:1;height:18px;background:#eee;border-radius:3px;overflow:hidden;">';
        html += '<div style="width:' + pct + '%;height:100%;background:' + color + ';border-radius:3px;"></div></div>';
        html += '<span style="font-size:12px;font-weight:600;width:45px;text-align:right;">' + a.turnout_pct + '%</span>';
        html += '<span style="font-size:11px;color:#999;width:60px;text-align:right;">' + a.voted + '/' + a.registered + '</span>';
        html += '</div>';
    });
    html += '</div>';
    
    // Gender breakdown
    html += '<div style="padding:10px 18px;border-bottom:2px solid #d4a853;">';
    html += '<div style="font-size:14px;font-weight:700;color:#333;' + font + '">⚤ Staff Turnout by Gender</div>';
    d.gender.forEach(function(g) {
        const icon = g.group === 'Women' ? '👩' : '👨';
        const clr = g.group === 'Women' ? '#e91e63' : '#2196f3';
        const barW = Math.min(Math.round(g.turnout_pct / 25 * 100), 100);
        html += '<div style="display:flex;align-items:center;gap:8px;padding:4px 0;' + font + '">';
        html += '<span style="font-size:16px;">' + icon + '</span>';
        html += '<span style="width:55px;font-size:13px;font-weight:600;">' + g.group + '</span>';
        html += '<div style="flex:1;height:20px;background:#eee;border-radius:3px;overflow:hidden;">';
        html += '<div style="width:' + barW + '%;height:100%;background:' + clr + ';border-radius:3px;"></div></div>';
        html += '<span style="font-size:13px;font-weight:700;width:45px;text-align:right;">' + g.turnout_pct + '%</span>';
        html += '<span style="font-size:11px;color:#999;width:55px;text-align:right;">' + g.voted + '/' + g.registered + '</span>';
        html += '</div>';
    });
    html += '</div>';
    
    // Party breakdown of those who voted
    html += '<div style="padding:10px 18px;border-bottom:2px solid #d4a853;">';
    html += '<div style="font-size:14px;font-weight:700;color:#333;' + font + '">🗳️ Staff Who Voted - Party</div>';
    const totalP = d.party.Democratic + d.party.Republican + d.party.Other;
    if (totalP > 0) {
        const demPct = Math.round(d.party.Democratic / totalP * 100);
        const repPct = Math.round(d.party.Republican / totalP * 100);
        const othPct = 100 - demPct - repPct;
        html += '<div style="display:flex;height:28px;border-radius:4px;overflow:hidden;margin:6px 0;">';
        html += '<div style="width:' + demPct + '%;background:#1E90FF;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:700;">' + demPct + '%</div>';
        html += '<div style="width:' + repPct + '%;background:#DC143C;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:700;">' + repPct + '%</div>';
        html += '<div style="width:' + othPct + '%;background:#95a5a6;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:700;">' + othPct + '%</div>';
        html += '</div>';
    }
    html += '<div style="display:flex;justify-content:space-between;font-size:12px;' + font + '">';
    html += '<span>🔵 Dem: ' + d.party.Democratic + '</span>';
    html += '<span>🔴 Rep: ' + d.party.Republican + '</span>';
    html += '<span>⚪ Other: ' + d.party.Other + '</span>';
    html += '</div></div>';
    
    // Party breakdown of all registered staff
    html += '<div style="padding:10px 18px;">';
    html += '<div style="font-size:14px;font-weight:700;color:#333;' + font + '">📋 All Registered Staff - Party</div>';
    const totalR = d.party_registered.Democratic + d.party_registered.Republican + d.party_registered.Other;
    if (totalR > 0) {
        const demR = Math.round(d.party_registered.Democratic / totalR * 100);
        const repR = Math.round(d.party_registered.Republican / totalR * 100);
        const othR = 100 - demR - repR;
        html += '<div style="display:flex;height:28px;border-radius:4px;overflow:hidden;margin:6px 0;">';
        html += '<div style="width:' + demR + '%;background:#1E90FF;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:700;">' + demR + '%</div>';
        html += '<div style="width:' + repR + '%;background:#DC143C;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:700;">' + repR + '%</div>';
        html += '<div style="width:' + othR + '%;background:#95a5a6;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:700;">' + othR + '%</div>';
        html += '</div>';
    }
    html += '<div style="display:flex;justify-content:space-between;font-size:12px;' + font + '">';
    html += '<span>🔵 Dem: ' + d.party_registered.Democratic + '</span>';
    html += '<span>🔴 Rep: ' + d.party_registered.Republican + '</span>';
    html += '<span>⚪ Other: ' + d.party_registered.Other + '</span>';
    html += '</div>';
    html += '<div style="font-size:10px;color:#bbb;font-style:italic;margin-top:8px;' + font + '">⚠️ This is a rough guesstimate only. Staff names were matched against public voter rolls by first and last name. Common names may produce false matches, married/hyphenated names may be missed, and many staff live outside McAllen. These numbers could be totally inaccurate — take them with a big grain of salt.</div>';
    html += '</div>';
    
    list.innerHTML = html;
}

function renderReportCard(data, itemKey, tab) {
    const s = data.summary;
    const gradeColor = {A:'#27ae60',B:'#2ecc71',C:'#f39c12',D:'#e67e22',F:'#e74c3c'};
    const gradeEmoji = {A:'⭐',B:'👍',C:'😐',D:'😬',F:'😱'};
    const gradeComment = {A:'Gold star!',B:'Not bad!',C:'Room to grow',D:'Needs work',F:'Uh oh...'};
    const titles = {districts:'🏛️',campuses:'🏫',hs:'🎓',elem:'📚'};
    const icon = titles[tab] || '📊';
    
    document.getElementById('reportcard-summary').innerHTML = `
        <div style="text-align:center;margin-bottom:4px;">
            <div style="font-size:12px;color:#999;font-family:'Patrick Hand',cursive;">McAllen ISD Bond 2026</div>
            <div style="font-size:18px;font-weight:700;font-family:'Patrick Hand',cursive;color:#333;">${icon} Overall Grade</div>
        </div>
        <div style="display:flex;align-items:center;justify-content:center;gap:14px;">
            <div class="rc-grade rc-grade-${s.overall_grade}" style="width:56px;height:56px;font-size:28px;transform:rotate(-5deg);">${s.overall_grade}</div>
            <div style="text-align:left;">
                <div style="font-size:18px;font-weight:700;color:#333;font-family:'Patrick Hand',cursive;">${s.overall_turnout_pct}% turnout ${gradeEmoji[s.overall_grade]}</div>
                <div style="font-size:13px;color:#666;font-family:'Patrick Hand',cursive;">✅ ${s.total_voted.toLocaleString()} voted · 🪑 ${s.total_not_voted.toLocaleString()} stayed home</div>
                <div style="font-size:13px;color:#888;font-family:'Patrick Hand',cursive;">📋 ${s.total_registered.toLocaleString()} registered</div>
            </div>
        </div>
        <div style="text-align:center;margin-top:6px;font-size:11px;color:#aaa;font-family:'Patrick Hand',cursive;">
            ✏️ A=5%+ · B=3%+ · C=2%+ · D=1%+ · F=below 1%
        </div>
    `;
    
    const list = document.getElementById('reportcard-list');
    const items = data[itemKey] || data.districts || data.campuses || data.precincts || [];
    const sectionTitles = {districts:'📖 City Commission Report Cards',campuses:'📖 Middle School Report Cards',hs:'📖 High School Report Cards',elem:'📖 Elementary Report Cards'};
    const sectionTitle = sectionTitles[tab] || '📖 Report Cards';
    const isSchool = (tab === 'campuses' || tab === 'hs' || tab === 'elem');
    const disclaimer = isSchool ? '<div style="padding:4px 18px;font-size:10px;color:#bbb;font-style:italic;font-family:\'Patrick Hand\',cursive;">⚠️ Based on school attendance zone boundaries from City of McAllen GIS. Zones may not reflect current school year assignments.</div>' : '';
    
    // Sort function
    window._rcItems = items;
    window._rcRenderItems = function(sortBy) {
        const sorted = [...window._rcItems];
        if (sortBy === 'alpha') sorted.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
        else if (sortBy === 'grade') sorted.sort((a, b) => b.turnout_pct - a.turnout_pct);
        else if (sortBy === 'pct') sorted.sort((a, b) => (b.voted/b.registered||0) - (a.voted/a.registered||0));
        else sorted.sort((a, b) => b.voted - a.voted); // default: most votes
        
        const header = '<div style="padding:6px 18px;display:flex;align-items:center;justify-content:space-between;border-bottom:2px solid #d4a853;">' +
            '<span style="font-size:14px;color:#999;font-family:\'Patrick Hand\',cursive;">' + sectionTitle + '</span>' +
            '<select id="rc-sort" style="font-size:11px;padding:2px 4px;border:1px solid #d4a853;border-radius:3px;background:#fff9e6;font-family:\'Patrick Hand\',cursive;" onchange="window._rcRenderItems(this.value)">' +
            '<option value="votes"' + (sortBy === 'votes' ? ' selected' : '') + '>Most votes</option>' +
            '<option value="pct"' + (sortBy === 'pct' ? ' selected' : '') + '>% of total</option>' +
            '<option value="grade"' + (sortBy === 'grade' ? ' selected' : '') + '>Grade</option>' +
            '<option value="alpha"' + (sortBy === 'alpha' ? ' selected' : '') + '>A-Z</option>' +
            '</select></div>';
        
        list.innerHTML = header + disclaimer +
        sorted.map(p => {
        const barColor = gradeColor[p.grade] || '#ccc';
        const barWidth = Math.min(p.turnout_pct * 10, 100);
        const label = p.name || ('Precinct ' + p.precinct);
        const emoji = gradeEmoji[p.grade] || '';
        const comment = gradeComment[p.grade] || '';
        const rep = p.rep ? `<div class="rc-rep">👤 ${p.rep}</div>` : '';
        const dem = p.dem || 0;
        const repP = p.rep_party || 0;
        const other = p.voted - dem - repP;
        return `<div class="rc-row">
            <div class="rc-grade rc-grade-${p.grade}">${p.grade}</div>
            <div class="rc-info">
                <div class="rc-pct">${label} ${emoji}</div>
                ${rep}
                <div class="rc-detail">✅ ${p.voted} voted · 🪑 ${p.not_voted.toLocaleString()} didn't · 📋 ${p.registered.toLocaleString()}</div>
                <div style="font-size:12px;font-family:'Patrick Hand',cursive;margin-top:2px;">
                    <span style="color:#1E90FF;">🔵 ${dem}</span>
                    <span style="margin:0 4px;color:#ccc;">vs</span>
                    <span style="color:#DC143C;">🔴 ${repP}</span>
                    ${other > 0 ? `<span style="margin-left:4px;color:#888;">⚪ ${other}</span>` : ''}
                </div>
                <div style="font-size:11px;color:#aaa;font-style:italic;font-family:'Patrick Hand',cursive;">"${comment}"</div>
            </div>
            <div class="rc-turnout">${p.turnout_pct}%</div>
            <div class="rc-bar"><div class="rc-bar-fill" style="width:${barWidth}%;background:${barColor};"></div></div>
        </div>`;
    }).join('');
    }; // end _rcRenderItems
    window._rcRenderItems('votes');
}

// Click tab to show banner again
document.getElementById('banner-tab').addEventListener('click', function() {
    const banner = document.getElementById('sliding-banner');
    const tab = document.getElementById('banner-tab');
    
    if (banner && tab) {
        banner.classList.remove('hidden');
        tab.classList.remove('visible');
        
        // Auto-hide after 5 seconds or on tap
        bannerTimeout = setTimeout(hideBanner, 5000);
        document.addEventListener('click', hideBannerOnTap, { once: true });
        document.addEventListener('touchstart', hideBannerOnTap, { once: true });
    }
});

// Disclaimer modal
document.getElementById('disclaimer-notice').addEventListener('click', function() {
    document.getElementById('disclaimer-modal').classList.add('visible');
});

// Mobile disclaimer link
document.getElementById('mobile-disclaimer').addEventListener('click', function() {
    document.getElementById('disclaimer-modal').classList.add('visible');
});

// Settings gear (mobile)
document.getElementById('settings-btn').addEventListener('click', function(e) {
    e.stopPropagation();
    document.getElementById('settings-dropdown').classList.toggle('visible');
});

// Close settings when clicking elsewhere
document.addEventListener('click', function(e) {
    const dd = document.getElementById('settings-dropdown');
    if (dd && !dd.contains(e.target) && e.target.id !== 'settings-btn') {
        dd.classList.remove('visible');
    }
});

// Sync mobile controls with desktop ones
document.getElementById('mcallen-filter-mobile').addEventListener('change', function(e) {
    document.getElementById('mcallen-filter').checked = e.target.checked;
    document.getElementById('mcallen-filter').dispatchEvent(new Event('change'));
});
document.getElementById('heatmap-mode-mobile').addEventListener('change', function(e) {
    document.getElementById('heatmap-mode').value = e.target.value;
    setHeatmapMode(e.target.value);
});
document.getElementById('show-city-districts-mobile').addEventListener('change', function(e) {
    document.getElementById('show-city-districts').checked = e.target.checked;
    toggleDistrictBoundaries(e.target.checked);
});
document.getElementById('show-school-zones-mobile').addEventListener('change', function(e) {
    document.getElementById('show-school-zones').checked = e.target.checked;
    toggleSchoolZones(e.target.checked);
});
document.getElementById('show-hs-zones-mobile').addEventListener('change', function(e) {
    document.getElementById('show-hs-zones').checked = e.target.checked;
    toggleHsZones(e.target.checked);
});

document.getElementById('disclaimer-close').addEventListener('click', function() {
    document.getElementById('disclaimer-modal').classList.remove('visible');
});

// Close modal when clicking outside
document.getElementById('disclaimer-modal').addEventListener('click', function(e) {
    if (e.target === this) {
        this.classList.remove('visible');
    }
});

// === GAZETTE ===
document.getElementById('gazette-btn').addEventListener('click', async function() {
    document.getElementById('gazette-panel').classList.add('visible');
    try {
        const resp = await fetch('/cache/misdbond2026_gazette.json?t=' + Date.now());
        const g = await resp.json();
        renderGazette(g);
    } catch(err) {
        document.getElementById('gazette-content').innerHTML = '<p style="padding:20px;text-align:center;">Could not load gazette data.</p>';
    }
});
document.getElementById('gazette-close').addEventListener('click', function() {
    document.getElementById('gazette-panel').classList.remove('visible');
});
document.getElementById('gazette-panel').addEventListener('click', function(e) {
    if (e.target === this) this.classList.remove('visible');
});

function renderGazette(g) {
    const gc = document.getElementById('gazette-content');
    let h = '';
    
    // Masthead
    h += '<div class="gazette-masthead">';
    h += '<h1>The Politiquera Gazette</h1>';
    h += '<div class="gazette-date">McAllen ISD Bond 2026 Edition &mdash; ' + g.date + '</div>';
    h += '</div>';
    
    // Headline
    h += '<div class="gazette-headline">';
    h += '<h2>' + g.headline + '</h2>';
    const arrow = g.change > 0 ? '📈' : g.change < 0 ? '📉' : '➡️';
    h += '<div class="sub">' + arrow + ' ' + g.subhead + '</div>';
    h += '</div>';
    
    // Daily chart
    if (g.daily && g.daily.length > 0) {
        h += '<div class="gazette-chart">';
        h += '<h3>📅 Daily Voting Pace</h3>';
        const maxNew = Math.max(...g.daily.map(d => d.new));
        g.daily.forEach(function(d) {
            const pct = Math.round(d.new / maxNew * 100);
            const dateStr = new Date(d.date + 'T12:00:00').toLocaleDateString('en-US', {weekday:'short', month:'short', day:'numeric'});
            h += '<div class="gazette-bar">';
            h += '<span style="width:80px;color:#666;">' + dateStr + '</span>';
            h += '<div style="flex:1;height:14px;background:#eee;border-radius:2px;overflow:hidden;">';
            h += '<div class="gazette-bar-fill" style="width:' + pct + '%;background:#2980b9;"></div></div>';
            h += '<span style="width:35px;text-align:right;font-weight:600;">+' + d.new.toLocaleString() + '</span>';
            h += '<span style="width:40px;text-align:right;color:#999;">' + d.total.toLocaleString() + '</span>';
            h += '</div>';
        });
        h += '</div>';
    }
    
    // Bullet points
    h += '<div class="gazette-bullets"><ul style="margin:0;padding-left:20px;">';
    g.bullets.forEach(function(b) { h += '<li>' + b + '</li>'; });
    h += '</ul></div>';
    
    // Three columns
    h += '<div class="gazette-columns">';
    
    // Districts column
    h += '<div class="gazette-col">';
    h += '<h3>🏛️ City Districts</h3>';
    g.districts.forEach(function(d) {
        const color = {A:'#27ae60',B:'#2ecc71',C:'#f39c12',D:'#e67e22',F:'#e74c3c'}[d.grade] || '#999';
        h += '<div class="gazette-col-item">';
        h += '<span>' + d.name + '</span>';
        h += '<span style="font-weight:700;color:' + color + ';">' + d.pct + '% ' + d.grade + '</span>';
        h += '</div>';
    });
    h += '</div>';
    
    // Schools column
    h += '<div class="gazette-col">';
    h += '<h3>🏫 Top Campuses</h3>';
    g.schools_top.forEach(function(s) {
        const color = {A:'#27ae60',B:'#2ecc71',C:'#f39c12',D:'#e67e22',F:'#e74c3c'}[s.grade] || '#999';
        h += '<div class="gazette-col-item">';
        h += '<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100px;">' + s.name + '</span>';
        h += '<span style="font-weight:700;color:' + color + ';">' + s.pct + '% ' + s.grade + '</span>';
        h += '</div>';
    });
    h += '<h3 style="margin-top:8px;">💀 Bottom Campuses</h3>';
    g.schools_bottom.forEach(function(s) {
        const color = {A:'#27ae60',B:'#2ecc71',C:'#f39c12',D:'#e67e22',F:'#e74c3c'}[s.grade] || '#999';
        h += '<div class="gazette-col-item">';
        h += '<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100px;">' + s.name + '</span>';
        h += '<span style="font-weight:700;color:' + color + ';">' + s.pct + '% ' + s.grade + '</span>';
        h += '</div>';
    });
    h += '</div>';
    
    // Staff column
    h += '<div class="gazette-col">';
    h += '<h3>👩‍🏫 Staff Turnout</h3>';
    h += '<div style="font-size:11px;color:#666;margin-bottom:4px;">' + g.staff_summary.voted + '/' + g.staff_summary.matched + ' staff voted (' + g.staff_summary.pct + '%)</div>';
    g.staff.forEach(function(s) {
        h += '<div class="gazette-col-item">';
        h += '<span>' + s.icon + ' ' + s.role + '</span>';
        h += '<span style="font-weight:600;">' + s.pct + '%</span>';
        h += '</div>';
    });
    h += '</div>';
    
    h += '</div>'; // end columns
    
    // Footer
    h += '<div class="gazette-footer">';
    h += '<a href="https://politiquera.com" target="_blank" style="text-decoration:none;color:#999;">';
    h += 'Published by <img src="../assets/politiquera.png" alt="Politiquera" style="height:18px;vertical-align:middle;margin:0 4px;"> politiquera.com';
    h += '</a><br>';
    h += '<span style="font-size:10px;">Data: Hidalgo County Elections, U.S. Census Bureau, TEA, McAllen ISD</span>';
    h += '</div>';
    
    gc.innerHTML = h;
}

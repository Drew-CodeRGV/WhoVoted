// search.js — Voter Search Modal (centered overlay)
let searchTimeout = null;

// Geolocation icon button
const geoIconBtn = document.createElement('button');
geoIconBtn.className = 'geo-icon-btn';
geoIconBtn.id = 'geolocation-button';
geoIconBtn.title = 'Find my location';
geoIconBtn.innerHTML = '<i class="fas fa-crosshairs"></i>';
document.body.appendChild(geoIconBtn);

// Search icon button — shown for full-access users via auth.js
const searchIconBtn = document.createElement('button');
searchIconBtn.className = 'search-icon-btn';
searchIconBtn.title = 'Search Voters';
searchIconBtn.innerHTML = '<i class="fas fa-search"></i>';
searchIconBtn.style.display = 'none';
document.body.appendChild(searchIconBtn);

searchIconBtn.addEventListener('click', openSearchModal);

// ── Modal helpers ──
function openSearchModal() {
    if (document.getElementById('voterSearchOverlay')) return;
    const overlay = document.createElement('div');
    overlay.id = 'voterSearchOverlay';
    overlay.className = 'vs-overlay';
    overlay.innerHTML = `
        <div class="vs-backdrop"></div>
        <div class="vs-modal">
            <button class="vs-close">&times;</button>
            <div class="vs-header">
                <div class="vs-header-icon"><i class="fas fa-search"></i></div>
                <h2>Voter Search</h2>
                <p>Search by name, VUID, address, birth year, precinct&hellip;</p>
            </div>
            <div class="vs-search-bar">
                <input id="vsInput" type="text" placeholder="Type to search..." autofocus>
                <button id="vsBtn">Search</button>
            </div>
            <div id="vsStatus" class="vs-status"></div>
            <div id="vsResults" class="vs-results"></div>
        </div>
    `;
    document.body.appendChild(overlay);

    const input = document.getElementById('vsInput');
    const btn = document.getElementById('vsBtn');

    overlay.querySelector('.vs-backdrop').addEventListener('click', closeSearchModal);
    overlay.querySelector('.vs-close').addEventListener('click', closeSearchModal);

    input.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        const q = input.value.trim();
        if (q.length < 2) { clearResults(); return; }
        searchTimeout = setTimeout(() => runSearch(q), 400);
    });
    btn.addEventListener('click', () => {
        const q = input.value.trim();
        if (q.length >= 2) runSearch(q);
    });
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const q = input.value.trim();
            if (q.length >= 2) runSearch(q);
        }
    });

    setTimeout(() => input.focus(), 50);
}

function closeSearchModal() {
    const el = document.getElementById('voterSearchOverlay');
    if (el) el.remove();
}

function clearResults() {
    const s = document.getElementById('vsStatus');
    const r = document.getElementById('vsResults');
    if (s) s.textContent = '';
    if (r) r.innerHTML = '';
}

// ── Search API call ──
async function runSearch(query) {
    const status = document.getElementById('vsStatus');
    const results = document.getElementById('vsResults');
    if (!status || !results) return;

    status.textContent = 'Searching...';
    results.innerHTML = '';

    try {
        const resp = await fetch('/api/search-voters?q=' + encodeURIComponent(query), {
            credentials: 'include'
        });
        if (resp.status === 401) {
            status.textContent = 'Sign in to search voters.';
            return;
        }
        if (!resp.ok) { status.textContent = 'Search failed.'; return; }

        const data = await resp.json();
        if (data.error) { status.textContent = data.error; return; }
        if (!data.results || data.results.length === 0) {
            status.textContent = 'No voters found.';
            return;
        }

        status.textContent = data.total + ' result' + (data.total === 1 ? '' : 's');
        renderResults(data.results, results);
    } catch (err) {
        console.error('Search error:', err);
        status.textContent = 'Search error.';
    }
}

// ── Render results ──
function renderResults(voters, container) {
    voters.forEach(v => {
        const card = document.createElement('div');
        card.className = 'vs-card';

        const name = [v.firstname, v.middlename, v.lastname, v.suffix].filter(Boolean).join(' ');
        const gender = v.sex === 'F' ? 'Female' : v.sex === 'M' ? 'Male' : v.sex || '';
        const addr = [v.address, v.city, v.zip].filter(Boolean).join(', ');
        const hasCoords = v.lat && v.lng;

        card.innerHTML = buildVoterRow(name, v, gender, addr, hasCoords, true) +
            buildHousehold(v.household || [], v.lat, v.lng);

        container.appendChild(card);
    });
}

function buildVoterRow(name, v, gender, addr, hasCoords, isPrimary) {
    const partyColor = getPartyColor(v.current_party);
    const historyHtml = buildHistoryPills(v.history || []);
    const zoomLink = hasCoords
        ? '<a class="vs-zoom" onclick="zoomToVoter(' + v.lat + ',' + v.lng + ',\'' + (v.vuid || '') + '\')">📍 Zoom to map</a>'
        : '<span class="vs-no-coords">No coordinates</span>';

    return '<div class="vs-voter' + (isPrimary ? ' vs-primary' : '') + '">' +
        '<div class="vs-voter-header">' +
            '<span class="vs-dot" style="background:' + partyColor + '"></span>' +
            '<span class="vs-name">' + name + '</span>' +
            '<span class="vs-vuid">' + (v.vuid || '') + '</span>' +
        '</div>' +
        '<div class="vs-details">' +
            '<span>' + addr + '</span>' +
            (gender ? ' · <span>' + gender + '</span>' : '') +
            (v.birth_year ? ' · <span>Born ' + v.birth_year + '</span>' : '') +
            (v.precinct ? ' · <span>Pct ' + v.precinct + '</span>' : '') +
        '</div>' +
        (historyHtml ? '<div class="vs-history-label">Vote History:</div>' + historyHtml : '<div class="vs-no-history">No vote history</div>') +
        '<div class="vs-actions">' + zoomLink + '</div>' +
    '</div>';
}

function buildHousehold(household, lat, lng) {
    if (!household || household.length === 0) return '';
    let html = '<div class="vs-household">' +
        '<div class="vs-household-title">🏠 ' + household.length + ' other' +
        (household.length === 1 ? '' : 's') + ' at this address</div>';
    household.forEach(hh => {
        const gender = hh.sex === 'F' ? 'Female' : hh.sex === 'M' ? 'Male' : hh.sex || '';
        const historyHtml = buildHistoryPills(hh.history || []);
        const hasCoords = lat && lng;
        html += '<div class="vs-voter vs-hh-member">' +
            '<div class="vs-voter-header">' +
                '<span class="vs-dot" style="background:' + getPartyColor(hh.current_party) + '"></span>' +
                '<span class="vs-name">' + hh.name + '</span>' +
                '<span class="vs-vuid">' + (hh.vuid || '') + '</span>' +
            '</div>' +
            '<div class="vs-details">' +
                (gender ? '<span>' + gender + '</span>' : '') +
                (hh.birth_year ? ' · <span>Born ' + hh.birth_year + '</span>' : '') +
            '</div>' +
            (historyHtml ? '<div class="vs-history-label">Vote History:</div>' + historyHtml : '<div class="vs-no-history">No vote history</div>') +
        '</div>';
    });
    html += '</div>';
    return html;
}

function buildHistoryPills(history) {
    if (!history || history.length === 0) return '';

    // Group by election year, reverse chronological (most recent first)
    const byYear = {};
    history.forEach(h => {
        const yr = (h.date || '').substring(0, 4) || '?';
        if (!byYear[yr]) byYear[yr] = [];
        byYear[yr].push(h);
    });
    const years = Object.keys(byYear).sort((a, b) => b.localeCompare(a));
    const currentYear = '2026';

    let html = '';
    years.forEach((yr, idx) => {
        const isCurrent = yr === currentYear;
        // Separator between year groups
        if (idx > 0) {
            html += '<div style="border-top:1px solid #e0e0e0;margin:4px 0;"></div>';
        }
        // Year label
        html += '<div style="font-size:9px;font-weight:700;color:' + (isCurrent ? '#1a73e8' : '#999') +
            ';text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px;">' +
            yr + (isCurrent ? ' — Current' : '') + '</div>';
        // Pills for this year
        html += '<div class="vs-history">';
        byYear[yr].forEach(h => {
            const type = (h.type || '').charAt(0).toUpperCase() + (h.type || '').slice(1);
            const method = (h.method || '').includes('early') ? 'EV' : 'ED';
            const pColor = h.party === 'Democratic' ? '#1E90FF' : h.party === 'Republican' ? '#DC143C' : '#888';
            const pLetter = h.party === 'Democratic' ? 'D' : h.party === 'Republican' ? 'R' : '?';
            html += '<span class="vs-pill" style="border-color:' + pColor + '">' +
                '<span class="vs-pill-party" style="background:' + pColor + '">' + pLetter + '</span>' +
                type + ' ' + method +
            '</span>';
        });
        html += '</div>';
    });
    return html;
}

function getPartyColor(party) {
    if (!party) return '#999';
    const p = party.toLowerCase();
    if (p.includes('democrat')) return '#1E90FF';
    if (p.includes('republican')) return '#DC143C';
    return '#999';
}

// ── Zoom to voter on map ──
function zoomToVoter(lat, lng, vuid) {
    closeSearchModal();
    
    // Zoom to max level so clusters fully expand
    map.setView([lat, lng], 18);
    
    // After zoom completes, find the marker and open its popup
    // Use a short delay to let the cluster group update after zoom
    setTimeout(() => {
        if (!markerClusterGroup) return;
        
        let found = false;
        markerClusterGroup.eachLayer(layer => {
            if (found) return;
            const ll = layer.getLatLng();
            const dist = Math.abs(ll.lat - lat) + Math.abs(ll.lng - lng);
            
            // Try matching by VUID first (check popup content), then by coords
            if (vuid && layer.getPopup()) {
                const content = layer.getPopup().getContent() || '';
                if (content.includes('history-' + vuid) || content.includes(vuid)) {
                    markerClusterGroup.zoomToShowLayer(layer, () => {
                        layer.openPopup();
                    });
                    found = true;
                    return;
                }
            }
            
            // Fallback: match by coordinates (within ~10m)
            if (!found && dist < 0.0002) {
                markerClusterGroup.zoomToShowLayer(layer, () => {
                    layer.openPopup();
                });
                found = true;
            }
        });
        
        // If marker not found in cluster (might be at a different zoom), 
        // try again after cluster animation finishes
        if (!found) {
            setTimeout(() => {
                markerClusterGroup.eachLayer(layer => {
                    if (found) return;
                    const ll = layer.getLatLng();
                    if (Math.abs(ll.lat - lat) + Math.abs(ll.lng - lng) < 0.001) {
                        layer.openPopup();
                        found = true;
                    }
                });
            }, 500);
        }
    }, 300);
}

// Reverse geocode for geolocation button
async function reverseGeocode(lat, lng) {
    try {
        const params = new URLSearchParams({ lat, lon: lng, format: 'json' });
        const response = await fetch(config.NOMINATIM_ENDPOINT + '/reverse?' + params, {
            headers: { 'User-Agent': config.USER_AGENT }
        });
        if (response.ok) {
            const data = await response.json();
            if (data.display_name) {
                const inp = document.getElementById('vsInput');
                if (inp) inp.value = data.display_name;
            }
        }
    } catch (error) {
        console.error('Reverse geocoding error:', error);
    }
}

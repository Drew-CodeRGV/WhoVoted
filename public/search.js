// search.js — Voter Search Modal (centered overlay)
let searchTimeout = null;

// Geolocation icon button
const geoIconBtn = document.createElement('button');
geoIconBtn.className = 'geo-icon-btn';
geoIconBtn.id = 'geolocation-button';
geoIconBtn.title = 'Find my location';
geoIconBtn.innerHTML = '<i class="fas fa-crosshairs"></i>';
document.body.appendChild(geoIconBtn);

// Basic Search icon button with magnifying glass
const searchIconBtn = document.createElement('button');
searchIconBtn.className = 'search-icon-btn';
searchIconBtn.title = 'Search Voters';
searchIconBtn.innerHTML = '<i class="fas fa-search"></i>'; // Magnifying glass icon
searchIconBtn.style.display = 'none'; // Will be shown by auth.js for authenticated users
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
                <p>Search by name or address</p>
            </div>
            <div class="vs-search-bar">
                <input id="vsInput" type="text" placeholder="Search by name or address..." autofocus>
                <button id="vsBtn"><i class="fas fa-search"></i></button>
            </div>
            <div class="vs-examples">
                <span class="vs-example-label">Examples:</span>
                <button class="vs-example-btn" onclick="fillExample('John Smith')">Name search</button>
                <button class="vs-example-btn" onclick="fillExample('123 Main St')">Address search</button>
            </div>
            <div id="vsAiResponse" class="vs-ai-response" style="display:none;">
                <div class="vs-ai-header">
                    <i class="fas fa-sparkles"></i>
                    <span>AI Response</span>
                </div>
                <div id="vsAiContent" class="vs-ai-content"></div>
                <div id="vsAiSql" class="vs-ai-sql" style="display:none;">
                    <div class="vs-ai-sql-header" onclick="toggleSql()">
                        <i class="fas fa-code"></i>
                        <span>View SQL Query</span>
                        <i class="fas fa-chevron-down vs-sql-toggle"></i>
                    </div>
                    <pre id="vsAiSqlCode" class="vs-ai-sql-code"></pre>
                </div>
                <div id="vsAiSuggestions" class="vs-ai-suggestions"></div>
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
        // Don't auto-search on typing - wait for user to click or press enter
    });
    btn.addEventListener('click', () => {
        const q = input.value.trim();
        if (q.length >= 2) runHybridSearch(q);
    });
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const q = input.value.trim();
            if (q.length >= 2) runHybridSearch(q);
        }
    });

    setTimeout(() => input.focus(), 50);
}

function fillExample(text) {
    const input = document.getElementById('vsInput');
    if (input) {
        input.value = text;
        input.focus();
    }
}

function toggleSql() {
    const sqlSection = document.getElementById('vsAiSql');
    if (sqlSection) {
        sqlSection.classList.toggle('expanded');
    }
}

function closeSearchModal() {
    const el = document.getElementById('voterSearchOverlay');
    if (el) el.remove();
}

function clearResults() {
    const s = document.getElementById('vsStatus');
    const r = document.getElementById('vsResults');
    const ai = document.getElementById('vsAiResponse');
    if (s) s.textContent = '';
    if (r) r.innerHTML = '';
    if (ai) ai.style.display = 'none';
}

// ── Hybrid Search: Detect if query is a question or traditional search ──
async function runHybridSearch(query) {
    const status = document.getElementById('vsStatus');
    const results = document.getElementById('vsResults');
    const aiResponse = document.getElementById('vsAiResponse');
    
    if (!status || !results || !aiResponse) return;

    // Clear previous results
    status.textContent = '';
    results.innerHTML = '';
    aiResponse.style.display = 'none';

    // Detect if this is a natural language question or traditional search
    const isQuestion = detectQuestion(query);

    if (isQuestion) {
        // Use AI-powered query
        await runAiSearch(query);
    } else {
        // Use traditional name/address search
        await runTraditionalSearch(query);
    }
}

// Detect if query is a question (vs name/address search)
function detectQuestion(query) {
    const q = query.toLowerCase();
    
    // Check if query needs geolocation
    const needsLocation = ['near me', 'my neighbors', 'my neighborhood', 'around me', 'close to me', 'nearby'].some(phrase => q.includes(phrase));
    if (needsLocation) {
        // Trigger geolocation if not already done
        if (!window.userLocation) {
            requestUserLocation();
        }
    }
    
    // Question words
    const questionWords = ['how many', 'show me', 'find', 'what', 'who', 'where', 'when', 'which', 'list', 'count', 'get'];
    if (questionWords.some(word => q.startsWith(word))) return true;
    
    // Contains SQL-like keywords
    const sqlKeywords = ['voted', 'voters', 'party', 'district', 'precinct', 'age', 'year', 'election', 'switched', 'new voter'];
    const hasMultipleKeywords = sqlKeywords.filter(kw => q.includes(kw)).length >= 2;
    if (hasMultipleKeywords) return true;
    
    // Contains comparison operators
    if (q.includes(' in ') || q.includes(' but not ') || q.includes(' and ') || q.includes(' or ')) {
        return true;
    }
    
    // Default to traditional search for simple queries (names, addresses)
    return false;
}

// Request user's location
function requestUserLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                window.userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                console.log('User location obtained:', window.userLocation);
            },
            (error) => {
                console.warn('Geolocation error:', error.message);
            }
        );
    }
}

// ── AI-Powered Search ──
async function runAiSearch(question) {
    const status = document.getElementById('vsStatus');
    const aiResponse = document.getElementById('vsAiResponse');
    const aiContent = document.getElementById('vsAiContent');
    const aiSql = document.getElementById('vsAiSql');
    const aiSqlCode = document.getElementById('vsAiSqlCode');
    const aiSuggestions = document.getElementById('vsAiSuggestions');
    const results = document.getElementById('vsResults');

    status.textContent = 'AI is thinking...';
    aiResponse.style.display = 'none';

    console.log('AI search query:', question);
    console.log('AI search context:', getSearchContext());

    try {
        const resp = await fetch('/api/llm/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ 
                question,
                context: getSearchContext()
            })
        });

        if (resp.status === 401) {
            status.textContent = '🔒 Please sign in to use AI search.';
            aiResponse.style.display = 'block';
            aiContent.innerHTML = '<p style="text-align:center;padding:20px;">AI-powered search requires authentication. Please sign in with Google to use this feature.</p>';
            return;
        }

        if (resp.status === 400) {
            const error = await resp.json();
            console.error('AI search 400 error:', error);
            status.textContent = 'Error: ' + (error.error || 'Bad request');
            aiResponse.style.display = 'block';
            aiContent.innerHTML = '<p style="color:#c33;">Error: ' + (error.error || 'Bad request') + '</p>';
            return;
        }

        if (resp.status === 503) {
            status.textContent = 'AI service not available. Using traditional search...';
            setTimeout(() => runTraditionalSearch(question), 1000);
            return;
        }

        if (!resp.ok) {
            const error = await resp.json();
            status.textContent = 'AI search failed: ' + (error.error || 'Unknown error');
            return;
        }

        const data = await resp.json();

        if (!data.success) {
            status.textContent = 'AI search failed: ' + (data.error || 'Unknown error');
            return;
        }

        // Show AI response section
        aiResponse.style.display = 'block';
        status.textContent = '';

        // Show explanation
        aiContent.innerHTML = '<p>' + (data.explanation || 'Query executed successfully.') + '</p>';

        // Show SQL query (collapsible)
        if (data.sql) {
            aiSql.style.display = 'block';
            aiSqlCode.textContent = data.sql;
        }

        // Show suggestions
        if (data.suggestions && data.suggestions.length > 0) {
            let suggestionsHtml = '<div class="vs-ai-suggestions-label">💡 You might also ask:</div>';
            data.suggestions.forEach(suggestion => {
                suggestionsHtml += '<button class="vs-ai-suggestion-btn" onclick="fillExample(\'' + 
                    suggestion.replace(/'/g, "\\'") + '\')">' + suggestion + '</button>';
            });
            aiSuggestions.innerHTML = suggestionsHtml;
        } else {
            aiSuggestions.innerHTML = '';
        }

        // Show results as table or cards
        if (data.results && data.results.length > 0) {
            status.textContent = data.count + ' result' + (data.count === 1 ? '' : 's');
            
            // Check if results look like voter records (have vuid, name fields)
            const hasVoterFields = data.results[0].vuid || data.results[0].firstname || data.results[0].name;
            
            if (hasVoterFields) {
                // Render as voter cards
                renderAiVoterResults(data.results, results);
            } else {
                // Render as data table
                renderAiTableResults(data.results, data.columns, results);
            }
        } else {
            status.textContent = 'No results found.';
        }

    } catch (err) {
        console.error('AI search error:', err);
        status.textContent = 'AI search error. Try traditional search.';
    }
}

function getSearchContext() {
    const context = {};
    if (window.activeDistrict) {
        context.district = window.activeDistrict.properties.district_id;
    }
    if (window.currentCounty) {
        context.county = window.currentCounty;
    }
    return context;
}

function renderAiVoterResults(voters, container) {
    // Convert AI results to voter card format
    voters.forEach(v => {
        const card = document.createElement('div');
        card.className = 'vs-card';

        const name = v.name || [v.firstname, v.middlename, v.lastname, v.suffix].filter(Boolean).join(' ');
        const gender = v.sex === 'F' ? 'Female' : v.sex === 'M' ? 'Male' : v.sex || '';
        const addr = v.full_address || [v.address, v.city, v.zip].filter(Boolean).join(', ');
        const hasCoords = v.lat && v.lng;

        card.innerHTML = buildVoterRow(name, v, gender, addr, hasCoords, true);
        container.appendChild(card);
    });
}

function renderAiTableResults(rows, columns, container) {
    const table = document.createElement('table');
    table.className = 'vs-ai-table';
    
    // Header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // Body
    const tbody = document.createElement('tbody');
    rows.forEach(row => {
        const tr = document.createElement('tr');
        columns.forEach(col => {
            const td = document.createElement('td');
            const val = row[col];
            td.textContent = val !== null && val !== undefined ? val : '';
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    
    container.appendChild(table);
}

// ── Traditional Name/Address Search ──
async function runTraditionalSearch(query) {
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

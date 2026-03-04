// District 15 Election Night Dashboard

let map;
let precinctLayer;
let countyLayer;
let districtBoundary;

// Initialize map centered on District 15
function initMap() {
    map = L.map('map', {
        zoomControl: true,
        attributionControl: false
    }).setView([26.3, -98.2], 9); // Centered on District 15
    
    // Dark base map
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        subdomains: 'abcd'
    }).addTo(map);
    
    // Load District 15 boundary
    loadDistrictBoundary();
    
    // Load initial data
    loadElectionData();
    
    // Auto-refresh every 30 seconds
    setInterval(loadElectionData, 30000);
}

async function loadDistrictBoundary() {
    try {
        const response = await fetch('/data/congressional_districts.json');
        const data = await response.json();
        
        // Find District 15
        const district15 = data.features.find(f => 
            f.properties.DISTRICT === '15' || f.properties.district === '15'
        );
        
        if (district15) {
            districtBoundary = L.geoJSON(district15, {
                style: {
                    color: '#667eea',
                    weight: 3,
                    opacity: 0.8,
                    fillOpacity: 0.05,
                    fillColor: '#667eea'
                }
            }).addTo(map);
            
            // Fit map to district bounds
            map.fitBounds(districtBoundary.getBounds(), { padding: [20, 20] });
        }
    } catch (error) {
        console.error('Error loading district boundary:', error);
    }
}

async function loadElectionData() {
    const btn = document.getElementById('refreshBtn');
    btn.classList.add('loading');
    
    try {
        const response = await fetch('/api/d15/results');
        const data = await response.json();
        
        updateStats(data.totals);
        updateCounties(data.counties);
        updatePrecincts(data.precincts);
        updateMap(data);
        
        document.getElementById('lastUpdated').textContent = 
            `Last updated: ${new Date().toLocaleTimeString()}`;
    } catch (error) {
        console.error('Error loading election data:', error);
    } finally {
        btn.classList.remove('loading');
    }
}

function updateStats(totals) {
    const demVotes = totals.dem || 0;
    const repVotes = totals.rep || 0;
    const total = demVotes + repVotes;
    
    const demPct = total > 0 ? (demVotes / total * 100).toFixed(1) : 0;
    const repPct = total > 0 ? (repVotes / total * 100).toFixed(1) : 0;
    
    document.getElementById('demVotes').textContent = demVotes.toLocaleString();
    document.getElementById('repVotes').textContent = repVotes.toLocaleString();
    document.getElementById('demPct').textContent = `${demPct}%`;
    document.getElementById('repPct').textContent = `${repPct}%`;
    
    // Highlight winning card
    const demCard = document.getElementById('demCard');
    const repCard = document.getElementById('repCard');
    
    demCard.classList.remove('winning', 'losing');
    repCard.classList.remove('winning', 'losing');
    
    if (demVotes > repVotes) {
        demCard.classList.add('winning');
        repCard.classList.add('losing');
    } else if (repVotes > demVotes) {
        repCard.classList.add('winning');
        demCard.classList.add('losing');
    }
}

function updateCounties(counties) {
    const list = document.getElementById('countiesList');
    list.innerHTML = '';
    
    counties.forEach(county => {
        const total = county.dem + county.rep;
        const demPct = total > 0 ? (county.dem / total * 100) : 50;
        const margin = Math.abs(county.dem - county.rep);
        const winner = county.dem > county.rep ? 'dem' : 'rep';
        const marginPct = total > 0 ? (margin / total * 100).toFixed(1) : 0;
        
        const item = document.createElement('div');
        item.className = `county-item ${winner}`;
        item.innerHTML = `
            <div class="item-header">
                <div class="item-name">${county.name}</div>
                <div class="item-margin">+${marginPct}%</div>
            </div>
            <div class="vote-bar">
                <div class="vote-bar-fill ${winner}" style="width: ${Math.max(demPct, 100 - demPct)}%"></div>
            </div>
            <div class="vote-counts">
                <span>D: ${county.dem.toLocaleString()}</span>
                <span>R: ${county.rep.toLocaleString()}</span>
            </div>
        `;
        
        item.addEventListener('click', () => zoomToCounty(county.name));
        list.appendChild(item);
    });
}

function updatePrecincts(precincts) {
    const list = document.getElementById('precinctsList');
    list.innerHTML = '';
    
    // Show top 10 precincts by total votes
    const sorted = precincts.sort((a, b) => (b.dem + b.rep) - (a.dem + a.rep)).slice(0, 10);
    
    sorted.forEach(precinct => {
        const total = precinct.dem + precinct.rep;
        const demPct = total > 0 ? (precinct.dem / total * 100) : 50;
        const margin = Math.abs(precinct.dem - precinct.rep);
        const winner = precinct.dem > precinct.rep ? 'dem' : 'rep';
        const marginPct = total > 0 ? (margin / total * 100).toFixed(1) : 0;
        
        const item = document.createElement('div');
        item.className = `precinct-item ${winner}`;
        item.innerHTML = `
            <div class="item-header">
                <div class="item-name">${precinct.county} - Precinct ${precinct.number}</div>
                <div class="item-margin">+${marginPct}%</div>
            </div>
            <div class="vote-bar">
                <div class="vote-bar-fill ${winner}" style="width: ${Math.max(demPct, 100 - demPct)}%"></div>
            </div>
            <div class="vote-counts">
                <span>D: ${precinct.dem.toLocaleString()}</span>
                <span>R: ${precinct.rep.toLocaleString()}</span>
            </div>
        `;
        
        item.addEventListener('click', () => zoomToPrecinct(precinct));
        list.appendChild(item);
    });
}

function updateMap(data) {
    // Remove existing layers
    if (precinctLayer) map.removeLayer(precinctLayer);
    if (countyLayer) map.removeLayer(countyLayer);
    
    // Add precinct layer with color coding
    loadPrecinctLayer(data.precincts);
}

async function loadPrecinctLayer(precincts) {
    try {
        const response = await fetch('/data/precinct_boundaries_combined.json');
        const geojson = await response.json();
        
        // Create lookup map for results
        const resultsMap = {};
        precincts.forEach(p => {
            const key = `${p.county}_${p.number}`;
            resultsMap[key] = p;
        });
        
        precinctLayer = L.geoJSON(geojson, {
            style: (feature) => {
                const county = feature.properties.county || feature.properties.COUNTY;
                const precinct = feature.properties.precinct || feature.properties.PRECINCT;
                const key = `${county}_${precinct}`;
                const results = resultsMap[key];
                
                if (!results || (results.dem + results.rep) === 0) {
                    return {
                        color: '#4a5568',
                        weight: 1,
                        opacity: 0.5,
                        fillOpacity: 0.1,
                        fillColor: '#2d3748'
                    };
                }
                
                const total = results.dem + results.rep;
                const demPct = results.dem / total;
                const intensity = Math.abs(demPct - 0.5) * 2; // 0 to 1
                
                const color = demPct > 0.5 ? '#3b82f6' : '#ef4444';
                const fillOpacity = 0.3 + (intensity * 0.5);
                
                return {
                    color: color,
                    weight: 2,
                    opacity: 0.8,
                    fillOpacity: fillOpacity,
                    fillColor: color
                };
            },
            onEachFeature: (feature, layer) => {
                const county = feature.properties.county || feature.properties.COUNTY;
                const precinct = feature.properties.precinct || feature.properties.PRECINCT;
                const key = `${county}_${precinct}`;
                const results = resultsMap[key];
                
                if (results) {
                    const total = results.dem + results.rep;
                    const demPct = total > 0 ? (results.dem / total * 100).toFixed(1) : 0;
                    const repPct = total > 0 ? (results.rep / total * 100).toFixed(1) : 0;
                    
                    layer.bindPopup(`
                        <div style="font-family: sans-serif;">
                            <h3 style="margin: 0 0 10px 0;">${county} - Precinct ${precinct}</h3>
                            <div style="margin-bottom: 5px;">
                                <strong>Democratic:</strong> ${results.dem.toLocaleString()} (${demPct}%)
                            </div>
                            <div>
                                <strong>Republican:</strong> ${results.rep.toLocaleString()} (${repPct}%)
                            </div>
                        </div>
                    `);
                }
            }
        }).addTo(map);
        
    } catch (error) {
        console.error('Error loading precinct layer:', error);
    }
}

function zoomToCounty(countyName) {
    // Zoom to county bounds (would need county boundaries data)
    console.log('Zoom to county:', countyName);
}

function zoomToPrecinct(precinct) {
    // Zoom to specific precinct (would need to find in layer)
    console.log('Zoom to precinct:', precinct);
}

// Event listeners
document.getElementById('refreshBtn').addEventListener('click', loadElectionData);

// Initialize on load
document.addEventListener('DOMContentLoaded', initMap);

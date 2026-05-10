// HD-41 Runoff Election Tracker — Map and Data Visualization
// Dem: Salinas vs Haddad | Rep: Sanchez vs Groves | May 26, 2026

let map;
let markerClusterGroup = null;
let heatLayer = null;
let nonvoterHeatLayer = null;
let allVotersData = null;
let currentFilter = null; // null = all, 'Democratic', 'Republican'

// ── Loading screen ──
function showLoading() {
    const div = document.createElement('div');
    div.id = 'loading-screen';
    div.innerHTML = `<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(255,255,255,0.95);z-index:10000;display:flex;align-items:center;justify-content:center;">
        <div style="text-align:center">
            <div style="font-size:24px;font-weight:600;color:#333;margin-bottom:10px">Loading HD-41 Data</div>
            <div style="font-size:14px;color:#666">Dem: Salinas vs Haddad · Rep: Sanchez vs Groves</div>
        </div>
    </div>`;
    document.body.appendChild(div);
}
function hideLoading() {
    const el = document.getElementById('loading-screen');
    if (el) el.remove();
}

// ── Initialize map ──
function initMap() {
    // HD-41 center — roughly Weslaco/Mercedes area
    map = L.map('map').setView([26.16, -97.99], 11);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);

    markerClusterGroup = L.markerClusterGroup({
        maxClusterRadius: 25,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        disableClusteringAtZoom: 17,
        iconCreateFunction: function() {
            return L.divIcon({ html: '', className: 'invisible-cluster', iconSize: L.point(1, 1) });
        }
    });
    map.addLayer(markerClusterGroup);

    map.on('zoomend', function() {
        const z = map.getZoom();
        if (heatLayer) {
            if (z >= 17 && map.hasLayer(heatLayer)) map.removeLayer(heatLayer);
            else if (z < 17 && !map.hasLayer(heatLayer) && document.getElementById('heatmap-btn').classList.contains('btn-active')) heatLayer.addTo(map);
        }
    });

    setupEventListeners();
    loadData();
}

// ── Event listeners ──
function setupEventListeners() {
    document.getElementById('search-input').addEventListener('input', handleSearch);
    document.getElementById('location-btn').addEventListener('click', zoomToUserLocation);
    document.getElementById('gazette-btn').addEventListener('click', toggleGazette);
    document.getElementById('reportcard-btn').addEventListener('click', toggleReportCard);
    document.getElementById('heatmap-btn').addEventListener('click', toggleHeatmap);
    document.getElementById('nonvoters-btn').addEventListener('click', toggleNonvoters);
    document.getElementById('layer-dem-btn').addEventListener('click', () => filterByParty('Democratic'));
    document.getElementById('layer-rep-btn').addEventListener('click', () => filterByParty('Republican'));
    document.getElementById('gazette-close').addEventListener('click', () => document.getElementById('gazette-panel').classList.remove('visible'));
    document.getElementById('reportcard-close').addEventListener('click', () => document.getElementById('reportcard-panel').classList.remove('visible'));
    document.getElementById('modal-close').addEventListener('click', () => document.getElementById('voters-breakdown-modal').classList.remove('visible'));
}

// ── Load data ──
async function loadData() {
    showLoading();
    try {
        const resp = await fetch('/cache/hd41_voters.json');
        if (!resp.ok) throw new Error('Cache not found');
        const data = await resp.json();
        allVotersData = data;

        updateStats(data);
        renderVoters(data.voters);
        hideLoading();
    } catch (e) {
        hideLoading();
        console.error('Error loading data:', e);
    }
}

// ── Update stats ──
function updateStats(data) {
    const totalVoted = data.total_voted || data.count;
    document.getElementById('total-voters').textContent = totalVoted.toLocaleString();
    document.getElementById('total-voters').style.cursor = 'pointer';
    document.getElementById('total-voters').onclick = function() {
        const mb = data.method_breakdown || {};
        let html = '<h4>🗳️ Voting Method Breakdown</h4><table style="width:100%;border-collapse:collapse;font-size:14px;margin:12px 0">';
        for (const [method, count] of Object.entries(mb)) {
            html += `<tr style="border-bottom:1px solid #eee"><td style="padding:6px">${method}</td><td style="padding:6px;font-weight:700;text-align:right">${count.toLocaleString()}</td></tr>`;
        }
        html += `<tr style="border-top:2px solid #333"><td style="padding:6px;font-weight:700">Total</td><td style="padding:6px;font-weight:700;text-align:right">${totalVoted.toLocaleString()}</td></tr></table>`;
        if (data.unmapped_count) html += `<p style="color:#888;font-size:12px">+ ${data.unmapped_count} unmapped voters (no address on file)</p>`;
        document.getElementById('voters-breakdown-content').innerHTML = html;
        document.getElementById('voters-breakdown-modal').classList.add('visible');
    };

    if (data.last_data_added) {
        const d = new Date(data.last_data_added.replace(' ', 'T') + 'Z');
        document.getElementById('last-update').textContent = d.toLocaleString('en-US', { timeZone: 'America/Chicago', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true });
    }
}

// ── Render voters on map ──
function renderVoters(voters, filter) {
    markerClusterGroup.clearLayers();
    if (heatLayer) { map.removeLayer(heatLayer); heatLayer = null; }

    const heatPoints = [];
    const filtered = filter ? voters.filter(v => v.party_voted === filter) : voters;

    for (const v of filtered) {
        if (!v.lat || !v.lng) continue;
        heatPoints.push([v.lat, v.lng, 0.5]);

        const color = v.party_voted === 'Democratic' ? '#1565c0' : v.party_voted === 'Republican' ? '#c62828' : '#666';
        const marker = L.circleMarker([v.lat, v.lng], {
            radius: 4, fillColor: color, color: color, weight: 1, opacity: 0.8, fillOpacity: 0.6
        });

        const age = v.birth_year ? (2026 - v.birth_year) : '?';
        const hist = (v.hist || []).map(h => `<span style="color:${h.p === 'D' ? '#1565c0' : h.p === 'R' ? '#c62828' : '#666'}">${h.y}${h.p}</span>`).join(' ');
        marker.bindPopup(`
            <div style="font-family:sans-serif;min-width:200px">
                <div style="font-weight:700;font-size:13px">${v.name}</div>
                <div style="font-size:11px;color:#666;margin:2px 0">${v.address || ''}, ${v.city || ''} ${v.zip || ''}</div>
                <div style="font-size:11px;margin-top:4px">
                    <b>Party:</b> ${v.party_voted || '—'} · <b>Age:</b> ${age} · <b>Sex:</b> ${v.sex || '—'}
                </div>
                <div style="font-size:11px"><b>Method:</b> ${v.voting_method || '—'} · <b>Precinct:</b> ${v.precinct || '—'}</div>
                ${hist ? `<div style="font-size:10px;margin-top:4px;color:#888">History: ${hist}</div>` : ''}
            </div>
        `, { maxWidth: 280 });

        markerClusterGroup.addLayer(marker);
    }

    // Add heatmap
    if (heatPoints.length > 0) {
        heatLayer = L.heatLayer(heatPoints, { radius: 15, blur: 20, maxZoom: 16, max: 1.0 });
        if (document.getElementById('heatmap-btn').classList.contains('btn-active')) {
            heatLayer.addTo(map);
        }
    }
}

// ── Party filter ──
function filterByParty(party) {
    if (currentFilter === party) {
        currentFilter = null;
        document.getElementById('layer-dem-btn').classList.remove('btn-active');
        document.getElementById('layer-rep-btn').classList.remove('btn-active');
    } else {
        currentFilter = party;
        document.getElementById('layer-dem-btn').classList.toggle('btn-active', party === 'Democratic');
        document.getElementById('layer-rep-btn').classList.toggle('btn-active', party === 'Republican');
    }
    if (allVotersData) renderVoters(allVotersData.voters, currentFilter);
}

// ── Heatmap toggle ──
function toggleHeatmap() {
    const btn = document.getElementById('heatmap-btn');
    btn.classList.toggle('btn-active');
    if (heatLayer) {
        if (btn.classList.contains('btn-active')) heatLayer.addTo(map);
        else map.removeLayer(heatLayer);
    }
}

// ── Non-voters toggle ──
async function toggleNonvoters() {
    const btn = document.getElementById('nonvoters-btn');
    btn.classList.toggle('btn-active');

    if (!btn.classList.contains('btn-active')) {
        if (nonvoterHeatLayer) { map.removeLayer(nonvoterHeatLayer); }
        return;
    }

    if (!nonvoterHeatLayer) {
        try {
            const resp = await fetch('/cache/hd41_nonvoters.json');
            const data = await resp.json();
            const points = data.points.map(p => [p[0], p[1], 0.3]);
            nonvoterHeatLayer = L.heatLayer(points, { radius: 12, blur: 18, maxZoom: 16, max: 1.0, gradient: { 0.4: '#bbb', 0.65: '#888', 1: '#333' } });
        } catch (e) {
            console.error('Failed to load non-voters:', e);
            btn.classList.remove('btn-active');
            return;
        }
    }
    nonvoterHeatLayer.addTo(map);
}

// ── Gazette ──
async function toggleGazette() {
    const panel = document.getElementById('gazette-panel');
    panel.classList.toggle('visible');
    if (!panel.classList.contains('visible')) return;

    try {
        const resp = await fetch('/cache/hd41_gazette.json');
        const data = await resp.json();
        let html = `<div class="gazette-headline">${data.headline}</div>`;
        html += `<div class="gazette-subhead">${data.subhead}</div>`;
        html += `<div style="font-size:11px;color:#888;margin-bottom:12px">${data.date}</div>`;
        for (const b of (data.bullets || [])) {
            html += `<div class="gazette-bullet">${b}</div>`;
        }
        for (const s of (data.stories || [])) {
            html += `<div class="gazette-story"><div class="gazette-story-title">${s.icon || ''} ${s.title}</div><div class="gazette-story-text">${s.text}</div></div>`;
        }
        document.getElementById('gazette-content').innerHTML = html;
    } catch (e) {
        document.getElementById('gazette-content').innerHTML = '<p style="color:#c62828">Failed to load gazette data.</p>';
    }
}

// ── Report Card ──
async function toggleReportCard() {
    const panel = document.getElementById('reportcard-panel');
    panel.classList.toggle('visible');
    if (!panel.classList.contains('visible')) return;

    try {
        const resp = await fetch('/cache/hd41_reportcard.json');
        const data = await resp.json();
        let html = `<h3 style="margin-bottom:4px">📋 HD-41 Precinct Report Card</h3>`;
        html += `<p style="font-size:12px;color:#666;margin-bottom:12px">Overall: ${data.summary.total_voted.toLocaleString()}/${data.summary.total_registered.toLocaleString()} = ${data.summary.overall_turnout_pct}% (${data.summary.overall_grade})</p>`;
        html += '<table style="width:100%;border-collapse:collapse;font-size:12px">';
        html += '<tr style="border-bottom:2px solid #333;text-align:left"><th style="padding:4px">Precinct</th><th style="padding:4px">Voted</th><th style="padding:4px">Reg</th><th style="padding:4px">%</th><th style="padding:4px">Grade</th></tr>';

        const sorted = [...data.districts].sort((a, b) => b.turnout_pct - a.turnout_pct);
        for (const d of sorted) {
            const gradeColor = d.grade === 'A' ? '#2e7d32' : d.grade === 'B' ? '#558b2f' : d.grade === 'C' ? '#f57f17' : d.grade === 'D' ? '#e65100' : '#c62828';
            html += `<tr style="border-bottom:1px solid #eee"><td style="padding:4px">${d.name}</td><td style="padding:4px">${d.voted.toLocaleString()}</td><td style="padding:4px">${d.registered.toLocaleString()}</td><td style="padding:4px">${d.turnout_pct}%</td><td style="padding:4px;font-weight:700;color:${gradeColor}">${d.grade}</td></tr>`;
        }
        html += '</table>';
        document.getElementById('reportcard-content').innerHTML = html;
    } catch (e) {
        document.getElementById('reportcard-content').innerHTML = '<p style="color:#c62828">Failed to load report card.</p>';
    }
}

// ── Search ──
function handleSearch(e) {
    const query = e.target.value.toLowerCase().trim();
    const resultsDiv = document.getElementById('search-results');
    if (!query || query.length < 2 || !allVotersData) { resultsDiv.classList.remove('visible'); return; }

    const results = allVotersData.voters.filter(v => {
        const name = v.name.toLowerCase();
        const addr = (v.address || '').toLowerCase();
        return name.includes(query) || addr.includes(query);
    }).slice(0, 8);

    if (!results.length) { resultsDiv.innerHTML = '<div class="search-result-item" style="color:#999">No results</div>'; resultsDiv.classList.add('visible'); return; }

    resultsDiv.innerHTML = results.map((v, i) => `
        <div class="search-result-item" data-idx="${i}">
            <div class="search-result-name">${v.name}</div>
            <div class="search-result-address">${v.address || ''} · ${v.party_voted || ''}</div>
        </div>
    `).join('');
    resultsDiv.classList.add('visible');

    resultsDiv.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
            const v = results[parseInt(item.dataset.idx)];
            if (!v || !v.lat) return;
            resultsDiv.classList.remove('visible');
            document.getElementById('search-input').value = v.name;
            map.setView([v.lat, v.lng], 17);
        });
    });
}

document.addEventListener('click', function(e) {
    const r = document.getElementById('search-results');
    if (r && !r.contains(e.target) && e.target.id !== 'search-input') r.classList.remove('visible');
});

// ── GPS ──
function zoomToUserLocation() {
    if (!navigator.geolocation) { alert('Geolocation not supported'); return; }
    navigator.geolocation.getCurrentPosition(
        pos => { map.setView([pos.coords.latitude, pos.coords.longitude], 15); },
        () => { alert('Unable to get location'); },
        { enableHighAccuracy: true, timeout: 10000 }
    );
}

// ── Init ──
document.addEventListener('DOMContentLoaded', initMap);

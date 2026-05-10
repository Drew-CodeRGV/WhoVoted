// HD-41 Runoff Election Tracker
// Dem: Salinas vs Haddad | Rep: Sanchez vs Groves | May 26, 2026

let map;
let markerClusterGroup = null;
let heatLayer = null;
let allVotersData = null;
let marchData = null;
let reportcardData = null;
let currentHeatMode = 'voters';

// Fun loading messages
const loadingMessages = [
    "Loading voter rolls...", "Counting ballots...", "Mapping precincts...",
    "Brewing coffee for poll workers...", "Sharpening pencils...",
    "Checking voter rolls...", "Organizing precinct maps..."
];
let currentMessageIndex = 0;
let loadingStartTime = 0;

function showLoading() {
    loadingStartTime = Date.now();
    const div = document.createElement('div');
    div.id = 'loading-screen';
    div.innerHTML = `<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(255,255,255,0.95);z-index:10000;display:flex;flex-direction:column;align-items:center;justify-content:center;">
        <div style="text-align:center">
            <div style="width:80px;height:80px;margin:0 auto 20px;"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="45" fill="none" stroke="#e0e0e0" stroke-width="8"/><circle cx="50" cy="50" r="45" fill="none" stroke="#0066cc" stroke-width="8" stroke-dasharray="283" stroke-dashoffset="283" stroke-linecap="round" transform="rotate(-90 50 50)"><animate attributeName="stroke-dashoffset" from="283" to="0" dur="3s" repeatCount="indefinite"/></circle></svg></div>
            <div style="font-size:24px;font-weight:600;color:#333;margin-bottom:10px">Loading HD-41 Data</div>
            <div id="loading-message" style="font-size:14px;color:#666;font-style:italic;">${loadingMessages[0]}</div>
            <div style="margin-top:15px;font-size:12px;color:#999;"><span id="loading-time">0.0s</span> elapsed</div>
        </div>
    </div>`;
    document.body.appendChild(div);
    setInterval(() => {
        currentMessageIndex = (currentMessageIndex + 1) % loadingMessages.length;
        const el = document.getElementById('loading-message');
        if (el) el.textContent = loadingMessages[currentMessageIndex];
    }, 1500);
    setInterval(() => {
        const el = document.getElementById('loading-time');
        if (el) el.textContent = ((Date.now() - loadingStartTime) / 1000).toFixed(1) + 's';
    }, 100);
}
function hideLoading() { const el = document.getElementById('loading-screen'); if (el) el.remove(); }

// ── Init ──
function initMap() {
    map = L.map('map').setView([26.16, -97.99], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors', maxZoom: 18
    }).addTo(map);

    markerClusterGroup = L.markerClusterGroup({
        maxClusterRadius: 25, spiderfyOnMaxZoom: true, showCoverageOnHover: false,
        zoomToBoundsOnClick: true, disableClusteringAtZoom: 17,
        iconCreateFunction: () => L.divIcon({ html: '', className: 'invisible-cluster', iconSize: L.point(1, 1) })
    });
    map.addLayer(markerClusterGroup);

    map.on('zoomend', () => {
        if (heatLayer && map.getZoom() >= 17 && map.hasLayer(heatLayer)) map.removeLayer(heatLayer);
        else if (heatLayer && map.getZoom() < 17 && !map.hasLayer(heatLayer)) heatLayer.addTo(map);
    });

    setupEventListeners();
    loadData();
}

function setupEventListeners() {
    document.getElementById('search-input').addEventListener('input', handleSearch);
    document.getElementById('location-btn').addEventListener('click', zoomToUserLocation);
    document.getElementById('reportcard-btn').addEventListener('click', toggleReportCard);
    document.getElementById('gazette-btn').addEventListener('click', toggleGazette);
    document.getElementById('reportcard-close').addEventListener('click', () => document.getElementById('reportcard-panel').classList.remove('visible'));
    document.getElementById('gazette-close').addEventListener('click', () => document.getElementById('gazette-panel').classList.remove('visible'));
    document.getElementById('disclaimer-notice').addEventListener('click', () => document.getElementById('disclaimer-modal').classList.add('visible'));
    document.getElementById('disclaimer-close').addEventListener('click', () => document.getElementById('disclaimer-modal').classList.remove('visible'));
    document.getElementById('heatmap-mode').addEventListener('change', handleHeatmapChange);
}

// ── Load data ──
async function loadData() {
    showLoading();
    try {
        // Load runoff voters (may be empty before election)
        const voterResp = await fetch('/cache/hd41_voters.json');
        allVotersData = await voterResp.json();

        // Load March primary data (always has data)
        const marchResp = await fetch('/cache/hd41_march_primary.json');
        marchData = await marchResp.json();

        // Load report card
        const rcResp = await fetch('/cache/hd41_reportcard.json');
        reportcardData = await rcResp.json();

        // If runoff has voters, show them. Otherwise show March primary.
        if (allVotersData.count > 0) {
            updateStats(allVotersData);
            renderVoters(allVotersData.voters);
        } else {
            // Show March primary data as the default view
            updateStatsMarch(marchData);
            renderMarchVoters(marchData);
        }

        hideLoading();
    } catch (e) {
        hideLoading();
        console.error('Error loading data:', e);
    }
}

// ── Stats (runoff) ──
function updateStats(data) {
    const total = data.total_voted || data.count;
    const el = document.getElementById('total-voters');
    el.textContent = total.toLocaleString();
    el.style.cursor = 'pointer';
    el.onclick = () => showBreakdownModal(data);
    if (data.last_data_added) {
        const d = new Date(data.last_data_added.replace(' ', 'T') + 'Z');
        document.getElementById('last-update').textContent = d.toLocaleString('en-US', { timeZone: 'America/Chicago', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true });
    }
}

// ── Stats (March primary — shown when runoff has no data yet) ──
function updateStatsMarch(data) {
    const total = data.summary.total_voted;
    const el = document.getElementById('total-voters');
    el.textContent = total.toLocaleString();
    el.style.cursor = 'pointer';
    el.onclick = () => {
        let html = `<h4>📜 March 3 Primary Results (HD-41)</h4>`;
        html += `<p style="font-size:13px;color:#666;margin-bottom:12px">First round — both races went to runoff</p>`;
        html += `<table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:12px">`;
        html += `<tr style="border-bottom:1px solid #eee"><td style="padding:6px">🔵 Democratic ballots</td><td style="padding:6px;font-weight:700;text-align:right">${data.summary.dem_total.toLocaleString()}</td></tr>`;
        html += `<tr style="border-bottom:1px solid #eee"><td style="padding:6px">🔴 Republican ballots</td><td style="padding:6px;font-weight:700;text-align:right">${data.summary.rep_total.toLocaleString()}</td></tr>`;
        html += `<tr style="border-top:2px solid #333"><td style="padding:6px;font-weight:700">Total</td><td style="padding:6px;font-weight:700;text-align:right">${total.toLocaleString()}</td></tr>`;
        html += `</table>`;
        html += `<p style="font-size:12px;color:#888">Dem retention into runoff: ${data.summary.dem_retention_pct}% | Rep: ${data.summary.rep_retention_pct}%</p>`;
        html += `<p style="font-size:12px;color:#c62828;font-weight:600">Dem mobilization targets: ${data.summary.dem_not_returned.toLocaleString()} | Rep: ${data.summary.rep_not_returned.toLocaleString()}</p>`;
        document.getElementById('voters-breakdown-content').innerHTML = html;
        document.getElementById('voters-breakdown-modal').classList.add('visible');
    };
    document.getElementById('last-update').textContent = 'March 3 primary';
}

function showBreakdownModal(data) {
    const mb = data.method_breakdown || {};
    let html = '<h4>🗳️ Voting Method Breakdown</h4><table style="width:100%;border-collapse:collapse;font-size:14px;margin:12px 0">';
    for (const [method, count] of Object.entries(mb)) {
        html += `<tr style="border-bottom:1px solid #eee"><td style="padding:6px">${method}</td><td style="padding:6px;font-weight:700;text-align:right">${count.toLocaleString()}</td></tr>`;
    }
    html += `</table>`;
    document.getElementById('voters-breakdown-content').innerHTML = html;
    document.getElementById('voters-breakdown-modal').classList.add('visible');
}

// ── Render voters ──
function renderVoters(voters) {
    markerClusterGroup.clearLayers();
    if (heatLayer) { map.removeLayer(heatLayer); heatLayer = null; }
    const heatPoints = [];
    for (const v of voters) {
        if (!v.lat || !v.lng) continue;
        heatPoints.push([v.lat, v.lng, 0.5]);
        const color = v.party_voted === 'Democratic' ? '#1565c0' : v.party_voted === 'Republican' ? '#c62828' : '#666';
        const marker = L.circleMarker([v.lat, v.lng], { radius: 4, fillColor: color, color: color, weight: 1, opacity: 0.8, fillOpacity: 0.6 });
        const age = v.birth_year ? (2026 - v.birth_year) : '?';
        const hist = (v.hist || []).map(h => `<span style="color:${h.p==='D'?'#1565c0':h.p==='R'?'#c62828':'#666'}">${h.y}${h.p}</span>`).join(' ');
        marker.bindPopup(`<div style="font-family:sans-serif;min-width:200px"><div style="font-weight:700;font-size:13px">${v.name}</div><div style="font-size:11px;color:#666">${v.address||''}, ${v.city||''} ${v.zip||''}</div><div style="font-size:11px;margin-top:4px"><b>Party:</b> ${v.party_voted||'—'} · <b>Age:</b> ${age} · <b>Sex:</b> ${v.sex||'—'}</div><div style="font-size:11px"><b>Method:</b> ${v.voting_method||'—'} · <b>Pct:</b> ${v.precinct||'—'}</div>${hist?`<div style="font-size:10px;margin-top:4px;color:#888">History: ${hist}</div>`:''}</div>`, { maxWidth: 280 });
        markerClusterGroup.addLayer(marker);
    }
    if (heatPoints.length) { heatLayer = L.heatLayer(heatPoints, { radius: 15, blur: 20, maxZoom: 16 }); heatLayer.addTo(map); }
}

function renderMarchVoters(data) {
    markerClusterGroup.clearLayers();
    if (heatLayer) { map.removeLayer(heatLayer); heatLayer = null; }
    const heatPoints = [];
    // Use mobilization targets (they have lat/lng in address field) or precincts
    for (const pct of data.precincts) {
        if (!pct.lat || !pct.lng) continue;
        // Draw precinct centroid as a larger circle
        const demPct = pct.dem_share;
        const color = demPct >= 60 ? '#1565c0' : demPct <= 40 ? '#c62828' : '#9c27b0';
        const size = Math.max(8, Math.min(25, Math.sqrt(pct.total) * 2));
        const marker = L.circleMarker([pct.lat, pct.lng], { radius: size, fillColor: color, color: color, weight: 2, opacity: 0.9, fillOpacity: 0.4 });
        marker.bindPopup(`<div style="font-family:sans-serif"><div style="font-weight:700">Precinct ${pct.precinct}</div><div style="font-size:12px;margin-top:4px">March primary: ${pct.total} voters<br>🔵 Dem: ${pct.dem} (${pct.dem_share}%) | 🔴 Rep: ${pct.rep} (${pct.rep_share}%)<br>Dem returned for runoff: ${pct.dem_returned} (${pct.dem_retention_pct}%)<br>Rep returned for runoff: ${pct.rep_returned} (${pct.rep_retention_pct}%)<br><b style="color:#c62828">Dem targets: ${pct.dem_not_returned}</b> | <b style="color:#1565c0">Rep targets: ${pct.rep_not_returned}</b></div></div>`, { maxWidth: 300 });
        markerClusterGroup.addLayer(marker);
        heatPoints.push([pct.lat, pct.lng, pct.total / 100]);
    }
    if (heatPoints.length) { heatLayer = L.heatLayer(heatPoints, { radius: 20, blur: 25, maxZoom: 14 }); heatLayer.addTo(map); }
}

// ── Heatmap mode change ──
async function handleHeatmapChange(e) {
    currentHeatMode = e.target.value;
    markerClusterGroup.clearLayers();
    if (heatLayer) { map.removeLayer(heatLayer); heatLayer = null; }

    if (currentHeatMode === 'voters') {
        if (allVotersData.count > 0) renderVoters(allVotersData.voters);
        else renderMarchVoters(marchData);
    } else if (currentHeatMode === 'march') {
        renderMarchVoters(marchData);
    } else if (currentHeatMode === 'nonvoters') {
        const resp = await fetch('/cache/hd41_nonvoters.json');
        const data = await resp.json();
        heatLayer = L.heatLayer(data.points.map(p => [p[0], p[1], 0.3]), { radius: 12, blur: 18, maxZoom: 16, gradient: {0.4:'#bbb',0.65:'#888',1:'#333'} });
        heatLayer.addTo(map);
    } else if (currentHeatMode === 'dem-targets' && marchData) {
        const targets = marchData.dem_target_precincts || [];
        for (const t of targets) {
            if (!t.lat || !t.lng) continue;
            const size = Math.max(8, Math.min(30, Math.sqrt(t.targets) * 3));
            const marker = L.circleMarker([t.lat, t.lng], { radius: size, fillColor: '#1565c0', color: '#0d47a1', weight: 2, opacity: 0.9, fillOpacity: 0.5 });
            marker.bindPopup(`<b>Pct ${t.precinct}</b><br>${t.targets} Dem voters from March who haven't returned<br>Retention: ${t.retention}%`);
            markerClusterGroup.addLayer(marker);
        }
    } else if (currentHeatMode === 'rep-targets' && marchData) {
        const targets = marchData.rep_target_precincts || [];
        for (const t of targets) {
            if (!t.lat || !t.lng) continue;
            const size = Math.max(8, Math.min(30, Math.sqrt(t.targets) * 3));
            const marker = L.circleMarker([t.lat, t.lng], { radius: size, fillColor: '#c62828', color: '#b71c1c', weight: 2, opacity: 0.9, fillOpacity: 0.5 });
            marker.bindPopup(`<b>Pct ${t.precinct}</b><br>${t.targets} Rep voters from March who haven't returned<br>Retention: ${t.retention}%`);
            markerClusterGroup.addLayer(marker);
        }
    }
}

// ── Report Card ──
function toggleReportCard() {
    const panel = document.getElementById('reportcard-panel');
    panel.classList.toggle('visible');
    if (panel.classList.contains('visible')) switchReportTab('all');
}

function switchReportTab(tab) {
    document.querySelectorAll('.rc-tab').forEach(t => t.classList.remove('active'));
    document.getElementById(`rc-tab-${tab}`).classList.add('active');

    const summary = document.getElementById('reportcard-summary');
    const list = document.getElementById('reportcard-list');

    if (tab === 'all' && reportcardData) {
        const s = reportcardData.summary;
        summary.innerHTML = `<div style="font-size:16px;font-weight:700;">HD-41 Runoff — ${s.total_voted.toLocaleString()} / ${s.total_registered.toLocaleString()} (${s.overall_turnout_pct}%)</div><div style="font-size:12px;color:#666;margin-top:4px;">🔵 Dem: ${s.total_dem.toLocaleString()} (${s.dem_share}%) | 🔴 Rep: ${s.total_rep.toLocaleString()} (${s.rep_share}%)</div>`;
        const sorted = [...reportcardData.districts].sort((a, b) => b.turnout_pct - a.turnout_pct);
        list.innerHTML = sorted.map(d => `<div class="rc-row"><div class="rc-grade rc-grade-${d.grade}">${d.grade}</div><div class="rc-info"><div class="rc-pct">Pct ${d.precinct} <span style="font-size:11px;color:#888;">(${d.lean})</span></div><div class="rc-detail">${d.voted}/${d.registered} voted · 🔵${d.dem} 🔴${d.rep}</div></div><div class="rc-turnout">${d.turnout_pct}%</div><div class="rc-bar"><div class="rc-bar-fill" style="width:${Math.min(100, d.turnout_pct*3)}%;background:${d.grade==='A'?'#27ae60':d.grade==='B'?'#2ecc71':d.grade==='C'?'#f39c12':d.grade==='D'?'#e67e22':'#e74c3c'}"></div></div></div>`).join('');
    } else if (tab === 'dem' && reportcardData) {
        summary.innerHTML = `<div style="font-size:16px;font-weight:700;">🔵 Democratic Runoff — Salinas vs Haddad</div><div style="font-size:12px;color:#666;">Precincts sorted by Dem ballot count</div>`;
        const sorted = [...reportcardData.districts].sort((a, b) => b.dem - a.dem);
        list.innerHTML = sorted.filter(d => d.dem > 0).map(d => `<div class="rc-row"><div class="rc-grade" style="background:#1565c0;font-size:14px;">${d.dem}</div><div class="rc-info"><div class="rc-pct">Pct ${d.precinct}</div><div class="rc-detail">${d.dem_share}% Dem share · March: ${d.march_dem} → Runoff: ${d.dem} (${d.dem_retention}% retention)</div></div><div class="rc-turnout" style="color:#1565c0">${d.dem_pct_of_reg}%</div></div>`).join('');
    } else if (tab === 'rep' && reportcardData) {
        summary.innerHTML = `<div style="font-size:16px;font-weight:700;">🔴 Republican Runoff — Sanchez vs Groves</div><div style="font-size:12px;color:#666;">Precincts sorted by Rep ballot count</div>`;
        const sorted = [...reportcardData.districts].sort((a, b) => b.rep - a.rep);
        list.innerHTML = sorted.filter(d => d.rep > 0).map(d => `<div class="rc-row"><div class="rc-grade" style="background:#c62828;font-size:14px;">${d.rep}</div><div class="rc-info"><div class="rc-pct">Pct ${d.precinct}</div><div class="rc-detail">${d.rep_share}% Rep share · March: ${d.march_rep} → Runoff: ${d.rep} (${d.rep_retention}% retention)</div></div><div class="rc-turnout" style="color:#c62828">${d.rep_pct_of_reg}%</div></div>`).join('');
    } else if (tab === 'march' && marchData) {
        const s = marchData.summary;
        summary.innerHTML = `<div style="font-size:16px;font-weight:700;">📜 March 3 Primary Results</div><div style="font-size:12px;color:#666;">${s.total_voted.toLocaleString()} voted · D:${s.dem_total.toLocaleString()} R:${s.rep_total.toLocaleString()}</div>`;
        const sorted = [...marchData.precincts].sort((a, b) => b.total - a.total);
        list.innerHTML = sorted.map(p => `<div class="rc-row"><div class="rc-grade" style="background:${p.dem_share>=60?'#1565c0':p.dem_share<=40?'#c62828':'#9c27b0'};font-size:12px;">${p.dem_share}%</div><div class="rc-info"><div class="rc-pct">Pct ${p.precinct}</div><div class="rc-detail">${p.total} voted · 🔵${p.dem} 🔴${p.rep} · Dem ret: ${p.dem_retention_pct}% · Rep ret: ${p.rep_retention_pct}%</div></div><div class="rc-turnout">${p.total}</div></div>`).join('');
    } else if (tab === 'demo') {
        summary.innerHTML = `<div style="font-size:16px;font-weight:700;">👥 Demographics</div>`;
        fetch('/cache/hd41_demographics.json').then(r => r.json()).then(data => {
            const d = data.all;
            let html = '<div style="padding:10px 18px;font-size:13px;">';
            html += `<p><b>Registered:</b> ${d.total_registered.toLocaleString()} | <b>Voted:</b> ${d.total_voted.toLocaleString()}</p>`;
            html += '<h4 style="margin:12px 0 6px;">Age Breakdown</h4>';
            for (const ag of d.age) { html += `<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px dotted #ddd;"><span>${ag.group}</span><span>${ag.voted}/${ag.registered} (${ag.turnout_pct}%)</span></div>`; }
            html += '<h4 style="margin:12px 0 6px;">Gender</h4>';
            for (const g of d.gender) { html += `<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px dotted #ddd;"><span>${g.group}</span><span>${g.voted}/${g.registered} (${g.turnout_pct}%)</span></div>`; }
            html += '<h4 style="margin:12px 0 6px;">Party</h4>';
            html += `<div>🔵 Dem: ${d.party.Democratic} | 🔴 Rep: ${d.party.Republican} | Other: ${d.party.Other}</div>`;
            html += '</div>';
            list.innerHTML = html;
        });
    }
}

// ── Gazette ──
async function toggleGazette() {
    const panel = document.getElementById('gazette-panel');
    panel.classList.toggle('visible');
    if (!panel.classList.contains('visible')) return;
    try {
        const resp = await fetch('/cache/hd41_gazette.json');
        const data = await resp.json();
        let html = `<div class="gazette-masthead"><h1>Politiquera Gazette</h1><div class="gazette-date">${data.date} · HD-41 Runoff Edition</div></div>`;
        html += `<div class="gazette-headline"><h2>${data.headline}</h2><div class="sub">${data.subhead}</div></div>`;
        html += `<ul class="gazette-bullets">`;
        for (const b of (data.bullets || [])) html += `<li>${b}</li>`;
        html += `</ul>`;
        for (const s of (data.stories || [])) {
            html += `<div class="gazette-story"><h3>${s.icon || ''} ${s.title}</h3><p>${s.text}</p></div>`;
        }
        html += `<div class="gazette-footer">Published by Politiquera.com · Not affiliated with any candidate</div>`;
        document.getElementById('gazette-content').innerHTML = html;
    } catch (e) {
        document.getElementById('gazette-content').innerHTML = '<p style="padding:20px;color:#c62828;">Failed to load gazette.</p>';
    }
}

// ── Search ──
function handleSearch(e) {
    const query = e.target.value.toLowerCase().trim();
    const resultsDiv = document.getElementById('search-results');
    if (!query || query.length < 2) { resultsDiv.classList.remove('visible'); return; }
    // Search runoff voters first, then march data
    let pool = (allVotersData && allVotersData.voters) || [];
    const results = pool.filter(v => (v.name||'').toLowerCase().includes(query) || (v.address||'').toLowerCase().includes(query)).slice(0, 8);
    if (!results.length) { resultsDiv.innerHTML = '<div class="search-result-item" style="color:#999">No results</div>'; resultsDiv.classList.add('visible'); return; }
    resultsDiv.innerHTML = results.map((v, i) => `<div class="search-result-item" data-idx="${i}"><div class="search-result-name">${v.name}</div><div class="search-result-address">${v.address||''} · ${v.party_voted||''}</div></div>`).join('');
    resultsDiv.classList.add('visible');
    resultsDiv.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
            const v = results[parseInt(item.dataset.idx)];
            if (v && v.lat) { resultsDiv.classList.remove('visible'); document.getElementById('search-input').value = v.name; map.setView([v.lat, v.lng], 17); }
        });
    });
}
document.addEventListener('click', e => { const r = document.getElementById('search-results'); if (r && !r.contains(e.target) && e.target.id !== 'search-input') r.classList.remove('visible'); });

// ── GPS ──
function zoomToUserLocation() {
    if (!navigator.geolocation) { alert('Geolocation not supported'); return; }
    navigator.geolocation.getCurrentPosition(pos => map.setView([pos.coords.latitude, pos.coords.longitude], 15), () => alert('Unable to get location'), { enableHighAccuracy: true, timeout: 10000 });
}

// ── Init ──
document.addEventListener('DOMContentLoaded', initMap);

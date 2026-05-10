// HD-41 Runoff Election Tracker — Real Data Only
// Dem: Salinas vs Haddad | Rep: Sanchez vs Groves | May 26, 2026
// ALL DATA IS REAL — from voter rolls. No estimates.

let map;
let boundaryLayer = null;
let precinctLayer = null;
let boundaryVisible = true;
let precinctData = null;
let plannerData = null;
let shapesData = null;
let currentView = 'party'; // 'party', 'planner', 'nonvoters'

const loadingMessages = ["Loading voter rolls...","Counting ballots...","Mapping precincts...","Verifying data..."];
let msgIdx = 0, loadStart = 0;

function showLoading() {
    loadStart = Date.now();
    const d = document.createElement('div'); d.id = 'loading-screen';
    d.innerHTML = `<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(255,255,255,0.95);z-index:10000;display:flex;align-items:center;justify-content:center;"><div style="text-align:center"><div style="width:60px;height:60px;margin:0 auto 16px;"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="45" fill="none" stroke="#e0e0e0" stroke-width="8"/><circle cx="50" cy="50" r="45" fill="none" stroke="#0066cc" stroke-width="8" stroke-dasharray="283" stroke-dashoffset="283" stroke-linecap="round" transform="rotate(-90 50 50)"><animate attributeName="stroke-dashoffset" from="283" to="0" dur="2s" repeatCount="indefinite"/></circle></svg></div><div style="font-size:20px;font-weight:600;color:#333;">Loading HD-41</div><div id="load-msg" style="font-size:13px;color:#666;margin-top:6px;">${loadingMessages[0]}</div></div></div>`;
    document.body.appendChild(d);
    setInterval(()=>{msgIdx=(msgIdx+1)%loadingMessages.length;const e=document.getElementById('load-msg');if(e)e.textContent=loadingMessages[msgIdx];},1200);
}
function hideLoading(){const e=document.getElementById('loading-screen');if(e)e.remove();}

function initMap() {
    map = L.map('map').setView([26.16, -97.99], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution:'© OpenStreetMap',maxZoom:18}).addTo(map);
    setupListeners();
    loadData();
}

function setupListeners() {
    document.getElementById('location-btn').addEventListener('click', ()=>{
        if(navigator.geolocation) navigator.geolocation.getCurrentPosition(p=>map.setView([p.coords.latitude,p.coords.longitude],14));
    });
    document.getElementById('boundary-toggle').addEventListener('change', e=>{
        boundaryVisible=e.target.checked;
        if(boundaryVisible&&boundaryLayer) boundaryLayer.addTo(map);
        else if(boundaryLayer&&map.hasLayer(boundaryLayer)) map.removeLayer(boundaryLayer);
    });
    document.getElementById('view-mode').addEventListener('change', e=>{
        currentView=e.target.value;
        renderMap();
    });
    document.getElementById('reportcard-btn').addEventListener('click', toggleReportCard);
    document.getElementById('gazette-btn').addEventListener('click', toggleGazette);
    document.getElementById('reportcard-close').addEventListener('click', ()=>document.getElementById('reportcard-panel').classList.remove('visible'));
    document.getElementById('gazette-close').addEventListener('click', ()=>document.getElementById('gazette-panel').classList.remove('visible'));
    document.getElementById('disclaimer-notice').addEventListener('click', ()=>document.getElementById('disclaimer-modal').classList.add('visible'));
    document.getElementById('disclaimer-close').addEventListener('click', ()=>document.getElementById('disclaimer-modal').classList.remove('visible'));
}

async function loadData() {
    showLoading();
    try {
        const [resultsResp, shapesResp, plannerResp, boundResp] = await Promise.all([
            fetch('/cache/hd41_precinct_results.json'),
            fetch('/cache/hd41_precinct_shapes.json'),
            fetch('/cache/hd41_planner.json'),
            fetch('/cache/hd41_boundary.json'),
        ]);
        precinctData = await resultsResp.json();
        shapesData = await shapesResp.json();
        plannerData = await plannerResp.json();
        const boundGeoJSON = await boundResp.json();

        // Draw HD-41 boundary
        boundaryLayer = L.geoJSON(boundGeoJSON, {style:{color:'#1a237e',weight:3,fillOpacity:0.02,dashArray:'8,4'}}).addTo(map);

        // Update header stats
        const s = precinctData.summary;
        document.getElementById('total-voters').textContent = s.total_votes.toLocaleString();
        document.getElementById('total-voters').onclick = ()=>{
            let h=`<h4>HD-41 March 3 Primary — Real Data</h4>`;
            h+=`<table style="width:100%;border-collapse:collapse;font-size:14px;margin:12px 0">`;
            h+=`<tr style="border-bottom:1px solid #eee"><td style="padding:6px">🔵 Democratic ballots</td><td style="padding:6px;font-weight:700;text-align:right">${s.total_dem_votes.toLocaleString()}</td></tr>`;
            h+=`<tr style="border-bottom:1px solid #eee"><td style="padding:6px">🔴 Republican ballots</td><td style="padding:6px;font-weight:700;text-align:right">${s.total_rep_votes.toLocaleString()}</td></tr>`;
            h+=`<tr style="border-top:2px solid #333"><td style="padding:6px;font-weight:700">Total</td><td style="padding:6px;font-weight:700;text-align:right">${s.total_votes.toLocaleString()}</td></tr></table>`;
            h+=`<p style="font-size:12px;color:#666">${s.total_precincts} precincts · ${s.precincts_with_shapes} with boundary outlines</p>`;
            h+=`<p style="font-size:12px;color:#666">Battleground: ${s.battleground} · Dem strongholds: ${s.dem_strongholds} · Lean Dem: ${s.lean_dem}</p>`;
            document.getElementById('voters-breakdown-content').innerHTML=h;
            document.getElementById('voters-breakdown-modal').classList.add('visible');
        };

        renderMap();
        hideLoading();
    } catch(e) { hideLoading(); console.error(e); }
}

function renderMap() {
    if(precinctLayer){map.removeLayer(precinctLayer);precinctLayer=null;}

    // Build precinct lookup
    const pctLookup = {};
    for(const p of precinctData.precincts) pctLookup[p.precinct]=p;

    if(currentView==='party'||currentView==='planner') {
        precinctLayer = L.geoJSON(shapesData, {
            style: feature => {
                const pct = feature.properties.db_precinct;
                const p = pctLookup[pct];
                if(!p) return {fillColor:'#ccc',fillOpacity:0.1,color:'#999',weight:1};

                let fillColor;
                if(currentView==='planner') {
                    // Color by classification
                    const pl = plannerData.all_precincts.find(x=>x.precinct===pct);
                    if(!pl) fillColor='#ccc';
                    else if(pl.classification==='Battleground') fillColor='#9c27b0';
                    else if(pl.classification==='Dem Stronghold') fillColor='#0d47a1';
                    else if(pl.classification==='Lean Dem') fillColor='#42a5f5';
                    else if(pl.classification==='Rep Stronghold') fillColor='#b71c1c';
                    else if(pl.classification==='Lean Rep') fillColor='#ef5350';
                    else fillColor='#bbb';
                } else {
                    // Color by party winner
                    if(p.winner==='Democratic') fillColor = p.dem_share>=70?'#0d47a1':'#1976d2';
                    else if(p.winner==='Republican') fillColor = p.rep_share>=70?'#b71c1c':'#e53935';
                    else fillColor='#9c27b0';
                }
                return {fillColor, fillOpacity:0.55, color:'#222', weight:1.5};
            },
            onEachFeature: (feature, layer) => {
                const pct = feature.properties.db_precinct;
                const p = pctLookup[pct];
                if(!p) return;

                let html = `<div style="font-family:sans-serif;min-width:260px">`;
                html += `<div style="font-weight:700;font-size:15px;margin-bottom:6px;">Precinct ${p.precinct}</div>`;
                html += `<table style="width:100%;border-collapse:collapse;font-size:13px;">`;
                html += `<tr style="border-bottom:1px solid #eee"><td style="padding:4px">🔵 Democratic</td><td style="padding:4px;font-weight:700;text-align:right">${p.dem_votes}</td><td style="padding:4px;text-align:right;color:#666">${p.dem_share}%</td></tr>`;
                html += `<tr style="border-bottom:1px solid #eee"><td style="padding:4px">🔴 Republican</td><td style="padding:4px;font-weight:700;text-align:right">${p.rep_votes}</td><td style="padding:4px;text-align:right;color:#666">${p.rep_share}%</td></tr>`;
                html += `<tr style="border-top:2px solid #333"><td style="padding:4px;font-weight:700">Total</td><td style="padding:4px;font-weight:700;text-align:right">${p.total_votes}</td><td></td></tr>`;
                html += `</table>`;
                html += `<div style="margin-top:8px;padding:6px;border-radius:4px;background:${p.winner==='Democratic'?'#e3f2fd':'#fce4ec'}">`;
                html += `<b>Winner:</b> ${p.winner} by ${p.margin_votes} votes (${p.margin_pct}% margin)`;
                html += `</div>`;
                html += `<div style="font-size:11px;color:#666;margin-top:6px;">Registered: ${p.registered.toLocaleString()} · Turnout: ${p.turnout_pct}%</div>`;
                if(p.runoff_total>0) {
                    html += `<div style="font-size:11px;color:#333;margin-top:4px;font-weight:600;">Runoff: 🔵${p.runoff_dem} 🔴${p.runoff_rep}</div>`;
                }
                html += `</div>`;
                layer.bindPopup(html, {maxWidth:300});
            }
        }).addTo(map);
    }

    // Update info strip
    const strip = document.querySelector('.info-strip');
    if(strip) {
        if(currentView==='planner') {
            strip.innerHTML = `<b>Priority Planner</b> · <span style="color:#9c27b0">■ Battleground</span> <span style="color:#0d47a1">■ Dem Stronghold</span> <span style="color:#42a5f5">■ Lean Dem</span> <span style="color:#b71c1c">■ Rep Stronghold</span> <span style="color:#ef5350">■ Lean Rep</span> <span style="color:#bbb">■ Low Volume</span>`;
        } else {
            strip.innerHTML = `HD-41 March Primary · ${precinctData.summary.total_votes.toLocaleString()} votes · 🔵 ${precinctData.summary.total_dem_votes.toLocaleString()} D · 🔴 ${precinctData.summary.total_rep_votes.toLocaleString()} R · Real data from voter rolls`;
        }
    }
}

// ── Report Card ──
function toggleReportCard() {
    const panel = document.getElementById('reportcard-panel');
    panel.classList.toggle('visible');
    if(!panel.classList.contains('visible')) return;
    renderReportCard();
}

function renderReportCard() {
    const summary = document.getElementById('reportcard-summary');
    const list = document.getElementById('reportcard-list');
    const s = precinctData.summary;

    summary.innerHTML = `<div style="font-size:16px;font-weight:700;">HD-41 — ${s.total_votes.toLocaleString()} votes</div><div style="font-size:12px;color:#666;margin-top:4px;">🔵 D: ${s.total_dem_votes.toLocaleString()} · 🔴 R: ${s.total_rep_votes.toLocaleString()} · ${s.total_precincts} precincts</div>`;

    // Sort by total votes (biggest precincts first)
    const sorted = [...precinctData.precincts].sort((a,b)=>b.total_votes-a.total_votes);

    list.innerHTML = sorted.map(p => {
        const barW = Math.min(100, p.dem_share);
        const winColor = p.winner==='Democratic'?'#1565c0':'#c62828';
        return `<div class="rc-row">
            <div class="rc-grade" style="background:${winColor};font-size:11px;width:36px;height:36px;">${p.winner==='Democratic'?'D':'R'}</div>
            <div class="rc-info">
                <div class="rc-pct">Pct ${p.precinct}</div>
                <div class="rc-detail">🔵${p.dem_votes} (${p.dem_share}%) · 🔴${p.rep_votes} (${p.rep_share}%) · Margin: ${p.margin_votes} · Reg: ${p.registered}</div>
            </div>
            <div style="width:60px;text-align:right;">
                <div style="font-weight:700;font-size:13px;">${p.total_votes}</div>
                <div style="height:4px;background:#eee;border-radius:2px;margin-top:2px;"><div style="height:4px;background:#1565c0;border-radius:2px;width:${barW}%"></div></div>
            </div>
        </div>`;
    }).join('');
}

// ── Gazette ──
async function toggleGazette() {
    const panel = document.getElementById('gazette-panel');
    panel.classList.toggle('visible');
    if(!panel.classList.contains('visible')) return;
    try {
        const resp = await fetch('/cache/hd41_gazette.json');
        const data = await resp.json();
        let html = `<div class="gazette-masthead"><h1>Politiquera Gazette</h1><div class="gazette-date">${data.date} · HD-41 Edition</div></div>`;
        html += `<div class="gazette-headline"><h2>${data.headline}</h2><div class="sub">${data.subhead}</div></div>`;
        if(data.bullets&&data.bullets.length) { html+=`<ul class="gazette-bullets">`; for(const b of data.bullets) html+=`<li>${b}</li>`; html+=`</ul>`; }
        for(const s of (data.stories||[])) html+=`<div class="gazette-story"><h3>${s.icon||''} ${s.title}</h3><p>${s.text}</p></div>`;
        html+=`<div class="gazette-footer">Politiquera.com · Not affiliated with any candidate · All data from voter rolls</div>`;
        document.getElementById('gazette-content').innerHTML=html;
    } catch(e) { document.getElementById('gazette-content').innerHTML='<p style="padding:20px;color:#c62828;">Failed to load.</p>'; }
}

document.addEventListener('DOMContentLoaded', initMap);

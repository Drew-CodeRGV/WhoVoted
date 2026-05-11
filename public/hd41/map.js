// HD-41 Runoff Election Tracker — Official Canvass Data
// All data from Hidalgo County Official Canvass (precinct-by-precinct)

let map, boundaryLayer, precinctLayer;
let precinctData = null, plannerData = null, shapesData = null, candidateData = null;
let currentMode = 'combined'; // 'dem', 'rep', 'combined', 'live'
let selectedCandidate = null;

function showLoading() {
    const d = document.createElement('div'); d.id = 'loading-screen';
    d.innerHTML = `<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(255,255,255,0.95);z-index:10000;display:flex;align-items:center;justify-content:center;"><div style="text-align:center"><div style="font-size:20px;font-weight:600;color:#333;">Loading HD-41</div><div style="font-size:13px;color:#666;margin-top:6px;">Official canvass data...</div></div></div>`;
    document.body.appendChild(d);
}
function hideLoading() { const e = document.getElementById('loading-screen'); if (e) e.remove(); }

function initMap() {
    map = L.map('map').setView([26.245, -98.23], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap', maxZoom: 18 }).addTo(map);
    loadData();
}

async function loadData() {
    showLoading();
    try {
        const [resResp, shpResp, planResp, bndResp, candResp] = await Promise.all([
            fetch('/cache/hd41_precinct_results.json'),
            fetch('/cache/hd41_precinct_shapes.json'),
            fetch('/cache/hd41_planner.json'),
            fetch('/cache/hd41_boundary.json'),
            fetch('/cache/hd41_primary_candidates.json'),
        ]);
        precinctData = await resResp.json();
        shapesData = await shpResp.json();
        plannerData = await planResp.json();
        const bndGeoJSON = await bndResp.json();
        candidateData = await candResp.json();

        boundaryLayer = L.geoJSON(bndGeoJSON, { style: { color: '#1a237e', weight: 3, fillOpacity: 0.02, dashArray: '8,4' } }).addTo(map);
        map.fitBounds(boundaryLayer.getBounds(), { padding: [20, 20] });

        // Stats
        const s = precinctData.summary;
        document.getElementById('total-voters').textContent = s.total_votes.toLocaleString();

        // Populate candidate dropdown
        populateCandidates();
        setupListeners();
        renderMap();
        hideLoading();
    } catch (e) { hideLoading(); console.error(e); }
}

function populateCandidates() {
    const selectors = [document.getElementById('candidate-select'), document.getElementById('candidate-select-mobile')];
    for (const sel of selectors) {
        if (!sel) continue;
        sel.innerHTML = '<option value="">All Precincts</option>';
        if (!candidateData) continue;
        if (currentMode === 'dem' || currentMode === 'combined') {
            const grp = document.createElement('optgroup');
            grp.label = '🔵 Democratic';
            for (const c of (candidateData.dem_candidates || [])) {
                const d = candidateData.candidates[c];
                if (d) { const o = document.createElement('option'); o.value = c; o.textContent = `${c.replace("Victor 'Seby' ","Seby ")} (${d.district_share}%)`; grp.appendChild(o); }
            }
            sel.appendChild(grp);
        }
        if (currentMode === 'rep' || currentMode === 'combined') {
            const grp = document.createElement('optgroup');
            grp.label = '🔴 Republican';
            for (const c of (candidateData.rep_candidates || [])) {
                const d = candidateData.candidates[c];
                if (d) { const o = document.createElement('option'); o.value = c; o.textContent = `${c} (${d.district_share}%)`; grp.appendChild(o); }
            }
            sel.appendChild(grp);
        }
    }
}

function setupListeners() {
    document.getElementById('candidate-select').addEventListener('change', e => { selectedCandidate = e.target.value || null; renderMap(); });
    document.getElementById('boundary-toggle').addEventListener('change', e => {
        if (e.target.checked && boundaryLayer) boundaryLayer.addTo(map);
        else if (boundaryLayer && map.hasLayer(boundaryLayer)) map.removeLayer(boundaryLayer);
    });
    document.getElementById('location-btn').addEventListener('click', () => {
        if (navigator.geolocation) navigator.geolocation.getCurrentPosition(p => map.setView([p.coords.latitude, p.coords.longitude], 14));
    });
    // Mode switch (both desktop and mobile)
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            // Activate all buttons with same mode (desktop + mobile)
            document.querySelectorAll(`.mode-btn[data-mode="${btn.dataset.mode}"]`).forEach(b => b.classList.add('active'));
            currentMode = btn.dataset.mode;
            selectedCandidate = null;
            document.getElementById('candidate-select').value = '';
            const mSel = document.getElementById('candidate-select-mobile');
            if (mSel) mSel.value = '';
            populateCandidates();
            renderMap();
        });
    });
    // Report card
    document.getElementById('reportcard-btn').addEventListener('click', toggleReportCard);
    document.getElementById('reportcard-close').addEventListener('click', () => document.getElementById('reportcard-panel').classList.remove('visible'));

    // Mobile menu
    const mobileBtn = document.getElementById('mobile-menu-btn');
    const mobileDrawer = document.getElementById('mobile-drawer');
    if (mobileBtn && mobileDrawer) {
        mobileBtn.addEventListener('click', () => mobileDrawer.classList.toggle('visible'));
        // Close drawer when clicking outside
        document.addEventListener('click', e => {
            if (!mobileDrawer.contains(e.target) && e.target !== mobileBtn) mobileDrawer.classList.remove('visible');
        });
    }
    // Mobile candidate select
    const mSel = document.getElementById('candidate-select-mobile');
    if (mSel) {
        mSel.addEventListener('change', e => {
            selectedCandidate = e.target.value || null;
            document.getElementById('candidate-select').value = selectedCandidate || '';
            renderMap();
            mobileDrawer.classList.remove('visible');
        });
    }
    // Mobile boundary toggle
    const mBound = document.getElementById('boundary-toggle-mobile');
    if (mBound) {
        mBound.addEventListener('change', e => {
            document.getElementById('boundary-toggle').checked = e.target.checked;
            if (e.target.checked && boundaryLayer) boundaryLayer.addTo(map);
            else if (boundaryLayer && map.hasLayer(boundaryLayer)) map.removeLayer(boundaryLayer);
        });
    }
    // Mobile report card button
    const mRC = document.getElementById('reportcard-btn-mobile');
    if (mRC) {
        mRC.addEventListener('click', () => { mobileDrawer.classList.remove('visible'); toggleReportCard(); });
    }
}

function renderMap() {
    if (precinctLayer) { map.removeLayer(precinctLayer); precinctLayer = null; }

    const pctLookup = {};
    for (const p of precinctData.precincts) pctLookup[p.precinct] = p;

    precinctLayer = L.geoJSON(shapesData, {
        style: feature => getStyle(feature, pctLookup),
        onEachFeature: (feature, layer) => {
            const pct = feature.properties.db_precinct;
            const p = pctLookup[pct];
            if (!p) return;
            layer.bindPopup(() => buildPopup(p), { maxWidth: 360 });
        }
    }).addTo(map);

    updateInfoStrip();
}

function getStyle(feature, pctLookup) {
    const pct = feature.properties.db_precinct;
    const p = pctLookup[pct];
    if (!p) return { fillColor: '#ccc', fillOpacity: 0.1, color: '#999', weight: 1 };

    let fillColor, fillOpacity = 0.6;

    if (currentMode === 'live') {
        // LIVE RUNOFF MODE: opacity = vote volume, color = party leading
        const runoffTotal = (p.runoff_dem || 0) + (p.runoff_rep || 0);
        if (runoffTotal === 0) {
            // No votes yet — transparent with light outline
            return { fillColor: '#ffffff', fillOpacity: 0.05, color: '#aaa', weight: 1, dashArray: '4,4' };
        }
        // Opacity scales with turnout (more votes = more opaque)
        // Max opacity at ~200 votes, min at 1 vote
        fillOpacity = Math.min(0.8, Math.max(0.1, runoffTotal / 200));
        // Color by which party is leading
        if (p.runoff_dem > p.runoff_rep) {
            const dominance = p.runoff_dem / runoffTotal;
            fillColor = dominance >= 0.7 ? '#0d47a1' : '#1976d2'; // dark blue vs medium blue
        } else if (p.runoff_rep > p.runoff_dem) {
            const dominance = p.runoff_rep / runoffTotal;
            fillColor = dominance >= 0.7 ? '#b71c1c' : '#e53935'; // dark red vs medium red
        } else {
            fillColor = '#7b1fa2'; // tied = purple
        }
        return { fillColor, fillOpacity, color: '#333', weight: 1.5 };
    }

    if (selectedCandidate && candidateData) {
        // Candidate view — 4-color gradient
        const cand = candidateData.candidates[selectedCandidate];
        if (cand) {
            const pctData = cand.precincts.find(x => x.precinct === pct);
            if (pctData) {
                const share = pctData.share;
                if (share >= 50) fillColor = '#1b5e20'; // Won decisively (dark green)
                else if (share >= 38) fillColor = '#66bb6a'; // Competitive/close (light green)
                else if (share >= 25) fillColor = '#ffb74d'; // Lost but close (orange)
                else fillColor = '#c62828'; // Lost badly (red)
            } else {
                fillColor = '#eee';
            }
        } else { fillColor = '#eee'; }
    } else if (currentMode === 'combined') {
        // Combined: blue for Dem, red for Rep, purple/maroon for close
        const demShare = p.dem_share;
        if (demShare >= 80) fillColor = '#0d47a1'; // Strong Dem (dark blue)
        else if (demShare >= 65) fillColor = '#7b1fa2'; // Lean Dem (purple)
        else if (demShare >= 50) fillColor = '#7b1fa2'; // Slight Dem (purple)
        else if (demShare >= 35) fillColor = '#880e4f'; // Slight Rep (maroon)
        else fillColor = '#b71c1c'; // Strong Rep (dark red)
    } else if (currentMode === 'dem') {
        // Dem primary: who won the Dem race in this precinct?
        const demWinner = p.dem_winner;
        if (demWinner && demWinner.includes('Haddad')) fillColor = '#1565c0';
        else if (demWinner && demWinner.includes('Salinas')) fillColor = '#2e7d32';
        else if (demWinner && demWinner.includes('Holgu')) fillColor = '#f57f17';
        else fillColor = '#666';
    } else if (currentMode === 'rep') {
        // Rep primary: who won the Rep race?
        const repWinner = p.rep_winner;
        if (repWinner && repWinner.includes('Sanchez')) fillColor = '#c62828';
        else if (repWinner && repWinner.includes('Groves')) fillColor = '#e65100';
        else if (repWinner && repWinner.includes('Sagredo')) fillColor = '#f9a825';
        else fillColor = '#666';
    }

    return { fillColor, fillOpacity, color: '#222', weight: 1.5 };
}

function buildPopup(p) {
    let html = `<div style="font-family:-apple-system,sans-serif;min-width:300px;max-width:360px">`;
    html += `<div style="font-weight:700;font-size:15px;margin-bottom:8px;border-bottom:2px solid #333;padding-bottom:4px;">Precinct ${p.precinct}</div>`;

    // Live runoff data (show if any runoff votes exist)
    if (currentMode === 'live') {
        const rd = (p.runoff_dem || 0), rr = (p.runoff_rep || 0), rt = rd + rr;
        if (rt === 0) {
            html += `<div style="padding:12px;text-align:center;color:#999;font-size:13px;">No runoff votes yet</div>`;
        } else {
            const leader = rd > rr ? 'Democratic' : rd < rr ? 'Republican' : 'Tied';
            const leaderColor = rd > rr ? '#1565c0' : '#c62828';
            html += `<div style="padding:8px;border-radius:6px;background:${rd > rr ? '#e3f2fd' : '#fce4ec'};margin-bottom:8px;">`;
            html += `<div style="font-weight:700;font-size:14px;color:${leaderColor};">${leader} leading</div>`;
            html += `<div style="font-size:12px;margin-top:4px;">🔵 Dem: ${rd} · 🔴 Rep: ${rr} · Total: ${rt}</div>`;
            html += `</div>`;
            // Bar
            const demPct = Math.round(rd / rt * 100);
            html += `<div style="height:12px;border-radius:6px;overflow:hidden;display:flex;margin-bottom:8px;">`;
            html += `<div style="width:${demPct}%;background:#1565c0;"></div>`;
            html += `<div style="width:${100 - demPct}%;background:#c62828;"></div>`;
            html += `</div>`;
        }
        // Also show March primary for context
        html += `<div style="font-size:11px;color:#666;border-top:1px solid #eee;padding-top:6px;margin-top:6px;">March primary: 🔵${p.dem_votes} 🔴${p.rep_votes} (${p.total_votes} total)</div>`;
        html += `</div>`;
        return html;
    }

    if (selectedCandidate && candidateData) {
        // Candidate-specific view with full competitive breakdown
        const cand = candidateData.candidates[selectedCandidate];
        if (cand) {
            const pctData = cand.precincts.find(x => x.precinct === p.precinct);
            const party = cand.party;
            const partyKey = party === 'Democratic' ? 'dem_candidates' : 'rep_candidates';
            const partyVotes = party === 'Democratic' ? p.dem_votes : p.rep_votes;
            const opponents = p[partyKey] || {};

            if (pctData) {
                const won = pctData.beaten_by.length === 0;
                const share = pctData.share;

                // Header: candidate result
                html += `<div style="padding:8px;border-radius:6px;background:${won ? '#e8f5e9' : share >= 38 ? '#fff3e0' : '#fce4ec'};margin-bottom:10px;">`;
                html += `<div style="font-weight:700;font-size:14px;">${selectedCandidate}: ${pctData.votes} votes (${share}%)</div>`;
                html += `<div style="font-size:12px;color:#555;margin-top:2px;">${won ? '✓ WON this precinct' : share >= 38 ? '⚠️ CLOSE — winnable' : '✗ LOST — needs work'}</div>`;
                html += `</div>`;

                // All candidates in this party, ranked
                const sorted = Object.entries(opponents).sort((a, b) => b[1] - a[1]);
                html += `<div style="font-size:12px;font-weight:700;margin-bottom:4px;">${party} breakdown (${partyVotes} total ballots):</div>`;
                html += `<table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:8px;">`;
                for (const [c, v] of sorted) {
                    const pct = partyVotes > 0 ? (v / partyVotes * 100).toFixed(1) : 0;
                    const isMe = c === selectedCandidate;
                    const isWinner = sorted[0][0] === c;
                    const barWidth = partyVotes > 0 ? Math.round(v / sorted[0][1] * 100) : 0;
                    const barColor = isMe ? '#1565c0' : '#ddd';
                    html += `<tr style="${isMe ? 'background:#e3f2fd;font-weight:700;' : ''}">`;
                    html += `<td style="padding:3px 4px;white-space:nowrap;">${isWinner ? '👑' : ''} ${c.replace("Victor 'Seby' ", "Seby ")}</td>`;
                    html += `<td style="padding:3px 4px;text-align:right;font-weight:700;">${v}</td>`;
                    html += `<td style="padding:3px 4px;text-align:right;color:#666;">${pct}%</td>`;
                    html += `<td style="padding:3px 4px;width:60px;"><div style="height:8px;background:#eee;border-radius:4px;"><div style="height:8px;background:${barColor};border-radius:4px;width:${barWidth}%"></div></div></td>`;
                    html += `</tr>`;
                }
                html += `</table>`;

                // Gap analysis
                if (!won && sorted.length > 0) {
                    const winnerVotes = sorted[0][1];
                    const myVotes = pctData.votes;
                    const gap = winnerVotes - myVotes;
                    html += `<div style="padding:6px;background:#fff8e1;border-radius:4px;font-size:11px;border:1px solid #ffe082;">`;
                    html += `<b>Gap to win:</b> Need ${gap} more votes to overtake ${sorted[0][0].replace("Victor 'Seby' ", "Seby ")}`;
                    html += `</div>`;
                }
            }
        }
    } else {
        // Side-by-side comparison (combined/dem/rep mode)
        html += `<div style="display:flex;gap:12px;">`;
        // Dem column
        html += `<div style="flex:1;"><div style="font-weight:700;color:#1565c0;font-size:12px;margin-bottom:4px;border-bottom:2px solid #1565c0;padding-bottom:2px;">🔵 DEM (${p.dem_votes})</div>`;
        if (p.dem_candidates) {
            const sorted = Object.entries(p.dem_candidates).sort((a, b) => b[1] - a[1]);
            for (const [c, v] of sorted) {
                const pct = p.dem_votes > 0 ? Math.round(v / p.dem_votes * 100) : 0;
                const isWinner = sorted[0][0] === c;
                html += `<div style="font-size:11px;padding:2px 0;${isWinner ? 'font-weight:700;' : ''}">${isWinner ? '👑 ' : ''}${c.replace("Victor 'Seby' ", "Seby ")}: ${v} (${pct}%)</div>`;
            }
        }
        html += `</div>`;
        // Rep column
        html += `<div style="flex:1;"><div style="font-weight:700;color:#c62828;font-size:12px;margin-bottom:4px;border-bottom:2px solid #c62828;padding-bottom:2px;">🔴 GOP (${p.rep_votes})</div>`;
        if (p.rep_candidates) {
            const sorted = Object.entries(p.rep_candidates).sort((a, b) => b[1] - a[1]);
            for (const [c, v] of sorted) {
                const pct = p.rep_votes > 0 ? Math.round(v / p.rep_votes * 100) : 0;
                const isWinner = sorted[0][0] === c;
                html += `<div style="font-size:11px;padding:2px 0;${isWinner ? 'font-weight:700;' : ''}">${isWinner ? '👑 ' : ''}${c}: ${v} (${pct}%)</div>`;
            }
        }
        html += `</div></div>`;
        // Summary bar
        html += `<div style="margin-top:8px;padding:6px;background:#f5f5f5;border-radius:4px;font-size:11px;">`;
        html += `<b>Total:</b> ${p.total_votes} · <b>Party winner:</b> ${p.winner} +${p.margin_votes} (${p.margin_pct}%) · <b>Reg:</b> ${p.registered.toLocaleString()} · <b>Turnout:</b> ${p.turnout_pct}%`;
        html += `</div>`;
    }
    html += `</div>`;
    return html;
}

function updateInfoStrip() {
    const strip = document.querySelector('.info-strip');
    if (!strip) return;
    if (selectedCandidate) {
        const cand = candidateData.candidates[selectedCandidate];
        if (cand) strip.innerHTML = `<b>${selectedCandidate}</b> (${cand.party}) · ${cand.total_votes} votes (${cand.district_share}%) · <span style="color:#1b5e20">■ Won (>50%)</span> <span style="color:#66bb6a">■ Close (38-50%)</span> <span style="color:#ffb74d">■ Lost close (25-38%)</span> <span style="color:#c62828">■ Lost badly (<25%)</span>`;
    } else if (currentMode === 'live') {
        const totalRunoff = precinctData.precincts.reduce((s, p) => s + (p.runoff_dem || 0) + (p.runoff_rep || 0), 0);
        const demRunoff = precinctData.precincts.reduce((s, p) => s + (p.runoff_dem || 0), 0);
        const repRunoff = precinctData.precincts.reduce((s, p) => s + (p.runoff_rep || 0), 0);
        strip.innerHTML = `<b>🔴 LIVE RUNOFF</b> · ${totalRunoff} votes so far (🔵${demRunoff} 🔴${repRunoff}) · Opacity = turnout volume · Color = party leading · Clear = no votes yet`;
    } else if (currentMode === 'combined') {
        strip.innerHTML = `Combined view · <span style="color:#0d47a1">■ Strong D</span> <span style="color:#7b1fa2">■ Lean D</span> <span style="color:#880e4f">■ Lean R</span> <span style="color:#b71c1c">■ Strong R</span> · Click precinct for side-by-side candidate breakdown`;
    } else if (currentMode === 'dem') {
        strip.innerHTML = `Democratic Primary · <span style="color:#1565c0">■ Haddad won</span> <span style="color:#2e7d32">■ Salinas won</span> <span style="color:#f57f17">■ Holguín won</span>`;
    } else {
        strip.innerHTML = `Republican Primary · <span style="color:#c62828">■ Sanchez won</span> <span style="color:#e65100">■ Groves won</span> <span style="color:#f9a825">■ Sagredo-Hammond won</span>`;
    }
}

// ── Report Card ──
function toggleReportCard() {
    const panel = document.getElementById('reportcard-panel');
    panel.classList.toggle('visible');
    if (!panel.classList.contains('visible')) return;
    const summary = document.getElementById('reportcard-summary');
    const list = document.getElementById('reportcard-list');
    const s = precinctData.summary;

    summary.innerHTML = `<div style="font-size:16px;font-weight:700;">HD-41 Official Canvass — ${s.total_votes.toLocaleString()} votes</div><div style="font-size:12px;color:#666;margin-top:4px;">🔵 D: ${s.total_dem_votes.toLocaleString()} · 🔴 R: ${s.total_rep_votes.toLocaleString()} · ${s.total_precincts} precincts · Source: Hidalgo County</div>`;

    const sorted = [...precinctData.precincts].sort((a, b) => b.total_votes - a.total_votes);
    list.innerHTML = sorted.map(p => {
        const winColor = p.winner === 'Democratic' ? '#1565c0' : '#c62828';
        // Dem winner in this precinct
        let demLine = '', repLine = '';
        if (p.dem_candidates) {
            const ds = Object.entries(p.dem_candidates).sort((a,b) => b[1]-a[1]);
            demLine = ds.map(([c,v]) => `${c.replace("Victor 'Seby' ","Seby ").split(' ')[0]}:${v}`).join(' ');
        }
        if (p.rep_candidates) {
            const rs = Object.entries(p.rep_candidates).sort((a,b) => b[1]-a[1]);
            repLine = rs.map(([c,v]) => `${c.split(' ')[0]}:${v}`).join(' ');
        }
        return `<div class="rc-row" style="cursor:pointer;" onclick="map.eachLayer(l=>{if(l.feature&&l.feature.properties&&l.feature.properties.db_precinct==='${p.precinct}'){l.openPopup();}});">
            <div class="rc-grade" style="background:${winColor};font-size:11px;width:36px;height:36px;">${p.winner==='Democratic'?'D':'R'}</div>
            <div class="rc-info">
                <div class="rc-pct" style="font-size:13px;">Pct ${p.precinct} <span style="font-size:10px;color:#888;">(+${p.margin_votes} ${p.winner.charAt(0)})</span></div>
                <div class="rc-detail" style="font-size:10px;">🔵 ${demLine}</div>
                <div class="rc-detail" style="font-size:10px;">🔴 ${repLine}</div>
            </div>
            <div style="width:50px;text-align:right;">
                <div style="font-weight:700;font-size:13px;">${p.total_votes}</div>
                <div style="font-size:9px;color:#666;">${p.turnout_pct}%</div>
            </div>
        </div>`;
    }).join('');
}

document.addEventListener('DOMContentLoaded', initMap);

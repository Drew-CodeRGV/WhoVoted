// HD-41 Runoff Election Tracker — Official Canvass Data
// All data from Hidalgo County Official Canvass (precinct-by-precinct)

let map, boundaryLayer, precinctLayer;
let precinctData = null, plannerData = null, shapesData = null, candidateData = null;
let currentMode = 'combined'; // 'dem', 'rep', 'combined', 'live', 'avail-dem', 'avail-rep', 'swing-dem', 'swing-rep', 'mopup-seby', 'mopup-julio', 'mopup-sergio', 'mopup-gary'
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

    // Mop-up dropdown (desktop)
    const mopupSel = document.getElementById('mopup-select');
    if (mopupSel) {
        mopupSel.addEventListener('change', e => {
            if (e.target.value) {
                document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                currentMode = e.target.value;
                selectedCandidate = null;
                document.getElementById('candidate-select').value = '';
                renderMap();
            } else {
                // Reset to combined
                currentMode = 'combined';
                document.querySelectorAll('.mode-btn[data-mode="combined"]').forEach(b => b.classList.add('active'));
                renderMap();
            }
        });
    }
    // Mop-up dropdown (mobile)
    const mopupSelM = document.getElementById('mopup-select-mobile');
    if (mopupSelM) {
        mopupSelM.addEventListener('change', e => {
            if (e.target.value) {
                document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                currentMode = e.target.value;
                selectedCandidate = null;
                renderMap();
                if (mobileDrawer) mobileDrawer.classList.remove('visible');
            }
            // Sync desktop
            if (mopupSel) mopupSel.value = e.target.value;
        });
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

    if (currentMode === 'avail-dem') {
        // Available Dem votes: total Dem primary voters minus those who already voted in runoff
        const available = p.dem_votes - (p.runoff_dem || 0);
        if (available <= 0) return { fillColor: '#e8f5e9', fillOpacity: 0.3, color: '#666', weight: 1 };
        // Gradient: light blue (few) to dark blue (many)
        const maxAvail = 400; // normalize against
        const intensity = Math.min(1, available / maxAvail);
        fillOpacity = 0.2 + intensity * 0.6;
        fillColor = intensity >= 0.6 ? '#0d47a1' : intensity >= 0.3 ? '#1976d2' : '#64b5f6';
        return { fillColor, fillOpacity, color: '#333', weight: 1.5 };
    }

    if (currentMode === 'avail-rep') {
        // Available Rep votes: total Rep primary voters minus those who already voted in runoff
        const available = p.rep_votes - (p.runoff_rep || 0);
        if (available <= 0) return { fillColor: '#fce4ec', fillOpacity: 0.3, color: '#666', weight: 1 };
        const maxAvail = 200;
        const intensity = Math.min(1, available / maxAvail);
        fillOpacity = 0.2 + intensity * 0.6;
        fillColor = intensity >= 0.6 ? '#b71c1c' : intensity >= 0.3 ? '#e53935' : '#ef9a9a';
        return { fillColor, fillOpacity, color: '#333', weight: 1.5 };
    }

    if (currentMode === 'swing-dem') {
        // Eric Holguín's voters — the swing votes in the Dem runoff
        const ericVotes = (p.dem_candidates && p.dem_candidates["Eric Holguín"]) || 0;
        if (ericVotes === 0) return { fillColor: '#f5f5f5', fillOpacity: 0.15, color: '#aaa', weight: 1 };
        const maxSwing = 200;
        const intensity = Math.min(1, ericVotes / maxSwing);
        fillOpacity = 0.25 + intensity * 0.6;
        // Hot gradient: yellow (few) → orange → deep orange (many)
        if (intensity >= 0.6) fillColor = '#e65100';
        else if (intensity >= 0.3) fillColor = '#ff9800';
        else fillColor = '#ffcc02';
        return { fillColor, fillOpacity, color: '#333', weight: 1.5 };
    }

    if (currentMode === 'swing-rep') {
        // Sarah Sagredo-Hammond's voters — the swing votes in the Rep runoff
        const sarahVotes = (p.rep_candidates && p.rep_candidates["Sarah Sagredo-Hammond"]) || 0;
        if (sarahVotes === 0) return { fillColor: '#f5f5f5', fillOpacity: 0.15, color: '#aaa', weight: 1 };
        const maxSwing = 80;
        const intensity = Math.min(1, sarahVotes / maxSwing);
        fillOpacity = 0.25 + intensity * 0.6;
        if (intensity >= 0.6) fillColor = '#e65100';
        else if (intensity >= 0.3) fillColor = '#ff9800';
        else fillColor = '#ffcc02';
        return { fillColor, fillOpacity, color: '#333', weight: 1.5 };
    }

    if (currentMode === 'mopup-seby') {
        // Seby's mop-up map: precincts where Seby WON + Eric had voters to absorb
        const sebyVotes = (p.dem_candidates && p.dem_candidates["Victor 'Seby' Haddad"]) || 0;
        const julioVotes = (p.dem_candidates && p.dem_candidates["Julio Salinas"]) || 0;
        const ericVotes = (p.dem_candidates && p.dem_candidates["Eric Holguín"]) || 0;
        const sebyWon = sebyVotes > julioVotes;

        if (!sebyWon || ericVotes === 0) {
            // Not Seby's turf or no Eric voters — gray it out
            return { fillColor: sebyWon ? '#e8f5e9' : '#f5f5f5', fillOpacity: 0.1, color: '#aaa', weight: 1 };
        }
        // Seby won AND Eric had voters here — this is mop-up territory
        // Intensity = Eric's votes (more = bigger opportunity)
        const maxMopup = 150;
        const intensity = Math.min(1, ericVotes / maxMopup);
        fillOpacity = 0.3 + intensity * 0.55;
        if (intensity >= 0.6) fillColor = '#1b5e20'; // Deep green — high impact
        else if (intensity >= 0.3) fillColor = '#43a047'; // Medium green
        else fillColor = '#81c784'; // Light green
        return { fillColor, fillOpacity, color: '#1b5e20', weight: 2 };
    }

    if (currentMode === 'mopup-sergio') {
        // Sergio's mop-up map: precincts where Sergio WON + Sarah had voters
        const sergioVotes = (p.rep_candidates && p.rep_candidates["Sergio Sanchez"]) || 0;
        const garyVotes = (p.rep_candidates && p.rep_candidates["Gary Groves"]) || 0;
        const sarahVotes = (p.rep_candidates && p.rep_candidates["Sarah Sagredo-Hammond"]) || 0;
        const sergioWon = sergioVotes > garyVotes;

        if (!sergioWon || sarahVotes === 0) {
            return { fillColor: sergioWon ? '#fce4ec' : '#f5f5f5', fillOpacity: 0.1, color: '#aaa', weight: 1 };
        }
        const maxMopup = 50;
        const intensity = Math.min(1, sarahVotes / maxMopup);
        fillOpacity = 0.3 + intensity * 0.55;
        if (intensity >= 0.6) fillColor = '#b71c1c';
        else if (intensity >= 0.3) fillColor = '#e53935';
        else fillColor = '#ef9a9a';
        return { fillColor, fillOpacity, color: '#b71c1c', weight: 2 };
    }

    if (currentMode === 'mopup-julio') {
        // Julio's mop-up: precincts where Julio WON + Eric had voters
        const julioVotes = (p.dem_candidates && p.dem_candidates["Julio Salinas"]) || 0;
        const sebyVotes = (p.dem_candidates && p.dem_candidates["Victor 'Seby' Haddad"]) || 0;
        const ericVotes = (p.dem_candidates && p.dem_candidates["Eric Holguín"]) || 0;
        const julioWon = julioVotes > sebyVotes;

        if (!julioWon || ericVotes === 0) {
            return { fillColor: julioWon ? '#e8f5e9' : '#f5f5f5', fillOpacity: 0.1, color: '#aaa', weight: 1 };
        }
        const maxMopup = 150;
        const intensity = Math.min(1, ericVotes / maxMopup);
        fillOpacity = 0.3 + intensity * 0.55;
        if (intensity >= 0.6) fillColor = '#1b5e20';
        else if (intensity >= 0.3) fillColor = '#43a047';
        else fillColor = '#81c784';
        return { fillColor, fillOpacity, color: '#1b5e20', weight: 2 };
    }

    if (currentMode === 'mopup-gary') {
        // Gary's mop-up: precincts where Gary WON + Sarah had voters
        const garyVotes = (p.rep_candidates && p.rep_candidates["Gary Groves"]) || 0;
        const sergioVotes = (p.rep_candidates && p.rep_candidates["Sergio Sanchez"]) || 0;
        const sarahVotes = (p.rep_candidates && p.rep_candidates["Sarah Sagredo-Hammond"]) || 0;
        const garyWon = garyVotes > sergioVotes;

        if (!garyWon || sarahVotes === 0) {
            return { fillColor: garyWon ? '#fce4ec' : '#f5f5f5', fillOpacity: 0.1, color: '#aaa', weight: 1 };
        }
        const maxMopup = 50;
        const intensity = Math.min(1, sarahVotes / maxMopup);
        fillOpacity = 0.3 + intensity * 0.55;
        if (intensity >= 0.6) fillColor = '#e65100';
        else if (intensity >= 0.3) fillColor = '#ff9800';
        else fillColor = '#ffcc80';
        return { fillColor, fillOpacity, color: '#e65100', weight: 2 };
    }

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

    // Mop-up mode (stronghold + available swing voters)
    if (currentMode.startsWith('mopup-')) {
        const configs = {
            'mopup-seby': { myName: "Victor 'Seby' Haddad", oppName: "Julio Salinas", elimName: "Eric Holguín", short: 'Seby', oppShort: 'Julio', elimShort: 'Eric', partyKey: 'dem_candidates' },
            'mopup-julio': { myName: "Julio Salinas", oppName: "Victor 'Seby' Haddad", elimName: "Eric Holguín", short: 'Julio', oppShort: 'Seby', elimShort: 'Eric', partyKey: 'dem_candidates' },
            'mopup-sergio': { myName: "Sergio Sanchez", oppName: "Gary Groves", elimName: "Sarah Sagredo-Hammond", short: 'Sergio', oppShort: 'Gary', elimShort: 'Sarah', partyKey: 'rep_candidates' },
            'mopup-gary': { myName: "Gary Groves", oppName: "Sergio Sanchez", elimName: "Sarah Sagredo-Hammond", short: 'Gary', oppShort: 'Sergio', elimShort: 'Sarah', partyKey: 'rep_candidates' },
        };
        const cfg = configs[currentMode];
        if (cfg) {
            const candidates = p[cfg.partyKey] || {};
            const myVotes = candidates[cfg.myName] || 0;
            const oppVotes = candidates[cfg.oppName] || 0;
            const swingVotes = candidates[cfg.elimName] || 0;
            const iWon = myVotes > oppVotes;
            const totalParty = Object.values(candidates).reduce((s, v) => s + v, 0);

            if (iWon && swingVotes > 0) {
                html += `<div style="padding:10px;border-radius:6px;background:#e8f5e9;margin-bottom:10px;border:2px solid #4caf50;">`;
                html += `<div style="font-size:11px;color:#2e7d32;font-weight:700;">✓ ${cfg.short.toUpperCase()}'S TURF — MOP-UP OPPORTUNITY</div>`;
                html += `<div style="font-size:28px;font-weight:700;color:#1b5e20;margin:4px 0;">${swingVotes}</div>`;
                html += `<div style="font-size:12px;color:#555;">${cfg.elimShort}'s voters to absorb</div>`;
                html += `</div>`;
                html += `<table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:8px;">`;
                html += `<tr style="background:#e8f5e9;font-weight:700;"><td style="padding:4px;">👑 ${cfg.short} (won)</td><td style="padding:4px;text-align:right;">${myVotes}</td></tr>`;
                html += `<tr><td style="padding:4px;">${cfg.oppShort}</td><td style="padding:4px;text-align:right;">${oppVotes}</td></tr>`;
                html += `<tr style="background:#fff3e0;"><td style="padding:4px;">🔥 ${cfg.elimShort} (eliminated)</td><td style="padding:4px;text-align:right;font-weight:700;color:#e65100;">${swingVotes}</td></tr>`;
                html += `</table>`;
                html += `<div style="padding:6px;background:#f1f8e9;border-radius:4px;font-size:11px;">`;
                html += `<b>If ${cfg.short} wins all ${swingVotes}:</b> ${myVotes + swingVotes} total vs ${cfg.oppShort}'s ${oppVotes}`;
                html += `<br><b>New margin: +${(myVotes + swingVotes) - oppVotes}</b> (was +${myVotes - oppVotes})`;
                html += `</div>`;
            } else if (!iWon) {
                html += `<div style="padding:8px;background:#f5f5f5;border-radius:4px;font-size:12px;color:#666;">Not ${cfg.short}'s turf — ${cfg.oppShort} won here (${oppVotes} vs ${myVotes})</div>`;
            } else {
                html += `<div style="padding:8px;background:#f5f5f5;border-radius:4px;font-size:12px;color:#666;">${cfg.short} won but no ${cfg.elimShort} voters here</div>`;
            }
            html += `<div style="font-size:10px;color:#888;margin-top:6px;border-top:1px solid #eee;padding-top:4px;">Total party ballots: ${totalParty}</div>`;
        }
        html += `</div>`;
        return html;
    }

    // Swing votes mode (eliminated candidates' voters)
    if (currentMode === 'swing-dem' || currentMode === 'swing-rep') {
        const isDem = currentMode === 'swing-dem';
        const candidates = isDem ? p.dem_candidates : p.rep_candidates;
        const eliminatedName = isDem ? "Eric Holguín" : "Sarah Sagredo-Hammond";
        const runoffCands = isDem ? ["Victor 'Seby' Haddad", "Julio Salinas"] : ["Sergio Sanchez", "Gary Groves"];
        const color = isDem ? '#e65100' : '#e65100';
        const swingVotes = (candidates && candidates[eliminatedName]) || 0;
        const totalParty = isDem ? p.dem_votes : p.rep_votes;

        html += `<div style="padding:10px;border-radius:6px;background:#fff3e0;margin-bottom:10px;border:2px solid #ff9800;">`;
        html += `<div style="font-size:24px;font-weight:700;color:#e65100;">${swingVotes}</div>`;
        html += `<div style="font-size:12px;color:#555;">${eliminatedName} voters — <b>up for grabs</b></div>`;
        html += `</div>`;

        if (swingVotes > 0) {
            html += `<div style="font-size:12px;margin-bottom:8px;">These ${swingVotes} voters must now choose between:</div>`;
            for (const cand of runoffCands) {
                const candVotes = (candidates && candidates[cand]) || 0;
                const candPct = totalParty > 0 ? Math.round(candVotes / totalParty * 100) : 0;
                html += `<div style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12px;">`;
                html += `<span style="font-weight:600;width:100px;">${cand.replace("Victor 'Seby' ","Seby ")}</span>`;
                html += `<span>${candVotes} (${candPct}%)</span>`;
                html += `</div>`;
            }
            html += `<div style="margin-top:8px;padding:6px;background:#e8f5e9;border-radius:4px;font-size:11px;">`;
            html += `<b>If you win all ${swingVotes} swing voters here</b>, you'd have ${swingVotes + ((candidates && candidates[runoffCands[0]]) || 0)} total (vs opponent's ${(candidates && candidates[runoffCands[1]]) || 0})`;
            html += `</div>`;
        } else {
            html += `<div style="font-size:12px;color:#999;">No ${eliminatedName} voters in this precinct</div>`;
        }
        html += `<div style="font-size:10px;color:#888;margin-top:6px;border-top:1px solid #eee;padding-top:4px;">Total ${isDem ? 'Dem' : 'Rep'} ballots in March: ${totalParty}</div>`;
        html += `</div>`;
        return html;
    }

    // Available votes mode
    if (currentMode === 'avail-dem' || currentMode === 'avail-rep') {
        const isDem = currentMode === 'avail-dem';
        const partyVotes = isDem ? p.dem_votes : p.rep_votes;
        const runoffVotes = isDem ? (p.runoff_dem || 0) : (p.runoff_rep || 0);
        const available = partyVotes - runoffVotes;
        const partyLabel = isDem ? 'Democratic' : 'Republican';
        const color = isDem ? '#1565c0' : '#c62828';
        const candidates = isDem ? p.dem_candidates : p.rep_candidates;

        html += `<div style="padding:10px;border-radius:6px;background:${isDem ? '#e3f2fd' : '#fce4ec'};margin-bottom:10px;">`;
        html += `<div style="font-size:24px;font-weight:700;color:${color};">${available}</div>`;
        html += `<div style="font-size:12px;color:#555;">available ${partyLabel} votes for runoff</div>`;
        html += `</div>`;

        html += `<table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:8px;">`;
        html += `<tr style="border-bottom:1px solid #eee;"><td style="padding:4px;">March primary total</td><td style="padding:4px;text-align:right;font-weight:700;">${partyVotes}</td></tr>`;
        html += `<tr style="border-bottom:1px solid #eee;"><td style="padding:4px;">Already voted in runoff</td><td style="padding:4px;text-align:right;">${runoffVotes}</td></tr>`;
        html += `<tr style="border-top:2px solid #333;"><td style="padding:4px;font-weight:700;">Still available</td><td style="padding:4px;text-align:right;font-weight:700;color:${color};">${available}</td></tr>`;
        html += `</table>`;

        // Show March primary breakdown (who these voters chose)
        if (candidates) {
            html += `<div style="font-size:11px;font-weight:700;margin-bottom:4px;">March primary breakdown (who they voted for):</div>`;
            const sorted = Object.entries(candidates).sort((a, b) => b[1] - a[1]);
            for (const [c, v] of sorted) {
                const pct = partyVotes > 0 ? Math.round(v / partyVotes * 100) : 0;
                const barW = partyVotes > 0 ? Math.round(v / sorted[0][1] * 100) : 0;
                html += `<div style="display:flex;align-items:center;gap:6px;padding:2px 0;font-size:11px;">`;
                html += `<span style="width:80px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${c.replace("Victor 'Seby' ","Seby ").split(' ').slice(0,2).join(' ')}</span>`;
                html += `<span style="width:30px;text-align:right;font-weight:600;">${v}</span>`;
                html += `<div style="flex:1;height:8px;background:#eee;border-radius:4px;"><div style="height:8px;background:${color};border-radius:4px;width:${barW}%;opacity:0.6;"></div></div>`;
                html += `<span style="width:30px;text-align:right;color:#666;">${pct}%</span>`;
                html += `</div>`;
            }
            // Note about eliminated candidate's voters
            if (isDem) {
                const ericVotes = candidates["Eric Holguín"] || 0;
                if (ericVotes > 0) html += `<div style="margin-top:6px;padding:4px;background:#fff3e0;border-radius:4px;font-size:10px;">⚡ ${ericVotes} of these voted for Holguín (eliminated) — up for grabs in runoff</div>`;
            } else {
                const sarahVotes = candidates["Sarah Sagredo-Hammond"] || 0;
                if (sarahVotes > 0) html += `<div style="margin-top:6px;padding:4px;background:#fff3e0;border-radius:4px;font-size:10px;">⚡ ${sarahVotes} of these voted for Sagredo-Hammond (eliminated) — up for grabs in runoff</div>`;
            }
        }
        html += `</div>`;
        return html;
    }

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
    } else if (currentMode === 'avail-dem') {
        const totalAvail = precinctData.precincts.reduce((s, p) => s + p.dem_votes - (p.runoff_dem || 0), 0);
        strip.innerHTML = `<b>🔵 Available Dem Votes</b> · ${totalAvail.toLocaleString()} Dem primary voters available for runoff · Darker = more votes to win · Click for breakdown (Seby vs Julio vs Eric voters)`;
    } else if (currentMode === 'avail-rep') {
        const totalAvail = precinctData.precincts.reduce((s, p) => s + p.rep_votes - (p.runoff_rep || 0), 0);
        strip.innerHTML = `<b>🔴 Available GOP Votes</b> · ${totalAvail.toLocaleString()} Rep primary voters available for runoff · Darker = more votes to win · Click for breakdown (Sergio vs Gary vs Sarah voters)`;
    } else if (currentMode === 'swing-dem') {
        const totalSwing = precinctData.precincts.reduce((s, p) => s + ((p.dem_candidates && p.dem_candidates["Eric Holguín"]) || 0), 0);
        strip.innerHTML = `<b>🔥 Holguín's Voters (${totalSwing.toLocaleString()})</b> — eliminated, now choosing between Seby & Julio · Darker = more swing votes · THE runoff battleground`;
    } else if (currentMode === 'swing-rep') {
        const totalSwing = precinctData.precincts.reduce((s, p) => s + ((p.rep_candidates && p.rep_candidates["Sarah Sagredo-Hammond"]) || 0), 0);
        strip.innerHTML = `<b>🔥 Sagredo-Hammond's Voters (${totalSwing.toLocaleString()})</b> — eliminated, now choosing between Sergio & Gary · Darker = more swing votes`;
    } else if (currentMode === 'mopup-seby') {
        const mopupPcts = precinctData.precincts.filter(p => {
            const s = (p.dem_candidates && p.dem_candidates["Victor 'Seby' Haddad"]) || 0;
            const j = (p.dem_candidates && p.dem_candidates["Julio Salinas"]) || 0;
            const e = (p.dem_candidates && p.dem_candidates["Eric Holguín"]) || 0;
            return s > j && e > 0;
        });
        const totalMopup = mopupPcts.reduce((s, p) => s + ((p.dem_candidates && p.dem_candidates["Eric Holguín"]) || 0), 0);
        strip.innerHTML = `<b>💪 Seby's Mop-Up</b> · ${mopupPcts.length} precincts where Seby won + ${totalMopup} Eric voters to absorb · Darker = higher impact`;
    } else if (currentMode === 'mopup-julio') {
        const mopupPcts = precinctData.precincts.filter(p => {
            const j = (p.dem_candidates && p.dem_candidates["Julio Salinas"]) || 0;
            const s = (p.dem_candidates && p.dem_candidates["Victor 'Seby' Haddad"]) || 0;
            const e = (p.dem_candidates && p.dem_candidates["Eric Holguín"]) || 0;
            return j > s && e > 0;
        });
        const totalMopup = mopupPcts.reduce((s, p) => s + ((p.dem_candidates && p.dem_candidates["Eric Holguín"]) || 0), 0);
        strip.innerHTML = `<b>💪 Julio's Mop-Up</b> · ${mopupPcts.length} precincts where Julio won + ${totalMopup} Eric voters to absorb · Darker = higher impact`;
    } else if (currentMode === 'mopup-sergio') {
        const mopupPcts = precinctData.precincts.filter(p => {
            const s = (p.rep_candidates && p.rep_candidates["Sergio Sanchez"]) || 0;
            const g = (p.rep_candidates && p.rep_candidates["Gary Groves"]) || 0;
            const sa = (p.rep_candidates && p.rep_candidates["Sarah Sagredo-Hammond"]) || 0;
            return s > g && sa > 0;
        });
        const totalMopup = mopupPcts.reduce((s, p) => s + ((p.rep_candidates && p.rep_candidates["Sarah Sagredo-Hammond"]) || 0), 0);
        strip.innerHTML = `<b>💪 Sergio's Mop-Up</b> · ${mopupPcts.length} precincts where Sergio won + ${totalMopup} Sarah voters to absorb · Darker = higher impact`;
    } else if (currentMode === 'mopup-gary') {
        const mopupPcts = precinctData.precincts.filter(p => {
            const g = (p.rep_candidates && p.rep_candidates["Gary Groves"]) || 0;
            const s = (p.rep_candidates && p.rep_candidates["Sergio Sanchez"]) || 0;
            const sa = (p.rep_candidates && p.rep_candidates["Sarah Sagredo-Hammond"]) || 0;
            return g > s && sa > 0;
        });
        const totalMopup = mopupPcts.reduce((s, p) => s + ((p.rep_candidates && p.rep_candidates["Sarah Sagredo-Hammond"]) || 0), 0);
        strip.innerHTML = `<b>💪 Gary's Mop-Up</b> · ${mopupPcts.length} precincts where Gary won + ${totalMopup} Sarah voters to absorb · Darker = higher impact`;
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

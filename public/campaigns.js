/* campaigns.js — Campaign District Viewer
 * Adds a "Campaigns" button to the bottom toolbar that lets users
 * select state/federal districts, highlights them on the map,
 * filters voters to only those inside the boundary, and shows
 * a rich stats modal with turnout data.
 */

(function () {
    'use strict';

    // State
    let districtsData = null;       // GeoJSON FeatureCollection
    let oldCongressionalData = null; // Old congressional boundaries for comparison
    let activeDistrict = null;       // Currently selected district feature
    let districtLayer = null;        // Leaflet GeoJSON layer for boundary
    let isLoading = false;
    let lastActiveTab = 'congressional'; // Remember which tab was last viewed

    // Incumbent representatives lookup
    const INCUMBENTS = {
        'TX-15': { name: 'Monica De La Cruz', party: 'R' },
        'TX-28': { name: 'Henry Cuellar', party: 'D' },
        'TX-34': { name: 'Vicente Gonzalez', party: 'D' },
        'HD-31': { name: 'Ryan Guillen', party: 'R' },
        'HD-35': { name: 'Oscar Longoria', party: 'D' },
        'HD-36': { name: 'Sergio Muñoz Jr.', party: 'D' },
        'HD-37': { name: 'Luis V. Gutierrez Jr.', party: 'R' },
        'HD-38': { name: 'Erin Gamez', party: 'D' },
        'HD-39': { name: 'Armando Martinez', party: 'D' },
        'HD-40': { name: 'Terry Canales', party: 'D' },
        'HD-41': { name: 'Bobby Guerra', party: 'D' },
        'CPct-1': { name: 'David L. Fuentes', party: 'D' },
        'CPct-2': { name: 'Eduardo "Eddie" Cantu', party: 'D' },
        'CPct-3': { name: 'Everardo "Ever" Villarreal', party: 'D' },
        'CPct-4': { name: 'Ellie Torres', party: 'D' },
    };

    const btn = document.getElementById('campaignsBtn');
    if (!btn) return;

    // ── Load district boundaries on page load ──
    loadDistricts();

    btn.addEventListener('click', openCampaignSelector);

    async function loadDistricts() {
        try {
            const resp = await fetch('data/districts.json');
            if (!resp.ok) return;
            districtsData = await resp.json();
            console.log('[Campaigns] Loaded', districtsData.features.length, 'districts');
        } catch (e) {
            console.warn('[Campaigns] Could not load districts:', e);
        }
        // Load old congressional boundaries for redistricting comparison
        try {
            const resp2 = await fetch('data/districts_old_congressional.json');
            if (resp2.ok) {
                oldCongressionalData = await resp2.json();
                console.log('[Campaigns] Loaded', oldCongressionalData.features.length, 'old congressional boundaries');
            }
        } catch (e) {
            console.warn('[Campaigns] Could not load old congressional boundaries:', e);
        }
    }

    function openCampaignSelector() {
        if (!districtsData || !districtsData.features.length) {
            alert('District data not loaded yet. Please try again.');
            return;
        }
        showSelectorModal();
    }

    // ── Selector Modal ──
    function showSelectorModal() {
            // Remove existing
            const existing = document.getElementById('campaignSelectorOverlay');
            if (existing) existing.remove();

            const overlay = document.createElement('div');
            overlay.id = 'campaignSelectorOverlay';
            overlay.className = 'campaign-overlay';
            overlay.innerHTML = `
                <div class="campaign-backdrop"></div>
                <div class="campaign-selector">
                    <button class="campaign-close">&times;</button>
                    <div class="campaign-selector-header">
                        <div class="campaign-selector-icon">🏛️</div>
                        <h2>Campaign Districts</h2>
                        <p>Select a district to view turnout data and highlight on the map</p>
                    </div>
                    <div class="campaign-tab-bar">
                        <button class="campaign-tab${lastActiveTab === 'congressional' ? ' active' : ''}" data-tab="congressional">🇺🇸 U.S. Congress</button>
                        <button class="campaign-tab${lastActiveTab === 'state_house' ? ' active' : ''}" data-tab="state_house">⭐ Texas State House</button>
                        <button class="campaign-tab${lastActiveTab === 'commissioner' ? ' active' : ''}" data-tab="commissioner">🏛️ Commissioner Pcts</button>
                    </div>
                    <div class="campaign-district-list" id="campaignDistrictList"></div>
                    ${activeDistrict ? '<button class="campaign-clear-btn" id="campaignClearBtn">✕ Clear District Filter</button>' : ''}
                </div>
            `;

            document.body.appendChild(overlay);

            // Tab switching
            const tabs = overlay.querySelectorAll('.campaign-tab');
            tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    tabs.forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');
                    lastActiveTab = tab.dataset.tab;
                    populateDistrictList(tab.dataset.tab);
                });
            });

            // Populate with last active tab
            populateDistrictList(lastActiveTab);

            // Clear button
            const clearBtn = document.getElementById('campaignClearBtn');
            if (clearBtn) {
                clearBtn.addEventListener('click', () => {
                    clearDistrict();
                    overlay.remove();
                });
            }

            // Close handlers
            overlay.querySelector('.campaign-backdrop').addEventListener('click', () => overlay.remove());
            overlay.querySelector('.campaign-close').addEventListener('click', () => overlay.remove());

            function populateDistrictList(type) {
                const list = document.getElementById('campaignDistrictList');
                list.innerHTML = '';
                const filtered = districtsData.features.filter(f => f.properties.district_type === type);
                if (!filtered.length) {
                    list.innerHTML = '<div style="padding:20px;text-align:center;color:#999;">No districts found for this category.</div>';
                    return;
                }
                filtered.forEach((feature) => {
                    const p = feature.properties;
                    const isActive = activeDistrict && activeDistrict.properties.district_id === p.district_id;
                    const inc = INCUMBENTS[p.district_id];
                    const incHtml = inc ? `<div class="campaign-card-rep" style="font-size:12px;color:#666;">${inc.name} (${inc.party})</div>` : '';
                    const card = document.createElement('div');
                    card.className = 'campaign-district-card' + (isActive ? ' active' : '');
                    card.innerHTML = `
                        <div class="campaign-card-color" style="background:${p.color}"></div>
                        <div class="campaign-card-body">
                            <div class="campaign-card-title">${p.district_name}</div>
                            ${incHtml}
                            <div class="campaign-card-type">${p.district_type === 'congressional' ? 'U.S. Congress' : p.district_type === 'commissioner' ? 'County Commissioner' : 'Texas State House'}</div>
                        </div>
                        <div class="campaign-card-arrow">→</div>
                    `;
                    card.addEventListener('click', () => selectDistrict(feature));
                    list.appendChild(card);
                });
            }
        }



    // ── Select a district ──
    async function selectDistrict(feature) {
        if (isLoading) return;
        isLoading = true;
        lastActiveTab = feature.properties.district_type;

        // Close selector
        const selectorOverlay = document.getElementById('campaignSelectorOverlay');
        if (selectorOverlay) selectorOverlay.remove();

        activeDistrict = feature;
        const props = feature.properties;

        // Toggle button active state
        btn.classList.add('active');

        // Draw boundary on map
        drawDistrictBoundary(feature);

        // Zoom map to district
        if (districtLayer) {
            map.fitBounds(districtLayer.getBounds(), { padding: [30, 30] });
        }

        // Show loading modal immediately
        showStatsModal(props, null, 0, null, []);

        // Send the district polygon to the backend — it will find ALL voters
        // across ALL counties inside the boundary, not just what's on the map
        try {
            const body = {
                district_id: props.district_id,
                election_date: '2026-03-03',
                polygon: feature.geometry
            };
            const resp = await fetch('/api/district-stats', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!resp.ok) throw new Error('API error');
            const stats = await resp.json();

            // For congressional districts, compute old-map comparison
            let oldMapStats = null;
            if (props.district_type === 'congressional' && oldCongressionalData) {
                const oldFeature = oldCongressionalData.features.find(
                    f => f.properties.district_id === props.district_id
                );
                if (oldFeature) {
                    // Also use polygon-based backend query for old map
                    try {
                        const oldResp = await fetch('/api/district-stats', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                district_id: props.district_id,
                                election_date: '2026-03-03',
                                polygon: oldFeature.geometry
                            })
                        });
                        if (oldResp.ok) {
                            oldMapStats = await oldResp.json();
                        }
                    } catch (e2) {
                        console.warn('[Campaigns] Old map stats failed:', e2);
                    }
                }
            }

            showStatsModal(props, stats, stats.total, oldMapStats, []);
        } catch (e) {
            console.error('[Campaigns] Stats fetch failed:', e);
            // Fallback: try client-side with whatever map data we have
            const votersInDistrict = findVotersInDistrict(feature);
            const clientStats = computeClientStats(votersInDistrict);
            showStatsModal(props, clientStats, votersInDistrict.length, null, votersInDistrict);
        }

        isLoading = false;
    }

    // ── Draw district boundary on map ──
    function drawDistrictBoundary(feature) {
        // Remove existing
        if (districtLayer) {
            map.removeLayer(districtLayer);
        }

        const color = feature.properties.color || '#667eea';

        districtLayer = L.geoJSON(feature, {
            style: {
                color: color,
                weight: 3,
                opacity: 0.9,
                fillColor: color,
                fillOpacity: 0.08,
                dashArray: '8, 4'
            }
        }).addTo(map);
    }

    // ── Clear district ──
    function clearDistrict() {
        activeDistrict = null;
        btn.classList.remove('active');
        if (districtLayer) {
            map.removeLayer(districtLayer);
            districtLayer = null;
        }
        // Close any open modal
        const modal = document.getElementById('campaignStatsOverlay');
        if (modal) modal.remove();
    }

    // ── Point-in-polygon (ray casting) ──
    function pointInPolygon(point, polygon) {
        const x = point[0], y = point[1];
        let inside = false;
        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const xi = polygon[i][0], yi = polygon[i][1];
            const xj = polygon[j][0], yj = polygon[j][1];
            const intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
            if (intersect) inside = !inside;
        }
        return inside;
    }

    function pointInFeature(lng, lat, feature) {
        const geom = feature.geometry;
        if (!geom) return false;

        if (geom.type === 'Polygon') {
            return pointInPolygon([lng, lat], geom.coordinates[0]);
        } else if (geom.type === 'MultiPolygon') {
            return geom.coordinates.some(poly => pointInPolygon([lng, lat], poly[0]));
        }
        return false;
    }

    function findVotersInDistrict(districtFeature) {
        if (!window.mapData || !window.mapData.features) return [];
        return window.mapData.features.filter(f => {
            if (!f.geometry || !f.geometry.coordinates) return false;
            const [lng, lat] = f.geometry.coordinates;
            return pointInFeature(lng, lat, districtFeature);
        });
    }

    // ── Client-side stats fallback ──
    function computeClientStats(voters) {
        let dem = 0, rep = 0, r2d = 0, d2r = 0, newTotal = 0, newDem = 0, newRep = 0;
        let female = 0, male = 0, demFemale = 0, demMale = 0, repFemale = 0, repMale = 0;
        const ageGroups = {};
        const newAgeGender = {};
        voters.forEach(f => {
            const p = f.properties;
            const cur = (p.party_affiliation_current || '').toLowerCase();
            const prev = (p.party_affiliation_previous || '').toLowerCase();
            const sex = (p.sex || '').toUpperCase();
            if (cur.includes('democrat')) dem++;
            else if (cur.includes('republican')) rep++;
            if (sex === 'F') {
                female++;
                if (cur.includes('democrat')) demFemale++;
                else if (cur.includes('republican')) repFemale++;
            } else if (sex === 'M') {
                male++;
                if (cur.includes('democrat')) demMale++;
                else if (cur.includes('republican')) repMale++;
            }
            // Age group
            const by = p.birth_year || 0;
            let ag = 'Unknown';
            if (by >= 2002 && by <= 2008) ag = '18-24';
            else if (by >= 1992 && by <= 2001) ag = '25-34';
            else if (by >= 1982 && by <= 1991) ag = '35-44';
            else if (by >= 1972 && by <= 1981) ag = '45-54';
            else if (by >= 1962 && by <= 1971) ag = '55-64';
            else if (by >= 1952 && by <= 1961) ag = '65-74';
            else if (by > 0 && by < 1952) ag = '75+';
            if (!ageGroups[ag]) ageGroups[ag] = {total: 0, dem: 0, rep: 0};
            ageGroups[ag].total++;
            if (cur.includes('democrat')) ageGroups[ag].dem++;
            else if (cur.includes('republican')) ageGroups[ag].rep++;

            if (p.is_new_voter) {
                newTotal++;
                if (cur.includes('democrat')) newDem++;
                else if (cur.includes('republican')) newRep++;
                if (!newAgeGender[ag]) newAgeGender[ag] = {total:0,female:0,male:0};
                newAgeGender[ag].total++;
                if (sex === 'F') newAgeGender[ag].female++;
                else if (sex === 'M') newAgeGender[ag].male++;
            }
            if (prev && cur) {
                if (prev.includes('republican') && cur.includes('democrat')) r2d++;
                if (prev.includes('democrat') && cur.includes('republican')) d2r++;
            }
        });
        return {
            total: voters.length, dem, rep,
            dem_share: (dem + rep) ? Math.round(dem / (dem + rep) * 1000) / 10 : 0,
            new_total: newTotal, new_dem: newDem, new_rep: newRep,
            r2d, d2r,
            total_2024: 0, dem_2024: 0, rep_2024: 0, dem_share_2024: 0,
            female, male, dem_female: demFemale, dem_male: demMale,
            rep_female: repFemale, rep_male: repMale,
            age_groups: ageGroups,
            new_age_gender: newAgeGender
        };
    }

    // ── Build stats body HTML from a stats object ──
    function buildStatsBodyHtml(stats, districtProps, oldMapStats) {
        const n = v => Number(v || 0).toLocaleString();
        const netFlip = stats.r2d - stats.d2r;
        const netDir = netFlip > 0 ? 'D' : netFlip < 0 ? 'R' : '—';
        const netColor = netFlip > 0 ? '#1E90FF' : netFlip < 0 ? '#DC143C' : '#888';
        const demPct = stats.dem_share || 0;
        const repPct = (100 - demPct).toFixed(1);
        const newPctDem = stats.new_total ? Math.round(stats.new_dem / stats.new_total * 100) : 0;
        const turnoutVs2024 = stats.total_2024 ? Math.round(stats.total / stats.total_2024 * 100) : 0;
        const demShift = stats.dem_share_2024 ? (stats.dem_share - stats.dem_share_2024).toFixed(1) : null;
        const shiftArrow = demShift > 0 ? '↑' : demShift < 0 ? '↓' : '→';
        const shiftColor = demShift > 0 ? '#1E90FF' : demShift < 0 ? '#DC143C' : '#888';

        let html = `
            <div class="campaign-party-bar">
                <div class="campaign-party-bar-dem" style="width:${demPct}%"></div>
                <div class="campaign-party-bar-rep" style="width:${repPct}%"></div>
            </div>
            <div class="campaign-party-labels">
                <span class="campaign-dem-label">DEM ${demPct}%</span>
                <span class="campaign-rep-label">REP ${repPct}%</span>
            </div>
            <div class="campaign-metrics">
                <div class="campaign-metric">
                    <div class="campaign-metric-value">${n(stats.total)}</div>
                    <div class="campaign-metric-label">Early Votes</div>
                </div>
                <div class="campaign-metric">
                    <div class="campaign-metric-value" style="color:#1E90FF">${n(stats.dem)}</div>
                    <div class="campaign-metric-label">Democratic</div>
                </div>
                <div class="campaign-metric">
                    <div class="campaign-metric-value" style="color:#DC143C">${n(stats.rep)}</div>
                    <div class="campaign-metric-label">Republican</div>
                </div>
                <div class="campaign-metric">
                    <div class="campaign-metric-value">${turnoutVs2024}%</div>
                    <div class="campaign-metric-label">of 2024 Total</div>
                </div>
            </div>`;

        if (demShift !== null) {
            html += `
            <div class="campaign-shift-banner" style="border-left: 4px solid ${shiftColor}">
                <span class="campaign-shift-arrow" style="color:${shiftColor}">${shiftArrow}</span>
                <span>DEM share shifted <strong style="color:${shiftColor}">${demShift > 0 ? '+' : ''}${demShift}pts</strong> vs 2024 (${stats.dem_share_2024}%)</span>
            </div>`;
        }

        html += `
            <div class="campaign-section">
                <h4>🔄 Party Switchers</h4>
                <div class="campaign-flip-row">
                    <div class="campaign-flip-item">
                        <span class="campaign-flip-dot" style="background:#6A1B9A"></span>
                        <span>${n(stats.r2d)} R→D</span>
                    </div>
                    <div class="campaign-flip-item">
                        <span class="campaign-flip-dot" style="background:#C62828"></span>
                        <span>${n(stats.d2r)} D→R</span>
                    </div>
                    <div class="campaign-flip-net" style="color:${netColor}">
                        Net: ${netFlip > 0 ? '+' : ''}${netFlip} ${netDir}
                    </div>
                </div>
            </div>
            <div class="campaign-section">
                <h4>⭐ New Voters</h4>
                <div class="campaign-new-voters">
                    <div class="campaign-metric-inline">
                        <span class="campaign-metric-big">${n(stats.new_total)}</span> first-time voters
                    </div>
                    <div class="campaign-new-bar">
                        <div class="campaign-new-bar-dem" style="width:${newPctDem}%"></div>
                        <div class="campaign-new-bar-rep" style="width:${100 - newPctDem}%"></div>
                    </div>
                    <div class="campaign-party-labels" style="font-size:11px">
                        <span style="color:#1E90FF">${n(stats.new_dem)} DEM (${newPctDem}%)</span>
                        <span style="color:#DC143C">${n(stats.new_rep)} REP</span>
                    </div>
                    ${(() => {
                        const nag = stats.new_age_gender || {};
                        const order = ['18-24','25-34','35-44','45-54','55-64','65-74','75+'];
                        const sorted = order.filter(a => nag[a] && nag[a].total > 0).sort((a,b) => nag[b].total - nag[a].total);
                        const top2 = sorted.slice(0, 3);
                        if (!top2.length) return '';
                        return '<div style="margin-top:4px;font-size:11px;color:#555;">Top groups: ' +
                            top2.map(a => {
                                const g = nag[a];
                                return '<b>' + a + '</b> (' + n(g.total) + ' — <span style="color:#FF1493">♀</span>' + n(g.female) + ' <span style="color:#000080">♂</span>' + n(g.male) + ')';
                            }).join(', ') + '</div>';
                    })()}
                </div>
            </div>
            <div class="campaign-section">
                <h4>👤 Gender</h4>
                <div style="display:flex;justify-content:space-between;align-items:center;font-size:13px;">
                    <span><span style="color:#FF1493">♀</span> <b>${n(stats.female)}</b> <span style="color:#666;font-size:11px">(${n(stats.dem_female)} D · ${n(stats.rep_female)} R)</span></span>
                    <span><span style="color:#000080">♂</span> <b>${n(stats.male)}</b> <span style="color:#666;font-size:11px">(${n(stats.dem_male)} D · ${n(stats.rep_male)} R)</span></span>
                </div>
                <div class="campaign-gender-bar" style="margin:4px 0 0;">
                    <div class="campaign-gender-bar-f" style="width:${stats.female + stats.male ? Math.round(stats.female / (stats.female + stats.male) * 100) : 50}%"></div>
                    <div class="campaign-gender-bar-m" style="width:${stats.female + stats.male ? Math.round(stats.male / (stats.female + stats.male) * 100) : 50}%"></div>
                </div>
            </div>
            <div class="campaign-section">
                <h4>📊 Age Groups</h4>
                <table class="campaign-table" style="font-size:11px;">
                    <tr><th style="text-align:left;padding:2px 4px">Age</th><th style="text-align:right;padding:2px 4px">Total</th><th style="text-align:right;padding:2px 4px;color:#1E90FF">DEM</th><th style="text-align:right;padding:2px 4px;color:#DC143C">REP</th><th style="text-align:right;padding:2px 4px">DEM%</th></tr>
                    ${(() => {
                        const order = ['18-24','25-34','35-44','45-54','55-64','65-74','75+'];
                        const ag = stats.age_groups || {};
                        let maxTurnout = 0, maxTurnoutAg = '';
                        let maxGap = 0, maxGapAg = '';
                        order.forEach(a => {
                            const g = ag[a] || {total:0,dem:0,rep:0};
                            if (g.total > maxTurnout) { maxTurnout = g.total; maxTurnoutAg = a; }
                            const gap = Math.abs(g.dem - g.rep);
                            if (gap > maxGap) { maxGap = gap; maxGapAg = a; }
                        });
                        return order.map(a => {
                            const g = ag[a] || {total:0,dem:0,rep:0};
                            const pct = (g.dem+g.rep) ? Math.round(g.dem/(g.dem+g.rep)*100) : 0;
                            const isTurnout = a === maxTurnoutAg;
                            const isGap = a === maxGapAg;
                            const bg = isTurnout && isGap ? 'background:linear-gradient(90deg,#fff3e0,#e8f5e9)' : isTurnout ? 'background:#fff3e0' : isGap ? 'background:#e8f5e9' : '';
                            const badge = (isTurnout ? ' 🔥' : '') + (isGap ? ' ⚡' : '');
                            return '<tr style="'+bg+'"><td style="padding:1px 4px;font-weight:'+(isTurnout||isGap?'700':'400')+'">'+a+badge+'</td><td style="text-align:right;padding:1px 4px">'+n(g.total)+'</td><td style="text-align:right;padding:1px 4px;color:#1E90FF">'+n(g.dem)+'</td><td style="text-align:right;padding:1px 4px;color:#DC143C">'+n(g.rep)+'</td><td style="text-align:right;padding:1px 4px">'+pct+'%</td></tr>';
                        }).join('');
                    })()}
                </table>
                <div style="font-size:9px;color:#999;margin-top:2px;">🔥 Highest turnout · ⚡ Largest party gap</div>
            </div>`;

        if (stats.total_2024) {
            html += `
            <div class="campaign-section">
                <h4>📊 2024 Comparison</h4>
                <table class="campaign-table">
                    <tr><th></th><th>2024 Final</th><th>2026 EV</th><th>Change</th></tr>
                    <tr>
                        <td>Total</td>
                        <td>${n(stats.total_2024)}</td>
                        <td>${n(stats.total)}</td>
                        <td>${turnoutVs2024}%</td>
                    </tr>
                    <tr>
                        <td style="color:#1E90FF">DEM</td>
                        <td>${n(stats.dem_2024)}</td>
                        <td>${n(stats.dem)}</td>
                        <td style="color:${shiftColor}">${demShift > 0 ? '+' : ''}${demShift}pts</td>
                    </tr>
                    <tr>
                        <td style="color:#DC143C">REP</td>
                        <td>${n(stats.rep_2024)}</td>
                        <td>${n(stats.rep)}</td>
                        <td></td>
                    </tr>
                </table>
            </div>`;
        }

        // County breakdown (from server stats)
        const cb = stats.county_breakdown || {};
        const cbCounties = Object.keys(cb).sort();
        if (cbCounties.length > 1) {
            html += `
            <div class="campaign-section">
                <h4>🗺️ Votes by County</h4>
                <table class="campaign-table" style="font-size:11px;width:100%;">
                    <tr><th style="text-align:left;padding:2px 4px">County</th><th style="text-align:right;padding:2px 4px">Total</th><th style="text-align:right;padding:2px 4px;color:#1E90FF">DEM</th><th style="text-align:right;padding:2px 4px;color:#DC143C">REP</th><th style="text-align:right;padding:2px 4px">DEM%</th></tr>
                    ${cbCounties.map(c => {
                        const d = cb[c];
                        const pct = (d.dem + d.rep) ? Math.round(d.dem / (d.dem + d.rep) * 100) : 0;
                        return '<tr><td style="padding:1px 4px;font-weight:600">' + c + '</td><td style="text-align:right;padding:1px 4px">' + n(d.total) + '</td><td style="text-align:right;padding:1px 4px;color:#1E90FF">' + n(d.dem) + '</td><td style="text-align:right;padding:1px 4px;color:#DC143C">' + n(d.rep) + '</td><td style="text-align:right;padding:1px 4px">' + pct + '%</td></tr>';
                    }).join('')}
                </table>
            </div>`;
        }

        if (districtProps.district_type === 'congressional' && oldMapStats) {
            const oldTotal = oldMapStats.total || 0;
            const oldDem = oldMapStats.dem || 0;
            const oldRep = oldMapStats.rep || 0;
            const oldDemPct = (oldDem + oldRep) ? Math.round(oldDem / (oldDem + oldRep) * 1000) / 10 : 0;
            const newTotal = stats.total || 0;
            const newDem = stats.dem || 0;
            const newRep = stats.rep || 0;
            const diffTotal = newTotal - oldTotal;
            const diffDem = newDem - oldDem;
            const diffRep = newRep - oldRep;
            const diffDemPct = (demPct - oldDemPct).toFixed(1);
            const diffTotalPct = oldTotal ? ((diffTotal / oldTotal) * 100).toFixed(1) : '—';
            const diffDemPctN = parseFloat(diffDemPct);
            const diffColor = diffDemPctN > 0 ? '#1E90FF' : diffDemPctN < 0 ? '#DC143C' : '#888';
            const arrow = diffDemPctN > 0 ? '↑' : diffDemPctN < 0 ? '↓' : '→';
            const sign = v => v > 0 ? '+' + n(v) : v < 0 ? '−' + n(Math.abs(v)) : '0';
            html += '<div class="campaign-section" style="background:#f8f0ff;border-radius:8px;padding:8px 10px;margin-top:6px;">' +
                '<h4 style="color:#4A148C;">🗺️ Redistricting Impact (New vs Old Map)</h4>' +
                '<div style="font-size:11px;color:#666;margin-bottom:6px;">Comparing PlanC2333 (2026) to PlanC2193 (2022–2024) boundaries</div>' +
                '<table class="campaign-table" style="font-size:11px;">' +
                '<tr><th style="text-align:left;padding:2px 4px"></th><th style="text-align:right;padding:2px 4px">Old Map</th><th style="text-align:right;padding:2px 4px">New Map</th><th style="text-align:right;padding:2px 4px">Diff</th></tr>' +
                '<tr><td style="padding:2px 4px;font-weight:600">Total</td><td style="text-align:right;padding:2px 4px">' + n(oldTotal) + '</td><td style="text-align:right;padding:2px 4px">' + n(newTotal) + '</td><td style="text-align:right;padding:2px 4px;font-weight:700;color:' + (diffTotal >= 0 ? '#333' : '#C62828') + '">' + sign(diffTotal) + ' (' + (diffTotal >= 0 ? '+' : '') + diffTotalPct + '%)</td></tr>' +
                '<tr><td style="padding:2px 4px;color:#1E90FF;font-weight:600">DEM</td><td style="text-align:right;padding:2px 4px;color:#1E90FF">' + n(oldDem) + '</td><td style="text-align:right;padding:2px 4px;color:#1E90FF">' + n(newDem) + '</td><td style="text-align:right;padding:2px 4px;font-weight:700;color:#1E90FF">' + sign(diffDem) + '</td></tr>' +
                '<tr><td style="padding:2px 4px;color:#DC143C;font-weight:600">REP</td><td style="text-align:right;padding:2px 4px;color:#DC143C">' + n(oldRep) + '</td><td style="text-align:right;padding:2px 4px;color:#DC143C">' + n(newRep) + '</td><td style="text-align:right;padding:2px 4px;font-weight:700;color:#DC143C">' + sign(diffRep) + '</td></tr>' +
                '<tr><td style="padding:2px 4px;font-weight:600">DEM %</td><td style="text-align:right;padding:2px 4px">' + oldDemPct + '%</td><td style="text-align:right;padding:2px 4px">' + demPct + '%</td><td style="text-align:right;padding:2px 4px;font-weight:700;color:' + diffColor + '">' + arrow + ' ' + (diffDemPctN > 0 ? '+' : '') + diffDemPct + 'pts</td></tr>' +
                '</table></div>';
        }

        return html;
    }

    // ── Stats Modal ──
    function showStatsModal(districtProps, stats, voterCount, oldMapStats, votersInDistrict) {
        // Remove existing
        const existing = document.getElementById('campaignStatsOverlay');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.id = 'campaignStatsOverlay';
        overlay.className = 'campaign-overlay';

        const color = districtProps.color || '#667eea';
        const isCongressional = districtProps.district_type === 'congressional';
        const isCommissioner = districtProps.district_type === 'commissioner';
        const icon = isCongressional ? '🇺🇸' : isCommissioner ? '🏛️' : '⭐';
        const levelLabel = isCongressional ? 'U.S. CONGRESSIONAL' : isCommissioner ? 'HIDALGO COUNTY COMMISSIONER' : 'TEXAS STATE HOUSE';

        // Detect counties from server-side county_breakdown (preferred) or client-side voter data
        const cb = (stats && stats.county_breakdown) || {};
        const counties = Object.keys(cb).sort();
        const hasMultipleCounties = counties.length > 1;

        let bodyHtml;
        if (!stats) {
            bodyHtml = `
                <div class="campaign-stats-loading">
                    <div class="loading-spinner"></div>
                    <p>Analyzing voters in district...</p>
                </div>`;
        } else {
            const allBodyHtml = buildStatsBodyHtml(stats, districtProps, oldMapStats);
            bodyHtml = `<div class="campaign-county-panel" data-county="__all__">${allBodyHtml}</div>`;
        }

        overlay.innerHTML = `
            <div class="campaign-backdrop"></div>
            <div class="campaign-stats-modal">
                <button class="campaign-close">&times;</button>
                <div class="campaign-stats-header" style="border-bottom: 3px solid ${color}">
                    <div class="campaign-stats-badge" style="background:${color}">${icon}</div>
                    <div>
                        <div class="campaign-stats-level">${levelLabel}</div>
                        <h2 class="campaign-stats-title">${districtProps.district_name}</h2>
                    </div>
                </div>
                <div class="campaign-stats-body">${bodyHtml}</div>
                <div class="campaign-stats-footer">
                    <button class="campaign-btn-secondary" id="campaignBackBtn">← Choose District</button>
                    <button class="campaign-btn-primary" id="campaignCloseBtn">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        // Wire up county tab switching
        const countyTabs = overlay.querySelectorAll('.campaign-county-tab');
        const countyPanels = overlay.querySelectorAll('.campaign-county-panel');
        countyTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                countyTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                const target = tab.dataset.county;
                countyPanels.forEach(p => {
                    p.style.display = p.dataset.county === target ? '' : 'none';
                });
            });
        });

        overlay.querySelector('.campaign-backdrop').addEventListener('click', () => overlay.remove());
        overlay.querySelector('.campaign-close').addEventListener('click', () => overlay.remove());
        document.getElementById('campaignCloseBtn').addEventListener('click', () => overlay.remove());
        document.getElementById('campaignBackBtn').addEventListener('click', () => {
            overlay.remove();
            showSelectorModal();
        });
    }

})();

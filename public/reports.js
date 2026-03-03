// Campaign Reports System
(function() {
    'use strict';
    
    let currentReport = null;
    let currentReportData = null;
    
    // Initialize reports system
    function initReports() {
        console.log('initReports called');
        
        // Wait for modal HTML to be loaded
        const modal = document.getElementById('reportsModal');
        const closeBtn = document.getElementById('reportsModalClose');
        
        console.log('Modal element:', modal);
        console.log('Close button:', closeBtn);
        
        if (!modal || !closeBtn) {
            // Modal not ready yet, wait for event
            console.log('Modal not ready, waiting for reportsModalReady event');
            window.addEventListener('reportsModalReady', initReports, { once: true });
            return;
        }
        
        console.log('Modal ready, attaching event listeners');
        
        // Reports button click
        const reportsBtn = document.getElementById('reportsIconBtn');
        console.log('Reports button:', reportsBtn);
        
        if (reportsBtn) {
            reportsBtn.addEventListener('click', function(e) {
                console.log('Reports button clicked!');
                openReportsModal();
            });
            console.log('Click listener attached to reports button');
        } else {
            console.error('Reports button not found!');
        }
        
        // Close button
        document.getElementById('reportsModalClose')?.addEventListener('click', closeReportsModal);
        
        // Click outside to close
        document.getElementById('reportsModal')?.addEventListener('click', function(e) {
            if (e.target.id === 'reportsModal') {
                closeReportsModal();
            }
        });
        
        // Run report buttons
        document.querySelectorAll('.btn-run-report').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const card = this.closest('.report-card');
                const reportType = card.dataset.report;
                runReport(reportType);
            });
        });
        
        // Report card click
        document.querySelectorAll('.report-card').forEach(card => {
            card.addEventListener('click', function() {
                const reportType = this.dataset.report;
                runReport(reportType);
            });
        });
        
        // Back to list button
        document.querySelector('.btn-back-to-list')?.addEventListener('click', showReportsList);
        
        // Export CSV button
        document.getElementById('btnExportCSV')?.addEventListener('click', exportCurrentReport);
    }
    
    function openReportsModal() {
        console.log('openReportsModal called');
        const modal = document.getElementById('reportsModal');
        console.log('Opening modal:', modal);
        if (modal) {
            modal.style.display = 'flex';
            showReportsList();
        } else {
            console.error('Modal not found when trying to open!');
        }
    }
    
    function closeReportsModal() {
        document.getElementById('reportsModal').style.display = 'none';
    }
    
    function showReportsList() {
        document.getElementById('reportsListView').style.display = 'block';
        document.getElementById('reportView').style.display = 'none';
        currentReport = null;
        currentReportData = null;
    }
    
    function showReportView() {
        document.getElementById('reportsListView').style.display = 'none';
        document.getElementById('reportView').style.display = 'block';
    }
    
    async function runReport(reportType) {
        currentReport = reportType;
        showReportView();
        
        const reportContent = document.getElementById('reportContent');
        const reportTitle = document.getElementById('reportTitle');
        const reportFilters = document.getElementById('reportFilters');
        
        // Show loading
        reportContent.innerHTML = '<div class="report-loading"><i class="fas fa-spinner fa-spin"></i> Loading report...</div>';
        
        try {
            switch(reportType) {
                case 'precinct-performance':
                    reportTitle.textContent = 'Precinct Performance Report';
                    await loadPrecinctPerformance();
                    break;
                case 'party-switchers':
                    reportTitle.textContent = 'Party Switchers Report';
                    await loadPartySwitchers();
                    break;
                case 'turf-cuts':
                    reportTitle.textContent = 'Turf Cuts (Non-Voters)';
                    await loadTurfCuts();
                    break;
                case 'new-voters':
                    reportTitle.textContent = 'New Voters Report';
                    await loadNewVoters();
                    break;
            }
        } catch (error) {
            console.error('Error loading report:', error);
            reportContent.innerHTML = `<div class="report-loading" style="color: #dc3545;"><i class="fas fa-exclamation-triangle"></i> Error loading report: ${error.message}</div>`;
        }
    }
    
    async function loadPrecinctPerformance() {
        const county = selectedCountyFilter || 'Hidalgo';
        const electionDate = currentDataset?.election_date || '2026-03-03';
        
        const response = await fetch(`/api/reports/precinct-performance?county=${encodeURIComponent(county)}&election_date=${encodeURIComponent(electionDate)}`);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load report');
        }
        
        currentReportData = data.precincts;
        
        // Build summary
        const totalPrecincts = data.precincts.length;
        const avgTurnout = (data.precincts.reduce((sum, p) => sum + p.turnout_pct, 0) / totalPrecincts).toFixed(1);
        const highestPrecinct = data.precincts[0];
        const lowestPrecinct = data.precincts[data.precincts.length - 1];
        
        let html = `
            <div class="report-summary">
                <div class="report-summary-item">
                    <div class="label">Total Precincts</div>
                    <div class="value">${totalPrecincts}</div>
                </div>
                <div class="report-summary-item">
                    <div class="label">Average Turnout</div>
                    <div class="value">${avgTurnout}%</div>
                </div>
                <div class="report-summary-item">
                    <div class="label">Highest</div>
                    <div class="value">${highestPrecinct.turnout_pct}%</div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;">${highestPrecinct.precinct}</div>
                </div>
                <div class="report-summary-item">
                    <div class="label">Lowest</div>
                    <div class="value">${lowestPrecinct.turnout_pct}%</div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;">${lowestPrecinct.precinct}</div>
                </div>
            </div>
            <table class="report-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Precinct</th>
                        <th>Registered</th>
                        <th>Voted</th>
                        <th>Turnout %</th>
                        <th>Dem</th>
                        <th>Rep</th>
                        <th>Dem %</th>
                    </tr>
                </thead>
                <tbody>`;
        
        data.precincts.forEach((p, idx) => {
            html += `
                <tr>
                    <td><strong>${idx + 1}</strong></td>
                    <td>${p.precinct}</td>
                    <td>${p.registered.toLocaleString()}</td>
                    <td>${p.voted.toLocaleString()}</td>
                    <td><strong>${p.turnout_pct}%</strong></td>
                    <td style="color: #0064FF;">${p.dem.toLocaleString()}</td>
                    <td style="color: #E6003C;">${p.rep.toLocaleString()}</td>
                    <td>${p.dem_pct}%</td>
                </tr>`;
        });
        
        html += '</tbody></table>';
        document.getElementById('reportContent').innerHTML = html;
    }
    
    async function loadPartySwitchers() {
        const county = selectedCountyFilter || 'Hidalgo';
        const electionDate = currentDataset?.election_date || '2026-03-03';
        
        // Add filters
        document.getElementById('reportFilters').innerHTML = `
            <div class="report-filter-group">
                <label>Direction</label>
                <select id="switcherDirection">
                    <option value="both">Both Directions</option>
                    <option value="d2r">D → R</option>
                    <option value="r2d">R → D</option>
                </select>
            </div>
        `;
        
        document.getElementById('switcherDirection').addEventListener('change', () => loadPartySwitchers());
        const direction = document.getElementById('switcherDirection')?.value || 'both';
        
        const response = await fetch(`/api/reports/party-switchers?county=${encodeURIComponent(county)}&election_date=${encodeURIComponent(electionDate)}&direction=${direction}`);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load report');
        }
        
        currentReportData = data.switchers;
        
        let html = `
            <div class="report-summary">
                <div class="report-summary-item">
                    <div class="label">Total Switchers</div>
                    <div class="value">${data.switchers.length}</div>
                </div>
                <div class="report-summary-item">
                    <div class="label">D → R</div>
                    <div class="value" style="color: #E6003C;">${data.d2r || 0}</div>
                </div>
                <div class="report-summary-item">
                    <div class="label">R → D</div>
                    <div class="value" style="color: #0064FF;">${data.r2d || 0}</div>
                </div>
            </div>
            <table class="report-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Address</th>
                        <th>Precinct</th>
                        <th>From</th>
                        <th>To</th>
                        <th>Age</th>
                    </tr>
                </thead>
                <tbody>`;
        
        data.switchers.forEach(s => {
            const fromColor = s.from_party === 'Democratic' ? '#0064FF' : '#E6003C';
            const toColor = s.to_party === 'Democratic' ? '#0064FF' : '#E6003C';
            html += `
                <tr>
                    <td><strong>${s.name}</strong></td>
                    <td>${s.address}</td>
                    <td>${s.precinct || 'N/A'}</td>
                    <td style="color: ${fromColor};">${s.from_party}</td>
                    <td style="color: ${toColor};">${s.to_party}</td>
                    <td>${s.age || 'N/A'}</td>
                </tr>`;
        });
        
        html += '</tbody></table>';
        document.getElementById('reportContent').innerHTML = html;
    }
    
    async function loadTurfCuts() {
        const county = selectedCountyFilter || 'Hidalgo';
        
        // Get current filter values if they exist, otherwise use defaults
        const precinct = document.getElementById('turfPrecinct')?.value || 'all';
        const partyAffinity = document.getElementById('turfPartyAffinity')?.value || 'all';
        const history = document.getElementById('turfHistory')?.value || 'all';
        const sortBy = document.getElementById('turfSortBy')?.value || 'precinct';
        const electionDate = currentDataset?.election_date || '2026-03-03';
        
        // Add filters HTML
        document.getElementById('reportFilters').innerHTML = `
            <div class="report-filter-group">
                <label>Sort By</label>
                <select id="turfSortBy">
                    <option value="precinct">Precinct Name</option>
                    <option value="turnout_asc">Lowest Turnout First</option>
                    <option value="turnout_desc">Highest Turnout First</option>
                </select>
            </div>
            <div class="report-filter-group">
                <label>Precinct</label>
                <select id="turfPrecinct">
                    <option value="all">All Precincts</option>
                </select>
            </div>
            <div class="report-filter-group">
                <label>Party Affinity</label>
                <select id="turfPartyAffinity">
                    <option value="all">All Voters</option>
                    <option value="democratic">Democratic History</option>
                    <option value="republican">Republican History</option>
                </select>
            </div>
            <div class="report-filter-group">
                <label>Voting History</label>
                <select id="turfHistory">
                    <option value="all">All Non-Voters</option>
                    <option value="never">Never Voted</option>
                    <option value="sporadic">Sporadic Voters</option>
                </select>
            </div>
        `;
        
        // Restore selected values
        if (document.getElementById('turfSortBy')) {
            document.getElementById('turfSortBy').value = sortBy;
        }
        if (document.getElementById('turfPrecinct')) {
            document.getElementById('turfPrecinct').value = precinct;
        }
        if (document.getElementById('turfPartyAffinity')) {
            document.getElementById('turfPartyAffinity').value = partyAffinity;
        }
        if (document.getElementById('turfHistory')) {
            document.getElementById('turfHistory').value = history;
        }
        
        // Add event listeners AFTER setting values
        document.getElementById('turfSortBy')?.addEventListener('change', () => loadTurfCuts());
        document.getElementById('turfPrecinct')?.addEventListener('change', () => loadTurfCuts());
        document.getElementById('turfPartyAffinity')?.addEventListener('change', () => loadTurfCuts());
        document.getElementById('turfHistory')?.addEventListener('change', () => loadTurfCuts());
        
        const response = await fetch(`/api/reports/non-voters?county=${encodeURIComponent(county)}&election_date=${encodeURIComponent(electionDate)}&precinct=${precinct}&history=${history}&party_affinity=${partyAffinity}&sort_by=${sortBy}`);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load report');
        }
        
        currentReportData = data.non_voters;
        
        // Group by precinct
        const byPrecinct = {};
        data.non_voters.forEach(v => {
            if (!byPrecinct[v.precinct]) {
                byPrecinct[v.precinct] = {
                    voters: [],
                    turnout: v.precinct_turnout,
                    registered: v.precinct_registered,
                    voted: v.precinct_voted
                };
            }
            byPrecinct[v.precinct].voters.push(v);
        });
        
        let html = `
            <div class="report-summary">
                <div class="report-summary-item">
                    <div class="label">Total Non-Voters</div>
                    <div class="value">${data.non_voters.length}</div>
                </div>
                <div class="report-summary-item">
                    <div class="label">Precincts</div>
                    <div class="value">${Object.keys(byPrecinct).length}</div>
                </div>
            </div>`;
        
        // Display by precinct
        for (const [precinctName, precinctData] of Object.entries(byPrecinct)) {
            const turnoutInfo = precinctData.turnout > 0 
                ? `${precinctData.turnout}% turnout (${precinctData.voted}/${precinctData.registered})`
                : '';
            
            html += `
                <div class="precinct-section">
                    <div class="precinct-header" style="cursor: pointer;" data-precinct="${precinctName}">
                        <div>
                            <h4><i class="fas fa-chevron-right precinct-toggle"></i> Precinct ${precinctName} <span style="color: #666; font-size: 14px; font-weight: normal;">${turnoutInfo}</span></h4>
                        </div>
                        <button class="btn-view-on-map" data-precinct="${precinctName}" style="background: #667eea; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px;">
                            <i class="fas fa-map-marked-alt"></i> View ${precinctData.voters.length} on Map
                        </button>
                    </div>
                    <div class="precinct-table-container" style="display: none;">
                    <table class="report-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Address</th>
                                <th>Party Affinity</th>
                                <th>Last Voted</th>
                                <th>Score</th>
                                <th>Age</th>
                            </tr>
                        </thead>
                        <tbody>`;
            
            precinctData.voters.forEach(v => {
                let affinityColor = '#666';
                let affinityText = v.party_affinity;
                
                if (v.party_affinity === 'Democratic') {
                    affinityColor = '#0064FF';
                    affinityText = `D (${v.dem_history})`;
                } else if (v.party_affinity === 'Republican') {
                    affinityColor = '#E6003C';
                    affinityText = `R (${v.rep_history})`;
                } else if (v.party_affinity === 'Mixed') {
                    affinityColor = '#6A1B9A';
                    affinityText = `Mixed (${v.dem_history}D/${v.rep_history}R)`;
                }
                
                html += `
                    <tr>
                        <td><strong>${v.name}</strong></td>
                        <td>${v.address}</td>
                        <td style="color: ${affinityColor}; font-weight: 600;">${affinityText}</td>
                        <td>${v.last_voted}</td>
                        <td>${v.voting_score}/10</td>
                        <td>${v.age || 'N/A'}</td>
                    </tr>`;
            });
            
            html += '</tbody></table></div></div>';
        }
        
        document.getElementById('reportContent').innerHTML = html;
        
        // Add toggle handlers for precinct headers
        document.querySelectorAll('.precinct-header').forEach(header => {
            header.addEventListener('click', function(e) {
                // Don't toggle if clicking the "View on Map" button
                if (e.target.closest('.btn-view-on-map')) return;
                
                const container = this.nextElementSibling;
                const toggle = this.querySelector('.precinct-toggle');
                
                if (container.style.display === 'none') {
                    container.style.display = 'block';
                    toggle.classList.remove('fa-chevron-right');
                    toggle.classList.add('fa-chevron-down');
                } else {
                    container.style.display = 'none';
                    toggle.classList.remove('fa-chevron-down');
                    toggle.classList.add('fa-chevron-right');
                }
            });
        });
        
        // Add click handlers for "View on Map" buttons
        document.querySelectorAll('.btn-view-on-map').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation(); // Prevent precinct toggle
                const precinctName = this.dataset.precinct;
                showPrecinctOnMap(precinctName, byPrecinct[precinctName].voters);
            });
        });
    }
    
    function showPrecinctOnMap(precinctName, voters) {
        // Close the reports modal
        closeReportsModal();
        
        // Filter voters with valid coordinates
        const validVoters = voters.filter(v => v.lat && v.lng);
        
        if (validVoters.length === 0) {
            alert('No geocoded addresses found for this precinct');
            return;
        }
        
        // Enter Turf Cut Mode
        enterTurfCutMode(precinctName, validVoters);
    }
    
    function enterTurfCutMode(precinctName, voters) {
        // Hide all UI elements
        document.querySelectorAll('.panel-icon-btn, .dataset-stats-box, .info-strip, .overlay-image').forEach(el => {
            el.style.display = 'none';
        });
        
        // Store original state
        window.turfCutModeActive = true;
        window.turfCutData = { precinctName, voters };
        
        // Create Turf Cut Mode overlay
        const overlay = document.createElement('div');
        overlay.id = 'turfCutModeOverlay';
        overlay.className = 'turf-cut-mode-overlay';
        overlay.innerHTML = `
            <div class="turf-cut-controls">
                <button class="btn-exit-turf-cut" onclick="exitTurfCutMode()">
                    <i class="fas fa-times"></i> Exit Turf Cut Mode
                </button>
                <button class="btn-generate-pdf" onclick="generateTurfCutPDF()">
                    <i class="fas fa-file-pdf"></i> Generate PDF
                </button>
            </div>
        `;
        document.body.appendChild(overlay);
        
        // Wait a moment for UI to update
        setTimeout(() => {
            // Check if map and Leaflet are available
            if (typeof map === 'undefined' || typeof L === 'undefined') {
                alert('Map is not available. Please refresh the page.');
                exitTurfCutMode();
                return;
            }
            
            // Clear existing markers
            if (typeof markerClusterGroup !== 'undefined' && markerClusterGroup) {
                markerClusterGroup.clearLayers();
            }
            
            // Remove existing routing control if any
            if (window.routingControl) {
                try {
                    map.removeControl(window.routingControl);
                } catch (e) {
                    console.log('Could not remove routing control:', e);
                }
                window.routingControl = null;
            }
            
            // Remove existing route line if any
            if (window.routeLine) {
                try {
                    map.removeLayer(window.routeLine);
                } catch (e) {
                    console.log('Could not remove route line:', e);
                }
                window.routeLine = null;
            }
            
            // Remove existing route segments if any
            if (window.routeSegments && window.routeSegments.length > 0) {
                window.routeSegments.forEach(segment => {
                    try {
                        map.removeLayer(segment);
                    } catch (e) {
                        console.log('Could not remove route segment:', e);
                    }
                });
                window.routeSegments = [];
            }
            
            // Remove existing route decorator if any
            if (window.routeDecorator) {
                try {
                    map.removeLayer(window.routeDecorator);
                } catch (e) {
                    console.log('Could not remove route decorator:', e);
                }
                window.routeDecorator = null;
            }
            
            // Remove existing canvassing markers if any
            if (window.canvassingMarkers && window.canvassingMarkers.length > 0) {
                window.canvassingMarkers.forEach(marker => {
                    try {
                        map.removeLayer(marker);
                    } catch (e) {
                        console.log('Could not remove marker:', e);
                    }
                });
            }
            
            // Optimize route using nearest neighbor algorithm
            const optimizedRoute = optimizeRoute(voters);
            
            // Store markers for click handling
            window.canvassingMarkers = [];
            
            // Add numbered markers for each stop
            optimizedRoute.forEach((stop, idx) => {
                // Create numbered marker
                const numberIcon = L.divIcon({
                    html: `<div style="background: #FFD700; color: #000; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; border: 3px solid #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.3);">${idx + 1}</div>`,
                    className: 'numbered-marker',
                    iconSize: [32, 32],
                    iconAnchor: [16, 16]
                });
                
                // Build popup content with all voters at this address
                let popupContent = `<strong>Stop ${idx + 1}</strong><br>${stop.address}<br><br>`;
                stop.voters.forEach((v, vIdx) => {
                    popupContent += `<strong>${v.name}</strong><br>`;
                    popupContent += `<span style="color: #666;">Party: ${v.party_affinity}</span>`;
                    if (v.age) popupContent += ` | Age: ${v.age}`;
                    if (vIdx < stop.voters.length - 1) popupContent += '<br><br>';
                });
                
                const marker = L.marker([stop.lat, stop.lng], { icon: numberIcon })
                    .bindPopup(popupContent)
                    .addTo(map);
                
                window.canvassingMarkers.push(marker);
            });
            
            console.log(`Created ${window.canvassingMarkers.length} markers for canvassing route`);
            
            // Create street-based routing segment by segment
            // This allows the route to change direction at each stop
            console.log(`Creating route with ${optimizedRoute.length} waypoints`);
            
            // Store all route segments
            window.routeSegments = [];
            let totalDistance = 0;
            let totalTime = 0;
            let segmentsCompleted = 0;
            
            // Function to fetch route segment between two stops
            const fetchSegment = async (fromStop, toStop, segmentIndex) => {
                const coords = `${fromStop.lng},${fromStop.lat};${toStop.lng},${toStop.lat}`;
                
                try {
                    const response = await fetch(`https://router.project-osrm.org/route/v1/walking/${coords}?overview=full&geometries=geojson`);
                    const data = await response.json();
                    
                    if (data.code === 'Ok' && data.routes && data.routes.length > 0) {
                        const route = data.routes[0];
                        const routeCoordinates = route.geometry.coordinates.map(c => [c[1], c[0]]);
                        
                        return {
                            coordinates: routeCoordinates,
                            distance: route.distance / 1609.34, // meters to miles
                            duration: route.duration / 60 // seconds to minutes
                        };
                    }
                } catch (error) {
                    console.error(`Error fetching segment ${segmentIndex}:`, error);
                }
                
                // Fallback to straight line
                return {
                    coordinates: [[fromStop.lat, fromStop.lng], [toStop.lat, toStop.lng]],
                    distance: getDistance(fromStop.lat, fromStop.lng, toStop.lat, toStop.lng),
                    duration: getDistance(fromStop.lat, fromStop.lng, toStop.lat, toStop.lng) * 20
                };
            };
            
            // Fetch all segments
            const segmentPromises = [];
            for (let i = 0; i < optimizedRoute.length - 1; i++) {
                segmentPromises.push(fetchSegment(optimizedRoute[i], optimizedRoute[i + 1], i));
            }
            
            // Wait for all segments and draw them
            Promise.all(segmentPromises).then(segments => {
                // Combine all coordinates
                let allCoordinates = [];
                segments.forEach((segment, idx) => {
                    totalDistance += segment.distance;
                    totalTime += segment.duration;
                    
                    // Draw each segment
                    const segmentLine = L.polyline(segment.coordinates, {
                        color: '#667eea',
                        weight: 4,
                        opacity: 0.7
                    }).addTo(map);
                    
                    window.routeSegments.push(segmentLine);
                    allCoordinates = allCoordinates.concat(segment.coordinates);
                });
                
                // Add arrow decorators to show direction
                if (typeof L.polylineDecorator !== 'undefined' && allCoordinates.length > 0) {
                    window.routeDecorator = L.polylineDecorator(allCoordinates, {
                        patterns: [
                            {
                                offset: 25,
                                repeat: 75,
                                symbol: L.Symbol.arrowHead({
                                    pixelSize: 12,
                                    polygon: false,
                                    pathOptions: {
                                        stroke: true,
                                        weight: 3,
                                        color: '#667eea',
                                        opacity: 0.8
                                    }
                                })
                            }
                        ]
                    }).addTo(map);
                }
                
                // Fit map to show all markers
                const group = L.featureGroup(window.canvassingMarkers);
                map.fitBounds(group.getBounds().pad(0.1));
                
                // Create walk list panel
                createWalkListPanel(precinctName, optimizedRoute, totalDistance, Math.ceil(totalTime));
            }).catch(error => {
                console.error('Error creating route:', error);
                
                // Fallback to simple polyline
                const routeCoords = optimizedRoute.map(stop => [stop.lat, stop.lng]);
                window.routeLine = L.polyline(routeCoords, {
                    color: '#667eea',
                    weight: 4,
                    opacity: 0.7
                }).addTo(map);
                
                const fallbackDistance = calculateRouteDistance(optimizedRoute);
                const fallbackTime = Math.ceil(fallbackDistance * 20);
                
                const group = L.featureGroup(window.canvassingMarkers);
                map.fitBounds(group.getBounds().pad(0.1));
                
                createWalkListPanel(precinctName, optimizedRoute, fallbackDistance, fallbackTime);
            });
        }, 300);
    }
    
    // Global function to exit Turf Cut Mode
    window.exitTurfCutMode = function() {
        // Remove overlay
        const overlay = document.getElementById('turfCutModeOverlay');
        if (overlay) overlay.remove();
        
        // Remove walk list panel
        const walkList = document.getElementById('walkListPanel');
        if (walkList) walkList.remove();
        
        // Clear markers and routes
        if (window.canvassingMarkers && window.canvassingMarkers.length > 0) {
            window.canvassingMarkers.forEach(marker => {
                try {
                    map.removeLayer(marker);
                } catch (e) {}
            });
            window.canvassingMarkers = [];
        }
        
        if (window.routingControl) {
            try {
                map.removeControl(window.routingControl);
            } catch (e) {}
            window.routingControl = null;
        }
        
        if (window.routeLine) {
            try {
                map.removeLayer(window.routeLine);
            } catch (e) {}
            window.routeLine = null;
        }
        
        if (window.routeSegments && window.routeSegments.length > 0) {
            window.routeSegments.forEach(segment => {
                try {
                    map.removeLayer(segment);
                } catch (e) {}
            });
            window.routeSegments = [];
        }
        
        if (window.routeDecorator) {
            try {
                map.removeLayer(window.routeDecorator);
            } catch (e) {}
            window.routeDecorator = null;
        }
        
        // Restore UI elements
        document.querySelectorAll('.panel-icon-btn, .dataset-stats-box, .info-strip, .overlay-image').forEach(el => {
            el.style.display = '';
        });
        
        window.turfCutModeActive = false;
        window.turfCutData = null;
    };
    
    // Global function to generate PDF
    window.generateTurfCutPDF = async function() {
        if (!window.turfCutData) {
            alert('No turf cut data available');
            return;
        }
        
        // Show loading indicator
        const pdfBtn = document.querySelector('.btn-generate-pdf');
        const originalHTML = pdfBtn.innerHTML;
        pdfBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        pdfBtn.disabled = true;
        
        try {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF('landscape', 'mm', 'letter'); // Landscape for side-by-side layout
            
            const pageWidth = doc.internal.pageSize.getWidth();
            const pageHeight = doc.internal.pageSize.getHeight();
            
            // Add Politiquera logo at top left
            const logoImg = document.querySelector('.overlay-image');
            if (logoImg) {
                try {
                    // Create a canvas to load the logo
                    const logoCanvas = document.createElement('canvas');
                    const logoCtx = logoCanvas.getContext('2d');
                    const img = new Image();
                    img.crossOrigin = 'anonymous';
                    
                    await new Promise((resolve, reject) => {
                        img.onload = () => {
                            // Set canvas to maintain aspect ratio
                            const aspectRatio = img.width / img.height;
                            const logoHeight = 15;
                            const logoWidth = logoHeight * aspectRatio;
                            
                            logoCanvas.width = img.width;
                            logoCanvas.height = img.height;
                            logoCtx.drawImage(img, 0, 0);
                            resolve({ width: logoWidth, height: logoHeight });
                        };
                        img.onerror = reject;
                        img.src = 'assets/politiquera.png';
                    }).then(dimensions => {
                        const logoData = logoCanvas.toDataURL('image/png');
                        doc.addImage(logoData, 'PNG', 10, 5, dimensions.width, dimensions.height);
                    });
                } catch (e) {
                    console.log('Could not load logo:', e);
                }
            }
            
            // Title at top center
            doc.setFontSize(18);
            doc.setFont(undefined, 'bold');
            doc.text(`Walk List - Precinct ${window.turfCutData.precinctName}`, pageWidth / 2, 15, { align: 'center' });
            
            // Temporarily zoom map to fit route with small padding before capturing
            const originalZoom = map.getZoom();
            const originalCenter = map.getCenter();
            
            if (window.canvassingMarkers && window.canvassingMarkers.length > 0) {
                const group = L.featureGroup(window.canvassingMarkers);
                map.fitBounds(group.getBounds().pad(0.05)); // 5% padding
            }
            
            // Wait for map to render at new zoom
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Capture map screenshot
            const mapElement = document.getElementById('map');
            const mapCanvas = await html2canvas(mapElement, {
                useCORS: true,
                allowTaint: true,
                backgroundColor: '#ffffff',
                scale: 2
            });
            
            // Restore original map view
            map.setView(originalCenter, originalZoom);
            
            const mapImgData = mapCanvas.toDataURL('image/png');
            
            // Calculate proper aspect ratio for map
            const mapWidth = (pageWidth / 2) - 15;
            const mapAspectRatio = mapCanvas.width / mapCanvas.height;
            const mapHeight = mapWidth / mapAspectRatio;
            
            // Ensure map doesn't exceed page height
            const maxMapHeight = pageHeight - 40;
            const finalMapHeight = Math.min(mapHeight, maxMapHeight);
            const finalMapWidth = finalMapHeight * mapAspectRatio;
            
            // Center the map vertically if it's shorter than max height
            const mapY = 30 + (maxMapHeight - finalMapHeight) / 2;
            
            doc.addImage(mapImgData, 'PNG', 10, mapY, finalMapWidth, finalMapHeight);
            
            // Get walk list data
            const route = window.canvassingMarkers.map((marker, idx) => {
                const stop = document.querySelectorAll('.walk-list-item')[idx];
                return {
                    number: idx + 1,
                    address: stop.querySelector('.walk-list-address').textContent,
                    voters: Array.from(stop.querySelectorAll('.walk-list-voter')).map(v => ({
                        name: v.querySelector('.walk-list-name').textContent,
                        party: v.querySelector('.walk-list-party').textContent,
                        age: v.querySelector('.walk-list-age')?.textContent || '',
                        score: v.querySelector('.walk-list-score')?.textContent || '',
                        history: v.querySelector('.walk-list-history')?.textContent || '',
                        lastVoted: v.querySelector('.walk-list-last-voted')?.textContent || ''
                    }))
                };
            });
            
            // Summary stats at top right
            const summaryX = (pageWidth / 2) + 10;
            doc.setFontSize(10);
            doc.setFont(undefined, 'normal');
            
            const stats = document.querySelector('.walk-list-summary');
            const stops = stats.children[0].querySelector('strong').textContent;
            const voters = stats.children[1].querySelector('strong').textContent;
            const miles = stats.children[2].querySelector('strong').textContent;
            const mins = stats.children[3].querySelector('strong').textContent;
            
            doc.text(`${stops} stops  |  ${voters} voters  |  ${miles} mi  |  ${mins} min`, summaryX, 25);
            
            // Walk list on right half
            let yPos = 35;
            const listX = summaryX;
            const listWidth = (pageWidth / 2) - 20;
            
            doc.setFontSize(9);
            
            route.forEach((stop, idx) => {
                // Check if we need a new page
                if (yPos > pageHeight - 30) {
                    doc.addPage();
                    yPos = 20;
                }
                
                // Stop number and address
                doc.setFont(undefined, 'bold');
                doc.setFillColor(255, 215, 0); // Gold
                doc.circle(listX + 5, yPos - 2, 5, 'F');
                doc.setTextColor(0, 0, 0);
                doc.text(stop.number.toString(), listX + 5, yPos + 1, { align: 'center' });
                
                doc.setTextColor(80, 80, 80);
                doc.setFontSize(9);
                const addressLines = doc.splitTextToSize(stop.address, listWidth - 15);
                doc.text(addressLines, listX + 12, yPos);
                yPos += addressLines.length * 4 + 2;
                
                // Voters at this address
                doc.setFontSize(8);
                stop.voters.forEach(voter => {
                    if (yPos > pageHeight - 20) {
                        doc.addPage();
                        yPos = 20;
                    }
                    
                    // Party color bar
                    if (voter.party.includes('Democratic')) {
                        doc.setDrawColor(0, 100, 255);
                    } else if (voter.party.includes('Republican')) {
                        doc.setDrawColor(230, 0, 60);
                    } else {
                        doc.setDrawColor(102, 102, 102);
                    }
                    doc.setLineWidth(1);
                    doc.line(listX + 12, yPos - 3, listX + 12, yPos + 3);
                    
                    // Voter name
                    doc.setFont(undefined, 'normal');
                    doc.setTextColor(51, 51, 51);
                    doc.text(voter.name, listX + 15, yPos);
                    yPos += 4;
                    
                    // Voter details
                    doc.setFont(undefined, 'normal');
                    doc.setTextColor(102, 102, 102);
                    doc.setFontSize(7);
                    let details = `${voter.party}  |  ${voter.age}  |  ${voter.score}`;
                    if (voter.history) details += `  |  ${voter.history}`;
                    if (voter.lastVoted) details += `  |  ${voter.lastVoted}`;
                    doc.text(details, listX + 15, yPos);
                    yPos += 4;
                });
                
                yPos += 3; // Space between stops
            });
            
            // Footer
            doc.setFontSize(8);
            doc.setTextColor(150, 150, 150);
            doc.text(`Generated ${new Date().toLocaleDateString()} at ${new Date().toLocaleTimeString()}`, pageWidth / 2, pageHeight - 5, { align: 'center' });
            
            // Save PDF
            const fileName = `turf-cut-precinct-${window.turfCutData.precinctName}-${new Date().toISOString().split('T')[0]}.pdf`;
            doc.save(fileName);
            
        } catch (error) {
            console.error('Error generating PDF:', error);
            alert('Error generating PDF. Please try again.');
        } finally {
            // Restore button
            pdfBtn.innerHTML = originalHTML;
            pdfBtn.disabled = false;
        }
    };
    
    // Create walk list panel
    function createWalkListPanel(precinctName, route, totalDistance, totalTime) {
        // Remove existing panel if any
        const existing = document.getElementById('walkListPanel');
        if (existing) existing.remove();
        
        // Determine position based on mode
        const topPosition = window.turfCutModeActive ? '120px' : '20px';
        
        // Count total voters
        const totalVoters = route.reduce((sum, stop) => sum + stop.voters.length, 0);
        
        // Create panel
        const panel = document.createElement('div');
        panel.id = 'walkListPanel';
        panel.className = 'walk-list-panel';
        panel.style.top = topPosition;
        panel.innerHTML = `
            <div class="walk-list-header">
                <h3><i class="fas fa-route"></i> Walk List - Precinct ${precinctName}</h3>
                <div class="walk-list-actions">
                    <button class="btn-print-walk-list" onclick="printWalkList()">
                        <i class="fas fa-print"></i> Print
                    </button>
                    ${!window.turfCutModeActive ? '<button class="btn-close-walk-list" onclick="closeWalkList()"><i class="fas fa-times"></i></button>' : ''}
                </div>
            </div>
            <div class="walk-list-summary">
                <div><strong>${route.length}</strong> stops</div>
                <div><strong>${totalVoters}</strong> voters</div>
                <div><strong>${totalDistance.toFixed(2)}</strong> mi</div>
                <div><strong>${totalTime}</strong> min</div>
            </div>
            <div class="walk-list-content">
                ${route.map((stop, idx) => {
                    // Get party affinity for the stop (use first voter's or determine majority)
                    const partyColors = stop.voters.map(v => {
                        if (v.party_affinity === 'Democratic') return '#0064FF';
                        if (v.party_affinity === 'Republican') return '#E6003C';
                        return '#666';
                    });
                    const primaryColor = partyColors[0];
                    
                    return `
                    <div class="walk-list-item" data-stop="${idx}">
                        <div class="walk-list-number">${idx + 1}</div>
                        <div class="walk-list-details">
                            <div class="walk-list-address" style="font-weight: 600; margin-bottom: 6px;">${stop.address}</div>
                            ${stop.voters.map(v => `
                                <div class="walk-list-voter" style="margin-bottom: 4px; padding-left: 8px; border-left: 3px solid ${
                                    v.party_affinity === 'Democratic' ? '#0064FF' : 
                                    v.party_affinity === 'Republican' ? '#E6003C' : '#666'
                                };">
                                    <div class="walk-list-name" style="font-size: 13px; color: #333;">${v.name}</div>
                                    <div class="walk-list-meta" style="display: flex; gap: 8px; font-size: 11px; margin-top: 2px;">
                                        <span class="walk-list-party" style="color: ${
                                            v.party_affinity === 'Democratic' ? '#0064FF' : 
                                            v.party_affinity === 'Republican' ? '#E6003C' : '#666'
                                        };">${v.party_affinity}</span>
                                        ${v.age ? `<span class="walk-list-age">Age ${v.age}</span>` : ''}
                                        <span class="walk-list-score">Score: ${v.voting_score}/10</span>
                                        ${v.dem_history || v.rep_history ? `<span class="walk-list-history" style="color: #999;">History: ${v.dem_history || 0}D/${v.rep_history || 0}R</span>` : ''}
                                        ${v.last_voted && v.last_voted !== 'Never' ? `<span class="walk-list-last-voted" style="color: #999;">Last: ${v.last_voted}</span>` : ''}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
                }).join('')}
            </div>
        `;
        
        document.body.appendChild(panel);
        
        // Add click handlers to highlight markers
        document.querySelectorAll('.walk-list-item').forEach(item => {
            item.addEventListener('click', function() {
                const stopIdx = parseInt(this.dataset.stop);
                
                // Pan to marker and open popup
                if (window.canvassingMarkers && window.canvassingMarkers[stopIdx]) {
                    const marker = window.canvassingMarkers[stopIdx];
                    map.setView(marker.getLatLng(), 18);
                    marker.openPopup();
                }
                
                // Highlight this item
                document.querySelectorAll('.walk-list-item').forEach(i => i.classList.remove('active'));
                this.classList.add('active');
            });
        });
    }
    
    // Global functions for walk list
    window.printWalkList = function() {
        window.print();
    };
    
    window.closeWalkList = function() {
        const panel = document.getElementById('walkListPanel');
        if (panel) panel.remove();
    };
    
    // Optimize route using nearest neighbor algorithm
    function optimizeRoute(voters) {
        if (voters.length <= 1) return voters;
        
        // First, group voters by address
        const addressGroups = {};
        voters.forEach(v => {
            const key = `${v.lat.toFixed(6)},${v.lng.toFixed(6)}`; // Group by coordinates
            if (!addressGroups[key]) {
                addressGroups[key] = {
                    lat: v.lat,
                    lng: v.lng,
                    address: v.address,
                    voters: []
                };
            }
            addressGroups[key].voters.push(v);
        });
        
        // Convert to array of stops
        const stops = Object.values(addressGroups);
        
        if (stops.length <= 1) return stops;
        
        const unvisited = [...stops];
        const route = [];
        
        // Start with the first stop
        let current = unvisited.shift();
        route.push(current);
        
        // Visit nearest unvisited stop each time
        while (unvisited.length > 0) {
            let nearestIndex = 0;
            let nearestDistance = Infinity;
            
            for (let i = 0; i < unvisited.length; i++) {
                const distance = getDistance(
                    current.lat, current.lng,
                    unvisited[i].lat, unvisited[i].lng
                );
                
                if (distance < nearestDistance) {
                    nearestDistance = distance;
                    nearestIndex = i;
                }
            }
            
            current = unvisited.splice(nearestIndex, 1)[0];
            route.push(current);
        }
        
        return route;
    }
    
    // Calculate distance between two points (Haversine formula)
    function getDistance(lat1, lon1, lat2, lon2) {
        const R = 3959; // Earth's radius in miles
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }
    
    // Calculate total route distance
    function calculateRouteDistance(route) {
        let total = 0;
        for (let i = 0; i < route.length - 1; i++) {
            total += getDistance(
                route[i].lat, route[i].lng,
                route[i + 1].lat, route[i + 1].lng
            );
        }
        return total;
    }
    
    async function loadNewVoters() {
        const county = selectedCountyFilter || 'Hidalgo';
        const electionDate = currentDataset?.election_date || '2026-03-03';
        
        // Add filters
        document.getElementById('reportFilters').innerHTML = `
            <div class="report-filter-group">
                <label>Party</label>
                <select id="newVoterParty">
                    <option value="both">Both Parties</option>
                    <option value="Democratic">Democratic</option>
                    <option value="Republican">Republican</option>
                </select>
            </div>
        `;
        
        document.getElementById('newVoterParty')?.addEventListener('change', () => loadNewVoters());
        const party = document.getElementById('newVoterParty')?.value || 'both';
        
        const response = await fetch(`/api/reports/new-voters?county=${encodeURIComponent(county)}&election_date=${encodeURIComponent(electionDate)}&party=${party}`);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load report');
        }
        
        currentReportData = data.new_voters;
        
        let html = `
            <div class="report-summary">
                <div class="report-summary-item">
                    <div class="label">Total New Voters</div>
                    <div class="value">${data.new_voters.length}</div>
                </div>
                <div class="report-summary-item">
                    <div class="label">Democratic</div>
                    <div class="value" style="color: #0064FF;">${data.dem_count || 0}</div>
                </div>
                <div class="report-summary-item">
                    <div class="label">Republican</div>
                    <div class="value" style="color: #E6003C;">${data.rep_count || 0}</div>
                </div>
            </div>
            <table class="report-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Address</th>
                        <th>Precinct</th>
                        <th>Party</th>
                        <th>Age</th>
                        <th>Registered</th>
                    </tr>
                </thead>
                <tbody>`;
        
        data.new_voters.forEach(v => {
            const partyColor = v.party === 'Democratic' ? '#0064FF' : '#E6003C';
            html += `
                <tr>
                    <td><strong>${v.name}</strong></td>
                    <td>${v.address}</td>
                    <td>${v.precinct || 'N/A'}</td>
                    <td style="color: ${partyColor};">${v.party}</td>
                    <td>${v.age || 'N/A'}</td>
                    <td>${v.registration_date || 'N/A'}</td>
                </tr>`;
        });
        
        html += '</tbody></table>';
        document.getElementById('reportContent').innerHTML = html;
    }
    
    function exportCurrentReport() {
        if (!currentReportData || !currentReportData.length) {
            alert('No data to export');
            return;
        }
        
        // Convert to CSV
        const headers = Object.keys(currentReportData[0]);
        let csv = headers.join(',') + '\n';
        
        currentReportData.forEach(row => {
            const values = headers.map(header => {
                const value = row[header] || '';
                // Escape commas and quotes
                return typeof value === 'string' && (value.includes(',') || value.includes('"')) 
                    ? `"${value.replace(/"/g, '""')}"` 
                    : value;
            });
            csv += values.join(',') + '\n';
        });
        
        // Download
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${currentReport}_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initReports);
    } else {
        initReports();
    }
})();

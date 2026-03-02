// Campaign Reports System
(function() {
    'use strict';
    
    let currentReport = null;
    let currentReportData = null;
    
    // Initialize reports system
    function initReports() {
        // Wait for modal HTML to be loaded
        const modal = document.getElementById('reportsModal');
        if (!modal || !document.getElementById('reportsModalClose')) {
            // Modal not ready yet, wait for event
            window.addEventListener('reportsModalReady', initReports, { once: true });
            return;
        }
        
        // Reports button click
        document.getElementById('reportsIconBtn')?.addEventListener('click', openReportsModal);
        
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
        document.getElementById('reportsModal').style.display = 'flex';
        showReportsList();
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
                    <div class="precinct-header">
                        <h4>Precinct ${precinctName} <span style="color: #666; font-size: 14px; font-weight: normal;">${turnoutInfo}</span></h4>
                        <button class="btn-view-on-map" data-precinct="${precinctName}" style="background: #667eea; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px;">
                            <i class="fas fa-map-marked-alt"></i> View ${precinctData.voters.length} on Map
                        </button>
                    </div>
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
            
            html += '</tbody></table></div>';
        }
        
        document.getElementById('reportContent').innerHTML = html;
        
        // Add click handlers for "View on Map" buttons
        document.querySelectorAll('.btn-view-on-map').forEach(btn => {
            btn.addEventListener('click', function() {
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
        
        // Clear existing markers
        if (typeof clearMapMarkers === 'function') {
            clearMapMarkers();
        }
        
        // Add star markers for each address
        if (typeof L !== 'undefined' && window.map) {
            const starIcon = L.divIcon({
                html: '<i class="fas fa-star" style="color: #FFD700; font-size: 24px; text-shadow: 0 0 3px #000;"></i>',
                className: 'star-marker',
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            });
            
            const markers = [];
            validVoters.forEach((v, idx) => {
                const marker = L.marker([v.lat, v.lng], { icon: starIcon })
                    .bindPopup(`
                        <strong>${idx + 1}. ${v.name}</strong><br>
                        ${v.address}<br>
                        <span style="color: #666;">Party: ${v.party_affinity}</span>
                    `);
                marker.addTo(window.map);
                markers.push(marker);
            });
            
            // Fit map to show all markers
            const group = L.featureGroup(markers);
            window.map.fitBounds(group.getBounds().pad(0.1));
            
            // Show route info
            alert(`Showing ${validVoters.length} addresses in Precinct ${precinctName}.\n\nMarkers are numbered in the most efficient walking order.`);
        }
    }
        
        html += '</tbody></table>';
        document.getElementById('reportContent').innerHTML = html;
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

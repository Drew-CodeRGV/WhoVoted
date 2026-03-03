/* County Report — mini-gazette for specific county data */

(function () {
    // Initialize county report button
    window.initCountyReport = function() {
        console.log('initCountyReport called');
        
        // Add button to dataset info inline section
        const infoDiv = document.querySelector('.dataset-info-inline');
        console.log('Found dataset-info-inline:', infoDiv);
        
        if (!infoDiv) return;
        
        // Check if button already exists
        if (document.getElementById('countyReportBtn')) {
            console.log('County report button already exists');
            return;
        }
        
        const btn = document.createElement('button');
        btn.id = 'countyReportBtn';
        btn.className = 'county-report-btn';
        btn.innerHTML = '<i class="fas fa-file-alt"></i> County Report';
        btn.style.cssText = 'padding: 4px 10px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 600; margin-top: 8px; display: inline-flex; align-items: center; gap: 5px;';
        btn.title = 'View detailed report for this county';
        
        btn.addEventListener('click', openCountyReport);
        infoDiv.appendChild(btn);
        
        console.log('County report button created and added');
    };
    
    window.openCountyReport = async function() {
        console.log('openCountyReport called');
        
        // Get current county from global filter
        const county = typeof selectedCountyFilter !== 'undefined' ? selectedCountyFilter : '';
        
        console.log('Current county:', county);
        
        if (!county || county === 'all') {
            alert('Please select a specific county to view its report.');
            return;
        }
        
        // Get election date from current dataset - try multiple sources
        let electionDate = null;
        let votingMethod = null;
        
        // Try datasetSelector first
        if (window.datasetSelector) {
            const currentDataset = window.datasetSelector.getCurrentDataset();
            if (currentDataset) {
                electionDate = currentDataset.electionDate;
                votingMethod = currentDataset.votingMethod || '';
            }
        }
        
        // Fallback: try to get from availableDatasets and current selection
        if (!electionDate && typeof availableDatasets !== 'undefined' && availableDatasets.length > 0) {
            const datasetSelect = document.getElementById('dataset-selector') || document.getElementById('dataset-selector-inline');
            if (datasetSelect && datasetSelect.value !== '') {
                const idx = parseInt(datasetSelect.value, 10);
                if (!isNaN(idx) && availableDatasets[idx]) {
                    electionDate = availableDatasets[idx].electionDate;
                    votingMethod = availableDatasets[idx].votingMethod || '';
                }
            }
        }
        
        // Last resort: use most recent election from availableDatasets
        if (!electionDate && typeof availableDatasets !== 'undefined' && availableDatasets.length > 0) {
            electionDate = availableDatasets[0].electionDate;
            votingMethod = availableDatasets[0].votingMethod || '';
        }
        
        if (!electionDate) {
            alert('Could not determine election date. Please try refreshing the page.');
            return;
        }
        
        // Show overlay
        let overlay = document.getElementById('countyReportOverlay');
        if (!overlay) {
            createCountyReportOverlay();
            overlay = document.getElementById('countyReportOverlay');
        }
        
        const body = document.getElementById('countyReportBody');
        overlay.style.display = 'flex';
        
        body.innerHTML = '<p class="county-report-loading">Loading county data&hellip;</p>';
        
        try {
            const params = new URLSearchParams({
                county: county,
                election_date: electionDate,
            });
            if (votingMethod) {
                params.append('voting_method', votingMethod);
            }
            
            const resp = await fetch(`/api/county-report?${params}`);
            if (!resp.ok) throw new Error('API error');
            const data = await resp.json();
            
            body.innerHTML = buildCountyReport(data);
            
            // Wire up collapsible sections
            body.querySelectorAll('.cr-section-title').forEach(title => {
                title.addEventListener('click', () => {
                    title.closest('.cr-section').classList.toggle('collapsed');
                });
            });
            
        } catch (e) {
            console.error('County report error:', e);
            body.innerHTML = '<p style="text-align:center;color:#C62828;padding:40px 0;">Could not load county data.</p>';
        }
    };
    
    function createCountyReportOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'countyReportOverlay';
        overlay.className = 'newspaper-overlay';
        overlay.style.display = 'none';
        
        overlay.innerHTML = `
            <div class="newspaper-content county-report-content">
                <button class="newspaper-close" onclick="closeCountyReport()">&times;</button>
                <div class="gazette-inner">
                    <div class="gazette-header">
                        <h1 class="gazette-title">County Report</h1>
                        <div class="gazette-subtitle" id="countyReportSubtitle"></div>
                    </div>
                    <div id="countyReportBody" class="gazette-body"></div>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
    }
    
    window.closeCountyReport = function() {
        const overlay = document.getElementById('countyReportOverlay');
        if (overlay) overlay.style.display = 'none';
    };
    
    function f(v) { return Number(v || 0).toLocaleString(); }
    function pct(a, b) { return b ? Math.round(a / b * 100) : 0; }
    
    function buildCountyReport(d) {
        // Update subtitle
        const subtitle = document.getElementById('countyReportSubtitle');
        if (subtitle) {
            const votingLabel = d.voting_method === 'early-voting' ? 'Early Voting' : 
                               d.voting_method === 'election-day' ? 'Election Day' : 'All Voting';
            subtitle.textContent = `${d.county} County · ${d.election_date} · ${votingLabel}`;
        }
        
        const demPct = d.dem_share;
        const repPct = (100 - demPct).toFixed(1);
        const netFlip = d.r2d - d.d2r;
        const netLabel = netFlip > 0 ? 'net D' : netFlip < 0 ? 'net R' : 'even';
        const ratio = d.rep_count ? (d.dem_count / d.rep_count).toFixed(1) : '—';
        const newDemPct = d.new_dem_pct;
        const fPct = d.female_pct;
        
        let html = '';
        
        // ── Top KPIs ──
        html += `
<div class="gz-kpi-row">
    <div class="gz-kpi neutral">
        <div class="gz-kpi-value">${f(d.total_voters)}</div>
        <div class="gz-kpi-label">Total Voters</div>
    </div>
    <div class="gz-kpi dem">
        <div class="gz-kpi-value">${demPct}%</div>
        <div class="gz-kpi-label">Democratic</div>
    </div>
    <div class="gz-kpi rep">
        <div class="gz-kpi-value">${repPct}%</div>
        <div class="gz-kpi-label">Republican</div>
    </div>
</div>`;
        
        // ── Party Breakdown ──
        html += `
<div class="cr-section">
    <div class="cr-section-title">Party Breakdown</div>
    <div class="cr-section-body">
        <div class="gz-bar-labels">
            <span class="gz-dem">${f(d.dem_count)} Dem</span>
            <span class="gz-rep">${f(d.rep_count)} Rep</span>
        </div>
        <div class="gz-bar">
            <div class="gz-bar-dem" style="width:${demPct}%"></div>
            <div class="gz-bar-rep" style="width:${repPct}%"></div>
        </div>
        <p class="gz-text">Democrats lead <span class="gz-dem gz-big">${ratio}</span>-to-1 in ${d.county} County.</p>
    </div>
</div>`;
        
        // ── Party Switchers ──
        if (d.r2d > 0 || d.d2r > 0) {
            html += `
<div class="cr-section">
    <div class="cr-section-title">Party Switchers</div>
    <div class="cr-section-body">
        <div class="gz-kpi-row">
            <div class="gz-kpi dem">
                <div class="gz-kpi-value">${f(d.r2d)}</div>
                <div class="gz-kpi-label">R → D</div>
            </div>
            <div class="gz-kpi rep">
                <div class="gz-kpi-value">${f(d.d2r)}</div>
                <div class="gz-kpi-label">D → R</div>
            </div>
            <div class="gz-kpi ${netFlip > 0 ? 'dem' : netFlip < 0 ? 'rep' : 'neutral'}">
                <div class="gz-kpi-value">${Math.abs(netFlip)}</div>
                <div class="gz-kpi-label">${netLabel}</div>
            </div>
        </div>
    </div>
</div>`;
        }
        
        // ── New Voters ──
        if (d.new_voters > 0) {
            html += `
<div class="cr-section">
    <div class="cr-section-title gold">★ New Voters</div>
    <div class="cr-section-body">
        <div class="gz-kpi-row">
            <div class="gz-kpi gold">
                <div class="gz-kpi-value">${f(d.new_voters)}</div>
                <div class="gz-kpi-label">First-Time</div>
            </div>
            <div class="gz-kpi gold">
                <div class="gz-kpi-value">${newDemPct}%</div>
                <div class="gz-kpi-label">Chose Dem</div>
            </div>
        </div>
        <div class="gz-bar-labels">
            <span class="gz-dem">${f(d.new_dem)} Dem</span>
            <span class="gz-rep">${f(d.new_rep)} Rep</span>
        </div>
        <div class="gz-bar">
            <div class="gz-bar-dem" style="width:${newDemPct}%"></div>
            <div class="gz-bar-rep" style="width:${100 - newDemPct}%"></div>
        </div>
    </div>
</div>`;
        }
        
        // ── Gender ──
        html += `
<div class="cr-section">
    <div class="cr-section-title">Gender</div>
    <div class="cr-section-body">
        <p class="gz-text"><span class="gz-big">${f(d.female_count)}</span> women (${fPct}%) · <span class="gz-big">${f(d.male_count)}</span> men (${100 - fPct}%)</p>
    </div>
</div>`;
        
        // ── Age Table ──
        if (d.age_groups && Object.keys(d.age_groups).length > 0) {
            const order = ['18-24','25-34','35-44','45-54','55-64','65-74','75+'];
            const ag = d.age_groups;
            html += `
<div class="cr-section">
    <div class="cr-section-title">Age Breakdown</div>
    <div class="cr-section-body">
    <table class="gz-table">
        <tr><th>Age</th><th class="r">Total</th><th class="r">Dem</th><th class="r">Rep</th><th class="r">Dem %</th></tr>`;
            order.forEach(a => {
                const g = ag[a] || {total:0,dem:0,rep:0};
                const p = pct(g.dem, g.dem + g.rep);
                html += `<tr><td>${a}</td><td class="r">${f(g.total)}</td><td class="r dem-val">${f(g.dem)}</td><td class="r rep-val">${f(g.rep)}</td><td class="r">${p}%</td></tr>`;
            });
            html += `</table></div></div>`;
        }
        
        // ── Footer ──
        const updated = d.last_updated
            ? new Date(d.last_updated + 'Z').toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'})
            : 'recently';
        html += `<div class="gz-footer">Politiquera.com · ${d.county} County · Data updated ${updated}</div>`;
        
        return html;
    }
})();

/* Gazette — clean data brief with collapsible sections */

(function () {
    const btn = document.getElementById('newspaperBtn');
    if (!btn) return;

    btn.addEventListener('click', () => openNewspaper('combined'));
    window.refreshGazette = openNewspaper;

    async function openNewspaper(votingMethod = 'combined') {
        const overlay = document.getElementById('newspaperOverlay');
        const body = document.getElementById('newspaperBody');
        if (!overlay) return;

        overlay.style.display = 'flex';
        const paper = document.getElementById('newspaperContent');
        paper.style.animation = 'none';
        void paper.offsetWidth;
        paper.style.animation = '';

        body.innerHTML = '<p class="gazette-loading">Loading data&hellip;</p>';

        try {
            const resp = await fetch(`/api/election-insights?voting_method=${votingMethod}`);
            if (!resp.ok) throw new Error('API error');
            const d = await resp.json();
            body.innerHTML = buildGazette(d, votingMethod);

            // Wire up collapsible sections
            body.querySelectorAll('.gz-section-title').forEach(title => {
                title.addEventListener('click', () => {
                    title.closest('.gz-section').classList.toggle('collapsed');
                });
            });

            // Wire up voting method toggle
            body.querySelectorAll('.gz-method-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const method = btn.dataset.method;
                    openNewspaper(method);
                });
            });

            const dateEl = document.getElementById('npDate');
            if (dateEl) {
                const now = new Date();
                dateEl.textContent = now.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
            }
        } catch (e) {
            body.innerHTML = '<p style="text-align:center;color:#C62828;padding:40px 0;">Could not load election data.</p>';
        }
    }

    function f(v) { return Number(v || 0).toLocaleString(); }
    function pct(a, b) { return b ? Math.round(a / b * 100) : 0; }

    function buildGazette(d, votingMethod = 'combined') {
        const demPct = d.dem_share;
        const repPct = (100 - demPct).toFixed(1);
        const netFlip = d.r2d - d.d2r;
        const netLabel = netFlip > 0 ? 'net D' : netFlip < 0 ? 'net R' : 'even';
        const ratio = d.rep ? (d.dem / d.rep).toFixed(1) : '—';
        const fPct = pct(d.female, d.female + d.male);
        const evPct = pct(d.early_voting, d.total);
        const mailPct = pct(d.mail_in, d.total);
        const edPct = pct(d.election_day, d.total);

        let html = '';

        // ── Voting Method Toggle ──
        html += `
<div class="gz-method-toggle">
    <button class="gz-method-btn ${votingMethod === 'combined' ? 'active' : ''}" data-method="combined">
        Combined
    </button>
    <button class="gz-method-btn ${votingMethod === 'early-voting' ? 'active' : ''}" data-method="early-voting">
        Early Vote
    </button>
    <button class="gz-method-btn ${votingMethod === 'election-day' ? 'active' : ''}" data-method="election-day">
        Election Day
    </button>
</div>`;

        // ── Top KPIs (always visible, not collapsible) ──
        html += `
<div class="gz-kpi-row">
    <div class="gz-kpi neutral">
        <div class="gz-kpi-value">${f(d.total)}</div>
        <div class="gz-kpi-label">Total Votes</div>
    </div>
    <div class="gz-kpi dem">
        <div class="gz-kpi-value">${demPct}%</div>
        <div class="gz-kpi-label">Democratic</div>
    </div>
    <div class="gz-kpi rep">
        <div class="gz-kpi-value">${repPct}%</div>
        <div class="gz-kpi-label">Republican</div>
    </div>
    ${votingMethod === 'combined' ? `
    <div class="gz-kpi neutral">
        <div class="gz-kpi-value">${f(d.early_voting)}</div>
        <div class="gz-kpi-label">Early (${evPct}%)</div>
    </div>
    <div class="gz-kpi neutral">
        <div class="gz-kpi-value">${f(d.election_day)}</div>
        <div class="gz-kpi-label">Election Day (${edPct}%)</div>
    </div>` : ''}
</div>`;

        // ── Party Breakdown ──
        html += `
<div class="gz-section">
    <div class="gz-section-title">Party Breakdown</div>
    <div class="gz-section-body">
        <div class="gz-bar-labels">
            <span class="gz-dem">${f(d.dem)} Dem</span>
            <span class="gz-rep">${f(d.rep)} Rep</span>
        </div>
        <div class="gz-bar">
            <div class="gz-bar-dem" style="width:${demPct}%"></div>
            <div class="gz-bar-rep" style="width:${repPct}%"></div>
        </div>
        <p class="gz-text">Democrats lead <span class="gz-dem gz-big">${ratio}</span>-to-1 across Texas.${votingMethod === 'combined' ? ` Early: ${f(d.early_voting)} (${evPct}%) · Election Day: ${f(d.election_day)} (${edPct}%)` : (votingMethod === 'early-voting' ? ` Mail-in: ${f(d.mail_in)} (${mailPct}%)` : '')}</p>
    </div>
</div>`;

        // ── Party Switchers ──
        html += `
<div class="gz-section">
    <div class="gz-section-title">Party Switchers</div>
    <div class="gz-section-body">
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
        <p class="gz-text">Voters who switched parties from their last primary election.</p>
    </div>
</div>`;

        // ── Gender ──
        html += `
<div class="gz-section">
    <div class="gz-section-title">Gender</div>
    <div class="gz-section-body">
        <p class="gz-text"><span class="gz-big">${f(d.female)}</span> women (${fPct}%) · <span class="gz-big">${f(d.male)}</span> men (${100 - fPct}%)</p>
        <p class="gz-text">Dem: <span class="gz-dem">${f(d.dem_female)}F / ${f(d.dem_male)}M</span> · Rep: <span class="gz-rep">${f(d.rep_female)}F / ${f(d.rep_male)}M</span></p>
    </div>
</div>`;

        // ── Age Table ──
        if (d.age_groups) {
            const order = ['18-24','25-34','35-44','45-54','55-64','65-74','75+'];
            const ag = d.age_groups;
            html += `
<div class="gz-section">
    <div class="gz-section-title">Age Breakdown</div>
    <div class="gz-section-body">
    <table class="gz-table">
        <tr><th>Age</th><th class="r">Total</th><th class="r">Dem</th><th class="r">Rep</th><th class="r">Dem %</th></tr>`;
            order.forEach(a => {
                const g = ag[a] || {total:0,dem:0,rep:0};
                const p = pct(g.dem, g.dem + g.rep);
                html += `<tr><td>${a}</td><td class="r">${f(g.total)}</td><td class="r dem-val">${f(g.dem)}</td><td class="r rep-val">${f(g.rep)}</td><td class="r">${p}%</td></tr>`;
            });
            html += `</table></div></div>`;
        }

        // ── Top Counties ──
        if (d.top_counties && d.top_counties.length) {
            html += `
<div class="gz-section">
    <div class="gz-section-title">🏆 Top Counties by Turnout</div>
    <div class="gz-section-body">
    <table class="gz-table">
        <tr><th>County</th><th class="r">Total</th><th class="r">Dem</th><th class="r">Rep</th><th class="r">Dem %</th></tr>`;
            d.top_counties.forEach(c => {
                html += `<tr><td>${c.county}</td><td class="r">${f(c.total)}</td><td class="r dem-val">${f(c.dem)}</td><td class="r rep-val">${f(c.rep)}</td><td class="r">${c.dem_pct}%</td></tr>`;
            });
            html += `</table></div></div>`;
        }

        // ── Bottom Counties ──
        if (d.bottom_counties && d.bottom_counties.length) {
            html += `
<div class="gz-section">
    <div class="gz-section-title">📊 Lowest Turnout Counties</div>
    <div class="gz-section-body">
    <table class="gz-table">
        <tr><th>County</th><th class="r">Total</th><th class="r">Dem</th><th class="r">Rep</th><th class="r">Dem %</th></tr>`;
            d.bottom_counties.forEach(c => {
                html += `<tr><td>${c.county}</td><td class="r">${f(c.total)}</td><td class="r dem-val">${f(c.dem)}</td><td class="r rep-val">${f(c.rep)}</td><td class="r">${c.dem_pct}%</td></tr>`;
            });
            html += `</table></div></div>`;
        }

        // ── Footer ──
        const updated = d.generated_at
            ? new Date(d.generated_at).toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'})
            : 'during early voting';
        html += `<div class="gz-footer">Politiquera.com · Texas Secretary of State · Data updated ${updated}</div>`;

        // ── Share buttons ──
        html += `
<div class="gz-share-row">
    <button class="gz-share-btn gz-share-fb" onclick="window.gazetteShare('facebook')">
        <i class="fab fa-facebook-f"></i> Facebook
    </button>
    <button class="gz-share-btn gz-share-ig" onclick="window.gazetteShare('instagram')">
        <i class="fab fa-instagram"></i> Instagram
    </button>
    <button class="gz-share-btn gz-share-x" onclick="window.gazetteShare('x')">
        <i class="fab fa-x-twitter"></i> X
    </button>
</div>`;

        return html;
    }
})();

function closeNewspaper() {
    const overlay = document.getElementById('newspaperOverlay');
    if (overlay) overlay.style.display = 'none';
}

// Unified share — capture gazette as image, then share to platform
window.gazetteShare = async function(platform) {
    const gazette = document.querySelector('.gazette-inner');
    if (!gazette) return;

    if (typeof html2canvas !== 'function') {
        alert('Take a screenshot of this brief and share it on ' + platform + '!');
        return;
    }

    // Hide share buttons during capture
    const shareRow = gazette.querySelector('.gz-share-row');
    if (shareRow) shareRow.style.display = 'none';

    try {
        const canvas = await html2canvas(gazette, { backgroundColor: '#ffffff', scale: 2, useCORS: true });
        if (shareRow) shareRow.style.display = '';

        const blob = await new Promise(r => canvas.toBlob(r, 'image/png'));
        const file = new File([blob], 'politiquera-brief.png', { type: 'image/png' });
        const shareText = 'Hidalgo County 2026 Early Vote Brief from Politiquera.com';
        const shareUrl = 'https://politiquera.com';

        // Try native Web Share API first (works on mobile for all platforms)
        if (navigator.canShare && navigator.canShare({ files: [file] })) {
            try {
                await navigator.share({ files: [file], title: 'Politiquera Early Vote Brief', text: shareText });
                return;
            } catch (e) {
                // User cancelled or share failed — fall through to platform-specific
            }
        }

        // Desktop fallback: download image + open platform share dialog
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'politiquera-brief.png'; a.click();
        URL.revokeObjectURL(url);

        if (platform === 'facebook') {
            window.open('https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(shareUrl), '_blank', 'width=600,height=400');
            alert('Image saved! Paste it into your Facebook post.');
        } else if (platform === 'instagram') {
            alert('Image saved! Open Instagram and share it as a post or story.');
        } else if (platform === 'x') {
            window.open('https://x.com/intent/tweet?text=' + encodeURIComponent(shareText + ' ' + shareUrl), '_blank', 'width=600,height=400');
            alert('Image saved! Attach it to your tweet.');
        }
    } catch (e) {
        if (shareRow) shareRow.style.display = '';
        console.error('Screenshot failed:', e);
        alert('Could not capture screenshot. Try a manual screenshot instead.');
    }
};

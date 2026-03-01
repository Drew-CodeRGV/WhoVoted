/* Gazette — clean data brief with collapsible sections */

(function () {
    const btn = document.getElementById('newspaperBtn');
    if (!btn) return;

    btn.addEventListener('click', openNewspaper);
    window.refreshGazette = openNewspaper;

    async function openNewspaper() {
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
            const resp = await fetch('/api/election-insights');
            if (!resp.ok) throw new Error('API error');
            const d = await resp.json();
            body.innerHTML = buildGazette(d);

            // Wire up collapsible sections
            body.querySelectorAll('.gz-section-title').forEach(title => {
                title.addEventListener('click', () => {
                    title.closest('.gz-section').classList.toggle('collapsed');
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

    function buildGazette(d) {
        const demPct = d.dem_share_2026;
        const repPct = (100 - demPct).toFixed(1);
        const netFlip = d.r2d_2026 - d.d2r_2026;
        const netLabel = netFlip > 0 ? 'net D' : netFlip < 0 ? 'net R' : 'even';
        const ratio = d.rep_2026 ? (d.dem_2026 / d.rep_2026).toFixed(1) : '—';
        const newDemPct = d.new_2026 ? pct(d.new_dem_2026, d.new_2026) : 0;
        const fPct = pct(d.female_2026, d.female_2026 + d.male_2026);

        let html = '';

        // ── Top KPIs (always visible, not collapsible) ──
        html += `
<div class="gz-kpi-row">
    <div class="gz-kpi neutral">
        <div class="gz-kpi-value">${f(d.ev_2026)}</div>
        <div class="gz-kpi-label">Early Votes</div>
    </div>
    <div class="gz-kpi dem">
        <div class="gz-kpi-value">${demPct}%</div>
        <div class="gz-kpi-label">Democratic</div>
    </div>
    <div class="gz-kpi rep">
        <div class="gz-kpi-value">${repPct}%</div>
        <div class="gz-kpi-label">Republican</div>
    </div>
    <div class="gz-kpi neutral">
        <div class="gz-kpi-value">${d.pct_of_2024}%</div>
        <div class="gz-kpi-label">of 2024 Total</div>
    </div>
</div>`;

        // ── Party Breakdown ──
        html += `
<div class="gz-section">
    <div class="gz-section-title">Party Breakdown</div>
    <div class="gz-section-body">
        <div class="gz-bar-labels">
            <span class="gz-dem">${f(d.dem_2026)} Dem</span>
            <span class="gz-rep">${f(d.rep_2026)} Rep</span>
        </div>
        <div class="gz-bar">
            <div class="gz-bar-dem" style="width:${demPct}%"></div>
            <div class="gz-bar-rep" style="width:${repPct}%"></div>
        </div>
        <p class="gz-text">Democrats lead <span class="gz-dem gz-big">${ratio}</span>-to-1. Dem share up from ${d.dem_share_2024}% in '24 and ${d.dem_share_2022}% in '22.</p>
    </div>
</div>`;

        // ── Party Switchers ──
        html += `
<div class="gz-section">
    <div class="gz-section-title">Party Switchers</div>
    <div class="gz-section-body">
        <div class="gz-kpi-row">
            <div class="gz-kpi dem">
                <div class="gz-kpi-value">${f(d.r2d_2026)}</div>
                <div class="gz-kpi-label">R → D</div>
            </div>
            <div class="gz-kpi rep">
                <div class="gz-kpi-value">${f(d.d2r_2026)}</div>
                <div class="gz-kpi-label">D → R</div>
            </div>
            <div class="gz-kpi ${netFlip > 0 ? 'dem' : netFlip < 0 ? 'rep' : 'neutral'}">
                <div class="gz-kpi-value">${Math.abs(netFlip)}</div>
                <div class="gz-kpi-label">${netLabel}</div>
            </div>
        </div>
        <p class="gz-text">In 2024: ${f(d.d2r_2024)} D→R vs ${f(d.r2d_2024)} R→D (net <span class="gz-rep">+${f(d.d2r_2024 - d.r2d_2024)} R</span>).</p>
    </div>
</div>`;

        // ── New Voters (golden) ──
        html += `
<div class="gz-section">
    <div class="gz-section-title gold">★ New Voters</div>
    <div class="gz-section-body">
        <div class="gz-kpi-row">
            <div class="gz-kpi gold">
                <div class="gz-kpi-value">${f(d.new_2026)}</div>
                <div class="gz-kpi-label">First-Time</div>
            </div>
            <div class="gz-kpi gold">
                <div class="gz-kpi-value">${newDemPct}%</div>
                <div class="gz-kpi-label">Chose Dem</div>
            </div>
        </div>
        <div class="gz-bar-labels">
            <span class="gz-dem">${f(d.new_dem_2026)} Dem</span>
            <span class="gz-rep">${f(d.new_rep_2026)} Rep</span>
        </div>
        <div class="gz-bar">
            <div class="gz-bar-dem" style="width:${newDemPct}%"></div>
            <div class="gz-bar-rep" style="width:${100 - newDemPct}%"></div>
        </div>${d.new_age_gender_2026 ? (() => {
            const nag = d.new_age_gender_2026;
            const sorted = Object.entries(nag)
                .filter(([k]) => k !== 'Unknown')
                .sort((a, b) => b[1].total - a[1].total)
                .slice(0, 3);
            if (!sorted.length) return '';
            return `
        <div style="margin-top:10px;">
            <div style="font-size:11px;font-weight:700;color:#b8860b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">Top Age Groups</div>
            <div class="gz-kpi-row">${sorted.map(([age, v]) => {
                const pctOfNew = d.new_2026 ? Math.round(v.total / d.new_2026 * 100) : 0;
                return `
                <div class="gz-kpi gold">
                    <div class="gz-kpi-value">${f(v.total)}</div>
                    <div class="gz-kpi-label">${age} (${pctOfNew}%)</div>
                </div>`;
            }).join('')}
            </div>
        </div>`;
        })() : ''}
    </div>
</div>`;

        // ── Gender ──
        html += `
<div class="gz-section">
    <div class="gz-section-title">Gender</div>
    <div class="gz-section-body">
        <p class="gz-text"><span class="gz-big">${f(d.female_2026)}</span> women (${fPct}%) · <span class="gz-big">${f(d.male_2026)}</span> men (${100 - fPct}%)</p>
        <p class="gz-text">Dem: <span class="gz-dem">${f(d.dem_female_2026)}F / ${f(d.dem_male_2026)}M</span> · Rep: <span class="gz-rep">${f(d.rep_female_2026)}F / ${f(d.rep_male_2026)}M</span></p>
    </div>
</div>`;

        // ── Age Table ──
        if (d.age_groups_2026) {
            const order = ['18-24','25-34','35-44','45-54','55-64','65-74','75+'];
            const ag = d.age_groups_2026;
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

        // ── Turnout ──
        html += `
<div class="gz-section">
    <div class="gz-section-title">Turnout vs. 2024</div>
    <div class="gz-section-body">
        <div class="gz-kpi-row">
            <div class="gz-kpi neutral">
                <div class="gz-kpi-value">${f(d.both_24_26)}</div>
                <div class="gz-kpi-label">Returned</div>
            </div>
            <div class="gz-kpi neutral">
                <div class="gz-kpi-value">${f(d.voted_24_not_26)}</div>
                <div class="gz-kpi-label">Haven't Voted</div>
            </div>
        </div>
        <table class="gz-table">
            <tr><th>Year</th><th class="r">Dem</th><th class="r">Rep</th><th class="r">Total</th><th class="r">Dem %</th></tr>
            <tr><td>2022</td><td class="r dem-val">${f(Math.round(d.dem_share_2022/100*d.total_2022))}</td><td class="r rep-val">${f(Math.round((100-d.dem_share_2022)/100*d.total_2022))}</td><td class="r">${f(d.total_2022)}</td><td class="r">${d.dem_share_2022}%</td></tr>
            <tr><td>2024</td><td class="r dem-val">${f(Math.round(d.dem_share_2024/100*d.total_2024))}</td><td class="r rep-val">${f(Math.round((100-d.dem_share_2024)/100*d.total_2024))}</td><td class="r">${f(d.total_2024)}</td><td class="r">${d.dem_share_2024}%</td></tr>
            <tr><td>2026 EV</td><td class="r dem-val">${f(d.dem_2026)}</td><td class="r rep-val">${f(d.rep_2026)}</td><td class="r">${f(d.ev_2026)}</td><td class="r">${d.dem_share_2026}%</td></tr>
        </table>
    </div>
</div>`;

        // ── Footer ──
        const updated = d.last_updated
            ? new Date(d.last_updated + 'Z').toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'})
            : 'during early voting';
        html += `<div class="gz-footer">Politiquera.com · Hidalgo County Elections Dept. · Data updated ${updated}</div>`;

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

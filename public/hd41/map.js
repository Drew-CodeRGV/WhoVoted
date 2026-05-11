// HD-41 Runoff Election Tracker — Voter Map + Precinct Analysis
// Default: voter dots + heatmap. Dropdown: Primary Results, Mop-Up targeting.
// All data from official Hidalgo County canvass + voter rolls.

let map, boundaryLayer, precinctLayer, markerClusterGroup, heatLayer;
let voterData = null, precinctData = null, shapesData = null, candidateData = null;
let currentView = 'voters'; // 'voters', 'primary', 'mopup'
let primaryMode = 'combined'; // 'dem', 'combined', 'rep'
let mopupCandidate = '';
let selectedCandidate = '';

function showLoading() {
    const d = document.createElement('div'); d.id='loading-screen';
    d.innerHTML=`<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(255,255,255,0.95);z-index:10000;display:flex;align-items:center;justify-content:center;"><div style="text-align:center"><div style="font-size:20px;font-weight:600;color:#333;">Loading HD-41</div><div style="font-size:13px;color:#666;margin-top:6px;">22,420 voters...</div></div></div>`;
    document.body.appendChild(d);
}
function hideLoading(){const e=document.getElementById('loading-screen');if(e)e.remove();}

function initMap() {
    map = L.map('map').setView([26.245,-98.23],12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap',maxZoom:18}).addTo(map);
    markerClusterGroup = L.markerClusterGroup({maxClusterRadius:25,spiderfyOnMaxZoom:true,showCoverageOnHover:false,zoomToBoundsOnClick:true,disableClusteringAtZoom:16,iconCreateFunction:()=>L.divIcon({html:'',className:'invisible-cluster',iconSize:L.point(1,1)})});
    map.addLayer(markerClusterGroup);
    map.on('zoomend',()=>{if(heatLayer){if(map.getZoom()>=16&&map.hasLayer(heatLayer))map.removeLayer(heatLayer);else if(map.getZoom()<16&&!map.hasLayer(heatLayer)&&currentView==='voters')heatLayer.addTo(map);}});
    loadData();
}

async function loadData() {
    showLoading();
    try {
        const [vResp,pResp,sResp,cResp,bResp] = await Promise.all([
            fetch('/cache/hd41_voters.json'),
            fetch('/cache/hd41_precinct_results.json'),
            fetch('/cache/hd41_precinct_shapes.json'),
            fetch('/cache/hd41_primary_candidates.json'),
            fetch('/cache/hd41_boundary.json'),
        ]);
        voterData = await vResp.json();
        precinctData = await pResp.json();
        shapesData = await sResp.json();
        candidateData = await cResp.json();
        const bnd = await bResp.json();
        boundaryLayer = L.geoJSON(bnd,{style:{color:'#1a237e',weight:3,fillOpacity:0.02,dashArray:'8,4'}}).addTo(map);
        map.fitBounds(boundaryLayer.getBounds(),{padding:[20,20]});

        document.getElementById('total-voters').textContent = voterData.count.toLocaleString();
        setupListeners();
        renderVoters();
        hideLoading();
    } catch(e){hideLoading();console.error(e);}
}

function setupListeners() {
    // Main view dropdown
    document.getElementById('view-select').addEventListener('change', e => {
        currentView = e.target.value;
        document.getElementById('primary-controls').style.display = currentView==='primary'?'inline-flex':'none';
        document.getElementById('mopup-controls').style.display = currentView==='mopup'?'inline-flex':'none';
        document.getElementById('candidate-select').style.display = currentView==='primary'?'inline-block':'none';
        render();
    });
    // Primary mode buttons
    document.querySelectorAll('.mode-btn').forEach(btn=>{
        btn.addEventListener('click',()=>{
            document.querySelectorAll('.mode-btn').forEach(b=>b.classList.remove('active'));
            document.querySelectorAll(`.mode-btn[data-mode="${btn.dataset.mode}"]`).forEach(b=>b.classList.add('active'));
            primaryMode = btn.dataset.mode;
            selectedCandidate = '';
            document.getElementById('candidate-select').value = '';
            render();
        });
    });
    // Candidate select
    document.getElementById('candidate-select').addEventListener('change', e => {
        selectedCandidate = e.target.value;
        render();
    });
    // Mop-up select
    document.getElementById('mopup-select').addEventListener('change', e => {
        mopupCandidate = e.target.value;
        render();
    });
    // Boundary toggle
    document.getElementById('boundary-toggle').addEventListener('change', e => {
        if(e.target.checked&&boundaryLayer)boundaryLayer.addTo(map);
        else if(boundaryLayer&&map.hasLayer(boundaryLayer))map.removeLayer(boundaryLayer);
    });
    // Location
    document.getElementById('location-btn').addEventListener('click',()=>{
        if(navigator.geolocation)navigator.geolocation.getCurrentPosition(p=>map.setView([p.coords.latitude,p.coords.longitude],15));
    });
    // Report card
    document.getElementById('reportcard-btn').addEventListener('click', toggleReportCard);
    document.getElementById('reportcard-close').addEventListener('click',()=>document.getElementById('reportcard-panel').classList.remove('visible'));
    // Mobile
    const mb=document.getElementById('mobile-menu-btn'),md=document.getElementById('mobile-drawer');
    if(mb&&md){mb.addEventListener('click',()=>md.classList.toggle('visible'));document.addEventListener('click',e=>{if(!md.contains(e.target)&&e.target!==mb)md.classList.remove('visible');});}
    // Mobile view select
    const mvs=document.getElementById('view-select-mobile');
    if(mvs)mvs.addEventListener('change',e=>{document.getElementById('view-select').value=e.target.value;document.getElementById('view-select').dispatchEvent(new Event('change'));if(md)md.classList.remove('visible');});
    const mms=document.getElementById('mopup-select-mobile');
    if(mms)mms.addEventListener('change',e=>{document.getElementById('mopup-select').value=e.target.value;mopupCandidate=e.target.value;render();if(md)md.classList.remove('visible');});
    // Populate candidate dropdown
    populateCandidates();
}

function populateCandidates() {
    const sel = document.getElementById('candidate-select');
    sel.innerHTML = '<option value="">All Precincts</option>';
    if(!candidateData) return;
    const dg=document.createElement('optgroup');dg.label='🔵 Democratic';
    for(const c of(candidateData.dem_candidates||[])){const d=candidateData.candidates[c];if(d){const o=document.createElement('option');o.value=c;o.textContent=`${c.replace("Victor 'Seby' ","Seby ")} (${d.district_share}%)`;dg.appendChild(o);}}
    sel.appendChild(dg);
    const rg=document.createElement('optgroup');rg.label='🔴 Republican';
    for(const c of(candidateData.rep_candidates||[])){const d=candidateData.candidates[c];if(d){const o=document.createElement('option');o.value=c;o.textContent=`${c} (${d.district_share}%)`;rg.appendChild(o);}}
    sel.appendChild(rg);
}

function render() {
    if(currentView==='voters') renderVoters();
    else if(currentView==='primary') renderPrimary();
    else if(currentView==='mopup') renderMopup();
}

// ── VOTER DOTS VIEW ──
function renderVoters() {
    clearLayers();
    if(!voterData||!voterData.voters) return;
    const hp=[];
    for(const v of voterData.voters){
        if(!v.lat||!v.lng)continue;
        hp.push([v.lat,v.lng,0.5]);
        const color = v.party_voted==='Democratic'?'#1565c0':v.party_voted==='Republican'?'#c62828':'#666';
        const marker = L.circleMarker([v.lat,v.lng],{radius:4,fillColor:color,color,weight:1,opacity:0.8,fillOpacity:0.6});
        const age = v.birth_year?(2026-v.birth_year):'?';
        const hist = (v.hist||[]).map(h=>`<span style="color:${h.p==='D'?'#1565c0':h.p==='R'?'#c62828':'#666'}">${h.y}${h.p}</span>`).join(' ');
        marker.bindPopup(`<div style="font-family:sans-serif;min-width:200px"><div style="font-weight:700;font-size:13px">${v.name}</div><div style="font-size:11px;color:#666">${v.address||''}, ${v.city||''} ${v.zip||''}</div><div style="font-size:11px;margin-top:4px"><b>Party:</b> ${v.party_voted||'—'} · <b>Age:</b> ${age} · <b>Sex:</b> ${v.sex||'—'}</div><div style="font-size:11px"><b>Method:</b> ${v.voting_method||'—'} · <b>Pct:</b> ${v.precinct||'—'}</div>${hist?`<div style="font-size:10px;margin-top:4px;color:#888">History: ${hist}</div>`:''}</div>`,{maxWidth:280});
        markerClusterGroup.addLayer(marker);
    }
    if(hp.length){heatLayer=L.heatLayer(hp,{radius:15,blur:20,maxZoom:15,max:1.0});heatLayer.addTo(map);}
    updateStrip(`${voterData.count.toLocaleString()} voters · Zoom in for individual dots · Click for voter details + history`);
}

// ── PRIMARY RESULTS VIEW ──
function renderPrimary() {
    clearLayers();
    const pctLookup={};for(const p of precinctData.precincts)pctLookup[p.precinct]=p;
    precinctLayer = L.geoJSON(shapesData,{
        style: feat => {
            const p=pctLookup[feat.properties.db_precinct];
            if(!p)return{fillColor:'#ccc',fillOpacity:0.1,color:'#999',weight:1};
            let fillColor;
            if(selectedCandidate&&candidateData){
                const cand=candidateData.candidates[selectedCandidate];
                if(cand){const pd=cand.precincts.find(x=>x.precinct===p.precinct);if(pd){const s=pd.share;fillColor=s>=50?'#1b5e20':s>=38?'#66bb6a':s>=25?'#ffb74d':'#c62828';}else fillColor='#eee';}else fillColor='#eee';
            } else if(primaryMode==='combined'){
                const ds=p.dem_share;fillColor=ds>=80?'#0d47a1':ds>=65?'#7b1fa2':ds>=50?'#7b1fa2':ds>=35?'#880e4f':'#b71c1c';
            } else if(primaryMode==='dem'){
                const w=p.dem_winner;fillColor=w&&w.includes('Haddad')?'#1565c0':w&&w.includes('Salinas')?'#2e7d32':w&&w.includes('Holgu')?'#f57f17':'#666';
            } else {
                const w=p.rep_winner;fillColor=w&&w.includes('Sanchez')?'#c62828':w&&w.includes('Groves')?'#e65100':w&&w.includes('Sagredo')?'#f9a825':'#666';
            }
            return{fillColor,fillOpacity:0.6,color:'#222',weight:1.5};
        },
        onEachFeature:(feat,layer)=>{
            const p=pctLookup[feat.properties.db_precinct];if(!p)return;
            layer.bindPopup(()=>buildPrimaryPopup(p),{maxWidth:360});
        }
    }).addTo(map);
    if(selectedCandidate){const c=candidateData.candidates[selectedCandidate];if(c)updateStrip(`<b>${selectedCandidate}</b> (${c.party}) · ${c.total_votes} votes (${c.district_share}%) · <span style="color:#1b5e20">■Won</span> <span style="color:#66bb6a">■Close</span> <span style="color:#ffb74d">■Lost close</span> <span style="color:#c62828">■Lost badly</span>`);}
    else if(primaryMode==='combined')updateStrip(`Combined · <span style="color:#0d47a1">■Strong D</span> <span style="color:#7b1fa2">■Lean D</span> <span style="color:#880e4f">■Lean R</span> <span style="color:#b71c1c">■Strong R</span> · Click for side-by-side`);
    else if(primaryMode==='dem')updateStrip(`Dem Primary · <span style="color:#1565c0">■Haddad</span> <span style="color:#2e7d32">■Salinas</span> <span style="color:#f57f17">■Holguín</span>`);
    else updateStrip(`GOP Primary · <span style="color:#c62828">■Sanchez</span> <span style="color:#e65100">■Groves</span> <span style="color:#f9a825">■Sagredo-Hammond</span>`);
}

function buildPrimaryPopup(p) {
    let html=`<div style="font-family:sans-serif;min-width:300px"><div style="font-weight:700;font-size:15px;border-bottom:2px solid #333;padding-bottom:4px;margin-bottom:8px;">Precinct ${p.precinct}</div>`;
    if(selectedCandidate&&candidateData){
        const cand=candidateData.candidates[selectedCandidate];
        if(cand){const pd=cand.precincts.find(x=>x.precinct===p.precinct);const party=cand.party;const pk=party==='Democratic'?'dem_candidates':'rep_candidates';const opponents=p[pk]||{};
        if(pd){const won=pd.beaten_by.length===0;html+=`<div style="padding:8px;border-radius:6px;background:${won?'#e8f5e9':pd.share>=38?'#fff3e0':'#fce4ec'};margin-bottom:10px;"><div style="font-weight:700">${selectedCandidate.replace("Victor 'Seby' ","Seby ")}: ${pd.votes} votes (${pd.share}%)</div><div style="font-size:12px;color:#555">${won?'✓ WON':'⚠️ '+(pd.share>=38?'CLOSE':'LOST')}</div></div>`;
        const sorted=Object.entries(opponents).sort((a,b)=>b[1]-a[1]);html+=`<table style="width:100%;border-collapse:collapse;font-size:12px;">`;
        for(const[c,v]of sorted){const pct=pd.pct_total>0?(v/pd.pct_total*100).toFixed(1):0;const isMe=c===selectedCandidate;html+=`<tr style="${isMe?'background:#e3f2fd;font-weight:700':''}"><td style="padding:3px">${c.replace("Victor 'Seby' ","Seby ")}</td><td style="padding:3px;text-align:right">${v}</td><td style="padding:3px;text-align:right;color:#666">${pct}%</td></tr>`;}
        html+=`</table>`;if(!won&&sorted.length){const gap=sorted[0][1]-pd.votes;html+=`<div style="margin-top:6px;padding:4px;background:#fff8e1;border-radius:4px;font-size:11px;"><b>Gap to win:</b> ${gap} votes</div>`;}}}
    } else {
        html+=`<div style="display:flex;gap:12px;"><div style="flex:1;"><div style="font-weight:700;color:#1565c0;font-size:12px;border-bottom:2px solid #1565c0;padding-bottom:2px;margin-bottom:4px;">🔵 DEM (${p.dem_votes})</div>`;
        if(p.dem_candidates){const s=Object.entries(p.dem_candidates).sort((a,b)=>b[1]-a[1]);for(const[c,v]of s){const w=s[0][0]===c;html+=`<div style="font-size:11px;padding:2px 0;${w?'font-weight:700':''};">${w?'👑 ':''}${c.replace("Victor 'Seby' ","Seby ")}: ${v}</div>`;}}
        html+=`</div><div style="flex:1;"><div style="font-weight:700;color:#c62828;font-size:12px;border-bottom:2px solid #c62828;padding-bottom:2px;margin-bottom:4px;">🔴 GOP (${p.rep_votes})</div>`;
        if(p.rep_candidates){const s=Object.entries(p.rep_candidates).sort((a,b)=>b[1]-a[1]);for(const[c,v]of s){const w=s[0][0]===c;html+=`<div style="font-size:11px;padding:2px 0;${w?'font-weight:700':''};">${w?'👑 ':''}${c}: ${v}</div>`;}}
        html+=`</div></div><div style="margin-top:8px;padding:6px;background:#f5f5f5;border-radius:4px;font-size:11px;"><b>Total:</b> ${p.total_votes} · <b>Winner:</b> ${p.winner} +${p.margin_votes} (${p.margin_pct}%) · <b>Turnout:</b> ${p.turnout_pct}%</div>`;
    }
    html+=`</div>`;return html;
}

// ── MOP-UP VIEW ──
function renderMopup() {
    clearLayers();
    if(!mopupCandidate){updateStrip('Select a candidate from the Mop-Up dropdown');return;}
    const configs={'mopup-seby':{my:"Victor 'Seby' Haddad",opp:"Julio Salinas",elim:"Eric Holguín",pk:'dem_candidates',short:'Seby',oppS:'Julio',elimS:'Eric'},'mopup-julio':{my:"Julio Salinas",opp:"Victor 'Seby' Haddad",elim:"Eric Holguín",pk:'dem_candidates',short:'Julio',oppS:'Seby',elimS:'Eric'},'mopup-sergio':{my:"Sergio Sanchez",opp:"Gary Groves",elim:"Sarah Sagredo-Hammond",pk:'rep_candidates',short:'Sergio',oppS:'Gary',elimS:'Sarah'},'mopup-gary':{my:"Gary Groves",opp:"Sergio Sanchez",elim:"Sarah Sagredo-Hammond",pk:'rep_candidates',short:'Gary',oppS:'Sergio',elimS:'Sarah'}};
    const cfg=configs[mopupCandidate];if(!cfg){updateStrip('Unknown candidate');return;}
    const pctLookup={};for(const p of precinctData.precincts)pctLookup[p.precinct]=p;

    precinctLayer=L.geoJSON(shapesData,{
        style:feat=>{
            const p=pctLookup[feat.properties.db_precinct];if(!p)return{fillColor:'#f5f5f5',fillOpacity:0.1,color:'#aaa',weight:1};
            const cands=p[cfg.pk]||{};const myV=cands[cfg.my]||0;const oppV=cands[cfg.opp]||0;const elimV=cands[cfg.elim]||0;
            if(myV<=oppV||elimV===0)return{fillColor:myV>oppV?'#e8f5e9':'#f5f5f5',fillOpacity:0.1,color:'#aaa',weight:1};
            const max=cfg.pk==='dem_candidates'?150:50;const intensity=Math.min(1,elimV/max);
            const fillOpacity=0.3+intensity*0.55;
            const fillColor=intensity>=0.6?'#1b5e20':intensity>=0.3?'#43a047':'#81c784';
            return{fillColor,fillOpacity,color:'#1b5e20',weight:2};
        },
        onEachFeature:(feat,layer)=>{
            const p=pctLookup[feat.properties.db_precinct];if(!p)return;
            layer.bindPopup(()=>{
                const cands=p[cfg.pk]||{};const myV=cands[cfg.my]||0;const oppV=cands[cfg.opp]||0;const elimV=cands[cfg.elim]||0;
                let h=`<div style="font-family:sans-serif;min-width:280px"><div style="font-weight:700;font-size:15px;border-bottom:2px solid #333;padding-bottom:4px;margin-bottom:8px;">Precinct ${p.precinct}</div>`;
                if(myV>oppV&&elimV>0){
                    h+=`<div style="padding:10px;border-radius:6px;background:#e8f5e9;border:2px solid #4caf50;margin-bottom:10px;"><div style="font-size:11px;color:#2e7d32;font-weight:700;">✓ ${cfg.short.toUpperCase()}'S TURF — MOP-UP</div><div style="font-size:28px;font-weight:700;color:#1b5e20;">${elimV}</div><div style="font-size:12px;">${cfg.elimS}'s voters to absorb</div></div>`;
                    h+=`<table style="width:100%;border-collapse:collapse;font-size:12px;"><tr style="background:#e8f5e9;font-weight:700"><td style="padding:4px">👑 ${cfg.short}</td><td style="padding:4px;text-align:right">${myV}</td></tr><tr><td style="padding:4px">${cfg.oppS}</td><td style="padding:4px;text-align:right">${oppV}</td></tr><tr style="background:#fff3e0"><td style="padding:4px">🔥 ${cfg.elimS}</td><td style="padding:4px;text-align:right;font-weight:700;color:#e65100">${elimV}</td></tr></table>`;
                    h+=`<div style="margin-top:8px;padding:6px;background:#f1f8e9;border-radius:4px;font-size:11px;"><b>Win all ${elimV}:</b> ${myV+elimV} vs ${cfg.oppS}'s ${oppV} · <b>Margin: +${myV+elimV-oppV}</b></div>`;
                } else if(myV<=oppV){h+=`<div style="padding:8px;background:#f5f5f5;border-radius:4px;font-size:12px;color:#666;">Not ${cfg.short}'s turf — ${cfg.oppS} won (${oppV} vs ${myV})</div>`;}
                else{h+=`<div style="padding:8px;background:#f5f5f5;border-radius:4px;font-size:12px;color:#666;">${cfg.short} won but no ${cfg.elimS} voters here</div>`;}
                h+=`</div>`;return h;
            },{maxWidth:320});
        }
    }).addTo(map);

    const mopupPcts=precinctData.precincts.filter(p=>{const c=p[cfg.pk]||{};return(c[cfg.my]||0)>(c[cfg.opp]||0)&&(c[cfg.elim]||0)>0;});
    const totalMopup=mopupPcts.reduce((s,p)=>s+((p[cfg.pk]||{})[cfg.elim]||0),0);
    updateStrip(`<b>💪 ${cfg.short}'s Mop-Up</b> · ${mopupPcts.length} stronghold precincts · ${totalMopup} ${cfg.elimS} voters to absorb · Darker green = higher impact`);
}

// ── Helpers ──
function clearLayers(){
    markerClusterGroup.clearLayers();
    if(heatLayer){map.removeLayer(heatLayer);heatLayer=null;}
    if(precinctLayer){map.removeLayer(precinctLayer);precinctLayer=null;}
}
function updateStrip(html){const s=document.querySelector('.info-strip');if(s)s.innerHTML=html;}

// ── Report Card ──
function toggleReportCard(){
    const panel=document.getElementById('reportcard-panel');panel.classList.toggle('visible');
    if(!panel.classList.contains('visible'))return;
    const summary=document.getElementById('reportcard-summary');const list=document.getElementById('reportcard-list');
    const s=precinctData.summary;
    summary.innerHTML=`<div style="font-size:16px;font-weight:700;">HD-41 — ${s.total_votes.toLocaleString()} votes</div><div style="font-size:12px;color:#666;margin-top:4px;">🔵D:${s.total_dem_votes.toLocaleString()} 🔴R:${s.total_rep_votes.toLocaleString()} · ${s.total_precincts} pcts · Official Canvass</div>`;
    const sorted=[...precinctData.precincts].sort((a,b)=>b.total_votes-a.total_votes);
    list.innerHTML=sorted.map(p=>{
        const wc=p.winner==='Democratic'?'#1565c0':'#c62828';
        let dl='',rl='';
        if(p.dem_candidates){const ds=Object.entries(p.dem_candidates).sort((a,b)=>b[1]-a[1]);dl=ds.map(([c,v])=>`${c.replace("Victor 'Seby' ","S.").replace("Julio ","J.").replace("Eric ","E.").split(' ')[0]}:${v}`).join(' ');}
        if(p.rep_candidates){const rs=Object.entries(p.rep_candidates).sort((a,b)=>b[1]-a[1]);rl=rs.map(([c,v])=>`${c.split(' ')[0]}:${v}`).join(' ');}
        return`<div class="rc-row"><div class="rc-grade" style="background:${wc};font-size:11px;width:36px;height:36px;">${p.winner==='Democratic'?'D':'R'}</div><div class="rc-info"><div class="rc-pct" style="font-size:13px;">Pct ${p.precinct} <span style="font-size:10px;color:#888;">(+${p.margin_votes})</span></div><div class="rc-detail" style="font-size:10px;">🔵${dl} · 🔴${rl}</div></div><div style="width:50px;text-align:right;"><div style="font-weight:700;font-size:13px;">${p.total_votes}</div><div style="font-size:9px;color:#666;">${p.turnout_pct}%</div></div></div>`;
    }).join('');
}

document.addEventListener('DOMContentLoaded',initMap);

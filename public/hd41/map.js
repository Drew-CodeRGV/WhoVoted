// HD-41 Runoff Election Tracker
// Views: Voter Map | Party View (DEM/ALL/GOP) | Candidate View (wins/losses/mopup)
// All data: Official Hidalgo County Canvass + Voter Rolls

let map, boundaryLayer, precinctLayer, precinctOutlineLayer, markerClusterGroup, heatLayer;
let voterData=null, precinctData=null, shapesData=null, candidateData=null;
let currentView='voters'; // 'voters','party','candidate'
let partyMode='combined'; // 'dem','combined','rep'
let selectedCandidate='';

function showLoading(){const d=document.createElement('div');d.id='loading-screen';d.innerHTML=`<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(255,255,255,0.95);z-index:10000;display:flex;align-items:center;justify-content:center;"><div style="text-align:center;"><div style="font-size:20px;font-weight:600;">Loading HD-41</div><div style="font-size:13px;color:#666;margin-top:6px;">15,876 voters...</div></div></div>`;document.body.appendChild(d);}
function hideLoading(){const e=document.getElementById('loading-screen');if(e)e.remove();}

function initMap(){
    map=L.map('map').setView([26.245,-98.23],12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap',maxZoom:18}).addTo(map);
    markerClusterGroup=L.markerClusterGroup({maxClusterRadius:25,spiderfyOnMaxZoom:true,showCoverageOnHover:false,zoomToBoundsOnClick:true,disableClusteringAtZoom:16,iconCreateFunction:()=>L.divIcon({html:'',className:'invisible-cluster',iconSize:L.point(1,1)})});
    map.addLayer(markerClusterGroup);
    map.on('zoomend',()=>{if(heatLayer){if(map.getZoom()>=16&&map.hasLayer(heatLayer))map.removeLayer(heatLayer);else if(map.getZoom()<16&&!map.hasLayer(heatLayer)&&currentView==='voters')heatLayer.addTo(map);}});
    loadData();
}

async function loadData(){
    showLoading();
    try{
        const[vR,pR,sR,cR,bR]=await Promise.all([fetch('/cache/hd41_voters.json'),fetch('/cache/hd41_precinct_results.json'),fetch('/cache/hd41_precinct_shapes.json'),fetch('/cache/hd41_primary_candidates.json'),fetch('/cache/hd41_boundary.json')]);
        voterData=await vR.json();precinctData=await pR.json();shapesData=await sR.json();candidateData=await cR.json();
        const bnd=await bR.json();
        boundaryLayer=L.geoJSON(bnd,{style:{color:'#1a237e',weight:3,fillOpacity:0.02,dashArray:'8,4'}}).addTo(map);
        map.fitBounds(boundaryLayer.getBounds(),{padding:[20,20]});
        document.getElementById('total-voters').textContent=voterData.count.toLocaleString();
        setupListeners();
        renderVoters();
        hideLoading();
    }catch(e){hideLoading();console.error(e);}
}

function setupListeners(){
    // View selector
    document.getElementById('view-select').addEventListener('change',e=>{
        currentView=e.target.value;
        // Show/hide sub-controls
        document.getElementById('party-controls').style.display=currentView==='party'?'inline-flex':'none';
        document.getElementById('candidate-controls').style.display=currentView==='candidate'?'inline-block':'none';
        selectedCandidate='';
        if(document.getElementById('candidate-select'))document.getElementById('candidate-select').value='';
        render();
    });
    // Party mode
    document.querySelectorAll('.mode-btn').forEach(btn=>{btn.addEventListener('click',()=>{
        document.querySelectorAll('.mode-btn').forEach(b=>b.classList.remove('active'));
        document.querySelectorAll(`.mode-btn[data-mode="${btn.dataset.mode}"]`).forEach(b=>b.classList.add('active'));
        partyMode=btn.dataset.mode;render();
    });});
    // Candidate select
    document.getElementById('candidate-select').addEventListener('change',e=>{selectedCandidate=e.target.value;render();});
    // Boundary
    document.getElementById('boundary-select').addEventListener('change',e=>updateBoundaries(e.target.value));
    // Location
    document.getElementById('location-btn').addEventListener('click',()=>{if(navigator.geolocation)navigator.geolocation.getCurrentPosition(p=>map.setView([p.coords.latitude,p.coords.longitude],15));});
    // Report card
    document.getElementById('reportcard-btn').addEventListener('click',toggleReportCard);
    document.getElementById('reportcard-close').addEventListener('click',()=>document.getElementById('reportcard-panel').classList.remove('visible'));
    // Mobile
    const mb=document.getElementById('mobile-menu-btn'),md=document.getElementById('mobile-drawer');
    if(mb&&md){mb.addEventListener('click',()=>md.classList.toggle('visible'));document.addEventListener('click',e=>{if(!md.contains(e.target)&&e.target!==mb)md.classList.remove('visible');});}
    const mvs=document.getElementById('view-select-mobile');
    if(mvs)mvs.addEventListener('change',e=>{document.getElementById('view-select').value=e.target.value;document.getElementById('view-select').dispatchEvent(new Event('change'));if(md)md.classList.remove('visible');});
    const mcs=document.getElementById('candidate-select-mobile');
    if(mcs)mcs.addEventListener('change',e=>{selectedCandidate=e.target.value;document.getElementById('candidate-select').value=e.target.value;currentView='candidate';document.getElementById('view-select').value='candidate';document.getElementById('party-controls').style.display='none';document.getElementById('candidate-controls').style.display='inline-block';render();if(md)md.classList.remove('visible');});
    const mbs=document.getElementById('boundary-select-mobile');
    if(mbs)mbs.addEventListener('change',e=>{document.getElementById('boundary-select').value=e.target.value;updateBoundaries(e.target.value);});
    const mrc=document.getElementById('reportcard-btn-mobile');
    if(mrc)mrc.addEventListener('click',()=>{if(md)md.classList.remove('visible');toggleReportCard();});
    // Populate candidate dropdown
    populateCandidates();
}

function populateCandidates(){
    const sels=[document.getElementById('candidate-select'),document.getElementById('candidate-select-mobile')];
    for(const sel of sels){if(!sel)continue;
        sel.innerHTML='<option value="">Choose candidate...</option>';
        if(!candidateData)continue;
        const dg=document.createElement('optgroup');dg.label='🔵 Democratic Runoff';
        for(const c of(candidateData.dem_candidates||[]).filter(x=>!x.includes('Holgu'))){const d=candidateData.candidates[c];if(d){const o=document.createElement('option');o.value=c;o.textContent=`${c.replace("Victor 'Seby' ","Seby ")} (${d.district_share}%)`;dg.appendChild(o);}}
        sel.appendChild(dg);
        const rg=document.createElement('optgroup');rg.label='🔴 Republican Runoff';
        for(const c of(candidateData.rep_candidates||[]).filter(x=>!x.includes('Sagredo'))){const d=candidateData.candidates[c];if(d){const o=document.createElement('option');o.value=c;o.textContent=`${c} (${d.district_share}%)`;rg.appendChild(o);}}
        sel.appendChild(rg);
    }
}

function render(){
    if(currentView==='voters')renderVoters();
    else if(currentView==='party')renderParty();
    else if(currentView==='candidate')renderCandidate();
}

// ═══ VOTER MAP ═══
function renderVoters(){
    clearLayers();
    if(!voterData||!voterData.voters)return;
    const hp=[];
    for(const v of voterData.voters){
        if(!v.lat||!v.lng)continue;
        hp.push([v.lat,v.lng,0.5]);
        const color=v.party_voted==='Democratic'?'#1E90FF':v.party_voted==='Republican'?'#DC143C':'#888';
        const marker=L.circleMarker([v.lat,v.lng],{radius:6,fillColor:color,color:'#fff',weight:2,opacity:1,fillOpacity:0.8});
        marker.bindPopup(()=>buildVoterPopup(v),{maxWidth:380});
        markerClusterGroup.addLayer(marker);
    }
    if(hp.length){heatLayer=L.heatLayer(hp,{radius:15,blur:20,maxZoom:15});heatLayer.addTo(map);}
    updateStrip(`${voterData.count.toLocaleString()} voters · Zoom in for street-level detail · Click dots for voter info + history`);
}

// ═══ PARTY VIEW ═══
function renderParty(){
    clearLayers();
    const pL={};for(const p of precinctData.precincts)pL[p.precinct]=p;
    precinctLayer=L.geoJSON(shapesData,{
        style:f=>{const p=pL[f.properties.db_precinct];if(!p)return{fillColor:'#ccc',fillOpacity:0.1,color:'#999',weight:1};
            let fc;
            if(partyMode==='combined'){const ds=p.dem_share;fc=ds>=80?'#0d47a1':ds>=65?'#7b1fa2':ds>=50?'#7b1fa2':ds>=35?'#880e4f':'#b71c1c';}
            else if(partyMode==='dem'){const w=p.dem_winner;fc=w&&w.includes('Haddad')?'#1565c0':w&&w.includes('Salinas')?'#2e7d32':w&&w.includes('Holgu')?'#f57f17':'#666';}
            else{const w=p.rep_winner;fc=w&&w.includes('Sanchez')?'#c62828':w&&w.includes('Groves')?'#e65100':w&&w.includes('Sagredo')?'#f9a825':'#666';}
            return{fillColor:fc,fillOpacity:0.6,color:'#222',weight:1.5};},
        onEachFeature:(f,l)=>{const p=pL[f.properties.db_precinct];if(!p)return;l.bindPopup(()=>buildPartyPopup(p),{maxWidth:360});}
    }).addTo(map);
    if(partyMode==='combined')updateStrip(`Party view · <span style="color:#0d47a1">■Strong D</span> <span style="color:#7b1fa2">■Lean D</span> <span style="color:#880e4f">■Lean R</span> <span style="color:#b71c1c">■Strong R</span>`);
    else if(partyMode==='dem')updateStrip(`Dem Primary · <span style="color:#1565c0">■Haddad</span> <span style="color:#2e7d32">■Salinas</span> <span style="color:#f57f17">■Holguín</span>`);
    else updateStrip(`GOP Primary · <span style="color:#c62828">■Sanchez</span> <span style="color:#e65100">■Groves</span> <span style="color:#f9a825">■Sagredo-Hammond</span>`);
}

// ═══ CANDIDATE VIEW (wins + losses + mop-up combined) ═══
function renderCandidate(){
    clearLayers();
    if(!selectedCandidate||!candidateData){updateStrip('Select a candidate to see their precinct performance');return;}
    const cand=candidateData.candidates[selectedCandidate];if(!cand)return;
    const pL={};for(const p of precinctData.precincts)pL[p.precinct]=p;
    const isDem=cand.party==='Democratic';
    const elimName=isDem?"Eric Holguín":"Sarah Sagredo-Hammond";
    const oppName=isDem?(selectedCandidate.includes('Salinas')?"Victor 'Seby' Haddad":"Julio Salinas"):(selectedCandidate.includes('Sanchez')?"Gary Groves":"Sergio Sanchez");

    precinctLayer=L.geoJSON(shapesData,{
        style:f=>{
            const p=pL[f.properties.db_precinct];if(!p)return{fillColor:'#f5f5f5',fillOpacity:0.1,color:'#aaa',weight:1};
            const pk=isDem?'dem_candidates':'rep_candidates';
            const cands=p[pk]||{};
            const myV=cands[selectedCandidate]||0;const oppV=cands[oppName]||0;const elimV=cands[elimName]||0;
            const total=Object.values(cands).reduce((s,v)=>s+v,0);
            const share=total>0?myV/total*100:0;
            // 4-state: Won + mop-up (dark green), Won (green), Close/lost (orange), Lost badly (red)
            if(myV>oppV&&elimV>0)return{fillColor:'#1b5e20',fillOpacity:0.3+Math.min(0.5,elimV/150*0.5),color:'#1b5e20',weight:2}; // Won + mop-up opportunity
            if(myV>oppV)return{fillColor:'#4caf50',fillOpacity:0.5,color:'#2e7d32',weight:1.5}; // Won, no mop-up
            if(share>=35)return{fillColor:'#ff9800',fillOpacity:0.5,color:'#e65100',weight:1.5}; // Close loss
            return{fillColor:'#c62828',fillOpacity:0.4,color:'#b71c1c',weight:1.5}; // Lost badly
        },
        onEachFeature:(f,l)=>{const p=pL[f.properties.db_precinct];if(!p)return;l.bindPopup(()=>buildCandidatePopup(p,selectedCandidate,cand,oppName,elimName),{maxWidth:360});}
    }).addTo(map);
    const shortName=selectedCandidate.replace("Victor 'Seby' ","Seby ").split(' ')[0];
    updateStrip(`<b>${shortName}</b> · ${cand.total_votes} votes (${cand.district_share}%) · <span style="color:#1b5e20">■Won+Mop-up</span> <span style="color:#4caf50">■Won</span> <span style="color:#ff9800">■Close loss</span> <span style="color:#c62828">■Lost badly</span>`);
}

// ═══ POPUPS ═══
function buildVoterPopup(v){
    const party=v.party_voted||'';const pColor=party.includes('Democrat')?'#1E90FF':party.includes('Republican')?'#DC143C':'#888';
    const age=v.birth_year&&v.birth_year>1900?(2026-v.birth_year):'';
    let h=`<div style="max-width:380px;font-family:-apple-system,sans-serif;">`;
    h+=`<div style="font-size:11px;color:#888;margin-bottom:2px;">${v.address||''}, ${v.city||''} ${v.zip||''}</div>`;
    h+=`<div style="display:flex;align-items:center;gap:6px;margin-bottom:2px;"><span style="width:10px;height:10px;border-radius:50%;background:${pColor};"></span><span style="font-weight:600;font-size:13px;">${v.name}</span></div>`;
    const details=[party,v.sex==='F'?'Female':v.sex==='M'?'Male':'',age?`Age ${age}`:'',v.precinct?'Pct '+v.precinct:''].filter(Boolean).join(' · ');
    if(details)h+=`<div style="font-size:11px;color:#666;margin-bottom:3px;">${details}</div>`;
    const m=v.voting_method||'';
    if(m==='early-voting')h+=`<div style="color:#2E7D32;font-size:11px;font-weight:600;">✓ Early Voter</div>`;
    else if(m==='mail-in')h+=`<div style="color:#6A1B9A;font-size:11px;font-weight:600;">📬 Mail-In</div>`;
    else if(m==='election-day')h+=`<div style="color:#E65100;font-size:11px;font-weight:600;">📍 Election Day</div>`;
    const hx=v.hist||[];
    if(hx.length){h+='<div style="font-size:10px;font-weight:600;color:#555;margin-top:4px;">Voting History</div><table style="border-collapse:collapse;margin-top:2px;width:100%;"><tr>';
    hx.forEach(e=>{h+=`<td style="padding:1px 2px;font-size:8px;color:#888;text-align:center;border:1px solid #e0e0e0;background:#f5f5f5;">${(e.y||'').slice(-2)}</td>`;});
    h+='</tr><tr>';hx.forEach(e=>{const bg=e.p==='D'?'#1E90FF':e.p==='R'?'#DC143C':'#888';h+=`<td style="padding:3px 2px;text-align:center;border:1px solid #e0e0e0;background:${bg};color:white;font-size:11px;font-weight:700;">${e.p}</td>`;});
    h+='</tr></table>';}
    h+=`</div>`;return h;
}

function buildPartyPopup(p){
    let h=`<div style="font-family:sans-serif;min-width:300px"><div style="font-weight:700;font-size:15px;border-bottom:2px solid #333;padding-bottom:4px;margin-bottom:8px;">Precinct ${p.precinct}</div>`;
    h+=`<div style="display:flex;gap:12px;"><div style="flex:1;"><div style="font-weight:700;color:#1565c0;font-size:12px;border-bottom:2px solid #1565c0;padding-bottom:2px;margin-bottom:4px;">🔵 DEM (${p.dem_votes})</div>`;
    if(p.dem_candidates){Object.entries(p.dem_candidates).sort((a,b)=>b[1]-a[1]).forEach(([c,v],i)=>{h+=`<div style="font-size:11px;padding:2px 0;${i===0?'font-weight:700':''};">${i===0?'👑 ':''}${c.replace("Victor 'Seby' ","Seby ")}: ${v}</div>`;});}
    h+=`</div><div style="flex:1;"><div style="font-weight:700;color:#c62828;font-size:12px;border-bottom:2px solid #c62828;padding-bottom:2px;margin-bottom:4px;">🔴 GOP (${p.rep_votes})</div>`;
    if(p.rep_candidates){Object.entries(p.rep_candidates).sort((a,b)=>b[1]-a[1]).forEach(([c,v],i)=>{h+=`<div style="font-size:11px;padding:2px 0;${i===0?'font-weight:700':''};">${i===0?'👑 ':''}${c}: ${v}</div>`;});}
    h+=`</div></div><div style="margin-top:8px;padding:6px;background:#f5f5f5;border-radius:4px;font-size:11px;"><b>Total:</b> ${p.total_votes} · <b>Winner:</b> ${p.winner} +${p.margin_votes} (${p.margin_pct}%) · <b>Turnout:</b> ${p.turnout_pct}%</div></div>`;
    return h;
}

function buildCandidatePopup(p,candName,cand,oppName,elimName){
    const isDem=cand.party==='Democratic';
    const pk=isDem?'dem_candidates':'rep_candidates';
    const cands=p[pk]||{};
    const myV=cands[candName]||0;const oppV=cands[oppName]||0;const elimV=cands[elimName]||0;
    const total=Object.values(cands).reduce((s,v)=>s+v,0);
    const share=total>0?(myV/total*100).toFixed(1):0;
    const won=myV>oppV;
    const shortMe=candName.replace("Victor 'Seby' ","Seby ").split(' ').slice(0,2).join(' ');
    const shortOpp=oppName.replace("Victor 'Seby' ","Seby ").split(' ').slice(0,2).join(' ');
    const shortElim=elimName.split(' ')[0];

    let h=`<div style="font-family:sans-serif;min-width:280px"><div style="font-weight:700;font-size:15px;border-bottom:2px solid #333;padding-bottom:4px;margin-bottom:8px;">Precinct ${p.precinct}</div>`;

    // Status header
    if(won&&elimV>0){
        h+=`<div style="padding:8px;border-radius:6px;background:#e8f5e9;border:2px solid #4caf50;margin-bottom:10px;"><div style="font-size:11px;color:#2e7d32;font-weight:700;">✓ ${shortMe.toUpperCase()}'S TURF — MOP-UP OPPORTUNITY</div><div style="font-size:24px;font-weight:700;color:#1b5e20;margin:2px 0;">${elimV}</div><div style="font-size:12px;color:#555;">${shortElim}'s voters to absorb</div></div>`;
    } else if(won){
        h+=`<div style="padding:8px;border-radius:6px;background:#e8f5e9;margin-bottom:10px;"><div style="font-weight:700;color:#2e7d32;">✓ WON — ${myV} votes (${share}%)</div></div>`;
    } else {
        h+=`<div style="padding:8px;border-radius:6px;background:#fce4ec;margin-bottom:10px;"><div style="font-weight:700;color:#c62828;">✗ LOST — ${myV} votes (${share}%)</div><div style="font-size:11px;color:#666;">Gap: ${oppV-myV} votes behind ${shortOpp}</div></div>`;
    }

    // All candidates ranked
    h+=`<table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:8px;">`;
    Object.entries(cands).sort((a,b)=>b[1]-a[1]).forEach(([c,v])=>{
        const isMe=c===candName;const isElim=c===elimName;const pct=total>0?(v/total*100).toFixed(0):'0';
        h+=`<tr style="${isMe?'background:#e3f2fd;font-weight:700;':isElim?'background:#fff3e0;':''}"><td style="padding:4px;">${c===Object.entries(cands).sort((a,b)=>b[1]-a[1])[0][0]?'👑 ':''}${isElim?'🔥 ':''}${c.replace("Victor 'Seby' ","Seby ")}</td><td style="padding:4px;text-align:right;font-weight:700;">${v}</td><td style="padding:4px;text-align:right;color:#666;">${pct}%</td></tr>`;
    });
    h+=`</table>`;

    // Projection if mop-up
    if(won&&elimV>0){
        h+=`<div style="padding:6px;background:#f1f8e9;border-radius:4px;font-size:11px;"><b>Win all ${elimV}:</b> ${myV+elimV} vs ${shortOpp}'s ${oppV} · <b>Margin: +${myV+elimV-oppV}</b></div>`;
    } else if(!won){
        h+=`<div style="padding:6px;background:#fff8e1;border-radius:4px;font-size:11px;"><b>Need ${oppV-myV+1} more votes</b> to win this precinct${elimV>0?` · ${elimV} ${shortElim} voters up for grabs`:''}</div>`;
    }
    h+=`</div>`;return h;
}

// ═══ BOUNDARIES ═══
function updateBoundaries(mode){
    if(boundaryLayer&&map.hasLayer(boundaryLayer))map.removeLayer(boundaryLayer);
    if(precinctOutlineLayer&&map.hasLayer(precinctOutlineLayer))map.removeLayer(precinctOutlineLayer);
    if(mode==='district'||mode==='both'){if(boundaryLayer)boundaryLayer.addTo(map);}
    if(mode==='precincts'||mode==='both'){
        if(!precinctOutlineLayer&&shapesData)precinctOutlineLayer=L.geoJSON(shapesData,{style:{color:'#555',weight:1.5,fillOpacity:0,dashArray:'3,3'},onEachFeature:(f,l)=>{l.bindTooltip('Pct '+f.properties.db_precinct,{permanent:false,direction:'center'});}});
        if(precinctOutlineLayer)precinctOutlineLayer.addTo(map);
    }
}

// ═══ HELPERS ═══
function clearLayers(){markerClusterGroup.clearLayers();if(heatLayer){map.removeLayer(heatLayer);heatLayer=null;}if(precinctLayer){map.removeLayer(precinctLayer);precinctLayer=null;}}
function updateStrip(html){const s=document.querySelector('.info-strip');if(s)s.innerHTML=html;}

// ═══ REPORT CARD ═══
function toggleReportCard(){
    const panel=document.getElementById('reportcard-panel');panel.classList.toggle('visible');
    if(!panel.classList.contains('visible'))return;
    document.getElementById('reportcard-summary').innerHTML=`<div style="font-size:16px;font-weight:700;">HD-41 — ${precinctData.summary.total_votes.toLocaleString()} votes</div><div style="font-size:12px;color:#666;margin-top:4px;">🔵D:${precinctData.summary.total_dem_votes.toLocaleString()} 🔴R:${precinctData.summary.total_rep_votes.toLocaleString()} · ${precinctData.summary.total_precincts} pcts · Official Canvass</div>`;
    const sorted=[...precinctData.precincts].sort((a,b)=>b.total_votes-a.total_votes);
    document.getElementById('reportcard-list').innerHTML=sorted.map(p=>{
        const wc=p.winner==='Democratic'?'#1565c0':'#c62828';
        let dl='',rl='';
        if(p.dem_candidates){const ds=Object.entries(p.dem_candidates).sort((a,b)=>b[1]-a[1]);dl=ds.map(([c,v])=>`${c.replace("Victor 'Seby' ","S.").replace("Julio ","J.").replace("Eric ","E.").split(' ')[0]}:${v}`).join(' ');}
        if(p.rep_candidates){const rs=Object.entries(p.rep_candidates).sort((a,b)=>b[1]-a[1]);rl=rs.map(([c,v])=>`${c.split(' ')[0]}:${v}`).join(' ');}
        return`<div class="rc-row"><div class="rc-grade" style="background:${wc};font-size:11px;width:36px;height:36px;">${p.winner==='Democratic'?'D':'R'}</div><div class="rc-info"><div class="rc-pct" style="font-size:13px;">Pct ${p.precinct} <span style="font-size:10px;color:#888;">(+${p.margin_votes})</span></div><div class="rc-detail" style="font-size:10px;">🔵${dl} · 🔴${rl}</div></div><div style="width:50px;text-align:right;"><div style="font-weight:700;font-size:13px;">${p.total_votes}</div><div style="font-size:9px;color:#666;">${p.turnout_pct}%</div></div></div>`;
    }).join('');
}

document.addEventListener('DOMContentLoaded',initMap);

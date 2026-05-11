// HD-41 Runoff Election Tracker
// Single dropdown menu + candidate sub-views
// All data: Official Hidalgo County Canvass + Voter Rolls (geometric filter)

let map,boundaryLayer,precinctLayer,precinctOutlineLayer,markerClusterGroup,heatLayer;
let voterData=null,precinctData=null,shapesData=null,candidateData=null;
let currentMain='voters'; // from main dropdown
let candidateSubView='won'; // 'won','lost','myvotes','partyvotes','mopup','otherparty'

// Subscription — default false, set by paywall script before this loads
if(typeof window.__subscribed==='undefined')window.__subscribed=false;

function showLoading(){const d=document.createElement('div');d.id='loading-screen';d.innerHTML=`<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(255,255,255,0.95);z-index:10000;display:flex;align-items:center;justify-content:center;"><div style="text-align:center;font-size:18px;font-weight:600;color:#333;">Loading HD-41...</div></div>`;document.body.appendChild(d);}
function hideLoading(){const e=document.getElementById('loading-screen');if(e)e.remove();}

function initMap(){
    map=L.map('map').setView([26.245,-98.23],12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap',maxZoom:18}).addTo(map);
    markerClusterGroup=L.markerClusterGroup({maxClusterRadius:25,spiderfyOnMaxZoom:true,showCoverageOnHover:false,zoomToBoundsOnClick:true,disableClusteringAtZoom:16,iconCreateFunction:()=>L.divIcon({html:'',className:'invisible-cluster',iconSize:L.point(1,1)})});
    map.addLayer(markerClusterGroup);
    map.on('zoomend',()=>{
        const z=map.getZoom();
        // Heatmap: hide at street level
        if(heatLayer){if(z>=16&&map.hasLayer(heatLayer))map.removeLayer(heatLayer);else if(z<16&&!map.hasLayer(heatLayer)&&currentMain==='voters')heatLayer.addTo(map);}
        // Street-level transition: show voter dots when zoomed in on precinct views
        if(currentMain!=='voters'){
            if(z>=16&&!markerClusterGroup.getLayers().length){
                // Add voter dots at street level
                addVoterDotsForView();
            } else if(z<16&&markerClusterGroup.getLayers().length&&precinctLayer){
                // Remove dots, show precincts
                markerClusterGroup.clearLayers();
            }
        }
    });
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
        await loadYardSigns();
        setupListeners();
        render();
        hideLoading();
    }catch(e){hideLoading();console.error(e);}
}

function setupListeners(){
    const mainSel=document.getElementById('main-select');
    const subSel=document.getElementById('sub-select');
    const boundSel=document.getElementById('boundary-select');

    // Ensure sub-select is hidden on load
    subSel.style.cssText='display:none !important;';

    mainSel.addEventListener('change',e=>{
        currentMain=e.target.value;
        // Show sub-dropdown ONLY for candidate selections
        if(currentMain.startsWith('cand-')){
            subSel.style.cssText='display:inline-block !important;';
            candidateSubView=subSel.value||'won';
            // Update sub-select label based on party
            const isDem=currentMain.includes('seby')||currentMain.includes('julio');
            subSel.querySelector('[value="partyvotes"]').textContent=isDem?'🔵 All Dem Votes':'🔴 All GOP Votes';
        } else {
            subSel.style.cssText='display:none !important;';
        }
        render();
    });
    subSel.addEventListener('change',e=>{candidateSubView=e.target.value;render();});
    boundSel.addEventListener('change',e=>updateBoundaries(e.target.value));

    document.getElementById('location-btn').addEventListener('click',()=>{if(navigator.geolocation)navigator.geolocation.getCurrentPosition(p=>map.setView([p.coords.latitude,p.coords.longitude],15));});
    document.getElementById('reportcard-btn').addEventListener('click',()=>{if(!window.__subscribed){showPaywall();return;}toggleReportCard();});
    document.getElementById('reportcard-close').addEventListener('click',()=>document.getElementById('reportcard-panel').classList.remove('visible'));

    // Mobile
    const mb=document.getElementById('mobile-menu-btn'),md=document.getElementById('mobile-drawer');
    if(mb&&md){mb.addEventListener('click',()=>md.classList.toggle('visible'));document.addEventListener('click',e=>{if(!md.contains(e.target)&&e.target!==mb)md.classList.remove('visible');});}
    const mms=document.getElementById('main-select-mobile');
    if(mms)mms.addEventListener('change',e=>{
        mainSel.value=e.target.value;mainSel.dispatchEvent(new Event('change'));
        const mobileSubWrapper=document.getElementById('sub-select-mobile-wrapper');
        if(mobileSubWrapper)mobileSubWrapper.style.display=e.target.value.startsWith('cand-')?'block':'none';
    });
    const mss=document.getElementById('sub-select-mobile');
    if(mss)mss.addEventListener('change',e=>{subSel.value=e.target.value;candidateSubView=e.target.value;render();});
    const mbs=document.getElementById('boundary-select-mobile');
    if(mbs)mbs.addEventListener('change',e=>{boundSel.value=e.target.value;updateBoundaries(e.target.value);});
    const mrc=document.getElementById('reportcard-btn-mobile');
    if(mrc)mrc.addEventListener('click',()=>{if(md)md.classList.remove('visible');toggleReportCard();});
}

function render(){
    if(currentMain==='voters')renderVoters();
    else if(currentMain==='yardsigns')renderYardSigns();
    else if(!window.__subscribed){showPaywall();return;}
    else if(currentMain==='party-all')renderParty('combined');
    else if(currentMain==='party-dem')renderParty('dem');
    else if(currentMain==='party-rep')renderParty('rep');
    else if(currentMain.startsWith('cand-'))renderCandidate();
}

function showPaywall(){
    clearLayers();
    // Show paywall modal
    let modal=document.getElementById('paywall-modal');
    if(!modal){
        modal=document.createElement('div');modal.id='paywall-modal';
        modal.innerHTML=`<div style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:5000;display:flex;align-items:center;justify-content:center;padding:20px;box-sizing:border-box;">
            <div style="background:white;border-radius:12px;padding:32px;max-width:420px;width:100%;text-align:center;box-shadow:0 8px 40px rgba(0,0,0,0.3);">
                <div style="font-size:40px;margin-bottom:12px;">🔒</div>
                <h2 style="margin:0 0 8px;font-size:22px;color:#1a1a1a;">Subscribers Only</h2>
                <p style="color:#666;font-size:14px;line-height:1.5;margin:0 0 20px;">Precinct analysis, candidate maps, voter details, and report cards require a subscription. The heatmap view is free.</p>
                <a href="/hd41/subscribe" style="display:inline-block;background:#0066cc;color:white;padding:12px 32px;border-radius:6px;text-decoration:none;font-weight:600;font-size:15px;">Subscribe — $10</a>
                <div style="margin-top:12px;"><button onclick="document.getElementById('paywall-modal').remove();document.getElementById('main-select').value='voters';currentMain='voters';render();" style="background:none;border:none;color:#888;cursor:pointer;font-size:13px;">← Back to free heatmap</button></div>
            </div>
        </div>`;
        document.body.appendChild(modal);
    }
}

function getSelectedCandidate(){
    const map={'cand-seby':"Victor 'Seby' Haddad",'cand-julio':"Julio Salinas",'cand-sergio':"Sergio Sanchez",'cand-gary':"Gary Groves"};
    return map[currentMain]||'';
}
function getOpponent(candName){
    if(candName.includes('Haddad'))return"Julio Salinas";if(candName.includes('Salinas'))return"Victor 'Seby' Haddad";
    if(candName.includes('Sanchez'))return"Gary Groves";if(candName.includes('Groves'))return"Sergio Sanchez";return'';
}
function getEliminated(candName){
    if(candName.includes('Haddad')||candName.includes('Salinas'))return"Eric Holguín";
    return"Sarah Sagredo-Hammond";
}
function getPartyKey(candName){return(candName.includes('Haddad')||candName.includes('Salinas')||candName.includes('Holgu'))?'dem_candidates':'rep_candidates';}
function shortName(c){return c.replace("Victor 'Seby' ","Seby ").replace("Sarah Sagredo-","S-").split(' ').slice(0,2).join(' ');}

// ═══ VOTER MAP ═══
function renderVoters(){
    clearLayers();if(!voterData||!voterData.voters)return;
    const hp=[];
    const yardSignLookup=window.__yardSigns||{};
    for(const v of voterData.voters){if(!v.lat||!v.lng)continue;hp.push([v.lat,v.lng,0.5]);
        const ys=yardSignLookup[v.vuid];
        const activeCand=currentMain.startsWith('cand-')?getSelectedCandidate():'';
        const isHostile=ys&&(activeCand?isHostileToCandidate(ys.candidate,activeCand):isHostileSign(v.party_voted,ys.candidate));
        const isFriendly=ys&&activeCand&&ys.candidate===activeCand;
        const color=v.party_voted==='Democratic'?'#1E90FF':v.party_voted==='Republican'?'#DC143C':'#888';
        const marker=L.circleMarker([v.lat,v.lng],{radius:9,fillColor:color,color:isHostile?'#FF8C00':isFriendly?'#4caf50':'#fff',weight:isHostile?3:2,opacity:1,fillOpacity:0.8});
        if(isHostile){
            const flag=L.marker([v.lat,v.lng],{interactive:false,icon:L.divIcon({html:'<div style="font-size:14px;transform:rotate(-15deg);text-shadow:0 1px 2px rgba(0,0,0,0.5);pointer-events:none;">⚠️</div>',className:'',iconSize:[16,16],iconAnchor:[8,20]})});
            markerClusterGroup.addLayer(flag);
        }
        if(isFriendly){
            const isSeby=ys.candidate.includes('Haddad');
            const signHtml=isSeby?'<img src="../assets/sebyhead.png" style="width:28px;height:auto;border-radius:50%;transform:rotate(5deg);box-shadow:0 2px 4px rgba(0,0,0,0.4);">':'<div style="font-size:14px;transform:rotate(5deg);text-shadow:0 1px 2px rgba(0,0,0,0.5);pointer-events:none;">🪧</div>';
            const sign=L.marker([v.lat,v.lng],{interactive:false,icon:L.divIcon({html:signHtml,className:'',iconSize:[28,28],iconAnchor:[14,30]})});
            markerClusterGroup.addLayer(sign);
        }
        if(window.__subscribed){
            marker.bindPopup(()=>buildVoterPopup(v),{maxWidth:380});
        } else {
            marker.on('click',()=>showPaywall());
        }
        markerClusterGroup.addLayer(marker);}
    if(hp.length){heatLayer=L.heatLayer(hp,{radius:15,blur:20,maxZoom:15});heatLayer.addTo(map);}
    updateStrip(`${voterData.count.toLocaleString()} voters · Zoom in for detail · Click for voter info + history`);
}

// ═══ YARD SIGNS MAP ═══
function renderYardSigns(){
    clearLayers();
    if(!voterData||!voterData.voters)return;
    const ysl=window.__yardSigns||{};
    const signVuids=Object.keys(ysl);
    if(!signVuids.length){updateStrip('🪧 No yard signs recorded yet. Zoom in on the Voter Map and mark signs from voter popups.');return;}

    const voterLookup={};
    for(const v of voterData.voters)voterLookup[v.vuid]=v;

    let friendly=0,hostile=0;
    const candCounts={};

    for(const vuid of signVuids){
        const v=voterLookup[vuid];
        if(!v||!v.lat||!v.lng)continue;
        const ys=ysl[vuid];
        const isH=isHostileSign(v.party_voted,ys.candidate);
        if(isH)hostile++;else friendly++;
        candCounts[ys.candidate]=(candCounts[ys.candidate]||0)+1;

        if(!window.__subscribed){
            // Non-subscriber: gray dot, paywall on click
            const marker=L.circleMarker([v.lat,v.lng],{radius:8,fillColor:'#999',color:'#666',weight:2,opacity:1,fillOpacity:0.7});
            marker.on('click',()=>showPaywall());
            markerClusterGroup.addLayer(marker);
            continue;
        }

        // Subscriber: full color + hostile flags
        let color;
        if(ys.candidate.includes('Haddad'))color='#1565c0';
        else if(ys.candidate.includes('Salinas'))color='#2e7d32';
        else if(ys.candidate.includes('Sanchez'))color='#c62828';
        else if(ys.candidate.includes('Groves'))color='#e65100';
        else color='#666';

        const marker=L.circleMarker([v.lat,v.lng],{
            radius:8,fillColor:isH?'#FF8C00':color,color:isH?'#FF4500':'#fff',weight:3,opacity:1,fillOpacity:0.9
        });

        if(isH){
            const flag=L.marker([v.lat,v.lng],{icon:L.divIcon({html:'<div style="font-size:16px;transform:rotate(-15deg);text-shadow:0 1px 3px rgba(0,0,0,0.5);">⚠️</div>',className:'',iconSize:[18,18],iconAnchor:[9,22]})});
            markerClusterGroup.addLayer(flag);
        }

        marker.bindPopup(()=>{
            let h=`<div style="font-family:sans-serif;min-width:220px;">`;
            h+=`<div style="font-size:11px;color:#888;">${v.address||''}, ${v.city||''}</div>`;
            h+=`<div style="font-weight:700;font-size:13px;margin:4px 0;">${v.name}</div>`;
            h+=`<div style="font-size:12px;margin-bottom:6px;">Voted: <b>${v.party_voted}</b> · Pct ${v.precinct||'—'}</div>`;
            h+=`<div style="padding:8px;border-radius:6px;background:${isH?'#fff3e0':'#e8f5e9'};border:1px solid ${isH?'#ff8a00':'#4caf50'};">`;
            h+=`<div style="font-size:14px;font-weight:700;color:${isH?'#e65100':'#2e7d32'};">${isH?'⚠️ HOSTILE':'🪧'} ${ys.candidate}</div>`;
            if(isH)h+=`<div style="font-size:11px;color:#e65100;margin-top:2px;">This ${v.party_voted} voter has an opposing party sign!</div>`;
            h+=`</div>`;
            h+=`<button onclick="removeYardSign('${vuid}')" style="margin-top:8px;padding:4px 10px;font-size:11px;background:#eee;border:1px solid #ccc;border-radius:3px;cursor:pointer;">Remove sign</button>`;
            h+=`</div>`;
            return h;
        },{maxWidth:300});
        markerClusterGroup.addLayer(marker);
    }

    // Summary
    if(window.__subscribed){
        const candList=Object.entries(candCounts).sort((a,b)=>b[1]-a[1]).map(([c,n])=>`${c.split(' ').pop()}:${n}`).join(' · ');
        updateStrip(`🪧 <b>${signVuids.length} Yard Signs</b> · Friendly: ${friendly} · <span style="color:#e65100">Hostile: ${hostile}</span> · ${candList}`);
    } else {
        updateStrip(`🪧 <b>${signVuids.length} Yard Signs</b> spotted in HD-41 · Subscribe to see which candidates`);
    }
}

// ═══ PARTY VIEW ═══
function renderParty(mode){
    clearLayers();const pL={};for(const p of precinctData.precincts)pL[p.precinct]=p;
    precinctLayer=L.geoJSON(shapesData,{
        style:f=>{const p=pL[f.properties.db_precinct];if(!p)return{fillColor:'#ccc',fillOpacity:0.1,color:'#999',weight:1};
            let fc;if(mode==='combined'){const ds=p.dem_share;fc=ds>=80?'#0d47a1':ds>=65?'#7b1fa2':ds>=50?'#7b1fa2':ds>=35?'#880e4f':'#b71c1c';}
            else if(mode==='dem'){const w=p.dem_winner;fc=w&&w.includes('Haddad')?'#1565c0':w&&w.includes('Salinas')?'#2e7d32':w&&w.includes('Holgu')?'#f57f17':'#666';}
            else{const w=p.rep_winner;fc=w&&w.includes('Sanchez')?'#c62828':w&&w.includes('Groves')?'#e65100':w&&w.includes('Sagredo')?'#f9a825':'#666';}
            return{fillColor:fc,fillOpacity:0.6,color:'#222',weight:1.5};},
        onEachFeature:(f,l)=>{const p=pL[f.properties.db_precinct];if(p)l.bindPopup(()=>buildPartyPopup(p),{maxWidth:360});}
    }).addTo(map);
    if(mode==='combined')updateStrip(`DEM vs GOP · <span style="color:#0d47a1">■Strong D</span> <span style="color:#7b1fa2">■Lean D</span> <span style="color:#880e4f">■Lean R</span> <span style="color:#b71c1c">■Strong R</span>`);
    else if(mode==='dem')updateStrip(`Dem Primary · <span style="color:#1565c0">■Haddad</span> <span style="color:#2e7d32">■Salinas</span> <span style="color:#f57f17">■Holguín</span>`);
    else updateStrip(`GOP Primary · <span style="color:#c62828">■Sanchez</span> <span style="color:#e65100">■Groves</span> <span style="color:#f9a825">■Sagredo-Hammond</span>`);
}

// ═══ CANDIDATE VIEW ═══
function renderCandidate(){
    clearLayers();
    const candName=getSelectedCandidate();if(!candName||!candidateData)return;
    const cand=candidateData.candidates[candName];if(!cand)return;
    const oppName=getOpponent(candName);const elimName=getEliminated(candName);
    const pk=getPartyKey(candName);const isDem=pk==='dem_candidates';
    const pL={};for(const p of precinctData.precincts)pL[p.precinct]=p;
    const sv=candidateSubView;

    precinctLayer=L.geoJSON(shapesData,{
        style:f=>{
            const p=pL[f.properties.db_precinct];if(!p)return{fillColor:'#f5f5f5',fillOpacity:0.1,color:'#aaa',weight:1};
            const cands=p[pk]||{};const myV=cands[candName]||0;const oppV=cands[oppName]||0;const elimV=cands[elimName]||0;
            const total=Object.values(cands).reduce((s,v)=>s+v,0);
            const partyTotal=isDem?p.dem_votes:p.rep_votes;

            if(sv==='won'){
                if(myV>oppV)return{fillColor:'#1b5e20',fillOpacity:0.3+Math.min(0.5,myV/300*0.5),color:'#1b5e20',weight:2};
                return{fillColor:'#f5f5f5',fillOpacity:0.08,color:'#ccc',weight:1};
            }
            if(sv==='lost'){
                if(myV<=oppV&&total>0){const gap=oppV-myV;return{fillColor:'#c62828',fillOpacity:0.3+Math.min(0.5,gap/100*0.5),color:'#b71c1c',weight:2};}
                return{fillColor:'#f5f5f5',fillOpacity:0.08,color:'#ccc',weight:1};
            }
            if(sv==='myvotes'){
                if(myV===0)return{fillColor:'#f5f5f5',fillOpacity:0.08,color:'#ccc',weight:1};
                const max=300;const i=Math.min(1,myV/max);
                return{fillColor:isDem?'#1565c0':'#c62828',fillOpacity:0.15+i*0.6,color:'#333',weight:1.5};
            }
            if(sv==='partyvotes'){
                if(partyTotal===0)return{fillColor:'#f5f5f5',fillOpacity:0.08,color:'#ccc',weight:1};
                const max=500;const i=Math.min(1,partyTotal/max);
                return{fillColor:isDem?'#0d47a1':'#b71c1c',fillOpacity:0.15+i*0.6,color:'#333',weight:1.5};
            }
            if(sv==='mopup'){
                if(myV>oppV&&elimV>0)return{fillColor:'#1b5e20',fillOpacity:0.3+Math.min(0.5,elimV/150*0.5),color:'#1b5e20',weight:2};
                return{fillColor:myV>oppV?'#e8f5e9':'#f5f5f5',fillOpacity:0.08,color:'#ccc',weight:1};
            }
            if(sv==='otherparty'){
                // Show precincts where the OTHER party had more total votes than your party
                const myPartyTotal=isDem?p.dem_votes:p.rep_votes;
                const otherPartyTotal=isDem?p.rep_votes:p.dem_votes;
                if(otherPartyTotal>myPartyTotal){
                    const margin=otherPartyTotal-myPartyTotal;
                    const i=Math.min(1,margin/150);
                    return{fillColor:isDem?'#c62828':'#0d47a1',fillOpacity:0.3+i*0.5,color:isDem?'#b71c1c':'#1a237e',weight:2};
                }
                return{fillColor:'#f5f5f5',fillOpacity:0.08,color:'#ccc',weight:1};
            }
            return{fillColor:'#ccc',fillOpacity:0.1,color:'#999',weight:1};
        },
        onEachFeature:(f,l)=>{const p=pL[f.properties.db_precinct];if(p)l.bindPopup(()=>buildCandidatePopup(p,candName,oppName,elimName,pk,isDem),{maxWidth:360});}
    }).addTo(map);

    const sn=shortName(candName);
    if(sv==='won')updateStrip(`<b>${sn} — Where I Won</b> · Darker = more votes · Click for full breakdown`);
    else if(sv==='lost')updateStrip(`<b>${sn} — Where I Lost</b> · Darker = bigger gap · Click to see who beat you + how many votes needed`);
    else if(sv==='myvotes')updateStrip(`<b>${sn} — My Vote Count</b> · Darker = more votes for ${sn} in that precinct`);
    else if(sv==='partyvotes')updateStrip(`<b>${sn} — All ${isDem?'Dem':'GOP'} Votes</b> · Total ${isDem?'Democratic':'Republican'} ballots per precinct (the full universe)`);
    else if(sv==='mopup')updateStrip(`<b>${sn} \u2014 Mop-Up</b> \xB7 Precincts I won + ${shortName(elimName)}'s voters to absorb \xB7 Darker = more swing votes`);
    else if(sv==='otherparty')updateStrip(`<b>${sn} \u2014 Where ${isDem?'GOP':'Dem'} Won</b> \xB7 Precincts where the other party had more total ballots \xB7 Darker = bigger ${isDem?'Republican':'Democratic'} advantage`);
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
    const m=v.voting_method||'';if(m==='early-voting')h+=`<div style="color:#2E7D32;font-size:11px;font-weight:600;">✓ Early Voter</div>`;else if(m==='mail-in')h+=`<div style="color:#6A1B9A;font-size:11px;font-weight:600;">📬 Mail-In</div>`;else if(m==='election-day')h+=`<div style="color:#E65100;font-size:11px;font-weight:600;">📍 Election Day</div>`;
    // Voting history
    const hx=v.hist||[];if(hx.length){h+='<div style="font-size:10px;font-weight:600;color:#555;margin-top:4px;">Voting History</div><table style="border-collapse:collapse;margin-top:2px;width:100%;"><tr>';hx.forEach(e=>{h+=`<td style="padding:1px 2px;font-size:8px;color:#888;text-align:center;border:1px solid #e0e0e0;background:#f5f5f5;">${(e.y||'').slice(-2)}</td>`;});h+='</tr><tr>';hx.forEach(e=>{const bg=e.p==='D'?'#1E90FF':e.p==='R'?'#DC143C':'#888';h+=`<td style="padding:3px 2px;text-align:center;border:1px solid #e0e0e0;background:${bg};color:white;font-size:11px;font-weight:700;">${e.p}</td>`;});h+='</tr></table>';}
    // Yard sign field
    const ys=(window.__yardSigns||{})[v.vuid];
    const isHostile=ys&&isHostileSign(v.party_voted,ys.candidate);
    h+=`<div style="margin-top:8px;padding:6px;border:1px solid ${isHostile?'#ff8a00':'#e0e0e0'};border-radius:4px;background:${isHostile?'#fff3e0':'#f9f9f9'};">`;
    h+=`<div style="font-size:10px;font-weight:600;color:#555;margin-bottom:4px;">🪧 Yard Sign</div>`;
    if(ys){
        h+=`<div style="font-size:12px;font-weight:600;color:${isHostile?'#e65100':'#2e7d32'};">${isHostile?'⚠️ HOSTILE — ':'✓ '}${ys.candidate}</div>`;
        h+=`<button onclick="removeYardSign('${v.vuid}')" style="margin-top:4px;padding:3px 8px;font-size:10px;background:#eee;border:1px solid #ccc;border-radius:3px;cursor:pointer;">Remove</button>`;
    } else {
        h+=`<select onchange="saveYardSign('${v.vuid}',this.value,${v.lat},${v.lng})" style="width:100%;padding:4px;font-size:12px;border:1px solid #ddd;border-radius:3px;">`;
        h+=`<option value="">No yard sign</option>`;
        h+=`<option value="Victor 'Seby' Haddad">Seby Haddad</option>`;
        h+=`<option value="Julio Salinas">Julio Salinas</option>`;
        h+=`<option value="Sergio Sanchez">Sergio Sanchez</option>`;
        h+=`<option value="Gary Groves">Gary Groves</option>`;
        h+=`</select>`;
    }
    h+=`</div>`;
    h+=`</div>`;
    return h;
}

function buildPartyPopup(p){
    let h=`<div style="font-family:sans-serif;min-width:300px"><div style="font-weight:700;font-size:15px;border-bottom:2px solid #333;padding-bottom:4px;margin-bottom:8px;">Precinct ${p.precinct}</div>`;
    h+=`<div style="display:flex;gap:12px;"><div style="flex:1;"><div style="font-weight:700;color:#1565c0;font-size:12px;border-bottom:2px solid #1565c0;padding-bottom:2px;margin-bottom:4px;">🔵 DEM (${p.dem_votes})</div>`;
    if(p.dem_candidates){Object.entries(p.dem_candidates).sort((a,b)=>b[1]-a[1]).forEach(([c,v],i)=>{h+=`<div style="font-size:11px;padding:2px 0;${i===0?'font-weight:700':''};">${i===0?'👑 ':''}${shortName(c)}: ${v}</div>`;});}
    h+=`</div><div style="flex:1;"><div style="font-weight:700;color:#c62828;font-size:12px;border-bottom:2px solid #c62828;padding-bottom:2px;margin-bottom:4px;">🔴 GOP (${p.rep_votes})</div>`;
    if(p.rep_candidates){Object.entries(p.rep_candidates).sort((a,b)=>b[1]-a[1]).forEach(([c,v],i)=>{h+=`<div style="font-size:11px;padding:2px 0;${i===0?'font-weight:700':''};">${i===0?'👑 ':''}${c}: ${v}</div>`;});}
    h+=`</div></div><div style="margin-top:8px;padding:6px;background:#f5f5f5;border-radius:4px;font-size:11px;"><b>Total:</b> ${p.total_votes} · <b>Winner:</b> ${p.winner} +${p.margin_votes} (${p.margin_pct}%) · <b>Turnout:</b> ${p.turnout_pct}%</div></div>`;return h;
}

function buildCandidatePopup(p,candName,oppName,elimName,pk,isDem){
    const cands=p[pk]||{};const myV=cands[candName]||0;const oppV=cands[oppName]||0;const elimV=cands[elimName]||0;
    const total=Object.values(cands).reduce((s,v)=>s+v,0);const share=total>0?(myV/total*100).toFixed(1):0;
    const won=myV>oppV;const sn=shortName(candName);const so=shortName(oppName);const se=shortName(elimName);
    let h=`<div style="font-family:sans-serif;min-width:280px"><div style="font-weight:700;font-size:15px;border-bottom:2px solid #333;padding-bottom:4px;margin-bottom:8px;">Precinct ${p.precinct}</div>`;
    // Status
    if(won&&elimV>0){h+=`<div style="padding:8px;border-radius:6px;background:#e8f5e9;border:2px solid #4caf50;margin-bottom:10px;"><div style="font-size:11px;color:#2e7d32;font-weight:700;">✓ ${sn.toUpperCase()}'S TURF — MOP-UP</div><div style="font-size:24px;font-weight:700;color:#1b5e20;margin:2px 0;">${elimV}</div><div style="font-size:12px;">${se}'s voters to absorb</div></div>`;}
    else if(won){h+=`<div style="padding:8px;border-radius:6px;background:#e8f5e9;margin-bottom:10px;"><div style="font-weight:700;color:#2e7d32;">✓ WON — ${myV} votes (${share}%)</div></div>`;}
    else{h+=`<div style="padding:8px;border-radius:6px;background:#fce4ec;margin-bottom:10px;"><div style="font-weight:700;color:#c62828;">✗ LOST — ${myV} votes (${share}%)</div><div style="font-size:11px;color:#666;">Gap: ${oppV-myV} votes behind ${so}</div></div>`;}
    // All candidates ranked
    h+=`<table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:8px;">`;
    Object.entries(cands).sort((a,b)=>b[1]-a[1]).forEach(([c,v])=>{const isMe=c===candName;const isElim=c===elimName;const pct=total>0?(v/total*100).toFixed(0):'0';h+=`<tr style="${isMe?'background:#e3f2fd;font-weight:700;':isElim?'background:#fff3e0;':''}"><td style="padding:4px;">${v===Math.max(...Object.values(cands))?'👑 ':''}${isElim?'🔥 ':''}${shortName(c)}</td><td style="padding:4px;text-align:right;font-weight:700;">${v}</td><td style="padding:4px;text-align:right;color:#666;">${pct}%</td></tr>`;});
    h+=`</table>`;
    // Projection
    if(won&&elimV>0){h+=`<div style="padding:6px;background:#f1f8e9;border-radius:4px;font-size:11px;"><b>Win all ${elimV}:</b> ${myV+elimV} vs ${so}'s ${oppV} · <b>Margin: +${myV+elimV-oppV}</b></div>`;}
    else if(!won){h+=`<div style="padding:6px;background:#fff8e1;border-radius:4px;font-size:11px;"><b>Need ${oppV-myV+1} more votes</b> to win${elimV>0?` · ${elimV} ${se} voters up for grabs`:''}</div>`;}
    h+=`</div>`;return h;
}

// ═══ BOUNDARIES ═══
function updateBoundaries(mode){
    if(boundaryLayer&&map.hasLayer(boundaryLayer))map.removeLayer(boundaryLayer);
    if(precinctOutlineLayer&&map.hasLayer(precinctOutlineLayer))map.removeLayer(precinctOutlineLayer);
    if(mode==='district'||mode==='both'){if(boundaryLayer)boundaryLayer.addTo(map);}
    if(mode==='precincts'||mode==='both'){if(!precinctOutlineLayer&&shapesData)precinctOutlineLayer=L.geoJSON(shapesData,{style:{color:'#555',weight:1.5,fillOpacity:0,dashArray:'3,3'},onEachFeature:(f,l)=>{l.bindTooltip('Pct '+f.properties.db_precinct,{permanent:false,direction:'center'});}});if(precinctOutlineLayer)precinctOutlineLayer.addTo(map);}
}

// ═══ HELPERS ═══
function isHostileSign(voterParty, signCandidate){
    // Hostile = yard sign for the other party's candidate
    const demCands=["Victor 'Seby' Haddad","Julio Salinas","Eric Holguín"];
    const repCands=["Sergio Sanchez","Gary Groves","Sarah Sagredo-Hammond"];
    if(voterParty==='Democratic'&&repCands.includes(signCandidate))return true;
    if(voterParty==='Republican'&&demCands.includes(signCandidate))return true;
    return false;
}

function isHostileToCandidate(signCandidate, selectedCand){
    // From a specific candidate's perspective: any sign that's NOT for them is hostile
    if(!selectedCand||!signCandidate)return false;
    return signCandidate!==selectedCand;
}

async function loadYardSigns(){
    try{
        const resp=await fetch('/api/hd41/yardsigns');
        if(resp.ok){const data=await resp.json();window.__yardSigns={};for(const s of(data.signs||[]))window.__yardSigns[s.vuid]=s;}
    }catch(e){}
}

function addVoterDotsForView(){
    if(!voterData||!voterData.voters||!window.__subscribed)return;
    markerClusterGroup.clearLayers();
    const bounds=map.getBounds();
    const yardSignLookup=window.__yardSigns||{};
    const activeCand=currentMain.startsWith('cand-')?getSelectedCandidate():'';

    for(const v of voterData.voters){
        if(!v.lat||!v.lng)continue;
        if(!bounds.contains([v.lat,v.lng]))continue;
        const ys=yardSignLookup[v.vuid];
        const isHostile=ys&&(activeCand?isHostileToCandidate(ys.candidate,activeCand):isHostileSign(v.party_voted,ys.candidate));
        const isFriendly=ys&&activeCand&&ys.candidate===activeCand;
        const color=v.party_voted==='Democratic'?'#1E90FF':v.party_voted==='Republican'?'#DC143C':'#888';
        const marker=L.circleMarker([v.lat,v.lng],{radius:9,fillColor:color,color:isHostile?'#FF8C00':isFriendly?'#4caf50':'#fff',weight:isHostile?3:2,opacity:1,fillOpacity:0.8});
        if(isHostile){
            const flag=L.marker([v.lat,v.lng],{interactive:false,icon:L.divIcon({html:'<div style="font-size:14px;transform:rotate(-15deg);text-shadow:0 1px 2px rgba(0,0,0,0.5);pointer-events:none;">⚠️</div>',className:'',iconSize:[16,16],iconAnchor:[8,20]})});
            markerClusterGroup.addLayer(flag);
        }
        if(isFriendly){
            const isSeby=ys.candidate.includes('Haddad');
            const signHtml=isSeby?'<img src="../assets/sebyhead.png" style="width:28px;height:auto;border-radius:50%;transform:rotate(5deg);box-shadow:0 2px 4px rgba(0,0,0,0.4);">':'<div style="font-size:14px;transform:rotate(5deg);text-shadow:0 1px 2px rgba(0,0,0,0.5);pointer-events:none;">🪧</div>';
            const sign=L.marker([v.lat,v.lng],{interactive:false,icon:L.divIcon({html:signHtml,className:'',iconSize:[28,28],iconAnchor:[14,30]})});
            markerClusterGroup.addLayer(sign);
        }
        marker.bindPopup(()=>buildVoterPopup(v),{maxWidth:380});
        markerClusterGroup.addLayer(marker);
    }
}

function clearLayers(){markerClusterGroup.clearLayers();if(heatLayer){map.removeLayer(heatLayer);heatLayer=null;}if(precinctLayer){map.removeLayer(precinctLayer);precinctLayer=null;}}
function updateStrip(html){const s=document.querySelector('.info-strip');if(s)s.innerHTML=html;}

// Yard sign save/remove (global for onclick handlers in popups)
window.saveYardSign=async function(vuid,candidate,lat,lng){
    if(!candidate){removeYardSign(vuid);return;}
    try{
        await fetch('/api/hd41/yardsign',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({vuid,candidate,lat,lng}),credentials:'include'});
        if(!window.__yardSigns)window.__yardSigns={};
        window.__yardSigns[vuid]={candidate,lat,lng};
        map.closePopup();render();
    }catch(e){console.error(e);}
};
window.removeYardSign=async function(vuid){
    try{
        await fetch(`/api/hd41/yardsign/${vuid}`,{method:'DELETE',credentials:'include'});
        if(window.__yardSigns)delete window.__yardSigns[vuid];
        map.closePopup();render();
    }catch(e){console.error(e);}
};

// ═══ REPORT CARD ═══
function toggleReportCard(){
    const panel=document.getElementById('reportcard-panel');
    if(!panel)return;
    panel.classList.toggle('visible');
    if(!panel.classList.contains('visible'))return;
    if(!precinctData||!precinctData.precincts)return;

    const sumEl=document.getElementById('reportcard-summary');
    const listEl=document.getElementById('reportcard-list');
    if(!sumEl||!listEl)return;

    const s=precinctData.summary;
    sumEl.innerHTML=`<div style="font-size:16px;font-weight:700;">HD-41 Official Canvass</div><div style="font-size:13px;color:#333;margin-top:4px;">${s.total_votes.toLocaleString()} total votes · 🔵 D: ${s.total_dem_votes.toLocaleString()} · 🔴 R: ${s.total_rep_votes.toLocaleString()}</div><div style="font-size:11px;color:#888;margin-top:2px;">${s.total_precincts} precincts · Source: Hidalgo County</div>`;

    const sorted=[...precinctData.precincts].sort((a,b)=>b.total_votes-a.total_votes);
    let html='';
    for(const p of sorted){
        const wc=p.winner==='Democratic'?'#1565c0':'#c62828';
        const wl=p.winner==='Democratic'?'D':'R';
        // Dem candidates summary
        let dl='';
        if(p.dem_candidates){
            const ds=Object.entries(p.dem_candidates).sort((a,b)=>b[1]-a[1]);
            dl=ds.map(([c,v])=>{
                const s=c.replace("Victor 'Seby' Haddad","Seby").replace("Julio Salinas","Julio").replace("Eric Holgu\u00EDn","Eric");
                return s+':'+v;
            }).join(' ');
        }
        // Rep candidates summary
        let rl='';
        if(p.rep_candidates){
            const rs=Object.entries(p.rep_candidates).sort((a,b)=>b[1]-a[1]);
            rl=rs.map(([c,v])=>{
                const s=c.replace("Sergio Sanchez","Sergio").replace("Gary Groves","Gary").replace("Sarah Sagredo-Hammond","Sarah");
                return s+':'+v;
            }).join(' ');
        }
        html+=`<div class="rc-row">`;
        html+=`<div class="rc-grade" style="background:${wc};font-size:11px;width:36px;height:36px;">${wl}</div>`;
        html+=`<div class="rc-info">`;
        html+=`<div class="rc-pct" style="font-size:13px;">Pct ${p.precinct} <span style="font-size:10px;color:#888;">(+${p.margin_votes} ${wl})</span></div>`;
        html+=`<div class="rc-detail" style="font-size:10px;">🔵 ${dl}</div>`;
        html+=`<div class="rc-detail" style="font-size:10px;">🔴 ${rl}</div>`;
        html+=`</div>`;
        html+=`<div style="width:50px;text-align:right;"><div style="font-weight:700;font-size:13px;">${p.total_votes}</div><div style="font-size:9px;color:#666;">${p.turnout_pct}%</div></div>`;
        html+=`</div>`;
    }
    listEl.innerHTML=html;
}

document.addEventListener('DOMContentLoaded',initMap);

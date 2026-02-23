// Data loading and management
let availableDatasets = [];
let currentDataset = null;

async function loadMapData() {
    try {
        console.log('Starting loadMapData...');
        
        // Show loading indicator
        const loadingIndicator = document.getElementById('map-loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'flex';
        }
        
        // First, discover all available datasets
        availableDatasets = await discoverDatasets();
        console.log('Available datasets:', availableDatasets);
        
        // Populate dataset selector
        populateDatasetSelector();
        
        // Load the most recent dataset by default
        if (availableDatasets.length > 0) {
            const defaultDataset = availableDatasets[0]; // Already sorted by date, most recent first
            console.log('Loading default dataset:', defaultDataset);
            await loadDataset(defaultDataset);
        } else {
            console.warn('No datasets found');
        }
        
        // Load metadata (this will be overridden by loadDataset, but kept for compatibility)
        await loadMetadata();
        
        // Update map view based on zoom
        map.on('zoomend', updateMapView);
        updateMapView();
        
        console.log('loadMapData completed successfully');
        
    } catch (error) {
        console.error('Error loading data:', error);
        console.error('Error stack:', error.stack);
    } finally {
        // Hide loading indicator
        const loadingIndicator = document.getElementById('map-loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
    }
}

function updateElectionYearsPanel() {
    const content = document.getElementById('layerControlContent');
    if (!content) return;
    
    if (!availableDatasets || availableDatasets.length === 0) {
        content.innerHTML = '<div class="layer-control-empty">No election data available</div>';
        return;
    }
    
    // Extract unique years from datasets
    const years = [...new Set(availableDatasets.map(d => d.year))].sort((a, b) => b - a);
    
    let html = '<div class="layer-list">';
    
    years.forEach(year => {
        // Count datasets for this year
        const datasetsForYear = availableDatasets.filter(d => d.year === year);
        const totalVoters = datasetsForYear.reduce((sum, d) => sum + d.totalAddresses, 0);
        
        html += `
            <div class="layer-item">
                <div class="layer-year-info">
                    <span class="layer-label">${year}</span>
                    <span class="layer-count">${totalVoters.toLocaleString()} voters</span>
                </div>
                <div class="layer-datasets">
        `;
        
        datasetsForYear.forEach((dataset, index) => {
            const datasetIndex = availableDatasets.indexOf(dataset);
            const votingMethodLabel = dataset.votingMethod === 'election-day' ? 'Election Day' : 'Early Voting';
            const electionTypeLabel = dataset.electionType.charAt(0).toUpperCase() + dataset.electionType.slice(1);
            
            html += `
                <div class="layer-dataset-item" onclick="selectDatasetFromPanel(${datasetIndex})">
                    <span>${dataset.county} ${electionTypeLabel} - ${votingMethodLabel}</span>
                    <span class="dataset-voter-count">${dataset.totalAddresses.toLocaleString()}</span>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    content.innerHTML = html;
}

async function selectDatasetFromPanel(index) {
    if (availableDatasets[index]) {
        // Update the dropdown selector
        const selector = document.getElementById('dataset-selector');
        if (selector) {
            selector.value = index;
        }
        
        // Load the dataset
        await loadDataset(availableDatasets[index]);
    }
}

async function discoverDatasets() {
    const datasets = [];
    
    try {
        // Call backend API to list all available datasets
        const response = await fetch('/admin/list-datasets');
        
        if (!response.ok) {
            console.error('Failed to fetch datasets from backend');
            return datasets;
        }
        
        const data = await response.json();
        
        if (data.success && data.datasets) {
            console.log(`Discovered ${data.datasets.length} datasets from backend`);
            
            // Group datasets by election (merge DEM/REP primaries into single dataset)
            const groupedDatasets = new Map();
            
            data.datasets.forEach(dataset => {
                // For early vote day snapshots, keep each as separate (for time-lapse)
                // For cumulative early vote, keep separate too
                // Only group non-early-vote DEM/REP primaries together
                const isEV = dataset.isEarlyVoting || false;
                const isCum = dataset.isCumulative || false;
                
                // Create key - early vote snapshots get unique keys per date/party
                // Cumulative and non-EV datasets group DEM+REP together (no party in key)
                const key = isEV && !isCum
                    ? `${dataset.county}_${dataset.year}_${dataset.electionType}_${dataset.votingMethod}_${dataset.electionDate}_${dataset.primaryParty}_${dataset.earlyVoteDay || ''}`
                    : isCum
                    ? `${dataset.county}_${dataset.year}_${dataset.electionType}_${dataset.votingMethod}_cumulative`
                    : `${dataset.county}_${dataset.year}_${dataset.electionType}_${dataset.votingMethod}_${dataset.electionDate}`;
                
                if (!groupedDatasets.has(key)) {
                    // First dataset for this election - store it
                    groupedDatasets.set(key, {
                        ...dataset,
                        isEarlyVoting: isEV,
                        isCumulative: isCum,
                        parties: [dataset.primaryParty].filter(p => p), // Array of parties
                        mapDataFiles: [dataset.mapDataFile], // Array of map data files to merge
                        totalAddresses: dataset.totalAddresses
                    });
                } else {
                    // Merge with existing dataset
                    const existing = groupedDatasets.get(key);
                    if (dataset.primaryParty) {
                        existing.parties.push(dataset.primaryParty);
                    }
                    existing.mapDataFiles.push(dataset.mapDataFile);
                    existing.totalAddresses += dataset.totalAddresses;
                }
            });
            
            // Convert map to array
            const mergedDatasets = Array.from(groupedDatasets.values());
            console.log(`Merged into ${mergedDatasets.length} combined datasets`);
            return mergedDatasets;
        } else {
            console.error('Backend returned invalid response:', data);
            return datasets;
        }
        
    } catch (error) {
        console.error('Error discovering datasets:', error);
    }
    
    return datasets;
}

function populateDatasetSelector() {
    const selector = document.getElementById('dataset-selector');
    if (!selector) return;
    
    selector.innerHTML = '';
    
    if (availableDatasets.length === 0) {
        selector.innerHTML = '<option value="">No datasets available</option>';
        selector.disabled = true;
        return;
    }
    
    // Separate cumulative early vote datasets and regular datasets
    // Hide individual day snapshots from dropdown (they're used by time-lapse only)
    const displayDatasets = [];
    
    availableDatasets.forEach((dataset, index) => {
        // Skip individual day snapshots — only show cumulative or non-early-vote
        if (dataset.isEarlyVoting && !dataset.isCumulative) return;
        displayDatasets.push({ dataset, index });
    });
    
    if (displayDatasets.length === 0) {
        selector.innerHTML = '<option value="">No datasets available</option>';
        selector.disabled = true;
        return;
    }
    
    displayDatasets.forEach(({ dataset, index }) => {
        const option = document.createElement('option');
        option.value = index;
        
        // Format label
        const votingMethodLabel = dataset.votingMethod === 'election-day' ? 'Election Day' : 'Early Voting';
        const electionTypeLabel = dataset.electionType.charAt(0).toUpperCase() + dataset.electionType.slice(1);
        // Only show party label if dataset has exactly one party (not merged DEM+REP)
        const parties = dataset.parties || [];
        const partyLabel = parties.length === 1 ? ` (${parties[0].charAt(0).toUpperCase() + parties[0].slice(1)})` : '';
        const cumulativeLabel = dataset.isCumulative ? ' [Cumulative]' : '';
        
        option.textContent = `${dataset.county} ${dataset.year} ${electionTypeLabel}${partyLabel} - ${votingMethodLabel}${cumulativeLabel} (${dataset.totalAddresses.toLocaleString()} voters)`;
        
        selector.appendChild(option);
    });
    
    // Add change event listener
    selector.addEventListener('change', async (e) => {
        const index = parseInt(e.target.value);
        if (!isNaN(index) && availableDatasets[index]) {
            await loadDataset(availableDatasets[index]);
        }
    });
    
    selector.disabled = false;
}

async function loadDataset(dataset) {
    try {
        console.log('Loading dataset:', dataset);
        
        // Show loading indicator
        const loadingIndicator = document.getElementById('map-loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'flex';
        }
        
        currentDataset = dataset;
        
        // If dataset has multiple map data files (DEM + REP), merge them
        let mergedGeojson = {
            type: 'FeatureCollection',
            features: []
        };
        
        const filesToLoad = dataset.mapDataFiles || [dataset.mapDataFile];
        console.log('Loading files:', filesToLoad);
        
        for (const mapDataFile of filesToLoad) {
            console.log('Fetching:', `data/${mapDataFile}`);
            const response = await fetch(`data/${mapDataFile}`);
            if (!response.ok) {
                console.error(`Failed to load ${mapDataFile}: ${response.status} ${response.statusText}`);
                continue;
            }
            
            const geojson = await response.json();
            console.log(`Loaded ${mapDataFile} with`, geojson.features ? geojson.features.length : 0, 'features');
            
            // Merge features
            if (geojson.features) {
                mergedGeojson.features.push(...geojson.features);
            }
        }
        
        console.log('Total merged features:', mergedGeojson.features.length);
        
        // Store the data globally
        window.mapData = mergedGeojson;
        
        // Reinitialize markers and heatmap with new data
        initializeDataLayers();
        
        // Update metadata display to show the selected dataset's info
        updateInfoStrip({
            successfully_geocoded: dataset.totalAddresses,
            last_updated: dataset.lastUpdated,
            county: dataset.county,
            year: dataset.year,
            election_type: dataset.electionType,
            voting_method: dataset.votingMethod
        });
        
        console.log(`Loaded ${dataset.mapDataFile} successfully`);
        
    } catch (error) {
        console.error('Error loading dataset:', error);
        alert(`Failed to load dataset: ${error.message}`);
    } finally {
        // Hide loading indicator
        const loadingIndicator = document.getElementById('map-loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
    }
}

/**
 * Update the dataset stats box below the logo
 */
function updateDatasetStatsBox() {
    const el = document.getElementById('dataset-stats-content');
    if (!el) return;
    
    const allFeatures = window.mapData ? window.mapData.features : [];
    if (!allFeatures.length) {
        el.innerHTML = 'No data loaded';
        return;
    }
    
    const ds = window.currentDataset || currentDataset;
    
    // Build title
    let title = '';
    if (ds) {
        const parts = [];
        if (ds.county) parts.push(ds.county + ' County');
        if (ds.year) parts.push(ds.year);
        if (ds.electionType) parts.push(ds.electionType.charAt(0).toUpperCase() + ds.electionType.slice(1));
        title = parts.join(' · ');
    }
    
    // Count party totals from all features
    let allDem = 0, allRep = 0, flippedToBlue = 0, flippedToRed = 0;
    allFeatures.forEach(f => {
        const p = f.properties;
        if (!p) return;
        const cur = (p.party_affiliation_current || '').toLowerCase();
        const prev = (p.party_affiliation_previous || '').toLowerCase();
        if (cur.includes('democrat')) allDem++;
        else if (cur.includes('republican')) allRep++;
        
        if (prev && cur) {
            const prevRep = prev.includes('republican');
            const prevDem = prev.includes('democrat');
            const curRep = cur.includes('republican');
            const curDem = cur.includes('democrat');
            if (prevRep && curDem) flippedToBlue++;
            if (prevDem && curRep) flippedToRed++;
        }
    });
    
    const totalAll = allFeatures.length;
    const flipFilter = typeof flippedVotersFilter !== 'undefined' ? flippedVotersFilter : 'none';
    const datasetManager = getDatasetManager();
    const partyFilter = datasetManager ? datasetManager.getPartyFilter() : 'all';
    
    let statsHtml = '';
    
    if (flipFilter === 'to-blue') {
        statsHtml = `
            <div class="stats-title">${title || 'Dataset'} — Flipped R→D</div>
            <div class="stats-row">
                <span class="stat-item" style="color:#6A1B9A">🟣 <span class="stat-value">${flippedToBlue.toLocaleString()}</span> voters flipped R→D</span>
            </div>
            <div class="stats-row" style="font-size:11px;color:#888;margin-top:2px;">of ${totalAll.toLocaleString()} total</div>`;
    } else if (flipFilter === 'to-red') {
        statsHtml = `
            <div class="stats-title">${title || 'Dataset'} — Flipped D→R</div>
            <div class="stats-row">
                <span class="stat-item" style="color:#C62828">🔴 <span class="stat-value">${flippedToRed.toLocaleString()}</span> voters flipped D→R</span>
            </div>
            <div class="stats-row" style="font-size:11px;color:#888;margin-top:2px;">of ${totalAll.toLocaleString()} total</div>`;
    } else if (partyFilter === 'democratic') {
        statsHtml = `
            <div class="stats-title">${title || 'Dataset'} — Democrats</div>
            <div class="stats-row">
                <span class="stat-item stat-dem">🔵 <span class="stat-value">${allDem.toLocaleString()}</span> Democratic voters</span>
            </div>
            <div class="stats-row" style="font-size:11px;color:#888;margin-top:2px;">of ${totalAll.toLocaleString()} total</div>`;
    } else if (partyFilter === 'republican') {
        statsHtml = `
            <div class="stats-title">${title || 'Dataset'} — Republicans</div>
            <div class="stats-row">
                <span class="stat-item stat-rep">🔴 <span class="stat-value">${allRep.toLocaleString()}</span> Republican voters</span>
            </div>
            <div class="stats-row" style="font-size:11px;color:#888;margin-top:2px;">of ${totalAll.toLocaleString()} total</div>`;
    } else {
        // Default: show all
        const totalFlipped = flippedToBlue + flippedToRed;
        statsHtml = `
            <div class="stats-title">${title || 'Dataset'}</div>
            <div class="stats-row">
                <span class="stat-item">📊 <span class="stat-value">${totalAll.toLocaleString()}</span> voters</span>
                <span class="stat-item stat-dem">🔵 <span class="stat-value">${allDem.toLocaleString()}</span></span>
                <span class="stat-item stat-rep">🔴 <span class="stat-value">${allRep.toLocaleString()}</span></span>
            </div>
            ${totalFlipped > 0 ? `<div class="stats-row" style="font-size:11px;color:#888;margin-top:2px;">🔄 ${totalFlipped.toLocaleString()} flipped (${flippedToBlue} R→D, ${flippedToRed} D→R)</div>` : ''}`;
    }
    
    el.innerHTML = statsHtml;
}

function initializeDataLayers() {
    if (!window.mapData || !window.mapData.features) {
        console.warn('No map data available');
        return;
    }
    
    console.log('Initializing data layers with', window.mapData.features.length, 'features');
    
    // Get current party filter from DatasetManager
    const datasetManager = getDatasetManager();
    const partyFilter = datasetManager.getPartyFilter();
    
    // Apply party filter if needed
    let features = window.mapData.features;
    if (partyFilter && partyFilter !== 'all') {
        const filterEngine = new PartyFilterEngine();
        features = filterEngine.filterByParty(features, partyFilter);
        console.log(`Applied ${partyFilter} filter, showing ${features.length} of ${window.mapData.features.length} features`);
    }
    
    // Clear existing layers
    if (markerClusterGroup) {
        markerClusterGroup.clearLayers();
    }
    
    // Create heatmap data arrays
    const heatmapData = [];
    const heatmapDataDemocratic = [];
    const heatmapDataRepublican = [];
    const heatmapDataFlipped = [];
    const addressGroups = {}; // Group voters by coordinate for numeric badges
    const bounds = L.latLngBounds();
    
    // Add markers for each voter
    features.forEach(feature => {
        // Skip features with no geometry (unmatched early vote records)
        if (!feature.geometry || !feature.geometry.coordinates) return;
        
        const coords = feature.geometry.coordinates;
        const props = feature.properties;
        
        const lat = coords[1];
        const lng = coords[0];
        
        // Skip features with null/invalid coordinates
        if (lat == null || lng == null || isNaN(lat) || isNaN(lng)) return;
        
        // Add to traditional heatmap
        heatmapData.push([lat, lng, 1]);
        
        // Add to party-specific heatmaps ONLY if no party filter is active
        // When filtering by party, only populate the relevant party's heatmap
        if (partyFilter === 'all' || !partyFilter) {
            // No filter active - populate both party heatmaps based on actual party
            const party = props.party_affiliation_current;
            if (party && party.toLowerCase().includes('democrat')) {
                heatmapDataDemocratic.push([lat, lng, 1]);
            } else if (party && party.toLowerCase().includes('republican')) {
                heatmapDataRepublican.push([lat, lng, 1]);
            }
        } else if (partyFilter === 'democratic') {
            // Democratic filter active - only populate Democratic heatmap
            heatmapDataDemocratic.push([lat, lng, 1]);
        } else if (partyFilter === 'republican') {
            // Republican filter active - only populate Republican heatmap
            heatmapDataRepublican.push([lat, lng, 1]);
        }
        
        // Extend bounds
        bounds.extend([lat, lng]);
        
        // Determine marker color based on party affiliation
        const markerColor = determineMarkerColor(props);
        
        // Collect flipped voter data for flipped heatmap
        if (markerColor === 'purple' || markerColor === 'maroon') {
            heatmapDataFlipped.push([lat, lng, 1]);
        }
        
        // Skip filtered-out voters (determineMarkerColor returns null when voter doesn't match active filter)
        if (markerColor === null) {
            return; // Skip this feature in forEach
        }
        
        // Group by coordinate key for household badges
        const coordKey = `${lat.toFixed(5)},${lng.toFixed(5)}`;
        if (!addressGroups[coordKey]) {
            addressGroups[coordKey] = [];
        }
        addressGroups[coordKey].push({ lat, lng, markerColor, props });
    });
    
    // Now create markers, grouping by address for numeric badges
    Object.values(addressGroups).forEach(group => {
        const { lat, lng } = group[0];
        const count = group.length;
        const showBadge = window.showNumericBadges && count > 1;
        
        // Use the first voter's color as the representative marker color
        const markerColor = group[0].markerColor;
        
        if (showBadge) {
            // Create a DivIcon marker with a numeric badge
            const fillColor = getMarkerFillColor(markerColor);
            const badgeIcon = L.divIcon({
                className: 'household-marker',
                html: `<div style="
                    width: 20px; height: 20px; border-radius: 50%;
                    background: ${fillColor}; border: 2px solid #fff;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.4);
                    position: relative;
                "><span style="
                    position: absolute; top: -10px; right: -10px;
                    background: rgba(0,0,0,0.75); color: #fff;
                    border-radius: 50%; width: 18px; height: 18px;
                    display: flex; align-items: center; justify-content: center;
                    font-size: 11px; font-weight: bold; border: 1px solid #fff;
                ">${count > 9 ? '9+' : count}</span></div>`,
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            });
            const marker = L.marker([lat, lng], { icon: badgeIcon });
            
            // Build popup with all voters at this address
            let popupContent = `<strong>Address:</strong> ${group[0].props.address || 'N/A'}<br>`;
            popupContent += `<strong>${count} voters at this address:</strong><br><hr style="margin:4px 0">`;
            group.forEach(v => {
                const voterName = v.props.name || [v.props.firstname, v.props.lastname].filter(Boolean).join(' ');
                if (voterName) popupContent += `${voterName}`;
                if (v.props.party_affiliation_current) popupContent += ` (${v.props.party_affiliation_current})`;
                if (v.props.party_affiliation_previous && v.props.party_affiliation_previous !== v.props.party_affiliation_current) {
                    const prev = v.props.party_affiliation_previous;
                    const cur = v.props.party_affiliation_current;
                    const color = cur.toLowerCase().includes('democrat') ? '#6A1B9A' : '#C62828';
                    popupContent += `<br><span style="color:${color};font-size:11px;">↩ Was ${prev}</span>`;
                }
                popupContent += `<br>`;
            });
            marker.bindPopup(popupContent);
            markerClusterGroup.addLayer(marker);
        } else {
            // Create individual markers for each voter
            group.forEach(v => {
                const marker = L.circleMarker([v.lat, v.lng], {
                    radius: 8,
                    fillColor: getMarkerFillColor(v.markerColor),
                    color: '#fff',
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8
                });
                
                let popupContent = `<strong>Address:</strong> ${v.props.address || 'N/A'}<br>`;
                const voterName = v.props.name || [v.props.firstname, v.props.lastname].filter(Boolean).join(' ');
                if (voterName) popupContent += `<strong>Name:</strong> ${voterName}<br>`;
                if (v.props.precinct) popupContent += `<strong>Precinct:</strong> ${v.props.precinct}<br>`;
                if (v.props.party_affiliation_current) popupContent += `<strong>Party:</strong> ${v.props.party_affiliation_current}<br>`;
                if (v.props.party_affiliation_previous && v.props.party_affiliation_previous !== v.props.party_affiliation_current) {
                    const prev = v.props.party_affiliation_previous;
                    const cur = v.props.party_affiliation_current;
                    const flipLabel = cur.toLowerCase().includes('democrat') ? 'R→D' : 'D→R';
                    const color = cur.toLowerCase().includes('democrat') ? '#6A1B9A' : '#C62828';
                    popupContent += `<strong style="color:${color}">Flipped:</strong> <span style="color:${color}">${prev} → ${cur} (${flipLabel})</span><br>`;
                }
                if (v.props.check_in) popupContent += `<strong>Voted:</strong> ${v.props.check_in}<br>`;
                
                marker.bindPopup(popupContent);
                markerClusterGroup.addLayer(marker);
            });
        }
    });
    
    console.log('Added', markerClusterGroup.getLayers().length, 'markers to cluster group');
    console.log('Created', heatmapData.length, 'heatmap points');
    console.log('Created', heatmapDataDemocratic.length, 'Democratic heatmap points');
    console.log('Created', heatmapDataRepublican.length, 'Republican heatmap points');
    console.log('Party filter:', partyFilter);
    console.log('Heatmap mode:', window.heatmapMode);
    
    // Update the stats box below the logo
    updateDatasetStatsBox();
    
    // Update heatmap layers with new data
    // CRITICAL: Remove layers from map BEFORE calling setLatLngs to avoid errors
    // IMPORTANT: Only update layers that have data to avoid internal Leaflet errors
    // Use setTimeout to avoid Leaflet internal state issues with _animating property
    
    // Update traditional heatmap (always has data)
    if (heatmapLayer) {
        // Remove from map before updating
        if (map && map.hasLayer(heatmapLayer)) {
            map.removeLayer(heatmapLayer);
        }
        // Defer the update to avoid internal Leaflet state issues
        setTimeout(() => {
            try {
                // Re-add to map briefly so canvas is available, then set data
                if (!map.hasLayer(heatmapLayer)) {
                    map.addLayer(heatmapLayer);
                }
                // Guard: ensure layer has valid map reference before updating
                if (heatmapLayer._map) {
                    heatmapLayer.setLatLngs(heatmapData);
                }
                // Remove again - updateMapView will decide what to show
                if (map.hasLayer(heatmapLayer)) {
                    map.removeLayer(heatmapLayer);
                }
                console.log('Updated traditional heatmap layer with', heatmapData.length, 'points');
            } catch (error) {
                console.error('Error updating traditional heatmap:', error);
            }
        }, 10);
    }
    
    // Update Democratic heatmap ONLY if it has data
    if (typeof heatmapLayerDemocratic !== 'undefined' && heatmapLayerDemocratic && heatmapDataDemocratic.length > 0) {
        // Remove from map before updating
        if (map && map.hasLayer(heatmapLayerDemocratic)) {
            map.removeLayer(heatmapLayerDemocratic);
        }
        // Defer the update to avoid internal Leaflet state issues
        setTimeout(() => {
            try {
                // Temporarily add to map so canvas is available
                if (!map.hasLayer(heatmapLayerDemocratic)) {
                    map.addLayer(heatmapLayerDemocratic);
                }
                if (heatmapLayerDemocratic._map) {
                    heatmapLayerDemocratic.setLatLngs(heatmapDataDemocratic);
                }
                // Remove again - updateMapView will decide what to show
                if (map.hasLayer(heatmapLayerDemocratic)) {
                    map.removeLayer(heatmapLayerDemocratic);
                }
                console.log('Updated Democratic heatmap layer with', heatmapDataDemocratic.length, 'points');
            } catch (error) {
                console.error('Error updating Democratic heatmap:', error);
            }
        }, 10);
    } else if (typeof heatmapLayerDemocratic !== 'undefined' && heatmapLayerDemocratic) {
        // If no data, just remove from map
        if (map && map.hasLayer(heatmapLayerDemocratic)) {
            map.removeLayer(heatmapLayerDemocratic);
        }
        console.log('Democratic heatmap has no data, cleared from map');
    }
    
    // Update Republican heatmap ONLY if it has data
    if (typeof heatmapLayerRepublican !== 'undefined' && heatmapLayerRepublican && heatmapDataRepublican.length > 0) {
        // Remove from map before updating
        if (map && map.hasLayer(heatmapLayerRepublican)) {
            map.removeLayer(heatmapLayerRepublican);
        }
        // Defer the update to avoid internal Leaflet state issues
        setTimeout(() => {
            try {
                // Temporarily add to map so canvas is available
                if (!map.hasLayer(heatmapLayerRepublican)) {
                    map.addLayer(heatmapLayerRepublican);
                }
                if (heatmapLayerRepublican._map) {
                    heatmapLayerRepublican.setLatLngs(heatmapDataRepublican);
                }
                // Remove again - updateMapView will decide what to show
                if (map.hasLayer(heatmapLayerRepublican)) {
                    map.removeLayer(heatmapLayerRepublican);
                }
                console.log('Updated Republican heatmap layer with', heatmapDataRepublican.length, 'points');
            } catch (error) {
                console.error('Error updating Republican heatmap:', error);
            }
        }, 10);
    } else if (typeof heatmapLayerRepublican !== 'undefined' && heatmapLayerRepublican) {
        // If no data, just remove from map
        if (map && map.hasLayer(heatmapLayerRepublican)) {
            map.removeLayer(heatmapLayerRepublican);
        }
        console.log('Republican heatmap has no data, cleared from map');
    }
    
    // Update flipped voters heatmap layer
    // Recreate the layer each time to ensure gradient color change takes effect
    // (Leaflet.heat caches the gradient palette internally)
    if (flippedHeatmapLayer) {
        if (map && map.hasLayer(flippedHeatmapLayer)) {
            map.removeLayer(flippedHeatmapLayer);
        }
    }
    
    if (heatmapDataFlipped.length > 0) {
        const flipColor = flippedVotersFilter === 'to-red' ? '#C62828' : '#6A1B9A';
        flippedHeatmapLayer = L.heatLayer(heatmapDataFlipped, {
            radius: 25,
            blur: 35,
            maxZoom: typeof config !== 'undefined' ? config.HEATMAP_MAX_ZOOM : 16,
            max: 1.0,
            minOpacity: 0.3,
            maxOpacity: 0.8,
            gradient: { 0.4: flipColor, 0.65: flipColor, 1: flipColor }
        });
        console.log('Recreated flipped heatmap layer with', heatmapDataFlipped.length, 'points, color:', flipColor);
    } else {
        console.log('Flipped heatmap has no data');
    }
    
    // Don't auto-zoom to fit data bounds - keep focused on Hidalgo County
    // Users can manually zoom/pan to see outlier data points
    
    // Defer updateMapView to run AFTER all heatmap setTimeout callbacks have fired
    // This ensures heatmap layers have their data before we decide which to show
    setTimeout(() => {
        updateMapView();
    }, 50);
    
    // Hide loading indicator after data layers are initialized
    const loadingIndicator = document.getElementById('map-loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
    }
}

async function detectAvailableYears() {
    const years = new Set();
    
    // Primary strategy: Check default metadata.json for the current year
    try {
        const metadataResponse = await fetch('data/metadata.json');
        if (metadataResponse.ok) {
            const metadata = await metadataResponse.json();
            if (metadata.year) {
                const year = typeof metadata.year === 'string' ? parseInt(metadata.year) : metadata.year;
                years.add(year);
                console.log(`Detected year from metadata.json: ${year}`);
            }
        }
    } catch (error) {
        console.warn('Could not load metadata.json:', error);
    }
    
    // Fallback strategy: Try to detect year-specific files
    // Check for common years (2020-2026)
    const currentYear = new Date().getFullYear();
    for (let year = 2020; year <= currentYear; year++) {
        try {
            // Try the simple pattern (for backward compatibility if files are renamed)
            const response = await fetch(`data/map_data_${year}.json`, { method: 'HEAD' });
            if (response.ok) {
                years.add(year);
            }
        } catch (error) {
            // File doesn't exist, skip
        }
    }
    
    // If no years detected, return empty array (will trigger loadDefaultData fallback)
    return Array.from(years).sort();
}

async function loadDefaultData() {
    try {
        console.log('Loading default data from data/map_data.json');
        
        // Load metadata first to get the correct year
        const metadataResponse = await fetch('data/metadata.json');
        let year = new Date().getFullYear(); // Fallback to current year
        
        if (metadataResponse.ok) {
            const metadata = await metadataResponse.json();
            if (metadata.year) {
                // Use year from metadata (could be string or number)
                year = typeof metadata.year === 'string' ? parseInt(metadata.year) : metadata.year;
                console.log(`Using year from metadata: ${year}`);
            } else {
                console.warn('metadata.json missing year field, using current year as fallback');
            }
        } else {
            console.warn('metadata.json not found, using current year as fallback');
        }
        
        // Load map data
        const response = await fetch('data/map_data.json');
        
        if (!response.ok) {
            throw new Error('Failed to load default data file');
        }
        
        const mapData = await response.json();
        console.log('Loaded map data:', mapData.features ? mapData.features.length : 0, 'features');
        
        // Use the year from metadata
        activeYears.add(year);
        
        // Process the data FIRST
        processYearData(year, mapData);
        
        // Update layer control with the correct year
        updateLayerControl([year]);
        const checkbox = document.getElementById(`layer-${year}`);
        if (checkbox) {
            checkbox.checked = true;
        }
        
        // Now show the layer after processing is complete
        showYearLayer(year);
        
    } catch (error) {
        console.error('Error loading default data:', error);
        throw error;
    }
}

async function loadMetadata() {
    try {
        const response = await fetch('data/metadata.json');
        
        if (!response.ok) {
            console.warn('Metadata file not found');
            return;
        }
        
        const metadata = await response.json();
        updateInfoStrip(metadata);
        
    } catch (error) {
        console.warn('Error loading metadata:', error);
    }
}


function updateInfoStrip(metadata) {
    const totalAddresses = document.getElementById('total-addresses');
    const lastUpdated = document.getElementById('last-updated');
    
    if (totalAddresses && metadata.successfully_geocoded) {
        totalAddresses.textContent = metadata.successfully_geocoded.toLocaleString();
    }
    
    if (lastUpdated && metadata.last_updated) {
        const date = new Date(metadata.last_updated);
        lastUpdated.textContent = date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }
}

// ============================================================================
// PARTY AFFILIATION DATA PARSING
// ============================================================================

/**
 * Parses and normalizes voter data to include party affiliation fields
 * @param {Object} rawVoterData - Raw voter data from JSON
 * @returns {Object} Normalized voter data with party affiliation fields
 */
function parseVoterData(rawVoterData) {
    return {
        // Coordinates
        lat: rawVoterData.lat || (rawVoterData.geometry?.coordinates?.[1]),
        lng: rawVoterData.lng || (rawVoterData.geometry?.coordinates?.[0]),
        
        // Basic info
        name: rawVoterData.name || rawVoterData.properties?.name,
        address: rawVoterData.address || rawVoterData.properties?.address,
        precinct: rawVoterData.precinct || rawVoterData.properties?.precinct,
        
        // Party affiliation fields (with defaults)
        party_affiliation_current: rawVoterData.party_affiliation_current || 
                                   rawVoterData.properties?.party_affiliation_current || 
                                   '',
        
        party_history: rawVoterData.party_history || 
                      rawVoterData.properties?.party_history || 
                      [],
        
        has_switched_parties: rawVoterData.has_switched_parties || 
                             rawVoterData.properties?.has_switched_parties || 
                             false,
        
        election_dates_participated: rawVoterData.election_dates_participated || 
                                    rawVoterData.properties?.election_dates_participated || 
                                    [],
        
        voted_in_current_election: rawVoterData.voted_in_current_election !== undefined ? 
                                  rawVoterData.voted_in_current_election : 
                                  (rawVoterData.properties?.voted_in_current_election !== undefined ? 
                                   rawVoterData.properties.voted_in_current_election : 
                                   false),
        
        is_registered: rawVoterData.is_registered !== undefined ? 
                      rawVoterData.is_registered : 
                      (rawVoterData.properties?.is_registered !== undefined ? 
                       rawVoterData.properties.is_registered : 
                       true), // Default to true if not specified
        
        household_voter_count: rawVoterData.household_voter_count || 
                              rawVoterData.properties?.household_voter_count || 
                              1
    };
}

/**
 * Loads election metadata including available election dates
 * @returns {Object} Metadata with elections array
 */
async function loadElectionMetadata() {
    try {
        const response = await fetch('data/metadata.json');
        
        if (!response.ok) {
            console.warn('Metadata file not found');
            return { elections: [] };
        }
        
        const metadata = await response.json();
        
        // Extract election information
        const elections = [];
        
        if (metadata.election) {
            elections.push({
                date: metadata.election.date,
                name: metadata.election.name || 'Election',
                type: metadata.election.type || 'general'
            });
        }
        
        // If there are multiple elections in the data
        if (metadata.elections && Array.isArray(metadata.elections)) {
            elections.push(...metadata.elections);
        }
        
        return { ...metadata, elections };
        
    } catch (error) {
        console.error('Error loading election metadata:', error);
        return { elections: [] };
    }
}

// ============================================================================
// DATASET MANAGER - State management for dataset selection and party filtering
// ============================================================================

/**
 * Manages dataset selection and party filter state with localStorage persistence
 * Handles graceful degradation if localStorage is unavailable
 */
class DatasetManager {
    constructor() {
        this.currentDataset = null;
        this.partyFilter = 'all'; // Default: show all voters
        this.selectedDatasetIndex = null;
        
        // Load saved state from localStorage
        this.loadState();
    }
    
    /**
     * Set the current dataset
     * @param {Object} dataset - Dataset object with metadata
     */
    setCurrentDataset(dataset) {
        this.currentDataset = dataset;
        this.saveState();
    }
    
    /**
     * Get the current dataset
     * @returns {Object|null} Current dataset or null if none selected
     */
    getCurrentDataset() {
        return this.currentDataset;
    }
    
    /**
     * Set the party filter value
     * @param {string} filterValue - Filter value: 'all', 'republican', or 'democratic'
     */
    setPartyFilter(filterValue) {
        if (!['all', 'republican', 'democratic'].includes(filterValue)) {
            console.warn(`Invalid party filter value: ${filterValue}, defaulting to 'all'`);
            filterValue = 'all';
        }
        this.partyFilter = filterValue;
        this.saveState();
    }
    
    /**
     * Get the current party filter value
     * @returns {string} Current filter value: 'all', 'republican', or 'democratic'
     */
    getPartyFilter() {
        return this.partyFilter;
    }
    
    /**
     * Set the selected dataset index
     * @param {number} index - Index of the selected dataset in the datasets array
     */
    setSelectedDatasetIndex(index) {
        this.selectedDatasetIndex = index;
        this.saveState();
    }
    
    /**
     * Get the selected dataset index
     * @returns {number|null} Selected dataset index or null if none selected
     */
    getSelectedDatasetIndex() {
        return this.selectedDatasetIndex;
    }
    
    /**
     * Check if the current dataset is a primary election
     * @returns {boolean} True if current dataset is a primary election
     */
    isPrimaryElection() {
        if (!this.currentDataset || !this.currentDataset.electionType) {
            return false;
        }
        return this.currentDataset.electionType.toLowerCase() === 'primary';
    }
    
    /**
     * Save current state to localStorage
     * Gracefully handles localStorage failures
     */
    saveState() {
        try {
            if (this.selectedDatasetIndex !== null) {
                localStorage.setItem('selectedDatasetIndex', this.selectedDatasetIndex.toString());
            }
            localStorage.setItem('partyFilter', this.partyFilter);
        } catch (error) {
            // localStorage may be unavailable (private browsing, quota exceeded, etc.)
            // Gracefully degrade to session-only state without showing error to user
            console.warn('Failed to save state to localStorage:', error.message);
        }
    }
    
    /**
     * Load saved state from localStorage
     * Gracefully handles localStorage failures and missing data
     */
    loadState() {
        try {
            const savedIndex = localStorage.getItem('selectedDatasetIndex');
            if (savedIndex !== null) {
                this.selectedDatasetIndex = parseInt(savedIndex, 10);
            }
            
            // Always default to 'all' on page load
            this.partyFilter = 'all';
        } catch (error) {
            console.warn('Failed to load state from localStorage:', error.message);
            this.selectedDatasetIndex = null;
            this.partyFilter = 'all';
        }
    }
}

// ============================================================================
// PARTY FILTER ENGINE - Filters voter data by party affiliation
// ============================================================================

/**
 * Filters voter data based on party affiliation criteria
 * Handles null/undefined party data gracefully with warning logging
 */
class PartyFilterEngine {
    /**
     * Filter GeoJSON features by party affiliation
     * @param {Array} features - Array of GeoJSON feature objects
     * @param {string} filterValue - Filter value: 'all', 'republican', or 'democratic'
     * @returns {Array} Filtered array of features
     */
    filterByParty(features, filterValue) {
        // Validate input
        if (!Array.isArray(features)) {
            console.warn('PartyFilterEngine.filterByParty: features is not an array');
            return [];
        }
        
        // Return all features if filter is 'all'
        if (filterValue === 'all') {
            return features;
        }
        
        // Debug: Log unique party values in the dataset
        if (features.length > 0) {
            const uniqueParties = [...new Set(features.map(f => f.properties?.party_affiliation_current).filter(p => p))];
            console.log('Unique party values in dataset:', uniqueParties);
            console.log('Filtering for:', filterValue);
        }
        
        // Filter features based on party affiliation
        return features.filter(feature => {
            return this.matchesPartyFilter(feature.properties, filterValue);
        });
    }
    
    /**
     * Check if voter properties match the party filter criteria
     * @param {Object} voterProperties - Voter properties object from GeoJSON feature
     * @param {string} filterValue - Filter value: 'republican' or 'democratic'
     * @returns {boolean} True if voter matches the filter criteria
     */
    matchesPartyFilter(voterProperties, filterValue) {
        const party = this.getPartyAffiliation(voterProperties);
        
        // Handle null/undefined party affiliation
        if (!party) {
            return false;
        }
        
        const partyLower = party.toLowerCase();
        
        if (filterValue === 'republican') {
            return partyLower.includes('republican') || partyLower.includes('rep');
        }
        
        if (filterValue === 'democratic') {
            return partyLower.includes('democrat') || partyLower.includes('dem');
        }
        
        return false;
    }
    
    /**
     * Extract party affiliation from voter properties with null/undefined handling
     * @param {Object} voterProperties - Voter properties object from GeoJSON feature
     * @returns {string|null} Party affiliation string or null if invalid
     */
    getPartyAffiliation(voterProperties) {
        // Handle null/undefined voterProperties
        if (!voterProperties) {
            console.warn('PartyFilterEngine.getPartyAffiliation: voterProperties is null or undefined');
            return null;
        }
        
        const party = voterProperties.party_affiliation_current;
        
        // Handle null/undefined party_affiliation_current
        if (party === null || party === undefined) {
            console.warn('PartyFilterEngine.getPartyAffiliation: party_affiliation_current is null or undefined for voter:', voterProperties);
            return null;
        }
        
        // Handle non-string party affiliation
        if (typeof party !== 'string') {
            console.warn('PartyFilterEngine.getPartyAffiliation: party_affiliation_current is not a string:', party, 'for voter:', voterProperties);
            return null;
        }
        
        return party;
    }
}

// ============================================================================
// GLOBAL INSTANCE INITIALIZATION
// ============================================================================

/**
 * Global DatasetManager instance
 * Initialized on application load with saved state from localStorage
 */
let datasetManager = null;

/**
 * Initialize the global DatasetManager instance
 * This should be called when the application loads
 */
function initializeDatasetManager() {
    if (!datasetManager) {
        datasetManager = new DatasetManager();
        console.log('DatasetManager initialized with state:', {
            selectedDatasetIndex: datasetManager.getSelectedDatasetIndex(),
            partyFilter: datasetManager.getPartyFilter()
        });
    }
    return datasetManager;
}

/**
 * Get the global DatasetManager instance
 * Creates one if it doesn't exist
 * @returns {DatasetManager} The global DatasetManager instance
 */
function getDatasetManager() {
    if (!datasetManager) {
        return initializeDatasetManager();
    }
    return datasetManager;
}

// Initialize DatasetManager when the script loads
initializeDatasetManager();

// Failsafe: Hide loading indicator after page load if still showing
window.addEventListener('load', () => {
    setTimeout(() => {
        const loadingIndicator = document.getElementById('map-loading-indicator');
        if (loadingIndicator && window.getComputedStyle(loadingIndicator).display !== 'none') {
            console.warn('Loading indicator still showing after page load, hiding it');
            loadingIndicator.style.display = 'none';
        }
    }, 5000); // Wait 5 seconds after page load
});

// ============================================================================
// EARLY VOTE DATA UTILITIES
// ============================================================================

/**
 * Deduplicate GeoJSON features by VUID, keeping the most recent early_vote_day
 * @param {Array} features - Array of GeoJSON features
 * @returns {Array} Deduplicated features
 */
function deduplicateByVUID(features) {
    const byVuid = {};
    features.forEach(f => {
        const vuid = f.properties && f.properties.vuid;
        if (!vuid) return;
        const existing = byVuid[vuid];
        if (!existing || (f.properties.early_vote_day || '') > (existing.properties.early_vote_day || '')) {
            byVuid[vuid] = f;
        }
    });
    return Object.values(byVuid);
}

/**
 * Filter features for map rendering — exclude unmatched/null geometry
 * @param {Array} features - Array of GeoJSON features
 * @returns {Object} { renderable: features for map, total: all count, unmatched: unmatched count }
 */
function filterEarlyVoteFeatures(features) {
    const renderable = features.filter(f => 
        f.geometry && f.geometry.coordinates && !f.properties.unmatched
    );
    const unmatchedCount = features.filter(f => f.properties && f.properties.unmatched).length;
    return { renderable, total: features.length, unmatched: unmatchedCount };
}

/**
 * Load all day snapshot files for time-lapse playback
 * @param {Array} datasets - Array of dataset objects from discoverDatasets
 * @param {string} county - County name
 * @param {string} year - Election year
 * @param {string} electionType - Election type
 * @param {string} party - Party (democratic/republican)
 * @returns {Array} Sorted array of { date, features } objects
 */
async function loadDaySnapshots(datasets, county, year, electionType, party) {
    // Find all day snapshot datasets (non-cumulative) matching criteria
    const snapshots = [];
    
    for (const ds of datasets) {
        if (ds.county !== county || ds.year !== year || ds.electionType !== electionType) continue;
        if (ds.isCumulative) continue;
        if (!ds.isEarlyVoting) continue;
        
        // Load the GeoJSON
        const files = ds.mapDataFiles || [ds.mapDataFile];
        for (const file of files) {
            // Check party match from filename
            const fileLower = file.toLowerCase();
            if (party && !fileLower.includes(party.toLowerCase())) continue;
            
            try {
                const response = await fetch(`data/${file}`);
                if (!response.ok) continue;
                const geojson = await response.json();
                
                // Extract date from filename (last part before .json)
                const parts = file.replace('.json', '').split('_');
                const datePart = parts[parts.length - 1];
                // Convert YYYYMMDD to YYYY-MM-DD
                const dateStr = datePart.length === 8 
                    ? `${datePart.slice(0,4)}-${datePart.slice(4,6)}-${datePart.slice(6,8)}`
                    : datePart;
                
                snapshots.push({
                    date: dateStr,
                    features: geojson.features || []
                });
            } catch (e) {
                console.warn(`Failed to load snapshot ${file}:`, e);
            }
        }
    }
    
    // Sort chronologically
    snapshots.sort((a, b) => a.date.localeCompare(b.date));
    return snapshots;
}

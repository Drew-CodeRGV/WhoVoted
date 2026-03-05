// Data loading and management
let availableDatasets = [];
let currentDataset = null;
let showRegisteredNotVoted = false;
let registeredNotVotedData = null;
let selectedCountyFilter = 'Hidalgo'; // Default to Hidalgo county

// Browser-side cache for voter popup details, keyed by "lat,lng" → voter array
const _voterDetailCache = new Map();
let _viewportPreloadInProgress = false;

// County overview layer for anonymous users (circle markers per county)
let countyOverviewLayer = null;
let _countyOverviewLoaded = false;

/**
 * Detect user's county via browser geolocation + reverse geocode.
 * Returns county name or 'Hidalgo' as fallback. Times out after 3s.
 */
async function detectUserCounty() {
    return new Promise((resolve) => {
        const timeout = setTimeout(() => resolve('Hidalgo'), 3000);
        if (!navigator.geolocation) { clearTimeout(timeout); resolve('Hidalgo'); return; }
        navigator.geolocation.getCurrentPosition(async (pos) => {
            try {
                const resp = await fetch(
                    `https://nominatim.openstreetmap.org/reverse?lat=${pos.coords.latitude}&lon=${pos.coords.longitude}&format=json&zoom=10`,
                    { signal: AbortSignal.timeout(2000) }
                );
                const data = await resp.json();
                let county = (data.address && data.address.county) || '';
                // Nominatim returns "Hidalgo County" — strip " County"
                county = county.replace(/\s+County$/i, '').trim();
                clearTimeout(timeout);
                resolve(county || 'Hidalgo');
            } catch { clearTimeout(timeout); resolve('Hidalgo'); }
        }, () => { clearTimeout(timeout); resolve('Hidalgo'); }, { timeout: 2500 });
    });
}

/**
 * Load lightweight county-level overview for anonymous (not-logged-in) users.
 * Uses the same Leaflet heatmap layer as logged-in users, but fed with one
 * data point per county (at the centroid) weighted by vote total.
 * Payload is ~7KB vs ~2MB+ for the full per-voter heatmap — same look, instant load.
 */
async function loadCountyOverview(electionDate, votingMethod) {
    try {
        console.log('Loading county overview heatmap (anonymous mode)...');
        const loadingIndicator = document.getElementById('map-loading-indicator');
        if (loadingIndicator) loadingIndicator.style.display = 'flex';

        const params = new URLSearchParams({ election_date: electionDate });
        if (votingMethod) params.set('voting_method', votingMethod);

        const resp = await fetch(`/api/county-overview?${params}`);
        if (!resp.ok) throw new Error(`API error: ${resp.status}`);
        const data = await resp.json();

        if (!data.success || !data.counties || !data.counties.length) {
            console.warn('No county overview data');
            return;
        }

        // Build heatmap data: [lat, lng, intensity] per county
        // Weight intensity by party margin to emphasize which party dominates
        const maxTotal = Math.max(...data.counties.map(c => c.total));
        const heatData = [];
        const heatDataDem = [];
        const heatDataRep = [];
        let grandTotal = 0, grandDem = 0, grandRep = 0;

        data.counties.forEach(c => {
            grandTotal += c.total;
            grandDem += c.dem;
            grandRep += c.rep;
            
            const baseIntensity = c.total / maxTotal;
            const demShare = c.dem / (c.dem + c.rep);
            const repShare = c.rep / (c.dem + c.rep);
            
            // Calculate margin of victory (0.5 = tie, 1.0 = 100% one party)
            const demMargin = demShare; // 0 to 1
            const repMargin = repShare; // 0 to 1
            
            // Amplify intensity based on margin - counties with bigger margins show darker/more vivid
            // Use stronger exponential scaling (0.5 instead of 0.7) for more dramatic color variation
            const demIntensity = baseIntensity * Math.pow(demMargin, 0.5);
            const repIntensity = baseIntensity * Math.pow(repMargin, 0.5);
            
            heatData.push([c.lat, c.lng, baseIntensity]);
            
            // Only show the color for the party that won, weighted by margin
            if (c.dem > c.rep) {
                heatDataDem.push([c.lat, c.lng, demIntensity]);
            } else if (c.rep > c.dem) {
                heatDataRep.push([c.lat, c.lng, repIntensity]);
            } else {
                // Tie - show both at half intensity
                heatDataDem.push([c.lat, c.lng, baseIntensity * 0.5]);
                heatDataRep.push([c.lat, c.lng, baseIntensity * 0.5]);
            }
        });

        // Remove any existing heatmap layers
        [heatmapLayer, heatmapLayerDemocratic, heatmapLayerRepublican].forEach(layer => {
            if (layer && map && map.hasLayer(layer)) map.removeLayer(layer);
        });

        // Create the traditional heatmap with county-level data (kept for compatibility)
        heatmapLayer = L.heatLayer(heatData, {
            radius: 50,
            blur: 40,
            maxZoom: typeof config !== 'undefined' ? config.HEATMAP_MAX_ZOOM : 16,
            max: 1.0,
            minOpacity: 0.3,
            maxOpacity: 0.8
        });

        // Democratic heatmap - GRADIENT FROM LIGHT TO BRIGHT DARK BLUE
        heatmapLayerDemocratic = L.heatLayer(heatDataDem, {
            radius: 55, 
            blur: 35,
            maxZoom: typeof config !== 'undefined' ? config.HEATMAP_MAX_ZOOM : 16,
            max: 1.0, 
            minOpacity: 0.5, 
            maxOpacity: 0.95,
            gradient: {
                0.0: 'rgba(173, 216, 255, 0)',      // Very light blue (toss-up)
                0.2: 'rgba(100, 180, 255, 0.6)',    // Light blue (lean)
                0.4: 'rgba(50, 140, 255, 0.75)',    // Medium blue (moderate)
                0.6: 'rgba(0, 100, 255, 0.85)',     // Bright blue (strong)
                0.8: 'rgba(0, 70, 220, 0.92)',      // Bright dark blue (landslide)
                1.0: 'rgba(0, 50, 200, 1.0)'        // Deep bright blue (overwhelming)
            }
        });

        // Republican heatmap - GRADIENT FROM LIGHT TO BRIGHT DARK RED
        heatmapLayerRepublican = L.heatLayer(heatDataRep, {
            radius: 55, 
            blur: 35,
            maxZoom: typeof config !== 'undefined' ? config.HEATMAP_MAX_ZOOM : 16,
            max: 1.0, 
            minOpacity: 0.5, 
            maxOpacity: 0.95,
            gradient: {
                0.0: 'rgba(255, 173, 173, 0)',      // Very light red/pink (toss-up)
                0.2: 'rgba(255, 100, 100, 0.6)',    // Light red (lean)
                0.4: 'rgba(255, 50, 50, 0.75)',     // Medium red (moderate)
                0.6: 'rgba(255, 0, 50, 0.85)',      // Bright red (strong)
                0.8: 'rgba(220, 0, 60, 0.92)',      // Bright dark red (landslide)
                1.0: 'rgba(200, 0, 70, 1.0)'        // Deep bright red (overwhelming)
            }
        });

        // DEFAULT: Show red vs blue party heatmap for county overview
        heatmapLayerDemocratic.addTo(map);
        heatmapLayerRepublican.addTo(map);
        
        // Set the mode so UI controls know what's active
        window.heatmapMode = 'party';

        // Add invisible markers for each county to enable popups
        if (!countyOverviewLayer) {
            countyOverviewLayer = L.layerGroup();
        } else {
            countyOverviewLayer.clearLayers();
        }
        
        data.counties.forEach(c => {
            const total = c.dem + c.rep;
            const demPct = total > 0 ? ((c.dem / total) * 100).toFixed(1) : 0;
            const repPct = total > 0 ? ((c.rep / total) * 100).toFixed(1) : 0;
            const winner = c.dem > c.rep ? 'Democratic' : c.rep > c.dem ? 'Republican' : 'Tie';
            const margin = Math.abs(c.dem - c.rep);
            const marginPct = total > 0 ? ((margin / total) * 100).toFixed(1) : 0;
            
            // Calculate color based on margin - deeper colors for bigger margins
            // marginPct ranges from 0 (50/50 tie) to 100 (100% one party)
            let fillColor, strokeColor;
            
            if (c.dem > c.rep) {
                // Democratic - varying shades of blue
                if (marginPct >= 60) {
                    // Landslide (80%+) - Deep navy blue
                    fillColor = '#001F5C';
                    strokeColor = '#003399';
                } else if (marginPct >= 40) {
                    // Strong (70-80%) - Dark blue
                    fillColor = '#0047AB';
                    strokeColor = '#0066CC';
                } else if (marginPct >= 20) {
                    // Moderate (60-70%) - Medium blue
                    fillColor = '#0066FF';
                    strokeColor = '#3399FF';
                } else if (marginPct >= 10) {
                    // Lean (55-60%) - Light blue
                    fillColor = '#4D94FF';
                    strokeColor = '#66B3FF';
                } else {
                    // Toss-up (50-55%) - Very light blue
                    fillColor = '#99CCFF';
                    strokeColor = '#B3D9FF';
                }
            } else if (c.rep > c.dem) {
                // Republican - varying shades of red
                if (marginPct >= 60) {
                    // Landslide (80%+) - Deep crimson
                    fillColor = '#8B0000';
                    strokeColor = '#B30000';
                } else if (marginPct >= 40) {
                    // Strong (70-80%) - Dark red
                    fillColor = '#CC0000';
                    strokeColor = '#E60000';
                } else if (marginPct >= 20) {
                    // Moderate (60-70%) - Medium red
                    fillColor = '#FF0000';
                    strokeColor = '#FF3333';
                } else if (marginPct >= 10) {
                    // Lean (55-60%) - Light red
                    fillColor = '#FF4D4D';
                    strokeColor = '#FF6666';
                } else {
                    // Toss-up (50-55%) - Very light red/pink
                    fillColor = '#FF9999';
                    strokeColor = '#FFB3B3';
                }
            } else {
                // Perfect tie - gray
                fillColor = '#888888';
                strokeColor = '#AAAAAA';
            }
            
            // Create invisible circle marker for popup functionality only
            const marker = L.circleMarker([c.lat, c.lng], {
                radius: 15,
                fillColor: fillColor,
                color: strokeColor,
                weight: 0,
                opacity: 0,
                fillOpacity: 0
            });
            
            // Show subtle marker on hover
            marker.on('mouseover', function() {
                this.setStyle({ 
                    opacity: 0.4, 
                    fillOpacity: 0.3,
                    weight: 2
                });
            });
            marker.on('mouseout', function() {
                this.setStyle({ 
                    opacity: 0, 
                    fillOpacity: 0,
                    weight: 0
                });
            });
            
            // Create popup with county stats
            const popupContent = `
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; min-width: 200px;">
                    <div style="font-size: 16px; font-weight: 700; margin-bottom: 8px; color: #333;">
                        ${c.county} County
                    </div>
                    <div style="font-size: 14px; font-weight: 600; color: ${fillColor}; margin-bottom: 10px;">
                        ${winner} +${marginPct}%
                    </div>
                    <div style="margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <span style="color: #0064FF; font-weight: 600;">🔵 Democratic</span>
                            <span style="font-weight: 700; color: #0064FF;">${demPct}%</span>
                        </div>
                        <div style="background: #e0e0e0; height: 6px; border-radius: 3px; overflow: hidden;">
                            <div style="background: #0064FF; height: 100%; width: ${demPct}%;"></div>
                        </div>
                        <div style="font-size: 12px; color: #666; margin-top: 2px;">
                            ${c.dem.toLocaleString()} votes
                        </div>
                    </div>
                    <div style="margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <span style="color: #E6003C; font-weight: 600;">🔴 Republican</span>
                            <span style="font-weight: 700; color: #E6003C;">${repPct}%</span>
                        </div>
                        <div style="background: #e0e0e0; height: 6px; border-radius: 3px; overflow: hidden;">
                            <div style="background: #E6003C; height: 100%; width: ${repPct}%;"></div>
                        </div>
                        <div style="font-size: 12px; color: #666; margin-top: 2px;">
                            ${c.rep.toLocaleString()} votes
                        </div>
                    </div>
                    <div style="border-top: 1px solid #ddd; padding-top: 8px; margin-top: 8px; font-size: 13px; color: #666;">
                        <strong>${total.toLocaleString()}</strong> total votes
                    </div>
                </div>
            `;
            
            marker.bindPopup(popupContent, {
                maxWidth: 300,
                className: 'county-popup'
            });
            
            countyOverviewLayer.addLayer(marker);
        });
        
        countyOverviewLayer.addTo(map);

        _countyOverviewLoaded = true;

        // Show aggregate stats
        const el = document.getElementById('dataset-stats-content');
        if (el) {
            el.innerHTML = `
                <div class="stats-title">Texas Early Voting Overview</div>
                <div class="stats-row">
                    <span class="stat-item">📊 <span class="stat-value">${grandTotal.toLocaleString()}</span> voters</span>
                    <span class="stat-item stat-dem">🔵 <span class="stat-value">${grandDem.toLocaleString()}</span></span>
                    <span class="stat-item stat-rep">🔴 <span class="stat-value">${grandRep.toLocaleString()}</span></span>
                </div>
                <div class="stats-row" style="font-size:11px;color:#888;margin-top:4px;">
                    Sign in for detailed voter-level data
                </div>`;
        }

        // Fit map to show all counties
        const bounds = L.latLngBounds(data.counties.map(c => [c.lat, c.lng]));
        if (bounds.isValid()) map.fitBounds(bounds, { padding: [30, 30], maxZoom: 9 });

        console.log(`County overview heatmap loaded: ${data.counties.length} counties, ${grandTotal} total voters`);
    } catch (err) {
        console.error('Error loading county overview:', err);
    } finally {
        const loadingIndicator = document.getElementById('map-loading-indicator');
        if (loadingIndicator) loadingIndicator.style.display = 'none';
    }
}
/**
 * Switch from county overview to full per-voter heatmap.
 * Called after user logs in.
 */
async function switchToFullHeatmap() {
    console.log('Switching from county overview to full heatmap...');

    // Remove county-level heatmap layers
    [heatmapLayer, heatmapLayerDemocratic, heatmapLayerRepublican].forEach(layer => {
        if (layer && map && map.hasLayer(layer)) map.removeLayer(layer);
    });
    // Also remove the old countyOverviewLayer if it was used
    if (countyOverviewLayer && map) {
        map.removeLayer(countyOverviewLayer);
        countyOverviewLayer = null;
    }
    _countyOverviewLoaded = false;

    // Re-run the full dataset controls init (detects county, loads heatmap)
    if (typeof initializeDatasetControls === 'function') {
        await initializeDatasetControls();
    }
}

/**
 * Preload voter details for all visible markers in the current viewport.
 * Called when user zooms past heatmap threshold. Fetches full voter data
 * from /api/voters with viewport bounds and indexes into _voterDetailCache.
 * Subsequent popup opens read from cache instantly.
 */
async function preloadViewportVoterDetails() {
    if (_viewportPreloadInProgress || !currentDataset || !window.authFullAccess) return;
    if (!map) return;
    
    _viewportPreloadInProgress = true;
    try {
        let counties;
        if (selectedCountyFilter !== 'all') {
            counties = [selectedCountyFilter];
        } else {
            counties = currentDataset.selectedCounties || currentDataset.counties || [currentDataset.county || 'Hidalgo'];
        }
        
        const bounds = map.getBounds();
        const params = new URLSearchParams({
            county: counties.join(','),
            election_date: currentDataset.electionDate,
            sw_lat: bounds.getSouthWest().lat,
            sw_lng: bounds.getSouthWest().lng,
            ne_lat: bounds.getNorthEast().lat,
            ne_lng: bounds.getNorthEast().lng,
        });
        if (currentDataset.votingMethod) params.set('voting_method', currentDataset.votingMethod);
        
        console.log('Preloading voter details for viewport...');
        const resp = await fetch(`/api/voters?${params}`);
        if (!resp.ok) return;
        const geojson = await resp.json();
        
        // Index by rounded coordinates → group voters at same address
        let cached = 0;
        const addrGroups = {};
        (geojson.features || []).forEach(f => {
            if (!f.geometry || !f.geometry.coordinates) return;
            const [lng, lat] = f.geometry.coordinates;
            // Normalize address for grouping (strip unit/apt)
            const addr = (f.properties.address || '').trim().toUpperCase();
            const baseAddr = addr.replace(/\b(?:APT|APARTMENT|UNIT|STE|SUITE|#)\s*[A-Z0-9-]+/i, '').replace(/\s{2,}/g, ' ').trim();
            const key = baseAddr || `${lat.toFixed(5)},${lng.toFixed(5)}`;
            if (!addrGroups[key]) addrGroups[key] = { voters: [], coords: [] };
            addrGroups[key].voters.push(f.properties);
            addrGroups[key].coords.push([lat, lng]);
        });
        
        // Cache each coordinate → its address group's voters
        Object.values(addrGroups).forEach(group => {
            group.coords.forEach(([lat, lng]) => {
                const cacheKey = `${lat.toFixed(5)},${lng.toFixed(5)}`;
                if (!_voterDetailCache.has(cacheKey)) {
                    _voterDetailCache.set(cacheKey, group.voters);
                    cached++;
                }
            });
        });
        
        console.log(`Preloaded ${cached} locations, ${geojson.features?.length || 0} voters into cache`);
    } catch (e) {
        console.warn('Viewport preload failed:', e);
    } finally {
        _viewportPreloadInProgress = false;
    }
}

/**
 * Show or hide the "no data available" overlay on the map.
 */
function showNoDataOverlay(show, countyName) {
    let overlay = document.getElementById('no-data-overlay');
    if (show) {
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'no-data-overlay';
            overlay.style.cssText = 'position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);z-index:1000;background:rgba(255,255,255,0.95);border-radius:12px;padding:24px 32px;box-shadow:0 4px 20px rgba(0,0,0,0.15);text-align:center;max-width:320px;pointer-events:auto;';
            const mapEl = document.getElementById('map');
            if (mapEl) mapEl.appendChild(overlay);
        }
        overlay.innerHTML = `
            <div style="font-size:32px;margin-bottom:8px;">📭</div>
            <div style="font-size:16px;font-weight:600;color:#333;margin-bottom:6px;">No Data Available for Visualization</div>
            <div style="font-size:13px;color:#666;">${countyName ? countyName + ' County has voter records but no geocoded addresses to display on the map.' : 'Select a different county or dataset.'}</div>
        `;
        overlay.style.display = 'block';
    } else {
        if (overlay) overlay.style.display = 'none';
    }
}

/**
 * Zoom the map to a county's centroid.
 */
async function zoomToCounty(county) {
    if (!county || county === 'all') return;
    try {
        const resp = await fetch(`/api/county-center?county=${encodeURIComponent(county)}`);
        if (!resp.ok) return;
        const data = await resp.json();
        if (data.lat && data.lng && data.count > 10 && typeof map !== 'undefined') {
            map.setView([data.lat, data.lng], 10);
            return;
        }
        // Fallback: use Nominatim to find county center in Texas
        const nomResp = await fetch(
            `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(county + ' County, Texas')}&format=json&limit=1`,
            { signal: AbortSignal.timeout(3000) }
        );
        const nomData = await nomResp.json();
        if (nomData.length > 0 && typeof map !== 'undefined') {
            map.setView([parseFloat(nomData[0].lat), parseFloat(nomData[0].lon)], 10);
        }
    } catch (e) { console.warn('Could not zoom to county:', e); }
}

async function loadMapData() {
    try {
        console.log('Starting loadMapData...');
        
        // Show loading indicator
        const loadingIndicator = document.getElementById('map-loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'flex';
        }
        
        // Detect user's county (or default to Hidalgo)
        selectedCountyFilter = await detectUserCounty();
        console.log('Default county:', selectedCountyFilter);
        
        // First, discover all available datasets
        availableDatasets = await discoverDatasets();
        console.log('Available datasets:', availableDatasets);
        
        // Populate dataset selector (will use selectedCountyFilter)
        populateDatasetSelector();
        
        // Find the most recent early-voting dataset that includes this county
        if (availableDatasets.length > 0) {
            // Repopulate dropdown filtered to the detected county
            repopulateFilteredDatasetDropdown();
            
            const inlineSelect = document.getElementById('dataset-selector-inline');
            if (inlineSelect && inlineSelect.options.length > 0) {
                const idx = parseInt(inlineSelect.options[0].value);
                if (!isNaN(idx) && availableDatasets[idx]) {
                    inlineSelect.selectedIndex = 0;
                    const originalSelect = document.getElementById('dataset-selector');
                    if (originalSelect) originalSelect.value = idx;
                    await loadDataset(availableDatasets[idx]);
                }
            } else {
                console.warn('No datasets found for county:', selectedCountyFilter);
            }
            
            // Zoom to the county
            await zoomToCounty(selectedCountyFilter);
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
            const votingMethodLabel = dataset.votingMethod === 'election-day' ? 'Election Day' : dataset.votingMethod === 'mail-in' ? 'Mail-In' : 'Early Voting';
            const electionTypeLabel = dataset.electionType.charAt(0).toUpperCase() + dataset.electionType.slice(1);
            const counties = dataset.counties || [dataset.county || 'Hidalgo'];
            
            html += `<div class="layer-dataset-item" onclick="selectDatasetFromPanel(${datasetIndex})">
                    <span>${electionTypeLabel} - ${votingMethodLabel}</span>
                    <span class="dataset-voter-count">${dataset.totalAddresses.toLocaleString()}</span>
                </div>`;
            
            // Show county checkboxes if multiple counties
            if (counties.length > 1) {
                html += `<div class="county-checkboxes" style="padding: 4px 0 4px 16px; font-size: 12px;">`;
                counties.forEach(county => {
                    const cb = dataset.countyBreakdown && dataset.countyBreakdown[county];
                    const voterCount = cb ? cb.totalVoters : 0;
                    const checked = (dataset.selectedCounties || counties).includes(county) ? 'checked' : '';
                    html += `<label style="display: flex; align-items: center; gap: 4px; padding: 2px 0; cursor: pointer;">
                        <input type="checkbox" ${checked} onchange="toggleCountyForDataset(${datasetIndex}, '${county}', this.checked)" style="margin: 0;">
                        <span>${county}</span>
                        <span style="color: #888; margin-left: auto;">${voterCount.toLocaleString()}</span>
                    </label>`;
                });
                html += `</div>`;
            } else {
                html += `<div style="padding: 2px 0 2px 16px; font-size: 12px; color: #666;">${counties[0]}</div>`;
            }
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

async function toggleCountyForDataset(datasetIndex, county, checked) {
    const dataset = availableDatasets[datasetIndex];
    if (!dataset) return;
    
    const counties = dataset.counties || [dataset.county || 'Hidalgo'];
    if (!dataset.selectedCounties) {
        dataset.selectedCounties = counties.slice();
    }
    
    if (checked && !dataset.selectedCounties.includes(county)) {
        dataset.selectedCounties.push(county);
    } else if (!checked) {
        dataset.selectedCounties = dataset.selectedCounties.filter(c => c !== county);
    }
    
    // Don't allow deselecting all counties
    if (dataset.selectedCounties.length === 0) {
        dataset.selectedCounties = [county];
        // Re-check the checkbox
        event.target.checked = true;
        return;
    }
    
    // If this is the currently loaded dataset, reload with new county selection
    if (currentDataset === dataset) {
        await loadDataset(dataset);
    }
}

async function discoverDatasets() {
    const datasets = [];
    
    try {
        // DB-driven: fetch ALL elections across all counties
        const response = await fetch('/api/elections');
        
        if (!response.ok) {
            console.error('Failed to fetch elections from backend');
            return datasets;
        }
        
        const data = await response.json();
        
        if (data.success && data.elections) {
            console.log(`Discovered ${data.elections.length} elections from DB`);
            
            // Convert DB election records to dataset objects the rest of the code expects
            data.elections.forEach(election => {
                datasets.push({
                    county: election.county,
                    counties: election.counties || [election.county],
                    year: election.electionYear,
                    electionType: election.electionType,
                    electionDate: election.electionDate,
                    votingMethod: election.votingMethod,
                    parties: election.parties || [],
                    totalAddresses: election.totalVoters,
                    rawVoterCount: election.totalVoters,
                    geocodedCount: election.geocodedCount,
                    lastUpdated: election.lastUpdated,
                    countyBreakdown: election.countyBreakdown || {},
                    // Track which counties are selected (default: all)
                    selectedCounties: (election.counties || [election.county]).slice(),
                    // DB-driven: no more file references
                    dbDriven: true,
                });
            });
            
            return datasets;
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
    
    // Build county pill tabs dynamically
    buildCountyPillTabs();
    
    // Populate the dropdown filtered by selected county
    repopulateFilteredDatasetDropdown();
    
    // Add change event listener on the hidden original selector
    selector.addEventListener('change', async (e) => {
        const index = parseInt(e.target.value);
        if (!isNaN(index) && availableDatasets[index]) {
            await loadDataset(availableDatasets[index]);
        }
    });
    
    selector.disabled = false;
}

/**
 * Build county dropdown from available datasets
 */
function buildCountyPillTabs() {
    const dropdown = document.getElementById('countyDropdown');
    if (!dropdown) return;
    
    // Collect all unique counties across all datasets
    const allCounties = new Set();
    availableDatasets.forEach(ds => {
        const counties = ds.counties || [ds.county || 'Hidalgo'];
        counties.forEach(c => allCounties.add(c));
    });
    
    const sortedCounties = [...allCounties].sort();
    
    dropdown.innerHTML = '';
    
    // "All Counties" option
    const allOpt = document.createElement('option');
    allOpt.value = 'all';
    allOpt.textContent = `All Counties (${sortedCounties.length})`;
    if (selectedCountyFilter === 'all') allOpt.selected = true;
    dropdown.appendChild(allOpt);
    
    // One option per county
    sortedCounties.forEach(county => {
        const opt = document.createElement('option');
        opt.value = county;
        opt.textContent = county;
        if (selectedCountyFilter === county) opt.selected = true;
        dropdown.appendChild(opt);
    });
    
    // Change handler
    dropdown.addEventListener('change', () => {
        selectCountyFilter(dropdown.value);
    });
}

/**
 * Handle county pill selection
 */
async function selectCountyFilter(county) {
    selectedCountyFilter = county;
    
    // Update dropdown selection
    const dropdown = document.getElementById('countyDropdown');
    if (dropdown) dropdown.value = county;
    
    // Hide any existing no-data overlay
    showNoDataOverlay(false);
    
    // Repopulate the dropdown for this county
    repopulateFilteredDatasetDropdown();
    
    // Zoom to the selected county
    if (county !== 'all') {
        await zoomToCounty(county);
    }
    
    // Auto-load the first (most recent) dataset in the filtered list
    const inlineSelect = document.getElementById('dataset-selector-inline');
    if (inlineSelect && inlineSelect.options.length > 0) {
        const idx = parseInt(inlineSelect.options[0].value);
        if (!isNaN(idx) && availableDatasets[idx]) {
            inlineSelect.selectedIndex = 0;
            // Sync hidden selector
            const originalSelect = document.getElementById('dataset-selector');
            if (originalSelect) originalSelect.value = idx;
            await loadDataset(availableDatasets[idx]);
            updateInlineDatasetInfo();
        }
    } else {
        // No datasets for this county — show overlay
        showNoDataOverlay(true, county !== 'all' ? county : null);
    }
}

/**
 * Repopulate the inline dataset dropdown based on the selected county filter.
 * When "All Counties" is selected, show multi-county combined datasets.
 * When a specific county is selected, show only datasets that include that county
 * (and set selectedCounties to just that county for single-county loading).
 */
function repopulateFilteredDatasetDropdown() {
    const inlineSelect = document.getElementById('dataset-selector-inline');
    const originalSelect = document.getElementById('dataset-selector');
    if (!inlineSelect) return;
    
    inlineSelect.innerHTML = '';
    if (originalSelect) originalSelect.innerHTML = '';
    
    const filtered = [];
    
    availableDatasets.forEach((dataset, index) => {
        const counties = dataset.counties || [dataset.county || 'Hidalgo'];
        
        if (selectedCountyFilter === 'all') {
            // Show all datasets (combined multi-county view)
            filtered.push({ dataset, index });
        } else {
            // Show only datasets that include this county
            if (counties.includes(selectedCountyFilter)) {
                filtered.push({ dataset, index });
            }
        }
    });
    
    if (filtered.length === 0) {
        inlineSelect.innerHTML = '<option value="">No datasets for this county</option>';
        return;
    }
    
    filtered.forEach(({ dataset, index }) => {
        const votingMethodLabel = dataset.votingMethod === 'election-day' ? 'Election Day' : dataset.votingMethod === 'mail-in' ? 'Mail-In' : 'Early Voting';
        const electionTypeLabel = dataset.electionType ? dataset.electionType.charAt(0).toUpperCase() + dataset.electionType.slice(1) : '';
        const parties = dataset.parties || [];
        const partyLabel = parties.length === 1 ? ` (${parties[0].charAt(0).toUpperCase() + parties[0].slice(1)})` : '';
        
        // Show voter count for the selected county or total
        let voterCount = dataset.totalAddresses || 0;
        if (selectedCountyFilter !== 'all' && dataset.countyBreakdown && dataset.countyBreakdown[selectedCountyFilter]) {
            voterCount = dataset.countyBreakdown[selectedCountyFilter].totalVoters;
        }
        
        const label = `${dataset.year || ''} ${electionTypeLabel}${partyLabel} — ${votingMethodLabel} (${voterCount.toLocaleString()})`;
        
        const opt = document.createElement('option');
        opt.value = index;
        opt.textContent = label;
        inlineSelect.appendChild(opt);
        
        // Also populate hidden original selector
        if (originalSelect) {
            const opt2 = opt.cloneNode(true);
            originalSelect.appendChild(opt2);
        }
    });
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
        _voterDetailCache.clear(); // Clear popup cache for new dataset
        // DB-driven: fetch voter data from API
        // If a specific county is selected via the pill filter, use only that county
        let counties;
        if (selectedCountyFilter !== 'all') {
            counties = [selectedCountyFilter];
        } else {
            counties = dataset.selectedCounties || dataset.counties || [dataset.county || 'Hidalgo'];
        }
        const params = new URLSearchParams({
            county: counties.join(','),
            election_date: dataset.electionDate,
        });
        if (dataset.votingMethod) params.set('voting_method', dataset.votingMethod);
        
        // Use lightweight heatmap endpoint for initial load (~90% smaller payload)
        console.log('Fetching heatmap data from DB:', params.toString());
        
        // Fire heatmap + stats requests in parallel so both are ready before rendering
        const [response] = await Promise.all([
            fetch(`/api/voters/heatmap?${params}`),
            _fetchAndDisplayStats(dataset),
        ]);
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Loaded', data.count, 'heatmap points from DB');
        
        // Show "no data" overlay if no geocoded points to visualize
        if (data.count === 0) {
            showNoDataOverlay(true, selectedCountyFilter !== 'all' ? selectedCountyFilter : null);
        } else {
            showNoDataOverlay(false);
        }
        
        // Convert compact array to GeoJSON features for compatibility with initializeDataLayers
        // Format: [lng, lat, party_code, flags, sex?, birth_year?]
        // party_code: 1=DEM, 2=REP, 0=other; flags: bit0=flipped, bit1=new_voter
        const partyNames = {1: 'Democratic', 2: 'Republican', 0: ''};
        const features = data.points.map(p => ({
            type: 'Feature',
            geometry: {type: 'Point', coordinates: [p[0], p[1]]},
            properties: {
                party_affiliation_current: partyNames[p[2]] || '',
                has_switched_parties: !!(p[3] & 1),
                party_affiliation_previous: (p[3] & 1) ? (p[2] === 1 ? 'Republican' : 'Democratic') : '',
                is_new_voter: !!(p[3] & 2),
                sex: p[4] || '',
                birth_year: p[5] || 0,
                voted_in_current_election: true,
                is_registered: true,
                unmatched: false,
            }
        }));
        
        const geojson = {type: 'FeatureCollection', features};
        
        // Store the data globally
        window.mapData = geojson;
        window.votedOnlyMapData = geojson;
        registeredNotVotedData = null;
        window.currentDataset = currentDataset;
        
        // Reinitialize markers and heatmap with new data
        // (stats already fetched in parallel via Promise.all above)
        initializeDataLayers();
        
        // Update metadata display
        const countyLabel = counties.length <= 2 ? counties.join(', ') : `${counties.length} Counties`;
        updateInfoStrip({
            successfully_geocoded: dataset.totalAddresses,
            last_updated: dataset.lastUpdated,
            county: countyLabel,
            year: dataset.year,
            election_type: dataset.electionType,
            voting_method: dataset.votingMethod
        });
        
        console.log('Dataset loaded successfully from DB');
        
    } catch (error) {
        console.error('Error loading dataset:', error);
        alert(`Failed to load dataset: ${error.message}`);
    } finally {
        const loadingIndicator = document.getElementById('map-loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
    }
}

// ============================================================================
// REGISTERED NOT VOTED TOGGLE
// ============================================================================

async function toggleRegisteredNotVoted() {
    showRegisteredNotVoted = !showRegisteredNotVoted;
    
    if (showRegisteredNotVoted && currentDataset) {
        if (map && map.getZoom() < 14) {
            console.log('Zoom in to at least level 14 to see registered-not-voted voters');
            // Still set the flag so it loads on next zoom/pan
            registeredNotVotedData = null;
            rebuildMapDataWithRegistered();
            return;
        }
        await loadRegisteredNotVoted();
    } else {
        registeredNotVotedData = null;
        rebuildMapDataWithRegistered();
    }
}

let _loadingRegistered = false; // Guard against concurrent fetches

async function loadRegisteredNotVoted() {
    if (!currentDataset) return;
    if (_loadingRegistered) return; // Skip if already fetching
    
    // Require zoom >= 14 to avoid massive queries
    if (map && map.getZoom() < 14) {
        console.log('Registered-not-voted: zoom too low (%d), need >= 14', map.getZoom());
        registeredNotVotedData = null;
        rebuildMapDataWithRegistered();
        return;
    }
    
    _loadingRegistered = true;
    
    let counties;
    if (selectedCountyFilter !== 'all') {
        counties = [selectedCountyFilter];
    } else {
        counties = currentDataset.selectedCounties || currentDataset.counties || [currentDataset.county || 'Hidalgo'];
    }
    const bounds = map.getBounds();
    const params = new URLSearchParams({
        county: counties.join(','),
        election_date: currentDataset.electionDate,
        sw_lat: bounds.getSouthWest().lat,
        sw_lng: bounds.getSouthWest().lng,
        ne_lat: bounds.getNorthEast().lat,
        ne_lng: bounds.getNorthEast().lng,
        limit: 5000,
    });
    
    console.log('Fetching registered-not-voted voters...');
    try {
        const response = await fetch(`/api/registered-voters?${params}`);
        if (!response.ok) throw new Error(`API error: ${response.status}`);
        const geojson = await response.json();
        console.log('Loaded', geojson.features ? geojson.features.length : 0, 'registered-not-voted features');
        registeredNotVotedData = geojson;
        rebuildMapDataWithRegistered();
    } catch (error) {
        console.error('Error loading registered-not-voted:', error);
    } finally {
        _loadingRegistered = false;
    }
}

function rebuildMapDataWithRegistered() {
    // Start with the voted-only data
    if (!window.votedOnlyMapData) {
        // First time: save the original voted-only data
        window.votedOnlyMapData = window.mapData;
    }
    
    if (showRegisteredNotVoted && registeredNotVotedData && registeredNotVotedData.features) {
        // Merge voted + registered-not-voted
        window.mapData = {
            type: 'FeatureCollection',
            features: [...window.votedOnlyMapData.features, ...registeredNotVotedData.features]
        };
    } else {
        window.mapData = window.votedOnlyMapData;
    }
    
    // Re-render
    initializeDataLayers();
}

// Fetch stats from DB API and update the stats box
async function _fetchAndDisplayStats(dataset) {
    try {
        let counties;
        if (selectedCountyFilter !== 'all') {
            counties = [selectedCountyFilter];
        } else {
            counties = dataset.selectedCounties || dataset.counties || [dataset.county || 'Hidalgo'];
        }
        const params = new URLSearchParams({
            county: counties.join(','),
            election_date: dataset.electionDate,
        });
        if (dataset.votingMethod) params.set('voting_method', dataset.votingMethod);
        
        const resp = await fetch(`/api/election-stats?${params}`);
        if (!resp.ok) return;
        const data = await resp.json();
        if (data.success && data.stats) {
            // Store stats on the dataset object for updateDatasetStatsBox
            dataset._dbStats = data.stats;
            window.currentDataset = dataset;
            updateDatasetStatsBox();
        }
    } catch (e) {
        console.warn('Failed to fetch election stats:', e);
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
        // Use the active county filter for the title, not the dataset's full county list
        if (selectedCountyFilter && selectedCountyFilter !== 'all') {
            parts.push(selectedCountyFilter + ' County');
        } else if (ds.county) {
            // Multi-county: show as "Brooks, Hidalgo County" 
            const countyNames = ds.counties || [ds.county];
            parts.push(countyNames.join(', ') + ' County');
        }
        if (ds.year) parts.push(ds.year);
        if (ds.electionType) parts.push(ds.electionType.charAt(0).toUpperCase() + ds.electionType.slice(1));
        
        // Add "Combined" or voting method label
        if (ds.votingMethod === 'combined') {
            parts.push('(Complete Election)');
        } else if (ds.votingMethod === 'early-voting') {
            parts.push('(Early Voting)');
        } else if (ds.votingMethod === 'election-day') {
            parts.push('(Election Day)');
        } else if (ds.votingMethod === 'mail-in') {
            parts.push('(Mail-In)');
        }
        
        title = parts.join(' ');
    }
    
    // Use DB stats if available, otherwise count from features
    const dbStats = ds ? ds._dbStats : null;
    let allDem = 0, allRep = 0, flippedToBlue = 0, flippedToRed = 0, newVoterCount = 0;
    let newDem = 0, newRep = 0;
    let totalAll = 0;
    
    if (dbStats) {
        // DB-driven stats — accurate, no client-side counting needed
        allDem = dbStats.democratic || 0;
        allRep = dbStats.republican || 0;
        flippedToBlue = dbStats.flipped_to_dem || 0;
        flippedToRed = dbStats.flipped_to_rep || 0;
        newVoterCount = dbStats.new_voters || 0;
        totalAll = dbStats.total || 0;
    } else {
        // Fallback: count from features (legacy path)
        allFeatures.forEach(f => {
        const p = f.properties;
        if (!p) return;
        const cur = (p.party_affiliation_current || '').toLowerCase();
        const prev = (p.party_affiliation_previous || '').toLowerCase();
        if (cur.includes('democrat')) allDem++;
        else if (cur.includes('republican')) allRep++;
        
        if (p.is_new_voter) {
            newVoterCount++;
            if (cur.includes('democrat')) newDem++;
            else if (cur.includes('republican')) newRep++;
        }
        
        if (prev && cur) {
            const prevRep = prev.includes('republican');
            const prevDem = prev.includes('democrat');
            const curRep = cur.includes('republican');
            const curDem = cur.includes('democrat');
            if (prevRep && curDem) flippedToBlue++;
            if (prevDem && curRep) flippedToRed++;
        }
    });
        // Fallback total from features
        const featureTotal = allFeatures.length;
        // When county filter is active, use county-specific count or feature count
        // Don't use ds.totalAddresses — that's the statewide total for all counties
        let metaTotal = 0;
        if (ds) {
            if (selectedCountyFilter && selectedCountyFilter !== 'all' && ds.countyBreakdown && ds.countyBreakdown[selectedCountyFilter]) {
                metaTotal = ds.countyBreakdown[selectedCountyFilter].totalVoters || 0;
            } else {
                metaTotal = ds.totalAddresses || 0;
            }
        }
        totalAll = Math.max(featureTotal, metaTotal);
    }
    
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
    } else if (typeof newVotersFilter !== 'undefined' && newVotersFilter) {
        // New voters mode — respect party filter
        let displayCount = newVoterCount;
        let partyLabel = '';
        if (partyFilter === 'democratic') {
            displayCount = newDem;
            partyLabel = ' Democratic';
        } else if (partyFilter === 'republican') {
            displayCount = newRep;
            partyLabel = ' Republican';
        }
        const filteredTotal = partyFilter === 'democratic' ? allDem : partyFilter === 'republican' ? allRep : totalAll;
        statsHtml = `
            <div class="stats-title">${title || 'Dataset'} — New${partyLabel} Voters</div>
            <div class="stats-row">
                <span class="stat-item" style="color:#DAA520">⭐ <span class="stat-value">${displayCount.toLocaleString()}</span> new${partyLabel.toLowerCase()} voters (first election)</span>
            </div>
            <div class="stats-row" style="font-size:11px;color:#888;margin-top:2px;">of ${filteredTotal.toLocaleString()}${partyLabel.toLowerCase()} voters (${totalAll.toLocaleString()} total)</div>`;
    } else if (partyFilter === 'democratic') {
        statsHtml = `
            <div class="stats-title">${title || 'Dataset'} — Democrats</div>
            <div class="stats-row">
                <span class="stat-item stat-dem">🔵 <span class="stat-value">${allDem.toLocaleString()}</span> Democratic voters</span>
            </div>
            ${newDem > 0 ? `<div class="stats-row" style="font-size:11px;color:#DAA520;margin-top:2px;">⭐ ${newDem.toLocaleString()} new voters</div>` : ''}
            <div class="stats-row" style="font-size:11px;color:#888;margin-top:2px;">of ${totalAll.toLocaleString()} total</div>`;
    } else if (partyFilter === 'republican') {
        statsHtml = `
            <div class="stats-title">${title || 'Dataset'} — Republicans</div>
            <div class="stats-row">
                <span class="stat-item stat-rep">🔴 <span class="stat-value">${allRep.toLocaleString()}</span> Republican voters</span>
            </div>
            ${newRep > 0 ? `<div class="stats-row" style="font-size:11px;color:#DAA520;margin-top:2px;">⭐ ${newRep.toLocaleString()} new voters</div>` : ''}
            <div class="stats-row" style="font-size:11px;color:#888;margin-top:2px;">of ${totalAll.toLocaleString()} total</div>`;
    } else {
        // Default: show all
        const totalFlipped = flippedToBlue + flippedToRed;
        statsHtml = `
            <div class="stats-title" id="statsToggleTitle" style="cursor: pointer; user-select: none; display: flex; align-items: center; justify-content: center; gap: 8px;">
                <span>${title || 'Dataset'}</span>
                <i class="fas fa-chevron-down" id="statsChevron" style="font-size: 10px; transition: transform 0.2s;"></i>
            </div>
            <div id="statsContent" style="transition: max-height 0.3s ease, opacity 0.3s ease; overflow: hidden;">
                <div class="stats-row">
                    <span class="stat-item">📊 <span class="stat-value">${totalAll.toLocaleString()}</span> voters</span>
                    <span class="stat-item stat-dem">🔵 <span class="stat-value">${allDem.toLocaleString()}</span></span>
                    <span class="stat-item stat-rep">🔴 <span class="stat-value">${allRep.toLocaleString()}</span></span>
                </div>
                ${newVoterCount > 0 ? `<div class="stats-row" style="font-size:11px;color:#DAA520;margin-top:2px;">⭐ ${newVoterCount.toLocaleString()} new voters</div>` : ''}
                ${totalFlipped > 0 ? `<div class="stats-row" style="font-size:11px;color:#888;margin-top:2px;">🔄 ${totalFlipped.toLocaleString()} flipped (${flippedToBlue} R→D, ${flippedToRed} D→R)</div>` : ''}
            </div>`;
    }
    
    el.innerHTML = statsHtml;
    
    // Add toggle functionality for stats content
    const toggleTitle = document.getElementById('statsToggleTitle');
    const statsContent = document.getElementById('statsContent');
    const chevron = document.getElementById('statsChevron');
    
    if (toggleTitle && statsContent && chevron) {
        // Check if stats should be collapsed (from localStorage)
        const isCollapsed = localStorage.getItem('statsBoxCollapsed') === 'true';
        if (isCollapsed) {
            statsContent.style.maxHeight = '0';
            statsContent.style.opacity = '0';
            chevron.style.transform = 'rotate(-90deg)';
        }
        
        toggleTitle.addEventListener('click', () => {
            const collapsed = statsContent.style.maxHeight === '0px' || statsContent.style.opacity === '0';
            if (collapsed) {
                statsContent.style.maxHeight = '200px';
                statsContent.style.opacity = '1';
                chevron.style.transform = 'rotate(0deg)';
                localStorage.setItem('statsBoxCollapsed', 'false');
            } else {
                statsContent.style.maxHeight = '0';
                statsContent.style.opacity = '0';
                chevron.style.transform = 'rotate(-90deg)';
                localStorage.setItem('statsBoxCollapsed', 'true');
            }
        });
    }
    
    // Add County Report button if a specific county is selected
    if (selectedCountyFilter && selectedCountyFilter !== 'all' && typeof openCountyReport === 'function') {
        const existingBtn = el.querySelector('.county-report-btn-stats');
        if (!existingBtn && statsContent) {
            const btn = document.createElement('button');
            btn.className = 'county-report-btn-stats';
            btn.innerHTML = '<i class="fas fa-file-alt"></i> County Report';
            btn.style.cssText = 'margin-top: 8px; padding: 6px 12px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 5px; transition: background 0.2s; -webkit-tap-highlight-color: rgba(0,0,0,0.1); touch-action: manipulation;';
            btn.onmouseover = () => btn.style.background = '#5568d3';
            btn.onmouseout = () => btn.style.background = '#667eea';
            
            // Use addEventListener for better mobile support
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                openCountyReport();
            });
            
            // Add touch event for better mobile responsiveness
            btn.addEventListener('touchend', (e) => {
                e.preventDefault();
                e.stopPropagation();
                openCountyReport();
            });
            
            statsContent.appendChild(btn);
        }
    }
}

/**
 * Bind a full popup (with all voter details) to a marker.
 * Used when full data is already available (e.g. from /api/voters).
 */
function _bindFullPopup(marker, group, addrKey, count) {
    const allVuids = [];
    let pc = `<div style="max-width:380px;">`;
    pc += `<div style="font-size:11px;color:#888;margin-bottom:2px;">${group[0].props.address || addrKey}</div>`;
    if (count > 1) {
        pc += `<div style="font-weight:700;font-size:13px;margin-bottom:6px;">${count} voters at this address</div>`;
    }
    group.forEach((v, i) => {
        if (i > 0) pc += `<hr style="margin:6px 0;border:none;border-top:1px dashed #ddd;">`;
        if (v.unitNum) pc += `<div style="font-size:10px;color:#666;font-weight:600;margin-bottom:1px;">${v.unitNum}</div>`;
        pc += _buildVoterCard(v.props);
        const vuid = v.props.vuid || '';
        if (vuid) allVuids.push(vuid);
    });
    pc += `</div>`;
    marker.bindPopup(pc, { maxWidth: 400, maxHeight: 400 });
    if (allVuids.length > 0) {
        marker.on('popupopen', () => allVuids.forEach(v => fetchVoterHistory(v)));
    }
}

/**
 * Lazy-load voter details from the DB when a marker popup is opened.
 * Fetches voter(s) at the given lat/lng via /api/voters/at, then
 * replaces the popup content with full voter cards + voting history.
 */
async function _lazyLoadPopup(marker, lat, lng) {
    try {
        const ds = currentDataset;
        if (!ds) return;
        
        // Check browser cache first (populated by preloadViewportVoterDetails)
        const cacheKey = `${lat.toFixed(5)},${lng.toFixed(5)}`;
        let voters = _voterDetailCache.get(cacheKey);
        
        if (!voters) {
            // Cache miss — fetch from API
            const params = new URLSearchParams({
                lat: lat.toFixed(6),
                lng: lng.toFixed(6),
                election_date: ds.electionDate,
            });
            if (ds.votingMethod) params.set('voting_method', ds.votingMethod);
            
            // Note: Not filtering by county for popups - let the backend find voters at this location
            // regardless of county boundaries (handles edge cases near county lines)
            
            const resp = await fetch(`/api/voters/at?${params}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            voters = data.voters || [];
            
            // Store in cache for next time
            if (voters.length > 0) {
                _voterDetailCache.set(cacheKey, voters);
            }
        }
        
        if (!voters || voters.length === 0) {
            marker.setPopupContent('<div style="padding:8px;color:#999;">No voter details found</div>');
            return;
        }
        
        let html = `<div style="max-width:380px;">`;
        html += `<div style="font-size:11px;color:#888;margin-bottom:2px;">${voters[0].address || 'N/A'}</div>`;
        if (voters.length > 1) {
            html += `<div style="font-weight:700;font-size:13px;margin-bottom:6px;">${voters.length} voters at this address</div>`;
        }
        
        const vuids = [];
        voters.forEach((v, i) => {
            if (i > 0) html += `<hr style="margin:6px 0;border:none;border-top:1px dashed #ddd;">`;
            html += _buildVoterCard(v);
            if (v.vuid) vuids.push(v.vuid);
        });
        html += `</div>`;
        
        marker.setPopupContent(html);
        
        // Fetch voting history for each voter
        vuids.forEach(vuid => fetchVoterHistory(vuid));
        
    } catch (error) {
        console.error('Error loading voter details:', error);
        marker.setPopupContent('<div style="padding:8px;color:#c00;">Failed to load voter details</div>');
    }
}

/**
 * Build HTML card for a single voter inside a popup.
 * Shows name, age, gender, party, precinct, badges, flip info, and a
 * placeholder for voting history (loaded on popup open via fetchVoterHistory).
 */
function _buildVoterCard(props) {
    const nm = props.name || [props.firstname, props.lastname].filter(Boolean).join(' ');
    const pty = props.party_affiliation_current || '';
    const isRegisteredNotVoted = props.voted_in_current_election === false;
    const pColor = isRegisteredNotVoted ? '#A0A0A0'
                 : pty.toLowerCase().includes('democrat') ? '#1E90FF'
                 : pty.toLowerCase().includes('republican') ? '#DC143C' : '#888';
    const gender = props.sex === 'F' ? 'Female' : props.sex === 'M' ? 'Male' : '';
    const currentYear = new Date().getFullYear();
    const age = props.birth_year && props.birth_year > 1900 ? (currentYear - props.birth_year) : '';
    const ageStr = age ? `Age ${age}` : '';
    const vuid = props.vuid || '';

    let html = '';
    // Name row with party dot
    html += `<div style="display:flex;align-items:center;gap:6px;margin-bottom:2px;">`;
    html += `<span style="width:10px;height:10px;border-radius:50%;background:${pColor};flex-shrink:0;"></span>`;
    html += `<span style="font-weight:600;font-size:13px;">${nm || 'Unknown'}</span>`;
    html += `</div>`;

    if (isRegisteredNotVoted) {
        // Show "Registered - Has Not Voted" instead of party info
        html += `<div style="font-size:11px;color:#A0A0A0;font-weight:600;margin-bottom:3px;">Registered - Has Not Voted</div>`;
        const regDetails = [gender, ageStr, props.precinct ? 'Pct ' + props.precinct : ''].filter(Boolean).join(' · ');
        if (regDetails) html += `<div style="font-size:11px;color:#666;margin-bottom:3px;">${regDetails}</div>`;
    } else {
        // Details line: party · gender · age · precinct
        const details = [pty, gender, ageStr, props.precinct ? 'Pct ' + props.precinct : ''].filter(Boolean).join(' · ');
        if (details) html += `<div style="font-size:11px;color:#666;margin-bottom:3px;">${details}</div>`;

        // Badges
        if (props.is_new_voter) {
            html += `<div style="color:#DAA520;font-size:11px;font-weight:bold;margin-bottom:2px;">⭐ New Voter (first primary)</div>`;
        }
        if (props.party_affiliation_previous && props.party_affiliation_previous !== pty) {
            const prev = props.party_affiliation_previous;
            const flipLabel = pty.toLowerCase().includes('democrat') ? 'R→D' : 'D→R';
            const fColor = pty.toLowerCase().includes('democrat') ? '#6A1B9A' : '#C62828';
            html += `<div style="color:${fColor};font-size:11px;font-weight:600;margin-bottom:2px;">↩ Flipped: ${prev} → ${pty} (${flipLabel})</div>`;
        }
    }

    // Voting history placeholder — always shown, loaded on popup open
    if (vuid) {
        html += `<div id="history-${vuid}" style="margin-top:4px;font-size:11px;color:#999;">Loading voting history...</div>`;
    }

    return html;
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
    const heatmapDataNewVoters = [];
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
        
        // Gender filter: skip features that don't match the active gender filter
        if (typeof genderFilter !== 'undefined' && genderFilter !== 'all') {
            const sex = (props.sex || '').toUpperCase();
            if (genderFilter === 'male' && sex !== 'M') return;
            if (genderFilter === 'female' && sex !== 'F') return;
        }
        
        // Age group filter: skip features that don't match the active age filter
        if (typeof ageFilter !== 'undefined' && ageFilter !== 'all') {
            const by = props.birth_year || 0;
            if (!by) return;
            const ageGroupMap = {
                '18-24': [2002, 2008], '25-34': [1992, 2001], '35-44': [1982, 1991],
                '45-54': [1972, 1981], '55-64': [1962, 1971], '65-74': [1952, 1961],
                '75+': [0, 1951]
            };
            const range = ageGroupMap[ageFilter];
            if (range && (by < range[0] || by > range[1])) return;
        }
        
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
        
        // Collect new voter data for new voters heatmap
        if (props.is_new_voter) {
            heatmapDataNewVoters.push([lat, lng, 1]);
        }
        
        // Skip filtered-out voters (determineMarkerColor returns null when voter doesn't match active filter)
        if (markerColor === null) {
            return; // Skip this feature in forEach
        }
        
        // Group by normalized address string so same-address voters always
        // cluster together even when geocoded to slightly different coords.
        // For apartments: strip unit/apt numbers to group all units at same building.
        let addrRaw = (props.address || '').trim().toUpperCase();
        let unitNum = '';
        if (addrRaw) {
            // Extract and strip apartment/unit identifiers for building-level grouping
            const unitMatch = addrRaw.match(/\b(?:APT|APARTMENT|UNIT|STE|SUITE|#)\s*[A-Z0-9-]+/i);
            if (unitMatch) {
                unitNum = unitMatch[0].trim();
                addrRaw = addrRaw.replace(unitMatch[0], '').replace(/\s{2,}/g, ' ').replace(/,\s*,/g, ',').trim();
            }
        }
        const addrKey = addrRaw || `${lat.toFixed(5)},${lng.toFixed(5)}`;
        if (!addressGroups[addrKey]) {
            addressGroups[addrKey] = [];
        }
        addressGroups[addrKey].push({ lat, lng, markerColor, props, unitNum });
    });
    
    // Now create markers, grouping by coordinates
    // Only show individual data points for logged-in users with full access
    if (window.authFullAccess) {
    Object.entries(addressGroups).forEach(([addrKey, group]) => {
        // Use first voter's coords as the marker position
        const { lat, lng } = group[0];
        const count = group.length;
        const markerColor = group[0].markerColor;
        const isNewVoter = group[0].props.is_new_voter;
        
        // Determine if we have full data (name/vuid) or just heatmap data
        const hasFullData = !!(group[0].props.vuid || group[0].props.name);

        let marker;
        if (count > 1) {
            // Multi-voter location
            const isApartment = group.some(v => v.unitNum);
            const badgeText = count > 9 ? '9+' : count;
            
            if (isApartment) {
                const buildingIcon = L.divIcon({
                    className: 'apartment-marker',
                    html: `<div style="width:26px;height:26px;display:flex;align-items:center;justify-content:center;background:#555;border-radius:4px;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.4);position:relative;color:#fff;font-size:14px;">🏢<span style="position:absolute;top:-10px;right:-12px;background:rgba(0,0,0,0.8);color:#fff;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:bold;border:1px solid #fff;">${badgeText}</span></div>`,
                    iconSize: [26, 26],
                    iconAnchor: [13, 13]
                });
                marker = L.marker([lat, lng], { icon: buildingIcon });
            } else {
                const fillColor = getMarkerFillColor(markerColor);
                const showBadgeNum = window.showNumericBadges !== false;
                const badgeHtml = showBadgeNum
                    ? `<span style="position:absolute;top:-10px;right:-10px;background:rgba(0,0,0,0.75);color:#fff;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:bold;border:1px solid #fff;">${badgeText}</span>`
                    : '';
                const badgeIcon = L.divIcon({
                    className: 'household-marker',
                    html: `<div style="width:20px;height:20px;border-radius:50%;background:${fillColor};border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,0.4);position:relative;">${badgeHtml}</div>`,
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                });
                marker = L.marker([lat, lng], { icon: badgeIcon });
            }
        } else {
            // Single voter
            if (isNewVoter && (newVotersFilter || !flippedVotersFilter || flippedVotersFilter === 'none')) {
                const starColor = newVotersFilter ? '#DAA520' : getMarkerFillColor(markerColor);
                marker = L.marker([lat, lng], { icon: createStarIcon(starColor, 20) });
            } else {
                marker = L.circleMarker([lat, lng], {
                    radius: 8,
                    fillColor: getMarkerFillColor(markerColor),
                    color: '#fff',
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8
                });
            }
        }

        if (hasFullData) {
            // Full data available — build popup immediately (legacy path)
            _bindFullPopup(marker, group, addrKey, count);
        } else {
            // Heatmap data only — lazy-load voter details on popup open
            marker.bindPopup(`<div id="popup-${lat.toFixed(5)}-${lng.toFixed(5)}" style="min-width:200px;text-align:center;padding:12px;"><span style="color:#999;">Loading voter details...</span></div>`, { maxWidth: 400, maxHeight: 400 });
            marker.on('popupopen', () => _lazyLoadPopup(marker, lat, lng));
        }

        markerClusterGroup.addLayer(marker);
    });
    } // end authFullAccess gate
    
    console.log('Added', markerClusterGroup.getLayers().length, 'markers to cluster group');
    console.log('Created', heatmapData.length, 'heatmap points');
    console.log('Created', heatmapDataDemocratic.length, 'Democratic heatmap points');
    console.log('Created', heatmapDataRepublican.length, 'Republican heatmap points');
    console.log('Party filter:', partyFilter);
    console.log('Heatmap mode:', window.heatmapMode);
    
    // Update the stats box — only show DB-driven stats (from _fetchAndDisplayStats).
    // If DB stats aren't loaded yet, show a brief loading state instead of
    // stale fallback numbers that use the statewide total.
    const ds = window.currentDataset || currentDataset;
    if (ds && ds._dbStats) {
        updateDatasetStatsBox();
    } else {
        const el = document.getElementById('dataset-stats-content');
        if (el) el.innerHTML = '<span style="color:#999;">Loading stats...</span>';
    }
    
    // Update heatmap layers by recreating them with new data
    // This avoids leaflet-heat internal errors with setLatLngs when map container isn't ready
    
    // Helper: safely remove a heatmap layer from the map
    function safeRemoveHeatLayer(layer) {
        if (layer && map && map.hasLayer(layer)) {
            map.removeLayer(layer);
        }
    }
    
    // Remove all existing heatmap layers
    safeRemoveHeatLayer(heatmapLayer);
    safeRemoveHeatLayer(heatmapLayerDemocratic);
    safeRemoveHeatLayer(heatmapLayerRepublican);
    safeRemoveHeatLayer(flippedHeatmapLayer);
    safeRemoveHeatLayer(newVotersHeatmapLayer);
    
    // Recreate traditional heatmap (rainbow gradient for turnout)
    if (heatmapData.length > 0) {
        heatmapLayer = L.heatLayer(heatmapData, {
            radius: 25,
            blur: 35,
            maxZoom: typeof config !== 'undefined' ? config.HEATMAP_MAX_ZOOM : 16,
            max: 1.0,
            minOpacity: 0.2,
            maxOpacity: 0.6
            // Uses default rainbow gradient: blue → cyan → green → yellow → orange → red
        });
        console.log('Updated traditional heatmap layer with', heatmapData.length, 'points');
    }
    
    // Recreate Democratic heatmap - VIBRANT BLUE
    if (heatmapDataDemocratic.length > 0) {
        heatmapLayerDemocratic = L.heatLayer(heatmapDataDemocratic, {
            radius: 25,
            blur: 35,
            maxZoom: typeof config !== 'undefined' ? config.HEATMAP_MAX_ZOOM : 16,
            max: 1.0,
            minOpacity: 0.4,
            maxOpacity: 0.85,
            gradient: {
                0.0: 'rgba(173, 216, 255, 0)',
                0.2: 'rgba(100, 180, 255, 0.6)',
                0.4: 'rgba(50, 140, 255, 0.75)',
                0.6: 'rgba(0, 100, 255, 0.85)',
                0.8: 'rgba(0, 70, 220, 0.92)',
                1.0: 'rgba(0, 50, 200, 1.0)'
            }
        });
        console.log('Updated Democratic heatmap layer with', heatmapDataDemocratic.length, 'points');
    } else {
        heatmapLayerDemocratic = null;
        console.log('Democratic heatmap has no data');
    }
    
    // Recreate Republican heatmap - VIBRANT RED
    if (heatmapDataRepublican.length > 0) {
        heatmapLayerRepublican = L.heatLayer(heatmapDataRepublican, {
            radius: 25,
            blur: 35,
            maxZoom: typeof config !== 'undefined' ? config.HEATMAP_MAX_ZOOM : 16,
            max: 1.0,
            minOpacity: 0.4,
            maxOpacity: 0.85,
            gradient: {
                0.0: 'rgba(255, 173, 173, 0)',
                0.2: 'rgba(255, 100, 100, 0.6)',
                0.4: 'rgba(255, 50, 50, 0.75)',
                0.6: 'rgba(255, 0, 50, 0.85)',
                0.8: 'rgba(220, 0, 60, 0.92)',
                1.0: 'rgba(200, 0, 70, 1.0)'
            }
        });
        console.log('Updated Republican heatmap layer with', heatmapDataRepublican.length, 'points');
    } else {
        heatmapLayerRepublican = null;
        console.log('Republican heatmap has no data');
    }
    
    // Recreate flipped voters heatmap
    if (heatmapDataFlipped.length > 0) {
        const flipColor = flippedVotersFilter === 'to-red' ? '#C62828' : '#6A1B9A';
        flippedHeatmapLayer = L.heatLayer(heatmapDataFlipped, {
            radius: 25,
            blur: 35,
            maxZoom: typeof config !== 'undefined' ? config.HEATMAP_MAX_ZOOM : 16,
            max: 1.0,
            minOpacity: 0.2,
            maxOpacity: 0.6,
            gradient: { 0.4: flipColor, 0.65: flipColor, 1: flipColor }
        });
        console.log('Recreated flipped heatmap layer with', heatmapDataFlipped.length, 'points, color:', flipColor);
    } else {
        flippedHeatmapLayer = null;
        console.log('Flipped heatmap has no data');
    }
    
    // Recreate new voters heatmap (golden yellow)
    if (heatmapDataNewVoters.length > 0) {
        newVotersHeatmapLayer = L.heatLayer(heatmapDataNewVoters, {
            radius: 25,
            blur: 35,
            maxZoom: typeof config !== 'undefined' ? config.HEATMAP_MAX_ZOOM : 16,
            max: 1.0,
            minOpacity: 0.2,
            maxOpacity: 0.6,
            gradient: {
                0.0: 'rgba(218, 165, 32, 0)',
                0.2: 'rgba(218, 165, 32, 0.3)',
                0.4: 'rgba(218, 165, 32, 0.5)',
                0.6: 'rgba(255, 193, 37, 0.7)',
                0.8: 'rgba(255, 215, 0, 0.85)',
                1.0: 'rgba(255, 215, 0, 1.0)'
            }
        });
        console.log('Recreated new voters heatmap with', heatmapDataNewVoters.length, 'points');
    } else {
        newVotersHeatmapLayer = null;
        console.log('New voters heatmap has no data');
    }
    
    // Don't auto-zoom to fit data bounds - keep focused on Hidalgo County
    // Users can manually zoom/pan to see outlier data points
    
    // Update map view to show the appropriate layers
    updateMapView();
    
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
    // Legacy: generic metadata.json is no longer used.
    // Per-dataset metadata is loaded via discoverDatasets() and the backend API.
    return;
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
 * Fetch and render voting history for a flipped voter.
 * Calls /api/voter-history/<vuid> and renders a compact table
 * showing each election with D/R colored cells.
 */
async function fetchVoterHistory(vuid) {
    const el = document.getElementById(`history-${vuid}`);
    if (!el) return;
    // Avoid re-fetching if already loaded
    if (el.dataset.loaded === 'true') return;
    try {
        const resp = await fetch(`/api/voter-history/${vuid}`);
        if (!resp.ok) {
            el.textContent = 'History unavailable';
            return;
        }
        const data = await resp.json();
        const history = data.history || [];
        if (history.length === 0) {
            el.innerHTML = '<span style="color:#aaa;">No prior voting history</span>';
            el.dataset.loaded = 'true';
            return;
        }
        // Show last 4 elections max (most recent first for readability)
        const recent = history.slice(-4);
        let html = '<div style="margin-top:2px;font-size:10px;color:#888;font-weight:600;">Voting History</div>';
        html += '<table style="border-collapse:collapse;margin-top:2px;font-size:10px;width:100%;table-layout:fixed;"><tr>';
        recent.forEach(h => {
            const yr = h.year ? ("'" + String(h.year).slice(-2)) : '?';
            const method = h.isEarlyVoting ? 'EV' : 'ED';
            html += `<td style="padding:2px 3px;text-align:center;border:1px solid #ddd;font-weight:600;background:#f5f5f5;font-size:9px;overflow:hidden;">${yr} ${method}</td>`;
        });
        html += '</tr><tr>';
        recent.forEach(h => {
            const party = (h.party || '').charAt(0).toUpperCase(); // D or R
            const bg = party === 'D' ? '#1565C0' : party === 'R' ? '#C62828' : '#888';
            html += `<td style="padding:3px 4px;text-align:center;border:1px solid #ddd;color:#fff;font-weight:bold;background:${bg}">${party || '?'}</td>`;
        });
        html += '</tr></table>';
        el.innerHTML = html;
        el.dataset.loaded = 'true';
    } catch (e) {
        console.warn('Failed to fetch voter history for', vuid, e);
        el.textContent = 'History unavailable';
    }
}

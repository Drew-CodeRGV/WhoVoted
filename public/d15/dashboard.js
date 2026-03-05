// District 15 Election Night Dashboard

let map;
let precinctLayer;
let countyLayer;
let districtBoundary;
let currentVizMode = 'solid'; // 'solid' or 'heatmap'
let currentData = null;

// Initialize map centered on District 15
function initMap() {
    map = L.map('map', {
        zoomControl: true,
        attributionControl: true
    }).setView([26.3, -98.2], 10); // Centered on District 15 - increased zoom
    
    // Use OpenStreetMap tiles (more reliable)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    console.log('Map initialized at [26.3, -98.2] zoom 10');
    
    // Load District 15 boundary
    loadDistrictBoundary();
    
    // Load initial data
    loadElectionData();
    
    // Auto-refresh every 30 seconds
    setInterval(loadElectionData, 30000);
    
    // Setup visualization mode toggle
    setupVizToggle();
}

async function loadDistrictBoundary() {
    try {
        console.log('Loading TX-15 boundary...');
        const response = await fetch('/d15/tx15_boundary.json');
        if (!response.ok) {
            console.error('Failed to load boundary:', response.status);
            return;
        }
        const data = await response.json();
        
        if (data.features && data.features.length > 0) {
            console.log('Found TX-15 boundary');
            
            districtBoundary = L.geoJSON(data, {
                style: {
                    color: '#3b82f6',
                    weight: 4,
                    opacity: 1,
                    fillOpacity: 0,
                    fillColor: 'transparent',
                    dashArray: '10, 5'
                }
            }).addTo(map);
            
            // Fit map to district bounds
            const bounds = districtBoundary.getBounds();
            console.log('District bounds:', bounds);
            map.fitBounds(bounds, { padding: [50, 50] });
        }
    } catch (error) {
        console.error('Error loading district boundary:', error);
    }
}

async function loadElectionData() {
    const btn = document.getElementById('refreshBtn');
    btn.classList.add('loading');
    
    try {
        const response = await fetch('/d15api/results');
        const data = await response.json();
        
        currentData = data; // Store for mode switching
        
        updateStats(data.totals);
        updateCounties(data.counties);
        updatePrecincts(data.precincts);
        updateMap(data);
        
        document.getElementById('lastUpdated').textContent = 
            `Last updated: ${new Date().toLocaleTimeString()}`;
    } catch (error) {
        console.error('Error loading election data:', error);
    } finally {
        btn.classList.remove('loading');
    }
}

function updateStats(totals) {
    if (!totals) {
        totals = { dem: 0, rep: 0 };
    }
    const demVotes = totals.dem || 0;
    const repVotes = totals.rep || 0;
    const total = demVotes + repVotes;
    
    const demPct = total > 0 ? (demVotes / total * 100).toFixed(1) : 0;
    const repPct = total > 0 ? (repVotes / total * 100).toFixed(1) : 0;
    
    document.getElementById('demVotes').textContent = demVotes.toLocaleString();
    document.getElementById('repVotes').textContent = repVotes.toLocaleString();
    document.getElementById('demPct').textContent = `${demPct}%`;
    document.getElementById('repPct').textContent = `${repPct}%`;
    
    // Highlight winning card
    const demCard = document.getElementById('demCard');
    const repCard = document.getElementById('repCard');
    
    demCard.classList.remove('winning', 'losing');
    repCard.classList.remove('winning', 'losing');
    
    if (demVotes > repVotes) {
        demCard.classList.add('winning');
        repCard.classList.add('losing');
    } else if (repVotes > demVotes) {
        repCard.classList.add('winning');
        demCard.classList.add('losing');
    }
}

function updateCounties(counties) {
    const list = document.getElementById('countiesList');
    list.innerHTML = '';
    
    if (!counties || counties.length === 0) {
        list.innerHTML = '<div style="padding: 20px; text-align: center; color: #718096;">No county data available yet</div>';
        return;
    }
    
    counties.forEach(county => {
        const total = county.dem + county.rep;
        const demPct = total > 0 ? (county.dem / total * 100) : 50;
        const margin = Math.abs(county.dem - county.rep);
        const winner = county.dem > county.rep ? 'dem' : 'rep';
        const marginPct = total > 0 ? (margin / total * 100).toFixed(1) : 0;
        
        const item = document.createElement('div');
        item.className = `county-item ${winner}`;
        item.innerHTML = `
            <div class="item-header">
                <div class="item-name">${county.name}</div>
                <div class="item-margin">+${marginPct}%</div>
            </div>
            <div class="vote-bar">
                <div class="vote-bar-fill ${winner}" style="width: ${Math.max(demPct, 100 - demPct)}%"></div>
            </div>
            <div class="vote-counts">
                <span>Bobby: ${county.dem.toLocaleString()}</span>
                <span>Ada: ${county.rep.toLocaleString()}</span>
            </div>
        `;
        
        item.addEventListener('click', () => zoomToCounty(county.name));
        list.appendChild(item);
    });
}

function updatePrecincts(precincts) {
    const list = document.getElementById('precinctsList');
    list.innerHTML = '';
    
    if (!precincts || precincts.length === 0) {
        list.innerHTML = '<div style="padding: 20px; text-align: center; color: #718096;">No precinct data available yet</div>';
        return;
    }
    
    // Show top 10 precincts by total votes
    const sorted = precincts.sort((a, b) => (b.dem + b.rep) - (a.dem + a.rep)).slice(0, 10);
    
    sorted.forEach(precinct => {
        const total = precinct.dem + precinct.rep;
        const demPct = total > 0 ? (precinct.dem / total * 100) : 50;
        const margin = Math.abs(precinct.dem - precinct.rep);
        const winner = precinct.dem > precinct.rep ? 'dem' : 'rep';
        const marginPct = total > 0 ? (margin / total * 100).toFixed(1) : 0;
        
        const item = document.createElement('div');
        item.className = `precinct-item ${winner}`;
        item.innerHTML = `
            <div class="item-header">
                <div class="item-name">${precinct.county} - Precinct ${precinct.number}</div>
                <div class="item-margin">+${marginPct}%</div>
            </div>
            <div class="vote-bar">
                <div class="vote-bar-fill ${winner}" style="width: ${Math.max(demPct, 100 - demPct)}%"></div>
            </div>
            <div class="vote-counts">
                <span>Bobby: ${precinct.dem.toLocaleString()}</span>
                <span>Ada: ${precinct.rep.toLocaleString()}</span>
            </div>
        `;
        
        item.addEventListener('click', () => zoomToPrecinct(precinct));
        list.appendChild(item);
    });
}

function updateMap(data) {
    // Remove existing layers
    if (precinctLayer) map.removeLayer(precinctLayer);
    if (countyLayer) map.removeLayer(countyLayer);
    
    // For now, just show the district boundary
    // Precinct boundaries would require actual GeoJSON files for each precinct
    console.log('Map showing district boundary only (precinct boundaries not available)');
}

async function loadPrecinctLayerSolid(precincts) {
    try {
        const response = await fetch('/data/precinct_boundaries_combined.json');
        if (!response.ok) {
            console.log('Precinct boundaries not available, skipping precinct layer');
            return;
        }
        const geojson = await response.json();
        
        if (!geojson || !geojson.features || geojson.features.length === 0) {
            console.log('No precinct features found in boundaries file');
            return;
        }
        
        console.log(`Loaded ${geojson.features.length} precinct boundaries`);
        
        // Create lookup map for results
        const resultsMap = {};
        precincts.forEach(p => {
            const key = `${p.county}_${p.number}`;
            resultsMap[key] = p;
        });
        
        precinctLayer = L.geoJSON(geojson, {
            style: (feature) => {
                const county = feature.properties.county || feature.properties.COUNTY;
                const precinct = feature.properties.precinct || feature.properties.PRECINCT;
                const key = `${county}_${precinct}`;
                const results = resultsMap[key];
                
                if (!results || (results.dem + results.rep) === 0) {
                    return {
                        color: '#3b82f6',
                        weight: 2,
                        opacity: 0.6,
                        fillOpacity: 0.1,
                        fillColor: '#94a3b8'
                    };
                }
                
                const total = results.dem + results.rep;
                const demPct = results.dem / total;
                
                // Blue for Democratic, avoid red - use purple/orange for Republican
                const color = demPct > 0.5 ? '#3b82f6' : '#f97316';
                const fillOpacity = 0.5;
                
                return {
                    color: '#3b82f6',
                    weight: 2,
                    opacity: 0.8,
                    fillOpacity: fillOpacity,
                    fillColor: color
                };
            },
            onEachFeature: (feature, layer) => {
                const county = feature.properties.county || feature.properties.COUNTY;
                const precinct = feature.properties.precinct || feature.properties.PRECINCT;
                const key = `${county}_${precinct}`;
                const results = resultsMap[key];
                
                if (results) {
                    const total = results.dem + results.rep;
                    const demPct = total > 0 ? (results.dem / total * 100).toFixed(1) : 0;
                    const repPct = total > 0 ? (results.rep / total * 100).toFixed(1) : 0;
                    
                    layer.bindPopup(`
                        <div style="font-family: sans-serif;">
                            <h3 style="margin: 0 0 10px 0;">${county} - Precinct ${precinct}</h3>
                            <div style="margin-bottom: 5px;">
                                <strong>Democratic:</strong> ${results.dem.toLocaleString()} (${demPct}%)
                            </div>
                            <div>
                                <strong>Republican:</strong> ${results.rep.toLocaleString()} (${repPct}%)
                            </div>
                        </div>
                    `);
                }
            }
        }).addTo(map);
        
    } catch (error) {
        console.error('Error loading precinct layer:', error);
    }
}

async function loadPrecinctLayerHeatmap(precincts) {
    try {
        const response = await fetch('/data/precinct_boundaries_combined.json');
        const geojson = await response.json();
        
        // Create lookup map for results
        const resultsMap = {};
        precincts.forEach(p => {
            const key = `${p.county}_${p.number}`;
            resultsMap[key] = p;
        });
        
        precinctLayer = L.geoJSON(geojson, {
            style: (feature) => {
                const county = feature.properties.county || feature.properties.COUNTY;
                const precinct = feature.properties.precinct || feature.properties.PRECINCT;
                const key = `${county}_${precinct}`;
                const results = resultsMap[key];
                
                if (!results || (results.dem + results.rep) === 0) {
                    return {
                        color: '#3b82f6',
                        weight: 2,
                        opacity: 0.6,
                        fillOpacity: 0.05,
                        fillColor: '#94a3b8'
                    };
                }
                
                const total = results.dem + results.rep;
                const demPct = results.dem / total;
                const margin = Math.abs(demPct - 0.5);
                
                // Intensity based on margin (0 = close race, 1 = landslide)
                const intensity = margin * 2; // 0 to 1
                
                // Blue for Democratic, orange for Republican
                const color = demPct > 0.5 ? '#3b82f6' : '#f97316';
                const fillOpacity = 0.15 + (intensity * 0.6); // More intense = more opaque
                
                return {
                    color: '#3b82f6',
                    weight: 2,
                    opacity: 0.8,
                    fillOpacity: fillOpacity,
                    fillColor: color
                };
            },
            onEachFeature: (feature, layer) => {
                const county = feature.properties.county || feature.properties.COUNTY;
                const precinct = feature.properties.precinct || feature.properties.PRECINCT;
                const key = `${county}_${precinct}`;
                const results = resultsMap[key];
                
                if (results) {
                    const total = results.dem + results.rep;
                    const demPct = total > 0 ? (results.dem / total * 100).toFixed(1) : 0;
                    const repPct = total > 0 ? (results.rep / total * 100).toFixed(1) : 0;
                    
                    layer.bindPopup(`
                        <div style="font-family: sans-serif;">
                            <h3 style="margin: 0 0 10px 0;">${county} - Precinct ${precinct}</h3>
                            <div style="margin-bottom: 5px;">
                                <strong>Democratic:</strong> ${results.dem.toLocaleString()} (${demPct}%)
                            </div>
                            <div>
                                <strong>Republican:</strong> ${results.rep.toLocaleString()} (${repPct}%)
                            </div>
                        </div>
                    `);
                }
            }
        }).addTo(map);
        
    } catch (error) {
        console.error('Error loading precinct layer:', error);
    }
}

function zoomToCounty(countyName) {
    // Zoom to county bounds (would need county boundaries data)
    console.log('Zoom to county:', countyName);
}

function zoomToPrecinct(precinct) {
    // Zoom to specific precinct (would need to find in layer)
    console.log('Zoom to precinct:', precinct);
}

function setupVizToggle() {
    const solidBtn = document.getElementById('solidBtn');
    const heatmapBtn = document.getElementById('heatmapBtn');
    
    solidBtn.addEventListener('click', () => {
        if (currentVizMode === 'solid') return;
        
        currentVizMode = 'solid';
        solidBtn.classList.add('active');
        heatmapBtn.classList.remove('active');
        
        if (currentData) {
            updateMap(currentData);
        }
    });
    
    heatmapBtn.addEventListener('click', () => {
        if (currentVizMode === 'heatmap') return;
        
        currentVizMode = 'heatmap';
        heatmapBtn.classList.add('active');
        solidBtn.classList.remove('active');
        
        if (currentData) {
            updateMap(currentData);
        }
    });
}

// Event listeners
document.getElementById('refreshBtn').addEventListener('click', loadElectionData);

// Upload modal functionality
const uploadModal = document.getElementById('uploadModal');
const uploadBtn = document.getElementById('uploadBtn');
const closeModal = document.getElementById('closeModal');
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const urlInput = document.getElementById('urlInput');
const uploadStatus = document.getElementById('uploadStatus');

// Precinct to county mapping for District 15
const PRECINCT_COUNTY_MAP = {
    // Hidalgo County precincts in D15
    '001': 'Hidalgo', '002': 'Hidalgo', '003': 'Hidalgo', '004': 'Hidalgo',
    '005': 'Hidalgo', '006': 'Hidalgo', '008': 'Hidalgo', '012': 'Hidalgo',
    '013': 'Hidalgo', '014': 'Hidalgo', '015': 'Hidalgo', '016': 'Hidalgo',
    '017': 'Hidalgo', '018': 'Hidalgo', '019': 'Hidalgo', '020': 'Hidalgo',
    '021': 'Hidalgo', '022': 'Hidalgo', '023': 'Hidalgo', '024': 'Hidalgo',
    '025': 'Hidalgo', '030': 'Hidalgo', '031': 'Hidalgo', '032': 'Hidalgo',
    '033': 'Hidalgo', '029': 'Hidalgo', '040': 'Hidalgo', '041': 'Hidalgo',
    '042': 'Hidalgo', '043': 'Hidalgo', '044': 'Hidalgo',
    // Cameron County precincts in D15
    '101': 'Cameron', '102': 'Cameron', '103': 'Cameron', '104': 'Cameron',
    '105': 'Cameron', '106': 'Cameron', '107': 'Cameron', '108': 'Cameron',
    '109': 'Cameron', '110': 'Cameron', '111': 'Cameron', '112': 'Cameron',
    '113': 'Cameron', '114': 'Cameron', '115': 'Cameron', '116': 'Cameron',
    '117': 'Cameron', '118': 'Cameron', '119': 'Cameron', '120': 'Cameron',
    // Willacy County precincts in D15
    '301': 'Willacy', '302': 'Willacy', '303': 'Willacy', '304': 'Willacy',
    '305': 'Willacy', '306': 'Willacy', '307': 'Willacy', '308': 'Willacy',
    // Brooks County precincts in D15
    '401': 'Brooks', '402': 'Brooks', '403': 'Brooks', '404': 'Brooks',
};

uploadBtn.addEventListener('click', () => {
    uploadModal.classList.add('active');
});

closeModal.addEventListener('click', () => {
    uploadModal.classList.remove('active');
    resetUploadForm();
});

uploadModal.addEventListener('click', (e) => {
    if (e.target === uploadModal) {
        uploadModal.classList.remove('active');
        resetUploadForm();
    }
});

dropZone.addEventListener('click', () => {
    fileInput.click();
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileUpload(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
    }
});

urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleUrlUpload(urlInput.value);
    }
});

async function handleFileUpload(file) {
    try {
        showStatus('Processing file...', 'processing');
        
        const data = await file.arrayBuffer();
        const workbook = XLSX.read(data, { type: 'array' });
        
        const results = parseWorkbook(workbook);
        await uploadResults(results);
        
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    }
}

async function handleUrlUpload(url) {
    if (!url) {
        showStatus('Please enter a URL', 'error');
        return;
    }
    
    try {
        showStatus('Downloading file...', 'processing');
        
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to download file');
        
        const data = await response.arrayBuffer();
        const workbook = XLSX.read(data, { type: 'array' });
        
        const results = parseWorkbook(workbook);
        await uploadResults(results);
        
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    }
}

function parseWorkbook(workbook) {
    if (workbook.SheetNames.length < 3) {
        throw new Error('Excel file must have at least 3 tabs');
    }
    
    const sheetName = workbook.SheetNames[2]; // Tab 3
    const worksheet = workbook.Sheets[sheetName];
    
    const results = [];
    let rowNum = 4;
    
    while (true) {
        const precinctCell = worksheet[`A${rowNum}`];
        if (!precinctCell || !precinctCell.v) break;
        
        const precinct = String(precinctCell.v).padStart(3, '0');
        
        // Bobby Pulido Total Vote (Column F)
        const bobbyCell = worksheet[`F${rowNum}`];
        const bobbyVotes = bobbyCell ? parseInt(bobbyCell.v) || 0 : 0;
        
        // Ada Cuellar Total Vote (Column J)
        const adaCell = worksheet[`J${rowNum}`];
        const adaVotes = adaCell ? parseInt(adaCell.v) || 0 : 0;
        
        const county = PRECINCT_COUNTY_MAP[precinct] || 'Unknown';
        
        results.push({
            precinct: precinct,
            county: county,
            bobby_votes: bobbyVotes,
            ada_votes: adaVotes
        });
        
        rowNum++;
    }
    
    if (results.length === 0) {
        throw new Error('No data found in tab 3');
    }
    
    return results;
}

async function uploadResults(results) {
    try {
        showStatus('Uploading results...', 'processing');
        
        const response = await fetch('/d15api/upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ results: results })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showStatus(`Success! Uploaded ${data.count} precinct results.`, 'success');
            setTimeout(() => {
                uploadModal.classList.remove('active');
                resetUploadForm();
                loadElectionData(); // Refresh the dashboard
            }, 2000);
        } else {
            showStatus(`Error: ${data.error}`, 'error');
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    }
}

function showStatus(message, type) {
    uploadStatus.textContent = message;
    uploadStatus.className = `upload-status ${type}`;
}

function resetUploadForm() {
    urlInput.value = '';
    fileInput.value = '';
    uploadStatus.className = 'upload-status';
    uploadStatus.textContent = '';
}

// Initialize on load
document.addEventListener('DOMContentLoaded', initMap);

uploadBtn.addEventListener('click', () => {
    uploadModal.classList.add('active');
});

closeModal.addEventListener('click', () => {
    uploadModal.classList.remove('active');
    resetUploadForm();
});

uploadModal.addEventListener('click', (e) => {
    if (e.target === uploadModal) {
        uploadModal.classList.remove('active');
        resetUploadForm();
    }
});

dropZone.addEventListener('click', () => {
    fileInput.click();
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleURL(urlInput.value);
    }
});

function resetUploadForm() {
    fileInput.value = '';
    urlInput.value = '';
    uploadStatus.className = 'upload-status';
    uploadStatus.textContent = '';
}

function showStatus(message, type) {
    uploadStatus.className = `upload-status ${type}`;
    uploadStatus.textContent = message;
}

async function handleFile(file) {
    showStatus('Processing file...', 'processing');
    
    try {
        let xlsxData;
        
        // Check if it's a ZIP file
        if (file.name.endsWith('.zip')) {
            const zip = await JSZip.loadAsync(file);
            
            // Find XLSX file in ZIP
            let xlsxFile = null;
            for (const [filename, zipEntry] of Object.entries(zip.files)) {
                if (filename.endsWith('.xlsx') || filename.endsWith('.xls')) {
                    xlsxFile = zipEntry;
                    break;
                }
            }
            
            if (!xlsxFile) {
                throw new Error('No Excel file found in ZIP');
            }
            
            xlsxData = await xlsxFile.async('arraybuffer');
        } else {
            xlsxData = await file.arrayBuffer();
        }
        
        // Parse Excel file
        const workbook = XLSX.read(xlsxData, { type: 'array' });
        const results = await parseD15Results(workbook);
        
        if (results.length === 0) {
            throw new Error('No D-15 results found in file');
        }
        
        // Upload to server
        await uploadResults(results);
        
    } catch (error) {
        console.error('File processing error:', error);
        showStatus(`Error: ${error.message}`, 'error');
    }
}

async function handleURL(url) {
    if (!url) return;
    
    showStatus('Downloading file...', 'processing');
    
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to download file');
        
        const blob = await response.blob();
        
        // Determine file type from URL or content-type
        let filename = 'results.xlsx';
        if (url.endsWith('.zip')) {
            filename = 'results.zip';
        } else if (url.endsWith('.xls')) {
            filename = 'results.xls';
        }
        
        const file = new File([blob], filename);
        await handleFile(file);
        
    } catch (error) {
        console.error('URL download error:', error);
        showStatus(`Error: ${error.message}`, 'error');
    }
}

async function parseD15Results(workbook) {
    const results = [];
    
    // Strategy 1: Try tab 3 (index 2)
    if (workbook.SheetNames.length >= 3) {
        const sheetName = workbook.SheetNames[2];
        const worksheet = workbook.Sheets[sheetName];
        
        // Check if this sheet has "District 15" in row 1
        const titleCell = worksheet['A1'];
        if (titleCell && titleCell.v && titleCell.v.toString().includes('District 15')) {
            return parseSheet(worksheet);
        }
    }
    
    // Strategy 2: Search all sheets for "District 15"
    for (const sheetName of workbook.SheetNames) {
        const worksheet = workbook.Sheets[sheetName];
        const titleCell = worksheet['A1'];
        
        if (titleCell && titleCell.v && titleCell.v.toString().includes('District 15')) {
            return parseSheet(worksheet);
        }
    }
    
    throw new Error('Could not find District 15 results in file');
}

function parseSheet(worksheet) {
    const results = [];
    let rowNum = 4; // Start from row 4
    
    while (true) {
        const precinctCell = worksheet[`A${rowNum}`];
        if (!precinctCell || !precinctCell.v) break;
        
        const precinct = String(precinctCell.v).padStart(3, '0');
        
        // Bobby Pulido Total Vote (Column F)
        const bobbyCell = worksheet[`F${rowNum}`];
        const bobbyVotes = bobbyCell ? parseInt(bobbyCell.v) || 0 : 0;
        
        // Ada Cuellar Total Vote (Column J)
        const adaCell = worksheet[`J${rowNum}`];
        const adaVotes = adaCell ? parseInt(adaCell.v) || 0 : 0;
        
        // Determine county from precinct mapping
        const county = PRECINCT_COUNTY_MAP[precinct] || 'Unknown';
        
        results.push({
            precinct: precinct,
            county: county,
            bobby_votes: bobbyVotes,
            ada_votes: adaVotes
        });
        
        rowNum++;
    }
    
    return results;
}

async function uploadResults(results) {
    showStatus('Uploading results...', 'processing');
    
    try {
        const response = await fetch('/d15api/upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ results: results })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showStatus(`Success! Uploaded ${data.count} precinct results.`, 'success');
            
            // Reload data after 2 seconds
            setTimeout(() => {
                loadElectionData();
                uploadModal.classList.remove('active');
                resetUploadForm();
            }, 2000);
        } else {
            throw new Error(data.error || 'Upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showStatus(`Error: ${error.message}`, 'error');
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', initMap);

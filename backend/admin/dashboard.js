// Admin dashboard JavaScript
let selectedFile = null;
let statusPollInterval = null;

// DOM elements
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const fileInfo = document.getElementById('file-info');
const fileDetails = document.getElementById('file-details');
const uploadBtn = document.getElementById('upload-btn');
const errorMessage = document.getElementById('error-message');
const successMessage = document.getElementById('success-message');
const progressSection = document.getElementById('progress-section');
const progressFill = document.getElementById('progress-fill');
const statusText = document.getElementById('status-text');
const totalRecords = document.getElementById('total-records');
const processedRecords = document.getElementById('processed-records');
const geocodedCount = document.getElementById('geocoded-count');
const failedCount = document.getElementById('failed-count');
const logViewer = document.getElementById('log-viewer');
const downloadErrorsBtn = document.getElementById('download-errors-btn');

// Upload zone click handler
uploadZone.addEventListener('click', (e) => {
    console.log('Upload zone clicked');
    e.preventDefault();
    e.stopPropagation();
    fileInput.click();
});

// File input change handler
fileInput.addEventListener('change', (e) => {
    console.log('File input changed', e.target.files);
    if (e.target.files && e.target.files[0]) {
        handleFileSelect(e.target.files[0]);
    }
});

// Drag and drop handlers
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('dragover');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    
    const file = e.dataTransfer.files[0];
    handleFileSelect(file);
});

// Handle file selection
function handleFileSelect(file) {
    if (!file) return;
    
    // Validate file type
    const validExtensions = ['.csv', '.xlsx', '.xls'];
    const hasValidExt = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
    if (!hasValidExt) {
        showError('Only CSV and Excel (.xlsx, .xls) files are accepted');
        return;
    }
    
    // Validate file size (100MB)
    const maxSize = 100 * 1024 * 1024;
    if (file.size > maxSize) {
        showError('File size exceeds 100MB limit');
        return;
    }
    
    selectedFile = file;
    
    // Display file info
    const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
    fileDetails.innerHTML = `
        <div><strong>Name:</strong> ${file.name}</div>
        <div><strong>Size:</strong> ${sizeMB} MB</div>
        <div><strong>Type:</strong> ${file.type || 'text/csv'}</div>
    `;
    
    fileInfo.classList.add('show');
    uploadBtn.classList.add('show');
    hideError();
}

// Upload button handler
uploadBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    
    // Get form values
    const county = document.getElementById('county-select').value;
    const year = document.getElementById('election-year').value;
    const electionType = document.getElementById('election-type').value;
    const electionDate = document.getElementById('election-date').value;
    
    // Validate required fields
    if (!county) {
        showError('Please select a county');
        return;
    }
    
    if (!electionType) {
        showError('Please select an election type');
        return;
    }
    
    if (!electionDate) {
        showError('Please enter an election date');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('county', county);
    formData.append('year', year);
    formData.append('election_type', electionType);
    formData.append('election_date', electionDate);
    
    try {
        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Uploading...';
        
        // Show progress section immediately for upload progress
        progressSection.classList.add('show');
        statusText.textContent = 'Uploading file...';
        progressFill.style.width = '0%';
        progressFill.style.background = '#007bff';
        progressFill.textContent = '0%';
        
        // Use XMLHttpRequest for upload progress tracking
        const data = await new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const pct = Math.round((e.loaded / e.total) * 100);
                    progressFill.style.width = pct + '%';
                    progressFill.textContent = pct + '%';
                    statusText.textContent = `Uploading file... ${(e.loaded / 1024 / 1024).toFixed(1)}MB / ${(e.total / 1024 / 1024).toFixed(1)}MB`;
                }
            });
            
            xhr.addEventListener('load', () => {
                try {
                    const json = JSON.parse(xhr.responseText);
                    if (xhr.status >= 200 && xhr.status < 300 && json.success) {
                        resolve(json);
                    } else {
                        reject(new Error(json.error || 'Upload failed'));
                    }
                } catch (e) {
                    reject(new Error('Invalid server response'));
                }
            });
            
            xhr.addEventListener('error', () => reject(new Error('Upload failed. Please try again.')));
            xhr.addEventListener('abort', () => reject(new Error('Upload cancelled')));
            
            xhr.open('POST', '/admin/upload');
            xhr.withCredentials = true;
            xhr.send(formData);
        });
        
        showSuccess(`File uploaded successfully for ${county} County, ${year}. Processing started...`);
        statusText.textContent = 'Processing...';
        progressFill.style.width = '0%';
        progressFill.textContent = '';
        
        // Start polling for processing status
        startStatusPolling();
        
        // Hide upload section
        fileInfo.classList.remove('show');
        uploadBtn.classList.remove('show');
        selectedFile = null;
        fileInput.value = '';
    } catch (error) {
        showError(error.message || 'Upload failed. Please try again.');
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload and Process';
    }
});

// Start polling for processing status
function startStatusPolling() {
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
    }
    
    statusPollInterval = setInterval(async () => {
        try {
            const response = await fetch('/admin/status', {
                credentials: 'include'
            });
            
            const data = await response.json();
            
            updateStatus(data);
            
            // Get the most recent job status
            let jobStatus = data.status;
            let jobErrors = data.errors;
            if (data.jobs && data.jobs.length > 0) {
                const lastJob = data.jobs[data.jobs.length - 1];
                jobStatus = lastJob.status;
                jobErrors = lastJob.errors;
            }
            
            // Stop polling if completed or failed
            if (jobStatus === 'completed' || jobStatus === 'failed') {
                clearInterval(statusPollInterval);
                statusPollInterval = null;
                
                if (jobStatus === 'completed') {
                    showSuccess('Processing completed successfully! The Gazette will reflect the new data on next open.');
                    uploadBtn.disabled = false;
                    uploadBtn.textContent = 'Upload and Process';
                } else {
                    showError('Processing failed. Check the log for details.');
                    uploadBtn.disabled = false;
                    uploadBtn.textContent = 'Upload and Process';
                }
                
                // Show download errors button if there are errors
                if (jobErrors && jobErrors.length > 0) {
                    downloadErrorsBtn.classList.add('show');
                }
            }
        } catch (error) {
            console.error('Status polling error:', error);
        }
    }, 2000); // Poll every 2 seconds
}

// Update status display
function updateStatus(data) {
    // Handle both flat format and jobs array format
    let jobData = data;
    if (data.jobs && data.jobs.length > 0) {
        // Use the most recent job (last in array)
        jobData = data.jobs[data.jobs.length - 1];
    }
    
    if (jobData.status === 'idle') {
        // Don't hide progress if we just started a job — keep polling
        statusText.textContent = 'Waiting for processing to start...';
        progressSection.classList.add('show');
        return;
    }
    
    // Make sure progress section is visible
    progressSection.classList.add('show');
    
    // DEBUG: Log received data
    console.log('[DEBUG] Received status data:', {
        status: jobData.status,
        cache_hits: jobData.cache_hits,
        processed_records: jobData.processed_records,
        total_records: jobData.total_records,
        geocoded_count: jobData.geocoded_count,
        failed_count: jobData.failed_count,
        progress: jobData.progress
    });
    
    // Get values from data
    const cacheHits = jobData.cache_hits || 0;
    const processedRecs = jobData.processed_records || 0;
    const totalRecs = jobData.total_records || 1; // Avoid division by zero
    
    // Calculate how many were newly geocoded (processed minus cached)
    const newGeocoded = processedRecs - cacheHits;
    
    // DEBUG: Log calculations
    console.log('[DEBUG] Calculations:', {
        cacheHits,
        processedRecs,
        newGeocoded,
        totalRecs
    });
    
    // Calculate percentages based on TOTAL records (not processed)
    const cachedPercent = Math.round((cacheHits / totalRecs) * 100);
    const newPercent = Math.round((newGeocoded / totalRecs) * 100);
    const totalPercent = Math.round((processedRecs / totalRecs) * 100);
    
    // DEBUG: Log percentages
    console.log('[DEBUG] Percentages:', {
        cachedPercent,
        newPercent,
        totalPercent
    });
    
    // Update progress bar with two colors
    if (cacheHits > 0 && newGeocoded > 0) {
        // Two-segment progress bar
        // Calculate the proportion of cached vs new within the total progress
        const cachedProportion = (cacheHits / processedRecs) * 100;
        progressFill.style.background = `linear-gradient(to right, 
            #28a745 0%, 
            #28a745 ${cachedProportion}%, 
            #007bff ${cachedProportion}%, 
            #007bff 100%)`;
        progressFill.textContent = `${totalPercent}% (${cachedPercent}% cached, ${newPercent}% new)`;
    } else if (cacheHits > 0 && newGeocoded === 0) {
        // All cached
        progressFill.style.background = '#28a745';
        progressFill.textContent = `${totalPercent}% (all cached)`;
    } else {
        // All new
        progressFill.style.background = '#007bff';
        progressFill.textContent = `${totalPercent}% (all new)`;
    }
    
    // Set width based on total progress
    progressFill.style.width = `${totalPercent}%`;
    
    // Update status text
    statusText.textContent = jobData.status.charAt(0).toUpperCase() + jobData.status.slice(1);
    
    // Update record counts
    document.getElementById('total-records').textContent = jobData.total_records || 0;
    document.getElementById('processed-records').textContent = jobData.processed_records || 0;
    document.getElementById('geocoded-count').textContent = jobData.geocoded_count || 0;
    document.getElementById('failed-count').textContent = jobData.failed_count || 0;
    
    // Update log
    if (jobData.log_messages && jobData.log_messages.length > 0) {
        logViewer.innerHTML = jobData.log_messages.map(log => {
            const timestamp = new Date(log.timestamp).toLocaleTimeString();
            return `<div class="log-entry"><span class="log-timestamp">[${timestamp}]</span> ${log.message}</div>`;
        }).join('');
        
        // Auto-scroll to bottom
        logViewer.scrollTop = logViewer.scrollHeight;
    }
}

// Download errors button handler
downloadErrorsBtn.addEventListener('click', () => {
    window.location.href = '/admin/download/errors';
});

// Logout function
async function logout() {
    try {
        await fetch('/admin/logout', {
            method: 'POST',
            credentials: 'include'
        });
        window.location.href = '/';
    } catch (error) {
        console.error('Logout error:', error);
        window.location.href = '/';
    }
}

// Helper functions
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.add('show');
    successMessage.classList.remove('show');
}

function hideError() {
    errorMessage.classList.remove('show');
}

function showSuccess(message) {
    successMessage.textContent = message;
    successMessage.classList.add('show');
    errorMessage.classList.remove('show');
}

// Check for existing processing job on page load
window.addEventListener('load', async () => {
    try {
        const response = await fetch('/admin/status', {
            credentials: 'include'
        });
        
        const data = await response.json();
        
        // Get the most recent job status
        let jobStatus = data.status;
        if (data.jobs && data.jobs.length > 0) {
            jobStatus = data.jobs[data.jobs.length - 1].status;
        }
        
        if (jobStatus && jobStatus !== 'idle') {
            progressSection.classList.add('show');
            updateStatus(data);
            
            if (jobStatus === 'running' || jobStatus === 'queued') {
                startStatusPolling();
            }
        }
    } catch (error) {
        console.error('Initial status check error:', error);
    }
});


// ═══════════════════════════════════════════════════════════════════════════
// OLLAMA MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════

async function refreshOllamaStatus() {
    const statusContent = document.getElementById('ollama-status-content');
    const updateContent = document.getElementById('ollama-update-content');
    const modelsContent = document.getElementById('ollama-models-content');
    const statsContent = document.getElementById('ollama-stats-content');
    
    statusContent.innerHTML = '<div style="text-align:center;padding:20px;color:#888;">Loading...</div>';
    
    try {
        // Get Ollama status
        const statusResp = await fetch('/api/admin/ollama/status', {
            credentials: 'include'
        });
        const statusData = await statusResp.json();
        
        // Display status
        if (statusData.ollama_installed) {
            const statusHtml = `
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;">
                    <div>
                        <div style="font-size:12px;color:#888;margin-bottom:4px;">Ollama Service</div>
                        <div style="font-size:18px;font-weight:600;color:#11998e;">✓ Running</div>
                    </div>
                    <div>
                        <div style="font-size:12px;color:#888;margin-bottom:4px;">Version</div>
                        <div style="font-size:18px;font-weight:600;">${statusData.ollama_version || 'Unknown'}</div>
                    </div>
                    <div>
                        <div style="font-size:12px;color:#888;margin-bottom:4px;">API Status</div>
                        <div style="font-size:18px;font-weight:600;color:${statusData.api_available ? '#11998e' : '#f5576c'};">
                            ${statusData.api_available ? '✓ Available' : '✗ Unavailable'}
                        </div>
                    </div>
                    <div>
                        <div style="font-size:12px;color:#888;margin-bottom:4px;">Models Installed</div>
                        <div style="font-size:18px;font-weight:600;">${statusData.models_count || 0}</div>
                    </div>
                </div>
            `;
            statusContent.innerHTML = statusHtml;
            
            // Check for updates
            checkOllamaUpdates(updateContent, statusData.ollama_version);
            
            // Load models
            loadOllamaModels(modelsContent, statusData.models);
            
            // Load stats
            loadOllamaStats(statsContent);
        } else {
            statusContent.innerHTML = `
                <div style="text-align:center;padding:20px;">
                    <div style="font-size:48px;margin-bottom:12px;">⚠️</div>
                    <div style="font-size:16px;font-weight:600;color:#f5576c;margin-bottom:8px;">Ollama Not Installed</div>
                    <div style="font-size:13px;color:#666;margin-bottom:16px;">
                        The AI assistant requires Ollama to be installed on the server.
                    </div>
                    <button class="btn-primary" onclick="installOllama()">
                        📦 Install Ollama
                    </button>
                </div>
            `;
            updateContent.innerHTML = '';
            modelsContent.innerHTML = '';
            statsContent.innerHTML = '';
        }
    } catch (err) {
        console.error('Failed to load Ollama status:', err);
        statusContent.innerHTML = `
            <div style="text-align:center;padding:20px;color:#f5576c;">
                Failed to load status: ${err.message}
            </div>
        `;
    }
}

async function checkOllamaUpdates(container, currentVersion) {
    try {
        const resp = await fetch('/api/admin/ollama/check-updates', {
            credentials: 'include'
        });
        const data = await resp.json();
        
        if (data.update_available) {
            container.innerHTML = `
                <div style="display:flex;align-items:center;justify-content:space-between;">
                    <div>
                        <div style="font-size:14px;font-weight:600;color:#f5576c;margin-bottom:4px;">
                            🎉 Update Available!
                        </div>
                        <div style="font-size:13px;color:#666;">
                            Current: ${currentVersion || 'Unknown'} → Latest: ${data.latest_version}
                        </div>
                    </div>
                    <button class="btn-primary" style="background:#f5576c;" onclick="updateOllama()">
                        ⬆️ Update Now
                    </button>
                </div>
            `;
        } else {
            container.innerHTML = `
                <div style="display:flex;align-items:center;gap:12px;">
                    <div style="font-size:32px;">✓</div>
                    <div>
                        <div style="font-size:14px;font-weight:600;color:#11998e;">Up to Date</div>
                        <div style="font-size:13px;color:#666;">Version ${currentVersion || 'Unknown'}</div>
                    </div>
                </div>
            `;
        }
    } catch (err) {
        container.innerHTML = `<div style="color:#888;font-size:13px;">Unable to check for updates</div>`;
    }
}

function loadOllamaModels(container, models) {
    if (!models || models.length === 0) {
        container.innerHTML = `
            <div style="text-align:center;padding:20px;color:#888;">
                No models installed. Pull a model to get started.
            </div>
        `;
        return;
    }
    
    let html = '<div style="display:flex;flex-direction:column;gap:12px;">';
    models.forEach(model => {
        const sizeMB = (model.size / (1024 * 1024)).toFixed(0);
        const sizeGB = (model.size / (1024 * 1024 * 1024)).toFixed(2);
        const sizeDisplay = model.size > 1024 * 1024 * 1024 ? `${sizeGB} GB` : `${sizeMB} MB`;
        
        const isRecommended = model.name.includes('llama3.2:3b-instruct');
        
        html += `
            <div style="display:flex;align-items:center;justify-content:space-between;padding:12px;background:#fff;border:1px solid #e0e0e0;border-radius:6px;">
                <div style="flex:1;">
                    <div style="font-weight:600;font-size:14px;margin-bottom:4px;">
                        ${model.name}
                        ${isRecommended ? '<span class="badge badge-success" style="margin-left:8px;">Recommended</span>' : ''}
                    </div>
                    <div style="font-size:12px;color:#888;">
                        Size: ${sizeDisplay} • Modified: ${new Date(model.modified_at).toLocaleDateString()}
                    </div>
                </div>
                <div style="display:flex;gap:8px;">
                    <button class="btn-sm btn-preview" onclick="testModel('${model.name}')">
                        🧪 Test
                    </button>
                    <button class="btn-sm btn-delete" onclick="deleteModel('${model.name}')">
                        🗑️ Delete
                    </button>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    container.innerHTML = html;
}

async function loadOllamaStats(container) {
    try {
        const resp = await fetch('/api/admin/ollama/stats', {
            credentials: 'include'
        });
        const data = await resp.json();
        
        const html = `
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:16px;">
                <div>
                    <div style="font-size:12px;color:#888;margin-bottom:4px;">Total Queries</div>
                    <div style="font-size:20px;font-weight:600;">${data.total_queries || 0}</div>
                </div>
                <div>
                    <div style="font-size:12px;color:#888;margin-bottom:4px;">Avg Response Time</div>
                    <div style="font-size:20px;font-weight:600;">${data.avg_response_time || 'N/A'}</div>
                </div>
                <div>
                    <div style="font-size:12px;color:#888;margin-bottom:4px;">Success Rate</div>
                    <div style="font-size:20px;font-weight:600;">${data.success_rate || 'N/A'}</div>
                </div>
                <div>
                    <div style="font-size:12px;color:#888;margin-bottom:4px;">Memory Usage</div>
                    <div style="font-size:20px;font-weight:600;">${data.memory_usage || 'N/A'}</div>
                </div>
            </div>
        `;
        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = `<div style="color:#888;font-size:13px;">Stats not available</div>`;
    }
}

async function installOllama() {
    if (!confirm('This will install Ollama on the server. Continue?')) return;
    
    appendOllamaLog('Starting Ollama installation...');
    
    try {
        const resp = await fetch('/api/admin/ollama/install', {
            method: 'POST',
            credentials: 'include'
        });
        const data = await resp.json();
        
        if (data.success) {
            appendOllamaLog('✓ Ollama installed successfully');
            setTimeout(refreshOllamaStatus, 2000);
        } else {
            appendOllamaLog('✗ Installation failed: ' + data.error);
        }
    } catch (err) {
        appendOllamaLog('✗ Installation error: ' + err.message);
    }
}

async function updateOllama() {
    if (!confirm('This will update Ollama to the latest version. The service will be restarted. Continue?')) return;
    
    appendOllamaLog('Starting Ollama update...');
    
    try {
        const resp = await fetch('/api/admin/ollama/update', {
            method: 'POST',
            credentials: 'include'
        });
        const data = await resp.json();
        
        if (data.success) {
            appendOllamaLog('✓ Ollama updated successfully');
            appendOllamaLog(data.output);
            setTimeout(refreshOllamaStatus, 2000);
        } else {
            appendOllamaLog('✗ Update failed: ' + data.error);
        }
    } catch (err) {
        appendOllamaLog('✗ Update error: ' + err.message);
    }
}

function showPullModelDialog() {
    const modelName = prompt('Enter model name to pull (e.g., llama3.2:3b-instruct, llama3.2:1b):');
    if (!modelName) return;
    
    pullModel(modelName);
}

async function pullModel(modelName) {
    appendOllamaLog(`Pulling model: ${modelName}...`);
    
    try {
        const resp = await fetch('/api/admin/ollama/pull-model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ model: modelName })
        });
        const data = await resp.json();
        
        if (data.success) {
            appendOllamaLog(`✓ Model ${modelName} pulled successfully`);
            setTimeout(refreshOllamaStatus, 2000);
        } else {
            appendOllamaLog(`✗ Failed to pull model: ${data.error}`);
        }
    } catch (err) {
        appendOllamaLog(`✗ Pull error: ${err.message}`);
    }
}

async function deleteModel(modelName) {
    if (!confirm(`Delete model ${modelName}? This cannot be undone.`)) return;
    
    appendOllamaLog(`Deleting model: ${modelName}...`);
    
    try {
        const resp = await fetch('/api/admin/ollama/delete-model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ model: modelName })
        });
        const data = await resp.json();
        
        if (data.success) {
            appendOllamaLog(`✓ Model ${modelName} deleted`);
            setTimeout(refreshOllamaStatus, 1000);
        } else {
            appendOllamaLog(`✗ Failed to delete model: ${data.error}`);
        }
    } catch (err) {
        appendOllamaLog(`✗ Delete error: ${err.message}`);
    }
}

async function testModel(modelName) {
    appendOllamaLog(`Testing model: ${modelName}...`);
    
    try {
        const resp = await fetch('/api/admin/ollama/test-model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ model: modelName })
        });
        const data = await resp.json();
        
        if (data.success) {
            appendOllamaLog(`✓ Model test successful`);
            appendOllamaLog(`Response time: ${data.response_time}ms`);
            appendOllamaLog(`Sample output: ${data.sample_output}`);
        } else {
            appendOllamaLog(`✗ Model test failed: ${data.error}`);
        }
    } catch (err) {
        appendOllamaLog(`✗ Test error: ${err.message}`);
    }
}

function appendOllamaLog(message) {
    const log = document.getElementById('ollama-log');
    const timestamp = new Date().toLocaleTimeString();
    log.textContent += `[${timestamp}] ${message}\n`;
    log.scrollTop = log.scrollHeight;
}

// Initialize Ollama tab when it's opened
document.addEventListener('DOMContentLoaded', () => {
    const ollamaTab = document.querySelector('[data-tab="ollama"]');
    if (ollamaTab) {
        ollamaTab.addEventListener('click', () => {
            setTimeout(refreshOllamaStatus, 100);
        });
    }
});

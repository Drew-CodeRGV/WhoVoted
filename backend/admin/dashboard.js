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
    if (!file.name.endsWith('.csv')) {
        showError('Only CSV files are accepted');
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
        
        const response = await fetch('/admin/upload', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showSuccess(`File uploaded successfully for ${county} County, ${year}. Processing started...`);
            progressSection.classList.add('show');
            
            // Start polling for status
            startStatusPolling();
            
            // Hide upload section
            fileInfo.classList.remove('show');
            uploadBtn.classList.remove('show');
            selectedFile = null;
            fileInput.value = '';
        } else {
            showError(data.error || 'Upload failed');
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'Upload and Process';
        }
    } catch (error) {
        showError('Upload failed. Please try again.');
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
            
            // Stop polling if completed or failed
            if (data.status === 'completed' || data.status === 'failed') {
                clearInterval(statusPollInterval);
                statusPollInterval = null;
                
                if (data.status === 'completed') {
                    showSuccess('Processing completed successfully!');
                    uploadBtn.disabled = false;
                    uploadBtn.textContent = 'Upload and Process';
                } else {
                    showError('Processing failed. Check the log for details.');
                    uploadBtn.disabled = false;
                    uploadBtn.textContent = 'Upload and Process';
                }
                
                // Show download errors button if there are errors
                if (data.errors && data.errors.length > 0) {
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
    if (data.status === 'idle') {
        return;
    }
    
    // DEBUG: Log received data
    console.log('[DEBUG] Received status data:', {
        cache_hits: data.cache_hits,
        processed_records: data.processed_records,
        total_records: data.total_records,
        geocoded_count: data.geocoded_count
    });
    
    // Get values from data
    const cacheHits = data.cache_hits || 0;
    const processedRecords = data.processed_records || 0;
    const totalRecords = data.total_records || 1; // Avoid division by zero
    
    // Calculate how many were newly geocoded (processed minus cached)
    const newGeocoded = processedRecords - cacheHits;
    
    // DEBUG: Log calculations
    console.log('[DEBUG] Calculations:', {
        cacheHits,
        processedRecords,
        newGeocoded,
        totalRecords
    });
    
    // Calculate percentages based on TOTAL records (not processed)
    const cachedPercent = Math.round((cacheHits / totalRecords) * 100);
    const newPercent = Math.round((newGeocoded / totalRecords) * 100);
    const totalPercent = Math.round((processedRecords / totalRecords) * 100);
    
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
        const cachedProportion = (cacheHits / processedRecords) * 100;
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
    statusText.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
    
    // Update record counts
    document.getElementById('total-records').textContent = data.total_records || 0;
    document.getElementById('processed-records').textContent = data.processed_records || 0;
    document.getElementById('geocoded-count').textContent = data.geocoded_count || 0;
    document.getElementById('failed-count').textContent = data.failed_count || 0;
    
    // Update log
    if (data.log_messages && data.log_messages.length > 0) {
        logViewer.innerHTML = data.log_messages.map(log => {
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
        window.location.href = '/admin/login';
    } catch (error) {
        console.error('Logout error:', error);
        window.location.href = '/admin/login';
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
        
        if (data.status !== 'idle') {
            progressSection.classList.add('show');
            updateStatus(data);
            
            if (data.status === 'running') {
                startStatusPolling();
            }
        }
    } catch (error) {
        console.error('Initial status check error:', error);
    }
});

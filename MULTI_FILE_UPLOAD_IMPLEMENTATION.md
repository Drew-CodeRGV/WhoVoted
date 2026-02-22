# Multi-File Upload Implementation Summary

## Backend Changes (COMPLETED)

### 1. app.py - Job Management System
- ✅ Replaced single `current_job` with `active_jobs` dictionary
- ✅ Added `job_queue` list for queued jobs
- ✅ Added `max_concurrent_jobs = 3` to process 3 files simultaneously
- ✅ Added persistent job storage to `processing_jobs.json`
- ✅ Created `load_jobs_from_disk()` and `save_jobs_to_disk()` functions

### 2. app.py - Upload Endpoint
- ✅ Updated `/admin/upload` to accept multiple files via `files` parameter
- ✅ Each file creates a separate job with unique `job_id`
- ✅ Jobs are added to queue and processed in background
- ✅ Returns array of created jobs with their IDs

### 3. app.py - Background Job Processor
- ✅ Created `start_job_processor()` function
- ✅ Created `process_job_queue()` background thread
- ✅ Processes up to 3 jobs concurrently
- ✅ Automatically starts when jobs are queued

### 4. app.py - Status Endpoints
- ✅ Updated `/admin/status` to return all jobs (not just one)
- ✅ Added `/admin/job/<job_id>` for individual job status
- ✅ Returns queue length and active job count

### 5. processor.py - ProcessingJob Class
- ✅ Added `job_id` parameter to `__init__`
- ✅ Job ID can be provided or auto-generated

## Frontend Changes (NEEDED)

### 1. dashboard.html - File Input
- ✅ Added `multiple` attribute to file input

### 2. dashboard.html - JavaScript Variables
- ✅ Changed `selectedFile` to `selectedFiles` array

### 3. dashboard.html - File Selection Handler (TODO)
```javascript
// Update fileInput.addEventListener('change') around line 978
fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
        selectedFiles = Array.from(e.target.files);
        displaySelectedFiles();
    }
});

function displaySelectedFiles() {
    const fileDetails = document.getElementById('file-details');
    if (selectedFiles.length === 0) {
        fileDetails.innerHTML = 'No files selected';
        return;
    }
    
    let html = `<strong>${selectedFiles.length} file(s) selected:</strong><ul>`;
    selectedFiles.forEach(file => {
        html += `<li>${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)</li>`;
    });
    html += '</ul>';
    fileDetails.innerHTML = html;
    
    fileInfo.classList.add('show');
    uploadBtn.classList.add('show');
}
```

### 4. dashboard.html - Upload Handler (TODO)
```javascript
// Update upload button click handler around line 1270
uploadBtn.addEventListener('click', async () => {
    if (selectedFiles.length === 0) {
        showError('Please select at least one file');
        return;
    }
    
    // Validate form fields...
    
    const formData = new FormData();
    
    // Append all files
    selectedFiles.forEach(file => {
        formData.append('files', file);
    });
    
    // Append metadata (same for all files)
    formData.append('county', county);
    formData.append('year', year);
    formData.append('election_type', electionType);
    formData.append('election_date', electionDate);
    formData.append('voting_method', votingMethod);
    formData.append('primary_party', primaryParty);
    
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
            showSuccess(`${data.jobs.length} file(s) uploaded successfully. Processing started...`);
            
            if (data.errors.length > 0) {
                showError(`Some files failed: ${data.errors.join(', ')}`);
            }
            
            // Start polling for all jobs
            startStatusPolling();
            
            // Reset form
            selectedFiles = [];
            fileInput.value = '';
            fileInfo.classList.remove('show');
            uploadBtn.classList.remove('show');
        } else {
            showError(data.errors.join(', ') || 'Upload failed');
        }
    } catch (error) {
        showError('Upload failed. Please try again.');
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload and Process';
    }
});
```

### 5. dashboard.html - Status Polling (TODO)
```javascript
// Update startStatusPolling() around line 1330
function startStatusPolling() {
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
    }
    
    statusPollInterval = setInterval(async () => {
        try {
            const response = await fetch('/admin/status', {
                credentials: 'include'
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    clearInterval(statusPollInterval);
                    showError('Session expired. Please log in again.');
                }
                return;
            }
            
            const data = await response.json();
            
            // Update UI with all jobs
            updateJobsDisplay(data.jobs);
            
            // Stop polling if no active jobs
            if (data.active_count === 0 && data.queue_length === 0) {
                clearInterval(statusPollInterval);
                statusPollInterval = null;
            }
            
        } catch (error) {
            console.error('Status poll error:', error);
        }
    }, 2000);  // Poll every 2 seconds
}

function updateJobsDisplay(jobs) {
    const progressSection = document.getElementById('progress-section');
    
    if (jobs.length === 0) {
        progressSection.classList.remove('show');
        return;
    }
    
    progressSection.classList.add('show');
    
    // Create HTML for all jobs
    let html = '<div class="jobs-container">';
    
    jobs.forEach(job => {
        const statusClass = job.status === 'completed' ? 'success' : 
                           job.status === 'failed' ? 'error' : 
                           job.status === 'running' ? 'running' : 'queued';
        
        html += `
            <div class="job-card ${statusClass}">
                <div class="job-header">
                    <strong>${job.original_filename}</strong>
                    <span class="job-status">${job.status}</span>
                </div>
                <div class="job-info">
                    <span>${job.county} County - ${job.year} ${job.election_type}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${job.progress * 100}%">
                        ${Math.round(job.progress * 100)}%
                    </div>
                </div>
                <div class="job-stats">
                    <span>Total: ${job.total_records}</span>
                    <span>Processed: ${job.processed_records}</span>
                    <span>Geocoded: ${job.geocoded_count}</span>
                    <span>Failed: ${job.failed_count}</span>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    
    // Replace progress section content
    progressSection.innerHTML = '<h2>Processing Status</h2>' + html;
}
```

### 6. dashboard.html - CSS Styles (TODO)
```css
/* Add these styles to the <style> section */
.jobs-container {
    display: flex;
    flex-direction: column;
    gap: 15px;
}

.job-card {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 15px;
}

.job-card.running {
    border-left: 4px solid #007bff;
}

.job-card.success {
    border-left: 4px solid #28a745;
}

.job-card.error {
    border-left: 4px solid #dc3545;
}

.job-card.queued {
    border-left: 4px solid #ffc107;
}

.job-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.job-status {
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
}

.job-card.running .job-status {
    background: #007bff;
    color: white;
}

.job-card.success .job-status {
    background: #28a745;
    color: white;
}

.job-card.error .job-status {
    background: #dc3545;
    color: white;
}

.job-card.queued .job-status {
    background: #ffc107;
    color: #000;
}

.job-info {
    color: #666;
    font-size: 14px;
    margin-bottom: 10px;
}

.job-stats {
    display: flex;
    gap: 15px;
    font-size: 13px;
    color: #666;
    margin-top: 10px;
}
```

## Testing Steps

1. Start the server: `python app.py` in `WhoVoted/backend`
2. Navigate to http://localhost:5000/admin
3. Select multiple CSV/Excel files (use Ctrl+Click or Shift+Click)
4. Fill in the form fields
5. Click "Upload and Process"
6. Observe multiple progress bars showing each file's status
7. Navigate away and come back - jobs should still be visible
8. Check that up to 3 files process simultaneously

## Benefits

- ✅ Upload multiple files at once
- ✅ Process up to 3 files concurrently
- ✅ View progress of all jobs simultaneously
- ✅ Navigate away and return - jobs persist
- ✅ Each job has independent progress tracking
- ✅ Jobs are saved to disk for persistence across server restarts

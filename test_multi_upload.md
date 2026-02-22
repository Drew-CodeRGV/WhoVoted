# Multi-File Upload Testing Guide

## Backend Verification

The backend is fully configured for multi-threaded processing:

✅ **Job Management System**
- `active_jobs` dictionary tracks all jobs by job_id
- `job_queue` list manages queued jobs
- `max_concurrent_jobs = 3` allows 3 simultaneous uploads
- Jobs persist to `processing_jobs.json` for crash recovery

✅ **Upload Endpoint** (`/admin/upload`)
- Accepts multiple files via `files` parameter
- Creates separate job for each file with unique job_id
- Returns array of created jobs

✅ **Background Processor**
- Runs in separate thread
- Processes up to 3 jobs concurrently
- Automatically starts when jobs are queued
- Polls every 2 seconds for new jobs

✅ **Status Endpoints**
- `/admin/status` returns all active jobs
- `/admin/job/<job_id>` returns specific job status
- Includes queue length and active job count

## Frontend Verification

The frontend is now fully configured for multi-file display:

✅ **File Selection**
- File input has `multiple` attribute
- `selectedFiles` array stores multiple files
- Displays list of selected files with sizes

✅ **Upload Handler**
- Sends all files in single FormData request
- Shows success message with file count
- Displays errors for failed files

✅ **Status Display**
- Shows individual job cards for each file
- Each card has its own progress bar
- Color-coded status badges (running, queued, success, error)
- Real-time updates every 2 seconds

✅ **Job Cards**
- Display filename, county, year, election type
- Show progress percentage
- Display total/processed/geocoded/failed counts
- Auto-refresh until all jobs complete

## Testing Steps

### 1. Start the Server
```bash
cd WhoVoted/backend
python app.py
```

### 2. Access Admin Dashboard
Navigate to: http://localhost:5000/admin
Login: admin / admin2026!

### 3. Test Single File Upload
1. Click "Choose Files" button
2. Select ONE CSV file
3. Verify form fields are populated
4. Click "Upload and Process"
5. Verify single job card appears with progress

### 4. Test Multi-File Upload
1. Click "Choose Files" button
2. Hold Ctrl (Windows) or Cmd (Mac) and select 3-5 CSV files
3. Verify "X file(s) selected" message appears
4. Fill in form fields (county, year, election type, date)
5. Click "Upload and Process"
6. Verify multiple job cards appear
7. Observe that up to 3 jobs show "running" status simultaneously
8. Additional jobs show "queued" status
9. Watch as queued jobs start when running jobs complete

### 5. Test Concurrent Processing
1. Upload 5 files at once
2. Observe that 3 jobs start immediately (status: "running")
3. Observe that 2 jobs wait in queue (status: "queued")
4. As each job completes, a queued job should start
5. All jobs should complete successfully

### 6. Test Persistence
1. Upload multiple files
2. While processing, close the browser tab
3. Reopen http://localhost:5000/admin
4. Verify jobs are still visible and processing
5. Verify progress continues from where it left off

### 7. Test Error Handling
1. Upload a file with invalid format
2. Verify error message appears
3. Verify other valid files continue processing
4. Verify failed job shows "error" status

## Expected Behavior

### Concurrent Processing
- Maximum 3 jobs run simultaneously
- Additional jobs wait in queue
- Jobs start automatically as slots become available

### Status Updates
- Job cards update every 2 seconds
- Progress bars show real-time progress
- Status badges change color based on state:
  - 🟡 Yellow = Queued
  - 🔵 Blue/Purple = Running
  - 🟢 Green = Success
  - 🔴 Red = Error

### Performance
- Large files (10,000+ records) process in parallel
- Geocoding happens concurrently across jobs
- No blocking - UI remains responsive

## Troubleshooting

### Jobs Not Starting
- Check backend logs for errors
- Verify `max_concurrent_jobs = 3` in app.py
- Check `processing_jobs.json` for stuck jobs

### Status Not Updating
- Hard refresh browser (Ctrl+F5)
- Check browser console for JavaScript errors
- Verify `/admin/status` endpoint returns data

### Files Not Uploading
- Check file format (CSV or Excel)
- Verify required columns (VUID or CERT)
- Check backend logs for validation errors

## Success Criteria

✅ Can select multiple files at once
✅ Can upload multiple files in single request
✅ Up to 3 files process simultaneously
✅ Additional files queue automatically
✅ Each file has independent progress tracking
✅ Jobs persist across browser refresh
✅ Jobs persist across server restart
✅ Status updates in real-time
✅ Completed jobs show in upload history

## Architecture Summary

```
Frontend (dashboard.html)
├── File Selection (multiple attribute)
├── Upload Handler (FormData with multiple files)
├── Status Polling (every 2 seconds)
└── Job Cards Display (individual progress bars)

Backend (app.py)
├── Upload Endpoint (/admin/upload)
│   ├── Accepts multiple files
│   ├── Creates job for each file
│   └── Returns array of job IDs
├── Job Processor (background thread)
│   ├── Monitors job queue
│   ├── Starts up to 3 jobs concurrently
│   └── Saves state to disk
└── Status Endpoint (/admin/status)
    ├── Returns all active jobs
    ├── Includes queue length
    └── Shows active job count
```

## Next Steps

After verifying multi-file upload works:
1. Test with real voter data files
2. Monitor geocoding performance with concurrent jobs
3. Adjust `max_concurrent_jobs` based on server capacity
4. Consider adding job cancellation feature
5. Add job history/archive feature

# Admin Dashboard - Ollama Management

## Overview

The admin dashboard now includes a comprehensive Ollama management interface, allowing you to manage the AI assistant directly from the web interface without SSH access.

## Access

1. Navigate to: `https://politiquera.com/admin`
2. Sign in with Google (superadmin account)
3. Click the **🧠 AI Assistant** tab

## Features

### 1. Service Status Monitor

**Real-time status display:**
- ✓ Ollama service running/stopped
- Version information
- API availability check
- Number of installed models
- One-click refresh button

**If Ollama is not installed:**
- Shows installation prompt
- **📦 Install Ollama** button
- Automated installation process
- Progress tracking in action log

### 2. Update Management

**Automatic update checker:**
- Checks for new Ollama versions
- Compares current vs latest version
- Visual indicator when updates available

**One-click updates:**
- **⬆️ Update Now** button
- Downloads and installs latest version
- Automatically restarts Ollama service
- Shows update progress in action log
- Requires superadmin role

**Update process:**
1. Click **⬆️ Update Now**
2. Confirm update dialog
3. System downloads latest version
4. Ollama service restarts automatically
5. Status refreshes to show new version

### 3. Model Management

**View installed models:**
- Model name and version
- File size (GB/MB)
- Last modified date
- Recommended model badge (Llama 3.2 3B)

**Pull new models:**
1. Click **➕ Pull New Model**
2. Enter model name (e.g., `llama3.2:3b-instruct`, `llama3.2:1b`)
3. System downloads model
4. Progress shown in action log
5. Model appears in list when complete

**Available models:**
- `llama3.2:3b-instruct` (Recommended, 2GB)
- `llama3.2:1b` (Lightweight, 1GB)
- `llama3.2:8b-instruct` (High quality, 5GB)
- `phi-3:mini` (Alternative, 1.5GB)
- Any model from Ollama registry

**Test models:**
- Click **🧪 Test** button on any model
- Runs sample SQL generation query
- Shows response time (ms)
- Displays sample output
- Verifies model is working correctly

**Delete models:**
- Click **🗑️ Delete** button
- Confirmation dialog
- Permanently removes model
- Frees up disk space
- Requires superadmin role

### 4. Performance Statistics

**Metrics displayed:**
- Total queries processed
- Average response time
- Success rate percentage
- Memory usage

**Future enhancements:**
- Query history
- Performance graphs
- Usage trends
- Error rate tracking

### 5. Action Log

**Real-time operation tracking:**
- Timestamped entries
- All operations logged
- Success/failure indicators
- Detailed error messages
- Auto-scrolls to latest entry

**Logged operations:**
- Ollama installation
- Version updates
- Model pulls
- Model deletions
- Model tests
- Status checks

## API Endpoints

All endpoints require authentication. Some require superadmin role.

### GET /api/admin/ollama/status
**Auth:** Required  
**Returns:** Service status, version, models list

```json
{
  "ollama_installed": true,
  "ollama_version": "0.1.17",
  "api_available": true,
  "models_count": 1,
  "models": [
    {
      "name": "llama3.2:3b-instruct",
      "size": 2147483648,
      "modified_at": "2024-03-04T12:00:00Z"
    }
  ]
}
```

### GET /api/admin/ollama/check-updates
**Auth:** Required  
**Returns:** Update availability status

```json
{
  "update_available": true,
  "current_version": "0.1.16",
  "latest_version": "0.1.17"
}
```

### POST /api/admin/ollama/update
**Auth:** Superadmin required  
**Returns:** Update result

```json
{
  "success": true,
  "output": "Ollama updated successfully..."
}
```

### POST /api/admin/ollama/install
**Auth:** Superadmin required  
**Returns:** Installation result

```json
{
  "success": true,
  "output": "Ollama installed successfully..."
}
```

### POST /api/admin/ollama/pull-model
**Auth:** Required  
**Body:** `{"model": "llama3.2:3b-instruct"}`  
**Returns:** Pull result

```json
{
  "success": true,
  "model": "llama3.2:3b-instruct"
}
```

### POST /api/admin/ollama/delete-model
**Auth:** Superadmin required  
**Body:** `{"model": "llama3.2:3b-instruct"}`  
**Returns:** Deletion result

```json
{
  "success": true,
  "model": "llama3.2:3b-instruct"
}
```

### POST /api/admin/ollama/test-model
**Auth:** Required  
**Body:** `{"model": "llama3.2:3b-instruct"}`  
**Returns:** Test result

```json
{
  "success": true,
  "model": "llama3.2:3b-instruct",
  "response_time": 2341,
  "sample_output": "SELECT * FROM voters WHERE congressional_district = 'TX-15'..."
}
```

### GET /api/admin/ollama/stats
**Auth:** Required  
**Returns:** Usage statistics

```json
{
  "total_queries": 1247,
  "avg_response_time": "2.3s",
  "success_rate": "98.5%",
  "memory_usage": "2.1 GB"
}
```

## Security

### Role-Based Access Control

**Authenticated Users:**
- View status
- Check for updates
- Pull new models
- Test models
- View statistics

**Superadmin Only:**
- Install Ollama
- Update Ollama
- Delete models

### Audit Trail

All operations are logged with:
- Timestamp
- User who performed action
- Operation type
- Success/failure status
- Error details (if failed)

## Troubleshooting

### "Ollama Not Installed"
1. Click **📦 Install Ollama** button
2. Wait for installation to complete
3. Check action log for progress
4. Refresh status after installation

### "API Not Available"
1. Check if Ollama service is running:
   ```bash
   systemctl status ollama
   ```
2. Restart service if needed:
   ```bash
   systemctl restart ollama
   ```
3. Refresh status in admin dashboard

### Update Fails
1. Check action log for error details
2. Try manual update via SSH:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   systemctl restart ollama
   ```
3. Refresh admin dashboard

### Model Pull Fails
1. Check internet connectivity
2. Verify model name is correct
3. Check disk space (models are 1-5GB)
4. Try again or use different model

### Model Test Fails
1. Check if model is fully downloaded
2. Verify Ollama service is running
3. Try restarting Ollama service
4. Check action log for error details

## Best Practices

### Model Selection
- **Start with:** `llama3.2:3b-instruct` (recommended, 2GB)
- **For low memory:** `llama3.2:1b` (1GB)
- **For better quality:** `llama3.2:8b-instruct` (5GB, slower)

### Updates
- Check for updates weekly
- Update during low-traffic periods
- Test AI search after updates
- Keep at least one model installed

### Disk Space
- Each model: 1-5GB
- Keep 10GB free for operations
- Delete unused models
- Monitor disk usage

### Performance
- Test models after installation
- Monitor response times
- Check success rates
- Restart service if slow

## Maintenance Schedule

### Daily
- Check service status
- Review action log for errors

### Weekly
- Check for Ollama updates
- Review performance stats
- Test models if issues reported

### Monthly
- Clean up unused models
- Review disk space usage
- Update to latest version

## Future Enhancements

### Planned Features
- [ ] Automatic update scheduling
- [ ] Model performance comparison
- [ ] Query history viewer
- [ ] Usage analytics dashboard
- [ ] Email alerts for failures
- [ ] Backup/restore configurations
- [ ] Multi-model A/B testing
- [ ] Custom model fine-tuning

### Integration Ideas
- [ ] Slack notifications for updates
- [ ] Prometheus metrics export
- [ ] Grafana dashboard integration
- [ ] Automated health checks
- [ ] Load balancing multiple models

## Support

### Getting Help
1. Check action log for error details
2. Review troubleshooting section
3. Check Ollama documentation: https://ollama.com/docs
4. Contact system administrator

### Reporting Issues
Include:
- Screenshot of error
- Action log entries
- Service status details
- Steps to reproduce

---

**Admin Dashboard Ollama Management** - Making AI assistant management accessible and easy!

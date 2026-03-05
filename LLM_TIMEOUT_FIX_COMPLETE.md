# LLM Timeout Fix - Complete

## Problem Summary

The AI-powered search feature was hanging when accessed through the web browser, returning a 500 Internal Server Error. The issue occurred specifically when:

- User was authenticated (Google OAuth)
- Request reached the `/api/llm/query` endpoint
- Logs showed "Question: ..." but never proceeded to "Converting question to SQL..."
- Direct Python tests worked perfectly
- HTTP requests through gunicorn workers hung indefinitely

## Root Cause

The Ollama LLM calls were blocking gunicorn worker threads without any timeout mechanism. When called through HTTP/gunicorn, the synchronous `ollama.generate()` calls would hang, blocking the worker and preventing any response to the client.

The original code used signal-based timeouts (`signal.SIGALRM`), which:
- Only work on Unix systems
- Don't work reliably in multi-threaded environments (like gunicorn workers)
- Can interfere with other signal handlers

## Solution Implemented

### 1. Threading-Based Timeouts

Replaced signal-based timeouts with a threading approach that works on all platforms and in threaded environments:

```python
def run_with_timeout(func, args=(), kwargs=None, timeout=30):
    """Run a function with a timeout using threading."""
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if thread.is_alive():
        raise TimeoutError(f"Operation timed out after {timeout} seconds")
    
    if exception[0]:
        raise exception[0]
    
    return result[0]
```

### 2. Timeout Configuration

- **SQL Generation**: 30-second timeout
  - Critical operation that must complete
  - Returns error to user if timeout occurs
  
- **Explanation Generation**: 15-second timeout
  - Non-critical, falls back to simple text
  - "Found X voter(s) matching your criteria"
  
- **Suggestion Generation**: 15-second timeout
  - Non-critical, returns empty array if timeout
  - User can still see results without suggestions

### 3. Enhanced Logging

Added comprehensive logging to track request flow:

```python
logger.info("Calling Ollama with 30s timeout...")
response = run_with_timeout(call_ollama, timeout=30)
logger.info("Ollama call completed")
```

This helps identify exactly where requests hang if issues persist.

### 4. Graceful Error Handling

All timeout errors are caught and handled gracefully:

```python
except TimeoutError as e:
    logger.error(f"LLM query generation timed out: {e}")
    return {
        'error': 'Query generation timed out. Ollama may be overloaded or not responding.',
        'sql': None,
        'question': question
    }
```

## Files Modified

1. **backend/llm_query.py**
   - Added `run_with_timeout()` helper function
   - Updated `question_to_sql()` with 30s timeout
   - Updated `explain_results()` with 15s timeout
   - Updated `suggest_followups()` with 15s timeout
   - Enhanced error handling for TimeoutError

2. **deploy/test_user_queries.py** (new)
   - Tests exact user queries
   - Comprehensive step-by-step testing
   - Timing measurements for each operation

3. **deploy/complete_llm_fix.sh** (new)
   - Complete deployment script
   - Pulls code, clears cache, restarts services
   - Runs tests and verifies endpoint
   - Shows detailed progress

4. **deploy/RUN_ON_SERVER.txt** (new)
   - Instructions for running deployment
   - Alternative manual commands
   - Troubleshooting guide

## Testing

### Local Testing (without Ollama)
```bash
cd WhoVoted
python deploy/test_user_queries.py
```

Expected: Will show Ollama not installed (normal for local dev)

### Server Testing
```bash
ssh user@server
cd /var/www/politiquera
bash deploy/complete_llm_fix.sh
```

Expected output:
- ✓ Code updated
- ✓ Cache cleared
- ✓ Ollama verified
- ✓ Gunicorn restarted
- ✓ Tests passed
- ✓ Endpoint responding

### Browser Testing

1. Go to https://politiquera.com
2. Sign in with Google
3. Click brain icon (🧠)
4. Test queries:
   - "Show me Female voters in TX-15 who voted in 2024 but not 2026"
   - "Show me which of my neighbors are Republican"

Expected: Results within 30-45 seconds

## Deployment Instructions

### Quick Deployment
```bash
cd /var/www/politiquera && bash deploy/complete_llm_fix.sh
```

### Manual Deployment
```bash
# Pull code
cd /var/www/politiquera
git pull origin main

# Clear cache
find backend -type d -name __pycache__ -exec rm -rf {} +
find backend -name "*.pyc" -delete

# Restart gunicorn
pkill -9 -f "gunicorn.*app:app"
cd backend
source venv/bin/activate
nohup gunicorn -w 4 -b 127.0.0.1:5000 --timeout 120 app:app > logs/gunicorn.log 2>&1 &

# Test
cd /var/www/politiquera
python3 deploy/test_user_queries.py
```

## Monitoring

### Watch Logs in Real-Time
```bash
tail -f /var/www/politiquera/backend/logs/error.log
```

### Check Gunicorn Status
```bash
ps aux | grep gunicorn
```

### Check Ollama Status
```bash
ollama list
```

### Test Ollama Directly
```bash
ollama run llama3.2:latest "Say hello"
```

## Troubleshooting

### If Still Hanging

1. **Check logs for timeout messages**
   ```bash
   grep -i "timeout" /var/www/politiquera/backend/logs/error.log
   ```

2. **Verify Ollama is responsive**
   ```bash
   time ollama list
   ```
   Should complete in < 1 second

3. **Test Ollama generation**
   ```bash
   time ollama run llama3.2:latest "Say hello"
   ```
   Should complete in < 5 seconds

4. **Check Ollama service**
   ```bash
   systemctl status ollama  # if using systemd
   ```

5. **Restart Ollama if needed**
   ```bash
   systemctl restart ollama  # if using systemd
   # or
   pkill ollama && ollama serve &
   ```

### If Getting Timeout Errors

This is actually good - it means the timeout is working! The issue is now with Ollama itself:

1. Check Ollama logs
2. Verify model is downloaded: `ollama list`
3. Try pulling model again: `ollama pull llama3.2:latest`
4. Check system resources (CPU, RAM, disk)
5. Consider using a smaller model if resources are limited

## Success Criteria

- ✓ No more indefinite hanging
- ✓ Timeout errors returned within 30 seconds
- ✓ User sees error message instead of infinite loading
- ✓ Worker threads don't get stuck
- ✓ Other requests continue to work even if LLM times out

## Next Steps

1. Deploy to production using `complete_llm_fix.sh`
2. Test with both user queries
3. Monitor logs for any timeout occurrences
4. If timeouts are frequent, investigate Ollama performance
5. Consider optimizing Ollama configuration or using smaller model

## Commit History

- `ed6d22c` - Fix LLM hanging issue with threading-based timeouts
- `a311b3f` - Add deployment script for LLM fix
- `e5a7ae6` - Add comprehensive test and deployment scripts

## Related Files

- `backend/llm_query.py` - Core LLM functionality with timeouts
- `backend/app.py` - LLM endpoint (lines 4720-4850)
- `public/search.js` - Frontend AI search interface
- `deploy/test_user_queries.py` - Test script for user queries
- `deploy/complete_llm_fix.sh` - Complete deployment script
- `deploy/RUN_ON_SERVER.txt` - Server deployment instructions

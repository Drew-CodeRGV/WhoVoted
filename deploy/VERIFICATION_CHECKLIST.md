# LLM Fix Verification Checklist

## Pre-Deployment Verification

- [x] Code committed to GitHub
- [x] Threading-based timeout implemented
- [x] Test scripts created
- [x] Deployment script created
- [x] Documentation complete

## Server Deployment Steps

### 1. SSH to Server
```bash
ssh user@politiquera.com
```

### 2. Run Deployment Script
```bash
cd /var/www/politiquera
bash deploy/complete_llm_fix.sh
```

### 3. Verify Output
Look for these success indicators:
- [ ] ✓ Code updated to latest version
- [ ] ✓ Python cache cleared
- [ ] ✓ Ollama command found
- [ ] ✓ llama3.2 model available
- [ ] ✓ Gunicorn is running
- [ ] ✓ Python tests passed (or completed with warnings)
- [ ] ✓ Endpoint responding correctly (401 Unauthorized)

## Post-Deployment Testing

### Test 1: Endpoint Accessibility
```bash
curl -X POST https://politiquera.com/api/llm/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me voters in TX-15"}'
```

Expected: HTTP 401 (Unauthorized) - this is correct!

### Test 2: Browser Test (Authenticated)

1. Open browser: https://politiquera.com
2. Sign in with Google
3. Click brain icon (🧠) in bottom-right corner
4. Enter query: "Show me Female voters in TX-15 who voted in 2024 but not 2026"
5. Click search or press Enter

Expected outcomes:
- [ ] Search modal opens
- [ ] "AI is thinking..." message appears
- [ ] Within 30-45 seconds, results appear OR timeout error shows
- [ ] If results appear: SQL query shown, explanation provided
- [ ] If timeout: Clear error message (not 500 error)

### Test 3: Second Query
Enter: "Show me which of my neighbors are Republican"

Expected:
- [ ] Geolocation permission requested (if first time)
- [ ] Query processes within 30-45 seconds
- [ ] Results or timeout error displayed

### Test 4: Monitor Logs
```bash
tail -f /var/www/politiquera/backend/logs/error.log
```

While testing, look for:
- [ ] "LLM query endpoint called"
- [ ] "Question: [your query]"
- [ ] "Calling Ollama with 30s timeout..."
- [ ] "Ollama call completed" (if successful)
- [ ] "LLM query generation timed out" (if timeout occurs)

## Success Criteria

### Minimum Success (Fix is Working)
- [ ] No more indefinite hanging
- [ ] Timeout errors appear within 30 seconds
- [ ] Worker threads don't get stuck
- [ ] Other site features continue working

### Optimal Success (Everything Working)
- [ ] Queries complete successfully in 10-30 seconds
- [ ] Results displayed with SQL, explanation, suggestions
- [ ] No timeout errors
- [ ] Smooth user experience

## Troubleshooting Guide

### Issue: Still Getting 500 Errors

Check:
```bash
# View recent errors
tail -n 50 /var/www/politiquera/backend/logs/error.log

# Check gunicorn is running
ps aux | grep gunicorn

# Restart if needed
pkill -9 -f "gunicorn.*app:app"
cd /var/www/politiquera/backend
source venv/bin/activate
nohup gunicorn -w 4 -b 127.0.0.1:5000 --timeout 120 app:app > logs/gunicorn.log 2>&1 &
```

### Issue: Timeout Errors Every Time

Check Ollama:
```bash
# Test Ollama directly
time ollama list
# Should complete in < 1 second

# Test generation
time ollama run llama3.2:latest "Say hello"
# Should complete in < 5 seconds

# If slow, restart Ollama
systemctl restart ollama  # if using systemd
# or
pkill ollama && ollama serve &
```

### Issue: "Ollama not available"

Check installation:
```bash
# Verify Ollama installed
which ollama

# Check Python can import
cd /var/www/politiquera/backend
source venv/bin/activate
python3 -c "import ollama; print('OK')"

# If import fails, install
pip install ollama
```

### Issue: Authentication Problems

Check session:
```bash
# View recent auth logs
grep -i "auth" /var/www/politiquera/backend/logs/error.log | tail -n 20

# Verify Google OAuth configured
cat /var/www/politiquera/backend/.env | grep GOOGLE
```

## Performance Benchmarks

Record these for comparison:

### Query 1: "Show me Female voters in TX-15 who voted in 2024 but not 2026"
- Time to SQL generation: _____ seconds
- Time to execute SQL: _____ seconds
- Time to explanation: _____ seconds
- Total time: _____ seconds
- Result count: _____ voters

### Query 2: "Show me which of my neighbors are Republican"
- Time to SQL generation: _____ seconds
- Time to execute SQL: _____ seconds
- Total time: _____ seconds
- Result count: _____ voters

### Acceptable Performance
- SQL generation: < 20 seconds
- SQL execution: < 5 seconds
- Explanation: < 10 seconds
- Total: < 35 seconds

### Excellent Performance
- SQL generation: < 10 seconds
- SQL execution: < 2 seconds
- Explanation: < 5 seconds
- Total: < 17 seconds

## Final Sign-Off

- [ ] Deployment completed successfully
- [ ] Both test queries work (or timeout gracefully)
- [ ] No indefinite hanging observed
- [ ] Logs show proper timeout handling
- [ ] User experience is acceptable
- [ ] Documentation updated

## Notes

Record any observations, issues, or performance metrics:

```
[Add notes here]
```

## Next Steps After Verification

If successful:
1. Monitor for 24 hours
2. Check for any timeout patterns
3. Optimize Ollama if needed
4. Consider caching common queries

If issues persist:
1. Review logs for patterns
2. Check Ollama resource usage
3. Consider smaller model (llama3.2:1b)
4. May need dedicated Ollama server

---

**Deployment Date:** _____________
**Deployed By:** _____________
**Status:** [ ] Success [ ] Partial [ ] Failed
**Notes:** _____________________________________________

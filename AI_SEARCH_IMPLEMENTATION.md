# AI-Powered Search Implementation

## Overview

The search interface has been upgraded to a hybrid AI-powered search that intelligently handles both:
1. **Traditional searches**: Name, address, VUID lookups (fast, direct database queries)
2. **Natural language queries**: Complex questions answered by local LLM (zero API costs)

## User Experience

### Search Icon
- Changed from magnifying glass (🔍) to brain icon (🧠) to indicate AI capabilities
- Located at bottom-left of screen (mobile-friendly positioning)

### Search Modal
- **Header**: "AI-Powered Search" with brain icon
- **Input**: Single search box that handles both types of queries
- **Examples**: Quick-fill buttons for common queries
- **AI Response Section**: Google-style AI answer box with:
  - ✨ AI Response header with sparkle icon
  - Natural language explanation of results
  - Collapsible SQL query viewer (for transparency)
  - Follow-up question suggestions
- **Results Section**: Data displayed below AI response
  - Voter cards for name/address searches
  - Data tables for aggregate queries

## Query Detection

The system automatically detects query type:

### Natural Language Queries (AI-powered)
Triggers when query contains:
- Question words: "how many", "show me", "find", "what", "who", etc.
- Multiple SQL keywords: "voted", "party", "district", "switched", etc.
- Comparison operators: "in", "but not", "and", "or"

**Examples:**
- "Show me voters in TX-15 who voted in 2024 but not 2026"
- "How many voters switched from Republican to Democratic?"
- "Find new voters in Hidalgo County"
- "What's the turnout rate by age group?"

### Traditional Searches (Direct DB)
Triggers for simple queries:
- Names: "John Smith", "Maria Garcia"
- Addresses: "123 Main St", "McAllen"
- VUIDs: "1234567890"

## Architecture

### Frontend (search.js)
```javascript
runHybridSearch(query)
  ├─> detectQuestion(query)
  │   ├─> isQuestion = true  → runAiSearch(query)
  │   └─> isQuestion = false → runTraditionalSearch(query)
  │
  ├─> runAiSearch(query)
  │   ├─> POST /api/llm/query
  │   ├─> Display AI response section
  │   ├─> Show explanation
  │   ├─> Show SQL (collapsible)
  │   ├─> Show suggestions
  │   └─> Render results (cards or table)
  │
  └─> runTraditionalSearch(query)
      ├─> GET /api/search-voters?q=...
      └─> Render voter cards
```

### Backend (app.py)
```python
@app.route('/api/llm/query', methods=['POST'])
@require_auth
def llm_query():
    # 1. Get query assistant (lazy load)
    # 2. Convert question to SQL
    # 3. Execute query
    # 4. Generate explanation
    # 5. Suggest follow-ups
    # 6. Return results
```

### LLM Engine (llm_query.py)
```python
class QueryAssistant:
    def question_to_sql(question, context)
        # Uses Llama 3.2 3B to generate SQL
    
    def execute_and_format(sql)
        # Runs query, formats results
    
    def explain_results(question, sql, results)
        # Generates natural language explanation
    
    def suggest_followups(question, results)
        # Suggests related questions
```

## Technical Stack

### Model
- **Name**: Llama 3.2 3B Instruct
- **Size**: 2GB RAM
- **Speed**: ~50 tokens/sec on CPU
- **Cost**: $0/month (runs locally via Ollama)
- **Quality**: Excellent for SQL generation

### Infrastructure
- **Ollama**: Local LLM runtime (systemd service)
- **Python**: ollama package for API access
- **Database**: SQLite (existing voter database)

## Deployment

### Prerequisites
- Ubuntu server with 4GB+ RAM
- Python 3.8+
- Existing WhoVoted installation

### Installation Steps

```bash
# 1. Copy files to server
scp -i deploy/whovoted-key.pem deploy/setup_llm_assistant.sh ubuntu@politiquera.com:/tmp/

# 2. Run setup script
ssh -i deploy/whovoted-key.pem ubuntu@politiquera.com
sudo bash /tmp/setup_llm_assistant.sh
```

The script will:
1. Install Ollama
2. Start Ollama service
3. Download Llama 3.2 3B model (~2GB)
4. Install Python ollama package
5. Restart gunicorn with new code

### Manual Installation

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull llama3.2:3b-instruct

# Install Python package
/opt/whovoted/venv/bin/pip install ollama

# Restart gunicorn
pkill gunicorn
cd /opt/whovoted
PYTHONPATH=/opt/whovoted/backend /opt/whovoted/venv/bin/gunicorn -w 5 -b 127.0.0.1:5000 'app:app' --daemon
```

## Security

### SQL Injection Prevention
- Blocks dangerous keywords: DROP, DELETE, TRUNCATE, ALTER, CREATE, INSERT, UPDATE
- Query validation before execution
- Read-only database access

### Authentication
- Requires login to use AI search
- Rate limiting (future enhancement)
- Audit logging (future enhancement)

### Query Limits
- Max 500 characters per question
- Auto-adds LIMIT clause to prevent huge result sets
- Timeout protection

## Performance

### Response Times
- **Traditional search**: 50-200ms (direct DB query)
- **AI search**: 2-5 seconds (LLM generation + DB query)
  - LLM generation: 1-3 seconds
  - SQL execution: 50-500ms
  - Explanation generation: 500ms-1s

### Resource Usage
- **RAM**: 2GB for model (loaded on first query)
- **CPU**: Moderate during query generation
- **Disk**: 2GB for model storage

### Caching Strategy
- Model stays in memory after first use
- Database query results use existing cache
- LLM responses not cached (each query is unique)

## Example Queries

### Voter Analysis
```
"Show me voters in TX-15 who voted in 2024 but not 2026"
"Find voters who switched from Republican to Democratic"
"How many new voters are there in Hidalgo County?"
"What's the turnout rate by age group?"
```

### Geographic Queries
```
"Show me all voters in precinct 123"
"Find voters in TX-15 who live in McAllen"
"How many voters are in each congressional district?"
```

### Demographic Queries
```
"Show me female voters born after 1990"
"Find voters aged 18-25 who voted early"
"How many voters are there by gender?"
```

### Voting Behavior
```
"Find voters who voted in every election since 2020"
"Show me voters who only vote in general elections"
"How many voters voted by mail?"
```

## Monitoring

### Check Ollama Status
```bash
systemctl status ollama
journalctl -u ollama -f
```

### Check Available Models
```bash
ollama list
```

### Test LLM Directly
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b-instruct",
  "prompt": "Convert to SQL: Show all voters in TX-15"
}'
```

### Check API Endpoint
```bash
curl http://localhost/api/llm/status
```

## Troubleshooting

### "AI service not available"
- Check Ollama is running: `systemctl status ollama`
- Check model is downloaded: `ollama list`
- Check Python package: `/opt/whovoted/venv/bin/pip list | grep ollama`

### Slow responses
- Normal for first query (model loading)
- Subsequent queries should be faster
- Consider upgrading to 8B model for better quality (slower)

### High memory usage
- Expected: 2GB for 3B model
- Upgrade server RAM if needed
- Alternative: Use smaller Phi-3 model (1.5GB)

### SQL errors
- LLM may generate invalid SQL occasionally
- User sees error message with SQL query
- Can refine question and try again
- Report persistent issues for prompt tuning

## Future Enhancements

### Phase 2
- [ ] Query refinement ("make it more specific")
- [ ] Export results to CSV
- [ ] Save favorite queries
- [ ] Query history

### Phase 3
- [ ] Multi-turn conversations
- [ ] Chart/graph generation
- [ ] Email reports
- [ ] Scheduled queries

### Phase 4
- [ ] Voice input
- [ ] Mobile app integration
- [ ] Real-time collaboration
- [ ] Advanced analytics

## Cost Comparison

### Traditional API (OpenAI GPT-4)
- $0.03 per 1K input tokens
- $0.06 per 1K output tokens
- ~500 tokens per query = $0.045/query
- 1000 queries/month = $45/month
- **Annual cost: $540**

### Local LLM (Llama 3.2)
- One-time: 2GB model download
- Ongoing: $0/month
- Unlimited queries
- **Annual cost: $0**
- **Savings: $540/year**

## Files Modified

### Frontend
- `public/search.js` - Hybrid search logic
- `public/index.html` - Added llm-chat.js script
- `public/styles.css` - AI response styles, mobile icon positioning

### Backend
- `backend/app.py` - Added LLM API endpoints
- `backend/llm_query.py` - Query assistant class (already created)

### Deployment
- `deploy/setup_llm_assistant.sh` - Automated setup script

### Documentation
- `AI_SEARCH_IMPLEMENTATION.md` - This file
- `LLM_QUERY_ASSISTANT.md` - Original design doc

## Support

For issues or questions:
1. Check logs: `journalctl -u ollama -f`
2. Test API: `curl http://localhost/api/llm/status`
3. Verify model: `ollama list`
4. Restart services: `sudo systemctl restart ollama && sudo pkill gunicorn && cd /opt/whovoted && PYTHONPATH=/opt/whovoted/backend /opt/whovoted/venv/bin/gunicorn -w 5 -b 127.0.0.1:5000 'app:app' --daemon`

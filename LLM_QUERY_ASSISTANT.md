# LLM-Powered Query Assistant

## Vision
Add a chatbot interface where users can ask questions in natural language and get back SQL queries, data tables, and reports - all powered by a local, open-source LLM with no API costs.

**Example Queries:**
- "Show me all voters in TX-15 who attended 3+ events but didn't vote in 2024"
- "What's the turnout rate by age group in Hidalgo County?"
- "Find high-income new voters for donor outreach"
- "Which precincts have the most party switchers?"

## Architecture Options

### Option 1: Llama 3.2 (Recommended)
**Model**: Llama 3.2 3B or 8B (instruction-tuned)
**Size**: 3B = 2GB RAM, 8B = 5GB RAM
**Speed**: 3B = ~50 tokens/sec on CPU, 8B = ~20 tokens/sec on CPU
**Quality**: Excellent for SQL generation, good reasoning

**Pros:**
- Small enough to run on your existing server
- Fast inference on CPU
- Excellent instruction following
- Free, no tokens

**Cons:**
- Needs 4-8GB RAM dedicated to model
- CPU inference slower than GPU

### Option 2: SQLCoder (Specialized)
**Model**: SQLCoder 7B or 15B
**Size**: 7B = 4GB RAM, 15B = 9GB RAM
**Speed**: Similar to Llama
**Quality**: Purpose-built for SQL generation

**Pros:**
- Specifically trained on SQL tasks
- Better at complex joins and aggregations
- Understands database schemas well

**Cons:**
- Larger model size
- Less flexible for non-SQL tasks

### Option 3: Phi-3 Mini (Lightweight)
**Model**: Phi-3 Mini 3.8B
**Size**: 2.3GB RAM
**Speed**: ~60 tokens/sec on CPU
**Quality**: Surprisingly good for its size

**Pros:**
- Smallest footprint
- Fast on CPU
- Good enough for most queries

**Cons:**
- May struggle with very complex queries
- Less context window (4K tokens)

## Recommended Stack

### Backend: Ollama + LangChain
```bash
# Install Ollama (one-time setup)
curl -fsSL https://ollama.com/install.sh | sh

# Pull model (one-time, ~2GB download)
ollama pull llama3.2:3b-instruct

# Ollama runs as a service, no tokens needed
```

### Python Integration
```python
# requirements.txt additions
ollama>=0.1.0
langchain>=0.1.0
langchain-community>=0.1.0
```

### Architecture Flow
```
User Question → Flask API → LLM (Ollama) → SQL Query → SQLite → Results → Format → User
```

## Implementation Plan

### Phase 1: Basic Text-to-SQL

#### 1. Add Ollama Endpoint
```python
# backend/llm_query.py
import ollama
import json
from typing import Dict, List

class QueryAssistant:
    def __init__(self):
        self.model = "llama3.2:3b-instruct"
        self.schema = self._load_schema()
    
    def _load_schema(self) -> str:
        """Load database schema for context"""
        return """
        Database Schema:
        
        voters (vuid, firstname, lastname, birth_year, sex, address, 
                county, lat, lng, precinct, congressional_district, 
                state_house_district, commissioner_district)
        
        voter_elections (vuid, election_date, election_year, election_type,
                        voting_method, party_voted, is_new_voter)
        
        voter_engagement_summary (vuid, total_events_attended, 
                                 attendance_rate, is_super_volunteer)
        
        voter_demographics_enriched (vuid, estimated_income_bracket,
                                    homeowner_status, education_level)
        """
    
    def question_to_sql(self, question: str) -> Dict:
        """Convert natural language question to SQL"""
        
        prompt = f"""You are a SQL expert. Convert this question to a SQLite query.

Database Schema:
{self.schema}

Question: {question}

Generate a valid SQLite query. Return ONLY the SQL query, no explanation.
Use proper JOINs, WHERE clauses, and aggregations as needed.

SQL Query:"""

        response = ollama.generate(
            model=self.model,
            prompt=prompt,
            options={
                'temperature': 0.1,  # Low temp for consistent SQL
                'top_p': 0.9,
            }
        )
        
        sql = response['response'].strip()
        
        # Clean up common issues
        sql = sql.replace('```sql', '').replace('```', '').strip()
        
        return {
            'sql': sql,
            'question': question,
            'model': self.model
        }
    
    def execute_and_format(self, sql: str, limit: int = 100) -> Dict:
        """Execute SQL and format results"""
        import database as db
        
        try:
            # Add LIMIT if not present
            if 'LIMIT' not in sql.upper():
                sql += f' LIMIT {limit}'
            
            conn = db.get_connection()
            results = conn.execute(sql).fetchall()
            
            # Convert to list of dicts
            rows = [dict(row) for row in results]
            
            return {
                'success': True,
                'rows': rows,
                'count': len(rows),
                'sql': sql
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'sql': sql
            }
```

#### 2. Add Flask API Endpoint
```python
# backend/app.py
from llm_query import QueryAssistant

query_assistant = QueryAssistant()

@app.route('/api/llm/query', methods=['POST'])
@require_auth  # Only authenticated users
def llm_query():
    """Natural language query interface"""
    data = request.get_json()
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'Question required'}), 400
    
    # Convert to SQL
    sql_result = query_assistant.question_to_sql(question)
    
    # Execute query
    result = query_assistant.execute_and_format(sql_result['sql'])
    
    return jsonify({
        'question': question,
        'sql': sql_result['sql'],
        'results': result['rows'] if result['success'] else [],
        'count': result.get('count', 0),
        'error': result.get('error'),
        'success': result['success']
    })
```

#### 3. Frontend Chat Interface
```javascript
// public/llm-chat.js
class LLMChat {
    constructor() {
        this.chatHistory = [];
        this.initUI();
    }
    
    initUI() {
        const chatBtn = document.createElement('button');
        chatBtn.id = 'llmChatBtn';
        chatBtn.className = 'panel-icon-btn';
        chatBtn.innerHTML = '🤖';
        chatBtn.title = 'Ask Questions';
        chatBtn.onclick = () => this.openChat();
        
        document.querySelector('.panel-icons').appendChild(chatBtn);
    }
    
    openChat() {
        const modal = document.createElement('div');
        modal.className = 'llm-chat-modal';
        modal.innerHTML = `
            <div class="llm-chat-container">
                <div class="llm-chat-header">
                    <h3>🤖 Ask Questions About Your Data</h3>
                    <button class="close-btn">&times;</button>
                </div>
                <div class="llm-chat-messages" id="llmChatMessages"></div>
                <div class="llm-chat-input">
                    <input type="text" id="llmChatInput" 
                           placeholder="e.g., Show me voters in TX-15 who attended 3+ events">
                    <button id="llmChatSend">Send</button>
                </div>
                <div class="llm-chat-examples">
                    <small>Try: "What's the turnout rate by age group?" or 
                    "Find high-income new voters"</small>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        modal.querySelector('.close-btn').onclick = () => modal.remove();
        modal.querySelector('#llmChatSend').onclick = () => this.sendMessage();
        modal.querySelector('#llmChatInput').onkeypress = (e) => {
            if (e.key === 'Enter') this.sendMessage();
        };
    }
    
    async sendMessage() {
        const input = document.getElementById('llmChatInput');
        const question = input.value.trim();
        if (!question) return;
        
        // Add user message
        this.addMessage('user', question);
        input.value = '';
        
        // Show loading
        this.addMessage('assistant', 'Thinking...', true);
        
        try {
            const resp = await fetch('/api/llm/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question })
            });
            
            const data = await resp.json();
            
            // Remove loading message
            document.querySelector('.llm-message.loading')?.remove();
            
            if (data.success) {
                // Show SQL query
                this.addMessage('assistant', 
                    `I generated this query:\n\`\`\`sql\n${data.sql}\n\`\`\``);
                
                // Show results as table
                if (data.count > 0) {
                    this.addTable(data.results);
                } else {
                    this.addMessage('assistant', 'No results found.');
                }
            } else {
                this.addMessage('assistant', 
                    `Error: ${data.error}\n\nSQL: ${data.sql}`);
            }
        } catch (e) {
            document.querySelector('.llm-message.loading')?.remove();
            this.addMessage('assistant', `Error: ${e.message}`);
        }
    }
    
    addMessage(role, content, loading = false) {
        const messages = document.getElementById('llmChatMessages');
        const msg = document.createElement('div');
        msg.className = `llm-message llm-${role}${loading ? ' loading' : ''}`;
        msg.textContent = content;
        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;
    }
    
    addTable(rows) {
        const messages = document.getElementById('llmChatMessages');
        const table = document.createElement('table');
        table.className = 'llm-results-table';
        
        // Header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        Object.keys(rows[0]).forEach(key => {
            const th = document.createElement('th');
            th.textContent = key;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Body
        const tbody = document.createElement('tbody');
        rows.forEach(row => {
            const tr = document.createElement('tr');
            Object.values(row).forEach(val => {
                const td = document.createElement('td');
                td.textContent = val;
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        
        messages.appendChild(table);
        messages.scrollTop = messages.scrollHeight;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new LLMChat();
});
```

### Phase 2: Enhanced Features

#### 1. Query Refinement
```python
def refine_query(self, original_sql: str, feedback: str) -> str:
    """Refine SQL based on user feedback"""
    prompt = f"""The user asked for a query but wants to refine it.

Original SQL:
{original_sql}

User feedback: {feedback}

Generate an improved SQL query based on the feedback.

Improved SQL:"""
    
    response = ollama.generate(model=self.model, prompt=prompt)
    return response['response'].strip()
```

#### 2. Explain Results
```python
def explain_results(self, question: str, sql: str, results: List[Dict]) -> str:
    """Generate natural language explanation of results"""
    prompt = f"""Explain these query results in simple terms.

Question: {question}
SQL: {sql}
Result count: {len(results)}
Sample results: {json.dumps(results[:3], indent=2)}

Provide a brief, clear explanation of what the data shows.

Explanation:"""
    
    response = ollama.generate(model=self.model, prompt=prompt)
    return response['response'].strip()
```

#### 3. Suggested Follow-ups
```python
def suggest_followups(self, question: str, results: List[Dict]) -> List[str]:
    """Suggest related questions"""
    prompt = f"""Based on this query, suggest 3 related questions the user might ask.

Original question: {question}
Results found: {len(results)} rows

Suggest 3 follow-up questions (one per line):"""
    
    response = ollama.generate(model=self.model, prompt=prompt)
    return response['response'].strip().split('\n')[:3]
```

## Deployment

### Server Requirements
- **RAM**: 4GB minimum (8GB recommended)
- **CPU**: 4 cores recommended
- **Disk**: 5GB for model storage

### Installation Steps
```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull model
ollama pull llama3.2:3b-instruct

# 3. Install Python dependencies
pip install ollama langchain langchain-community

# 4. Start Ollama service (runs automatically)
systemctl status ollama

# 5. Test
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b-instruct",
  "prompt": "Convert to SQL: Show all voters in TX-15"
}'
```

## Security Considerations

1. **SQL Injection Prevention**: Validate generated SQL before execution
2. **Query Limits**: Always add LIMIT clause to prevent huge result sets
3. **Authentication**: Require login for LLM queries
4. **Rate Limiting**: Limit queries per user per hour
5. **Audit Log**: Log all questions and generated SQL

## Cost Analysis

**Traditional API (OpenAI GPT-4)**:
- $0.03 per 1K input tokens
- $0.06 per 1K output tokens
- ~500 tokens per query = $0.045 per query
- 1000 queries/month = $45/month

**Local LLM (Llama 3.2)**:
- One-time: 2GB model download
- Ongoing: $0/month (uses existing server)
- Unlimited queries
- **Savings: $45/month → $540/year**

## Next Steps

1. Install Ollama on server
2. Test SQL generation with sample questions
3. Build Flask API endpoint
4. Create chat UI
5. Add authentication and rate limiting
6. Deploy and test with real users

This gives you a ChatGPT-like interface for your voter data with zero ongoing costs!

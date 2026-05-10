# Design: AI Search / LLM Query Interface

## Architecture

```
Browser (llm-chat.js)
  → POST /api/llm-query { question, context }
  → Flask (llm_api_endpoint.py)
  → QueryAssistant.question_to_sql() [llm_query.py]
  → Ollama HTTP API (127.0.0.1:11434)
  → SQL execution against SQLite
  → QueryAssistant.explain_results()
  → Response: { sql, rows, columns, explanation, suggestions }
```

## Components

### `backend/llm_query.py` — `QueryAssistant`

- `question_to_sql(question, context)` → `{ sql, question, model, success }`
  - Builds prompt with schema context
  - Calls `ollama.generate()` with 30s timeout via threading
  - Strips markdown formatting from response
  - Blocks dangerous keywords
- `execute_and_format(sql, limit=100)` → `{ success, rows, columns, count, sql }`
  - Enforces LIMIT if not aggregate
  - Returns dict rows
- `explain_results(question, sql, result)` → string
  - 15s timeout
  - Falls back to generic message on timeout
- `suggest_followups(question, result)` → list[str]
  - 15s timeout
  - Returns empty list on timeout

### `backend/llm_api_endpoint.py`

- `POST /api/llm-query` — main endpoint
- `GET /api/llm-status` — check if Ollama is available

### `public/llm-chat.js`

- Chat panel UI
- Sends question to `/api/llm-query`
- Renders results as table + explanation
- Shows follow-up suggestions as clickable chips

## Schema Context Maintenance

The schema string in `QueryAssistant._load_schema()` must be kept in sync with the actual DB schema. When new columns are added to `voters` or `voter_elections`, update the schema string.

**Current schema includes**:
- `voters`: vuid, firstname, lastname, birth_year, sex, address, city, zip, county, lat, lng, geocoded, precinct, congressional_district, old_congressional_district, state_house_district, commissioner_district, registered_party, current_party, registration_date
- `voter_elections`: vuid, election_date, election_year, election_type, voting_method, party_voted, is_new_voter, created_at

**Missing from schema context** (needs to be added):
- `voters.state_senate_district`
- Subscription tables (users, credits, subscriptions) — probably should NOT be in LLM context

## Ollama Management

Ollama must be running as a service. Check:
```bash
systemctl status ollama
curl http://127.0.0.1:11434/api/tags
```

If not running:
```bash
ollama serve &
```

The admin dashboard has an Ollama management panel (see `backend/admin/dashboard.js`).

## Known Issues

1. **Invalid SQL generation**: llama3.2 sometimes uses wrong column names. Mitigation: the schema prompt is very explicit about column names. Future fix: add SQL validation step before execution.
2. **Slow first response**: First query after Ollama restart takes 10–15s for model loading. Subsequent queries are faster.
3. **No streaming**: The 30s timeout means users wait silently. Future fix: streaming response with SSE.

## Files Touched

- `backend/llm_query.py` — core LLM logic
- `backend/llm_api_endpoint.py` — Flask endpoint
- `public/llm-chat.js` — chat UI
- `backend/admin/dashboard.js` — Ollama management panel

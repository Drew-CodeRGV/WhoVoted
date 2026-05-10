# Spec: AI Search / LLM Query Interface

## Problem

Voter data analysis requires SQL knowledge. Most campaign staff don't write SQL. The AI search feature lets users ask natural language questions ("How many Democrats voted early in precinct 101?") and get answers from the voter database.

## Users

- Campaign staff who need data but can't write SQL
- Researchers exploring the dataset
- Subscribers on Campaign Manager tier and above (per subscription spec)

## Acceptance Criteria

1. User types a natural language question in the chat panel.
2. The system converts the question to SQL using Ollama (llama3.2:latest on 127.0.0.1:11434).
3. SQL is executed against the SQLite DB with a 30-second timeout.
4. Results are returned as a table + natural language explanation.
5. Follow-up question suggestions are shown.
6. Dangerous SQL keywords (DROP, DELETE, etc.) are blocked.
7. All queries are read-only (SELECT only).
8. If Ollama is unavailable, return a clear error (not a 500).
9. Query timeout returns a user-friendly message, not a crash.
10. Results are limited to 100 rows unless the query is an aggregate.

## Current State

- `backend/llm_query.py` — `QueryAssistant` class (implemented)
- `backend/llm_api_endpoint.py` — Flask endpoint (implemented)
- `public/llm-chat.js` — chat UI (implemented)
- Ollama running on `127.0.0.1:11434` with `llama3.2:latest`
- 30-second timeout implemented via threading
- **Known issue**: Ollama sometimes unresponsive after server restart; requires `ollama serve` to be running

## Known Limitations

- LLM occasionally generates invalid SQL (wrong column names, wrong table)
- Schema context in the prompt is manually maintained — must be updated when DB schema changes
- No query history / saved queries
- No streaming response (waits for full LLM response before returning)

## Out of Scope

- Streaming responses
- Query history persistence
- Multi-turn conversation context
- Fine-tuned model (llama3.2 is used as-is)

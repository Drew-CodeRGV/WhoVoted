# Tasks: AI Search / LLM Query Interface

## Core (Done)

- [done] **1** Create `backend/llm_query.py` with `QueryAssistant` class
- [done] **2** Implement `question_to_sql()` with 30s timeout
- [done] **3** Implement `execute_and_format()` with LIMIT enforcement
- [done] **4** Implement `explain_results()` with 15s timeout
- [done] **5** Implement `suggest_followups()` with 15s timeout
- [done] **6** Create `backend/llm_api_endpoint.py` with `POST /api/llm-query`
- [done] **7** Create `public/llm-chat.js` chat panel UI
- [done] **8** Add Ollama management panel to admin dashboard

## Known Issues to Fix

- [pending] **9** Add SQL validation step: parse generated SQL and verify column names exist in schema before executing
- [pending] **10** Add `GET /api/llm-status` endpoint that returns Ollama availability + model loaded
- [pending] **11** Update schema context in `_load_schema()` to include `state_senate_district` column
- [pending] **12** Add streaming response support (SSE) to avoid 30s silent wait
- [pending] **13** Add query history: store last 10 queries per session in localStorage

## Subscription Gating

- [pending] **14** Gate `/api/llm-query` with subscription check (Campaign Manager and above, or 50 queries/mo for Individual)
- [pending] **15** Track AI query usage in `usage_logs` table
- [pending] **16** Return usage count in response: `{ queries_used: 12, queries_limit: 50 }`

## Reliability

- [pending] **17** Add Ollama health check on app startup; log warning if unavailable
- [pending] **18** Add retry logic: if Ollama returns empty response, retry once
- [pending] **19** Add `/api/admin/ollama/restart` endpoint (superadmin only) that runs `ollama serve`

## Status

**Overall**: [in-progress] — core functionality working, subscription gating and reliability improvements pending.

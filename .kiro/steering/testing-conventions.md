---
inclusion: manual
---

# Testing Conventions

## Test Location

Tests live in `deploy/test_*.py` (integration tests that run against the live server or DB). There is no `tests/` directory with unit tests.

## How to Run

```bash
# On server (integration tests against live DB):
cd /opt/whovoted
source venv/bin/activate
python deploy/test_llm_endpoint_live.py
python deploy/test_webhook_live.py
python deploy/test_email_registration.py
python deploy/test_sms.py

# Syntax check (no execution):
python -m py_compile backend/app.py
python deploy/syntax_check.py
```

## What's Expected to Pass Before Deploy

1. `python -m py_compile backend/app.py` — no syntax errors
2. `python -m py_compile backend/d15_app.py` — no syntax errors
3. `curl -s https://politiquera.com/api/config` returns JSON (after deploy)
4. `curl -s https://politiquera.com/api/elections` returns elections list

## What's Known-Flaky

- `test_llm_endpoint_live.py` — depends on Ollama being responsive; times out if model is loading
- `test_sms.py` — depends on AWS SNS sandbox; fails if phone number not verified
- `test_email_registration.py` — depends on AWS SES; fails if in sandbox mode

## Test Coverage

There is no formal test coverage measurement. The project relies on:
1. Integration tests against the live server
2. Manual verification after deploy
3. The EVR scraper state file as a canary (if scraper runs successfully, the DB and imports are working)

## What Should Exist But Doesn't

- Unit tests for `backend/llm_query.py` (mock Ollama, test SQL generation)
- Unit tests for `backend/processor.py` (test CSV parsing without geocoding)
- Unit tests for point-in-polygon algorithm
- Unit tests for subscription access checks
- A `pytest.ini` or `conftest.py` for proper test discovery

## Conventions for New Tests

- Name: `test_<what_you_are_testing>.py`
- Location: `deploy/` (for integration) or `tests/` (for unit tests, when created)
- Framework: `unittest` or plain `assert` statements (no pytest dependency currently)
- Each test should be runnable standalone: `python deploy/test_foo.py`
- Print PASS/FAIL at the end
- Exit with code 0 on success, 1 on failure

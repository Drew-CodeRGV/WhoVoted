#!/usr/bin/env python3
"""Remove legacy admin credentials from .env and wipe any stored admin sessions."""
import os, json

# Remove ADMIN_USERNAME and ADMIN_PASSWORD from .env
env_path = '/opt/whovoted/backend/.env'
if os.path.exists(env_path):
    lines = open(env_path).readlines()
    new_lines = [l for l in lines if not l.strip().startswith('ADMIN_USERNAME') and not l.strip().startswith('ADMIN_PASSWORD')]
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    print(f"Cleaned .env: removed ADMIN_USERNAME/ADMIN_PASSWORD")
else:
    print(f".env not found at {env_path}")

# Wipe all legacy admin sessions (those without an email)
sessions_path = '/opt/whovoted/data/sessions.json'
if os.path.exists(sessions_path):
    with open(sessions_path) as f:
        sessions = json.load(f)
    before = len(sessions)
    sessions = {k: v for k, v in sessions.items() if v.get('email')}
    with open(sessions_path, 'w') as f:
        json.dump(sessions, f)
    print(f"Wiped {before - len(sessions)} legacy sessions, kept {len(sessions)} Google SSO sessions")
else:
    print("No sessions file found")

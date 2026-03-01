---
name: PowerShell Safe Commands
description: Enforces PowerShell-compatible command patterns for Windows development
keywords: powershell, ssh, windows, commands, deployment
---

# PowerShell Safe Commands - Active Skill

## Context
This project is developed on Windows using PowerShell. All SSH commands, deployment scripts, and automation MUST be PowerShell-compatible.

## Hard Rules - NEVER VIOLATE

### 1. NO Python One-Liners via SSH
Never use: `ssh server "python -c 'code'"`
Always use: Create script file → SCP → Execute

### 2. NO Nested Quotes
Never use: `ssh server "echo \"nested 'quotes'\""`
Always use: `ssh server 'echo "quotes"'` (single quotes outside)

### 3. NO && or || Operators
Never use: `command1 && command2`
Always use: `command1; command2` (semicolons)

### 4. NO Unescaped Special Characters
Characters that break: `* $ { } [ ] ( ) | & ; < > \ ` `
Always use: Single quotes or script files

### 5. ALWAYS Use Script Files for Complex Operations
If command contains:
- Python/SQL code
- Multiple lines
- Special characters
- Nested quotes

Then: Create script file, SCP it, execute it.

## Enforcement

Before generating ANY SSH command, check:
1. Does it have nested quotes? → Script file
2. Does it have special chars? → Script file or single quotes
3. Is it Python/SQL? → Script file
4. Uses && or ||? → Replace with semicolons

## Safe Patterns

### Execute Python on Server
```powershell
# Create script locally
fsWrite("script.py", $content)

# Copy to server
scp -i key.pem script.py user@server:/tmp/

# Execute
ssh -i key.pem user@server "python3 /tmp/script.py"
```

### Simple Commands
```powershell
# Always use single quotes for outer command
ssh -i key.pem user@server 'ls -lh /path'
ssh -i key.pem user@server 'ps aux | grep app'
```

### Sequential Commands
```powershell
# Use semicolons, not &&
ssh -i key.pem user@server 'cd /app; git pull; restart'
```

## This Skill is ALWAYS Active

Every time you generate an SSH command or deployment script, you MUST follow these rules. No exceptions.

See POWERSHELL_RULES.md for complete documentation.

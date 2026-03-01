# PowerShell Compatibility Rules - MANDATORY

## ⚠️ CRITICAL: This project uses PowerShell on Windows

All scripts, commands, and automation MUST follow these rules to avoid wasted time debugging PowerShell issues.

## HARD RULES - NEVER VIOLATE

### 1. NO Complex Python One-Liners via SSH
❌ **NEVER DO THIS:**
```powershell
ssh server "python -c 'import sqlite3; c=sqlite3.connect(\"/path/db\"); print(c.execute(\"SELECT * FROM table\").fetchone())'"
```

**Why it fails:**
- PowerShell mangles nested quotes
- Backslashes get interpreted incorrectly
- Special characters (* $ ` etc) trigger PowerShell expansion

✅ **ALWAYS DO THIS:**
```powershell
# Create a script file first, then execute it
ssh server 'cat > /tmp/script.py << "EOF"
import sqlite3
conn = sqlite3.connect("/path/db")
result = conn.execute("SELECT * FROM table").fetchone()
print(result)
EOF
python3 /tmp/script.py'
```

### 2. NO Heredocs with Unquoted Delimiters
❌ **NEVER DO THIS:**
```bash
cat > file.py << EOF
path = "/some/path"
EOF
```

**Why it fails:**
- PowerShell interprets variables like $var
- Quotes get mangled
- Paths with backslashes fail

✅ **ALWAYS DO THIS:**
```bash
cat > file.py << "EOF"
path = "/some/path"
EOF
```
Note the quotes around EOF - this prevents variable expansion.

### 3. NO && or || Operators
❌ **NEVER DO THIS:**
```powershell
command1 && command2 || command3
```

**Why it fails:**
- PowerShell doesn't recognize && or ||
- Treats them as invalid tokens

✅ **ALWAYS DO THIS:**
```powershell
command1; if ($?) { command2 } else { command3 }
```

Or use semicolons for sequential commands:
```powershell
command1; command2; command3
```

### 4. NO Unescaped Special Characters
❌ **NEVER DO THIS:**
```powershell
ssh server "grep 'pattern*' file.txt"
```

**Why it fails:**
- `*` triggers PowerShell glob expansion
- `$` triggers variable expansion
- `` ` `` is PowerShell escape character

✅ **ALWAYS DO THIS:**
```powershell
ssh server 'grep "pattern*" file.txt'
```
Use single quotes for the outer SSH command to prevent PowerShell interpretation.

### 5. NO Complex Inline Scripts
❌ **NEVER DO THIS:**
```powershell
ssh server "for i in {1..10}; do echo $i; done"
```

**Why it fails:**
- PowerShell interprets $i as a variable
- Complex bash syntax confuses PowerShell parser

✅ **ALWAYS DO THIS:**
Create a script file on the server:
```powershell
ssh server 'bash -c "for i in {1..10}; do echo \$i; done"'
```

Or better yet, write a proper script file.

### 6. ALWAYS Use Script Files for Complex Operations
❌ **NEVER DO THIS:**
```powershell
ssh server "python -c 'complex python code with quotes and special chars'"
```

✅ **ALWAYS DO THIS:**
1. Create the script file locally
2. SCP it to the server
3. Execute it

```powershell
# Create script locally
fsWrite("script.py", "content")

# Copy to server
scp script.py server:/tmp/

# Execute
ssh server "python3 /tmp/script.py"
```

### 7. NO Nested Quotes in SSH Commands
❌ **NEVER DO THIS:**
```powershell
ssh server "echo \"nested 'quotes' here\""
```

**Why it fails:**
- PowerShell quote escaping is unpredictable
- Nested quotes get mangled

✅ **ALWAYS DO THIS:**
```powershell
ssh server 'echo "nested quotes here"'
```
Use single quotes for outer SSH command, double quotes inside.

### 8. ALWAYS Test Commands Locally First
Before running complex commands via SSH:
1. Test the command directly on the server
2. If it works, wrap it in single quotes for SSH
3. If it still fails, create a script file

## PowerShell-Safe Patterns

### Pattern 1: Execute Python Script on Server
```powershell
# Step 1: Create script locally
$script = @"
import sqlite3
conn = sqlite3.connect('/path/to/db')
result = conn.execute('SELECT COUNT(*) FROM table').fetchone()
print(f'Count: {result[0]}')
conn.close()
"@

# Step 2: Write to file
Set-Content -Path "script.py" -Value $script

# Step 3: Copy to server
scp -i key.pem script.py user@server:/tmp/

# Step 4: Execute
ssh -i key.pem user@server "/path/to/python3 /tmp/script.py"
```

### Pattern 2: Run Bash Script on Server
```powershell
ssh -i key.pem user@server 'bash -s' < local_script.sh
```

### Pattern 3: Simple Commands
```powershell
# Single quotes prevent PowerShell interpretation
ssh -i key.pem user@server 'ls -lh /path/to/dir'
ssh -i key.pem user@server 'ps aux | grep python'
ssh -i key.pem user@server 'cat /var/log/app.log | tail -50'
```

### Pattern 4: Sequential Commands
```powershell
# Use semicolons, not &&
ssh -i key.pem user@server 'cd /app; git pull; sudo systemctl restart app'
```

## Common Pitfalls and Solutions

### Pitfall 1: Python f-strings
❌ Problem: `print(f"Value: {var}")`
- PowerShell sees `{var}` and tries to expand it

✅ Solution: Use script files, not inline Python

### Pitfall 2: SQL Queries with Quotes
❌ Problem: `SELECT * FROM table WHERE name = "value"`
- Quote escaping nightmare

✅ Solution: Put SQL in script files

### Pitfall 3: Paths with Backslashes
❌ Problem: `C:\Users\path\file.txt`
- Backslashes get interpreted as escape characters

✅ Solution: Use forward slashes or raw strings

### Pitfall 4: Wildcards
❌ Problem: `grep "pattern*" file`
- PowerShell expands `*` before sending to SSH

✅ Solution: Use single quotes: `'grep "pattern*" file'`

## Enforcement

### For AI Assistants:
1. **ALWAYS** check if command contains:
   - Nested quotes
   - Special characters: `* $ { } [ ] ( ) | & ; < > \`
   - Python/SQL code
   - Heredocs
2. **IF YES**: Use script file approach
3. **IF NO**: Use single-quoted SSH command

### For Developers:
1. Test all SSH commands locally first
2. Use script files for anything complex
3. Never trust inline code with special characters
4. When in doubt, create a script file

## Quick Reference

| Task | ❌ Don't | ✅ Do |
|------|---------|-------|
| Python code | `ssh "python -c 'code'"` | Create .py file, SCP, execute |
| SQL query | `ssh "sqlite3 db 'SELECT...'"` | Create .sql file or Python script |
| Multiple commands | `ssh "cmd1 && cmd2"` | `ssh 'cmd1; cmd2'` |
| Heredoc | `cat > file << EOF` | `cat > file << "EOF"` |
| Special chars | `ssh "grep 'a*b'"` | `ssh 'grep "a*b"'` |
| Complex bash | Inline bash script | Create .sh file, SCP, execute |

## Testing Checklist

Before running any SSH command:
- [ ] Does it contain nested quotes? → Use script file
- [ ] Does it contain `* $ { } [ ]`? → Use single quotes or script file
- [ ] Is it Python/SQL code? → Use script file
- [ ] Does it use `&&` or `||`? → Replace with `;` or script file
- [ ] Is it more than one line? → Use script file

## Emergency Fix

If you encounter PowerShell issues:
1. **STOP** trying to fix the command
2. Create a script file instead
3. SCP the file to server
4. Execute the file

This is ALWAYS faster than debugging PowerShell escaping.

---

**Remember: PowerShell is not bash. Treat it accordingly.**

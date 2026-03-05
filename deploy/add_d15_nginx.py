#!/usr/bin/env python3
"""Add D15 API location block to nginx config - HTTPS block"""

import sys

nginx_config = '/etc/nginx/sites-available/whovoted'

d15_block = """    # D15 Election Night Dashboard API
    location /api/d15/ {
        proxy_pass http://127.0.0.1:5001/api/d15/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

"""

try:
    with open(nginx_config, 'r') as f:
        lines = f.readlines()
    
    # Find the SECOND server block (HTTPS) and add before its closing brace
    new_lines = []
    server_count = 0
    inserted = False
    
    for i, line in enumerate(lines):
        if 'server {' in line:
            server_count += 1
        
        # In the second server block, insert before the closing brace
        if server_count == 2 and line.strip() == '}' and not inserted:
            new_lines.append(d15_block)
            inserted = True
        
        new_lines.append(line)
    
    with open(nginx_config, 'w') as f:
        f.writelines(new_lines)
    
    print(f"D15 API location block added to HTTPS server block")
    sys.exit(0)
    
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

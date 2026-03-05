#!/bin/bash
# Fix D15 Dashboard nginx routing

echo "=== D15 Backend Status ==="
systemctl status d15-backend --no-pager

echo -e "\n=== Testing Backend Directly ==="
curl -s http://127.0.0.1:5001/d15api/results | head -20

echo -e "\n=== Current nginx D15 config ==="
grep -A 30 "location /d15" /etc/nginx/sites-available/whovoted

echo -e "\n=== Fixing nginx config ==="
# Backup current config
cp /etc/nginx/sites-available/whovoted /etc/nginx/sites-available/whovoted.backup.$(date +%s)

# Remove any existing d15api blocks
sed -i '/location \/d15api/,/^    }/d' /etc/nginx/sites-available/whovoted

# Add the correct d15api proxy configuration right after the main location / block
# Find the line with "location / {" and add our d15api block after its closing brace
awk '
/^    location \/ \{/ { in_main_location = 1 }
in_main_location && /^    \}/ { 
    print
    print ""
    print "    # D15 Dashboard API"
    print "    location /d15api/ {"
    print "        proxy_pass http://127.0.0.1:5001/d15api/;"
    print "        proxy_http_version 1.1;"
    print "        proxy_set_header Host $host;"
    print "        proxy_set_header X-Real-IP $remote_addr;"
    print "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;"
    print "        proxy_set_header X-Forwarded-Proto $scheme;"
    print "        proxy_read_timeout 300;"
    print "        proxy_connect_timeout 300;"
    print "    }"
    in_main_location = 0
    next
}
{ print }
' /etc/nginx/sites-available/whovoted > /tmp/whovoted.new

mv /tmp/whovoted.new /etc/nginx/sites-available/whovoted

echo -e "\n=== New nginx D15 config ==="
grep -A 15 "location /d15api" /etc/nginx/sites-available/whovoted

echo -e "\n=== Testing nginx config ==="
nginx -t

if [ $? -eq 0 ]; then
    echo -e "\n=== Reloading nginx ==="
    systemctl reload nginx
    
    echo -e "\n=== Waiting 2 seconds ==="
    sleep 2
    
    echo -e "\n=== Testing via nginx ==="
    curl -s https://politiquera.com/d15api/results | head -20
    
    echo -e "\n=== Done! ==="
else
    echo -e "\n=== nginx config test FAILED - restoring backup ==="
    cp /etc/nginx/sites-available/whovoted.backup.* /etc/nginx/sites-available/whovoted
fi

#!/bin/bash
# Fix the doubled AWS secret key in .env
cd /opt/whovoted

# Read current secret key
source .env
CURRENT_LEN=${#AWS_SECRET_ACCESS_KEY}

if [ "$CURRENT_LEN" -eq 80 ]; then
    # It's doubled — take just the first half
    CORRECT_KEY="${AWS_SECRET_ACCESS_KEY:0:40}"
    
    # Replace in .env file
    sed -i "s|^AWS_SECRET_ACCESS_KEY=.*|AWS_SECRET_ACCESS_KEY=$CORRECT_KEY|" .env
    
    echo "Fixed: AWS_SECRET_ACCESS_KEY trimmed from 80 to 40 characters"
    
    # Verify
    source .env
    echo "New length: ${#AWS_SECRET_ACCESS_KEY}"
else
    echo "Secret key length is $CURRENT_LEN (not doubled, no fix needed)"
fi

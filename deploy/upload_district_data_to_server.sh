#!/bin/bash
# Upload district reference data to server and extract

# Configuration - UPDATE THESE VALUES
SERVER_USER="your_username"
SERVER_HOST="your_server_ip"
SERVER_PATH="/home/ubuntu/WhoVoted/data/district_reference"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}District Data Upload Script${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if we're in the right directory
if [ ! -d "data/district_reference" ]; then
    echo -e "${RED}Error: Must run from WhoVoted directory${NC}"
    exit 1
fi

cd data/district_reference

# Check for ZIP files
echo -e "\n${YELLOW}Checking for ZIP files...${NC}"
ZIP_FILES=$(ls -1 *.zip 2>/dev/null | wc -l)

if [ $ZIP_FILES -eq 0 ]; then
    echo -e "${RED}No ZIP files found in data/district_reference/${NC}"
    echo -e "${YELLOW}Looking for:${NC}"
    echo "  - PLANC2333_All_Files_*.zip (Congressional)"
    echo "  - PLANS2168_All_Files_*.zip (State Senate)"
    echo "  - PLANH2316_All_Files_*.zip (State House)"
    exit 1
fi

echo -e "${GREEN}Found $ZIP_FILES ZIP file(s)${NC}"
ls -lh *.zip

# Create remote directory
echo -e "\n${YELLOW}Creating remote directory...${NC}"
ssh ${SERVER_USER}@${SERVER_HOST} "mkdir -p ${SERVER_PATH}"

# Upload ZIP files
echo -e "\n${YELLOW}Uploading ZIP files to server...${NC}"
for zipfile in *.zip; do
    echo -e "${GREEN}Uploading: $zipfile${NC}"
    scp "$zipfile" ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Uploaded: $zipfile${NC}"
    else
        echo -e "${RED}✗ Failed to upload: $zipfile${NC}"
        exit 1
    fi
done

# Extract on server
echo -e "\n${YELLOW}Extracting files on server...${NC}"
ssh ${SERVER_USER}@${SERVER_HOST} << 'ENDSSH'
cd /home/ubuntu/WhoVoted/data/district_reference

echo "Extracting ZIP files..."
for zipfile in *.zip; do
    if [ -f "$zipfile" ]; then
        echo "Extracting: $zipfile"
        unzip -o "$zipfile"
        echo "✓ Extracted: $zipfile"
    fi
done

echo ""
echo "Listing XLS files:"
ls -lh *.xls | head -20

echo ""
echo "Total XLS files:"
ls -1 *.xls | wc -l
ENDSSH

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Upload Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\nNext steps:"
echo -e "1. SSH to server: ${YELLOW}ssh ${SERVER_USER}@${SERVER_HOST}${NC}"
echo -e "2. Run parser: ${YELLOW}cd /home/ubuntu/WhoVoted && python deploy/parse_district_files.py${NC}"

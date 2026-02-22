#!/bin/bash

# WhoVoted Quick Start Script

echo "=== WhoVoted Modernization Quick Start ==="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Create directories
echo "Creating directories..."
mkdir -p data uploads logs public/data

# Initialize geocoding cache
echo "Initializing geocoding cache..."
echo "{}" > data/geocoding_cache.json

# Check if virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo "Creating virtual environment..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    
    echo "Installing dependencies..."
    pip install -r requirements.txt
    
    cd ..
else
    echo "Virtual environment already exists"
    cd backend
    source venv/bin/activate
    cd ..
fi

# Check if .env exists
if [ ! -f "backend/.env" ]; then
    echo "Creating .env file..."
    cp backend/.env.example backend/.env
    echo "WARNING: Please edit backend/.env and set a secure SECRET_KEY"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To start the server:"
echo "  cd backend"
echo "  source venv/bin/activate  # On Windows: venv\\Scripts\\activate"
echo "  python app.py"
echo ""
echo "Then visit:"
echo "  Public Map: http://localhost:5000/"
echo "  Admin Panel: http://localhost:5000/admin"
echo "  Login: admin / admin2026!"
echo ""

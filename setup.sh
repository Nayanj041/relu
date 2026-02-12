#!/bin/bash
# Nike Scraper Setup Script
# Automates dependency installation and environment setup

set -e

echo "======================================================"
echo "Nike Product Scraper - Setup Script"
echo "======================================================"
echo ""

# Check Python version
echo "[1/3] Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
echo "✓ Python $PYTHON_VERSION found"
echo ""

# Install pip dependencies
echo "[2/3] Installing Python dependencies..."
echo "Installing: selenium, pandas, webdriver-manager"
python3 -m pip install -r requirements.txt --quiet
echo "✓ Dependencies installed successfully"
echo ""

# Check for Chrome/Chromium
echo "[3/3] Checking for Chrome/Chromium browser..."
if command -v chromium-browser &> /dev/null; then
    echo "✓ Chromium browser found"
elif command -v google-chrome &> /dev/null; then
    echo "✓ Google Chrome found"
elif command -v chromium &> /dev/null; then
    echo "✓ Chromium found"
else
    echo "⚠ Chrome/Chromium not found. Installing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y chromium-browser -qq
        echo "✓ Chromium installed successfully"
    else
        echo "❌ Could not auto-install browser. Please install Chrome/Chromium manually."
        exit 1
    fi
fi
echo ""

echo "======================================================"
echo "✓ Setup Complete!"
echo "======================================================"
echo ""
echo "Ready to run scraper:"
echo "  python3 nike_scraper.py"
echo ""
echo "For more details, see README.md"

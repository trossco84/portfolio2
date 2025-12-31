#!/bin/bash
# Project initialization script

set -e

echo "=================================================="
echo "  Portfolio Management System - Initialization"
echo "=================================================="
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "ERROR: Python 3.11+ required. Found: $PYTHON_VERSION"
    exit 1
fi
echo "✓ Python $PYTHON_VERSION"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -e ".[dev,optimizer]" > /dev/null 2>&1
echo "✓ Dependencies installed"
echo ""

# Setup .env file
echo "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Created .env file from template"
    echo ""
    echo "IMPORTANT: Edit .env and set your DATABASE_URL"
    echo "  1. Go to https://supabase.com"
    echo "  2. Create a new project"
    echo "  3. Copy connection string from Settings → Database"
    echo "  4. Paste it into .env as DATABASE_URL"
    echo ""
    read -p "Press Enter when you've configured .env..."
else
    echo "✓ .env file already exists"
fi
echo ""

# Check if DATABASE_URL is set
if grep -q "DATABASE_URL=postgresql://" .env 2>/dev/null; then
    echo "Running database migrations..."
    python portfolio/db/migrations/migrate.py
    echo "✓ Database initialized"
    echo ""
else
    echo "⚠ DATABASE_URL not configured. Skipping migrations."
    echo "  Run manually: python portfolio/db/migrations/migrate.py"
    echo ""
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p reports logs
echo "✓ Directories created"
echo ""

echo "=================================================="
echo "  Setup Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Activate environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Run portfolio:"
echo "     python -m portfolio run --asof \$(date +%Y-%m-%d) --mode paper"
echo ""
echo "  3. Launch dashboard:"
echo "     uvicorn app.main:app --reload"
echo ""
echo "Or use the Makefile:"
echo "  make run        # Run portfolio"
echo "  make dashboard  # Launch dashboard"
echo "  make test       # Run tests"
echo ""
echo "See README.md for full documentation."
echo ""

#!/bin/bash
# Local development setup script for MyHealthTeam Chatbot

set -e

echo "=========================================="
echo "MyHealthTeam Chatbot Setup"
echo "=========================================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
echo ""
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✓ Created .env file from .env.example"
    echo "  Please edit .env with your configuration"
else
    echo "✓ .env file already exists"
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p logs
echo "✓ Created logs directory"

# Check for test database
echo ""
if [ -f production_backup_for_testing.db ]; then
    echo "✓ Test database found"
else
    echo "⚠ Test database not found"
    echo "  Copy it from: /home/ubuntu/myhealthteam/dev/production_backup_for_testing.db"
fi

# Run tests
echo ""
echo "Running tests..."
if pytest tests/ -v; then
    echo "✓ All tests passed"
else
    echo "⚠ Some tests failed (this may be expected without test database)"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To run the chatbot:"
echo "  source venv/bin/activate"
echo "  streamlit run chatbot_app.py --server.port=8502"
echo ""
echo "To run tests:"
echo "  source venv/bin/activate"
echo "  pytest tests/ -v"
echo ""

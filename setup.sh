#!/bin/bash
set -e

VENV_DIR=".venv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate and install dependencies
echo "Activating virtual environment and installing dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r requirements.txt

# Copy .env_example to .env if .env doesn't exist
if [ ! -f ".env" ]; then
    cp .env_example .env
    echo "Created .env from .env_example — fill in your credentials."
fi

echo ""
echo "Setup complete. To activate the virtual environment, run:"
echo "  source $VENV_DIR/bin/activate"

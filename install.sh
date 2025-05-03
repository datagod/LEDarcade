#!/bin/bash

set -e

echo " Setting up LEDarcade environment..."

# System dependencies
SYSTEM_PACKAGES=(
    python3
    python3-pip
    python3-venv
    python3-dev
    build-essential
    libopenjp2-7
    libtiff5
    libatlas-base-dev
    libjpeg-dev
    libfreetype6-dev
    libzmq3-dev
    libffi-dev
    libssl-dev
    libgraphicsmagick++-dev
)

# Python packages
PYTHON_PACKAGES=(
    yfinance
    numpy
    requests
    pillow
    flask
    twitchio
    configparser
    rgbmatrix
)

# Create and activate virtual environment
PROJECT_DIR="$(pwd)"
VENV_DIR="$PROJECT_DIR/ledarcade-env"

# Install system dependencies
echo "Installing system packages..."
sudo apt update
sudo apt install -y "${SYSTEM_PACKAGES[@]}"

# Create virtual environment if needed
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python packages
echo "Installing Python packages..."
pip install "${PYTHON_PACKAGES[@]}"

echo "LEDarcade setup complete!"

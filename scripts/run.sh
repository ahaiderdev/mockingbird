#!/bin/bash
# Quick start script for local development

set -e

echo "==================================="
echo "Synthetic Metrics Generator"
echo "==================================="
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Default to baseline config
CONFIG="${1:-configs/baseline.yaml}"

echo ""
echo "Starting generator with config: $CONFIG"
echo ""
echo "Endpoints:"
echo "  - Prometheus metrics: http://localhost:8000/metrics"
echo "  - Control API:        http://localhost:8081/status"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run the generator
python -m src.main --config "$CONFIG"


#!/bin/bash
# Quick start script for Docker Compose setup

set -e

echo "=========================================="
echo "Synthetic Metrics Generator - Docker Setup"
echo "=========================================="
echo ""

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install OrbStack or Docker Desktop."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install Docker Compose."
    exit 1
fi

echo "✓ Docker found"
echo "✓ Docker Compose found"
echo ""

# Build and start services
echo "Building and starting services..."
docker-compose up -d --build

echo ""
echo "Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "Service Status:"
docker-compose ps

echo ""
echo "=========================================="
echo "Services Started Successfully!"
echo "=========================================="
echo ""
echo "Access URLs:"
echo "  📊 Grafana:        http://localhost:3000"
echo "     Username: admin"
echo "     Password: admin"
echo ""
echo "  📈 Prometheus:     http://localhost:9090"
echo ""
echo "  🎛️  Control API:    http://localhost:8081/status"
echo "  📡 Metrics:        http://localhost:8000/metrics"
echo ""
echo "Quick Commands:"
echo "  View logs:         docker-compose logs -f"
echo "  Stop services:     docker-compose down"
echo "  Restart:           docker-compose restart"
echo ""
echo "Check status:"
curl -s http://localhost:8081/status | python3 -m json.tool 2>/dev/null || echo "  Waiting for generator to start..."
echo ""
echo "=========================================="


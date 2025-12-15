#!/bin/bash
# Container debugging script

echo "🔍 Crawl4AI Container Debug Script"
echo "=================================="

# Check if Docker is running
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Check Docker daemon
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running"
    exit 1
fi

echo "✅ Docker is available"

# Build the container
echo ""
echo "🔨 Building container..."
if docker compose build --no-cache; then
    echo "✅ Build successful"
else
    echo "❌ Build failed"
    exit 1
fi

# Try to start the container
echo ""
echo "🚀 Starting container..."
if docker compose up -d; then
    echo "✅ Container started"
else
    echo "❌ Failed to start container"
    docker compose logs
    exit 1
fi

# Wait a moment for services to initialize
echo ""
echo "⏳ Waiting for services to initialize..."
sleep 15

# Check container status
echo ""
echo "📊 Container Status:"
docker compose ps

# Check logs
echo ""
echo "📋 Recent Logs:"
docker compose logs --tail=50

# Check Redis connectivity
echo ""
echo "🔍 Testing Redis connectivity..."
if docker compose exec crawl4ai-service redis-cli ping; then
    echo "✅ Redis is responding"
else
    echo "❌ Redis is not responding"
fi

# Test HTTP endpoint
echo ""
echo "🌐 Testing HTTP endpoint..."
if curl -f http://localhost:8000/health 2>/dev/null; then
    echo "✅ HTTP endpoint is responding"
    echo "🎉 Container is running successfully!"
    echo ""
    echo "You can now access the service at: http://localhost:8000"
    echo "API docs available at: http://localhost:8000/docs"
else
    echo "❌ HTTP endpoint is not responding"
    echo ""
    echo "🔧 Debugging information:"
    echo "Container logs:"
    docker compose logs --tail=100
fi

echo ""
echo "To monitor logs in real-time: docker compose logs -f"
echo "To stop the container: docker compose down"
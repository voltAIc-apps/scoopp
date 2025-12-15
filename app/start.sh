#!/bin/bash
set -e

echo "🚀 Starting Crawl4AI Service..."

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to start..."
timeout=30
counter=0

while ! redis-cli -h ${REDIS_HOST:-127.0.0.1} -p ${REDIS_PORT:-6379} ping > /dev/null 2>&1; do
    sleep 1
    counter=$((counter + 1))
    if [ $counter -gt $timeout ]; then
        echo "❌ Redis failed to start within $timeout seconds"
        exit 1
    fi
done

echo "✅ Redis is ready!"

# Start the FastAPI application
echo "🌐 Starting FastAPI server..."
exec gunicorn --bind 0.0.0.0:11235 --workers 1 --threads 4 --timeout 1800 --graceful-timeout 30 --keep-alive 300 --log-level info --worker-class uvicorn.workers.UvicornWorker server:app
#!/bin/bash
# Refresh containers script - stops, rebuilds, and starts everything fresh

set -e

echo "🛑 Stopping all containers..."
docker-compose down 2>/dev/null || true
docker-compose -f docker-compose.dev.yml down 2>/dev/null || true

echo "🧹 Cleaning up old images and containers..."
docker-compose rm -f 2>/dev/null || true
docker-compose -f docker-compose.dev.yml rm -f 2>/dev/null || true

echo "🔨 Rebuilding containers (no cache)..."
docker-compose build --no-cache

echo "🚀 Starting containers..."
docker-compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 5

echo "🏥 Checking backend health..."
for i in {1..10}; do
  if curl -s http://localhost:8000/healthz > /dev/null 2>&1; then
    echo "✅ Backend is healthy!"
    curl -s http://localhost:8000/healthz | jq . || curl -s http://localhost:8000/healthz
    break
  fi
  echo "   Attempt $i/10 - waiting..."
  sleep 2
done

echo "🌐 Checking frontend..."
if curl -s http://localhost:5173 > /dev/null 2>&1; then
  echo "✅ Frontend is responding!"
else
  echo "⚠️  Frontend may still be starting..."
fi

echo ""
echo "📊 Container status:"
docker-compose ps

echo ""
echo "✨ Done! Services should be available at:"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "   API Docs: http://localhost:8000/docs"



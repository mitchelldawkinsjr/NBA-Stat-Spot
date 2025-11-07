#!/bin/bash
# Refresh dev containers script - for development with hot reload

set -e

echo "🛑 Stopping dev containers..."
docker-compose -f docker-compose.dev.yml down 2>/dev/null || true

echo "🧹 Cleaning up..."
docker-compose -f docker-compose.dev.yml rm -f 2>/dev/null || true

echo "🔨 Rebuilding dev containers..."
docker-compose -f docker-compose.dev.yml build --no-cache

echo "🚀 Starting dev containers..."
docker-compose -f docker-compose.dev.yml up -d

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
  echo "⚠️  Frontend may still be starting (check logs with: docker-compose -f docker-compose.dev.yml logs frontend)"
fi

echo ""
echo "📊 Container status:"
docker-compose -f docker-compose.dev.yml ps

echo ""
echo "✨ Done! Services should be available at:"
echo "   Backend:  http://localhost:8000 (with hot reload)"
echo "   Frontend: http://localhost:5173 (with hot reload)"
echo ""
echo "📝 View logs:"
echo "   docker-compose -f docker-compose.dev.yml logs -f"



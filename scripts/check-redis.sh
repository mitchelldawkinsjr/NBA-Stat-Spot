#!/bin/bash
# Script to check Redis configuration on Fly.io

echo "🔍 Checking Redis Configuration on Fly.io"
echo "=========================================="
echo ""

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo "❌ Fly CLI not found. Install it from: https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
fi

echo "1. Checking for REDIS_URL secret..."
REDIS_URL=$(fly secrets list --app nba-stat-spot-ai 2>/dev/null | grep REDIS_URL || echo "")
if [ -z "$REDIS_URL" ]; then
    echo "   ⚠️  REDIS_URL secret not found"
    echo ""
    echo "   To set up Redis:"
    echo "   1. Create Redis instance: fly redis create"
    echo "   2. Set REDIS_URL: fly secrets set REDIS_URL='redis://your-redis-url'"
else
    echo "   ✅ REDIS_URL is configured"
    echo "   $REDIS_URL"
fi

echo ""
echo "2. Checking Redis instances..."
REDIS_INSTANCES=$(fly redis list 2>/dev/null | grep -v "NAME" || echo "")
if [ -z "$REDIS_INSTANCES" ]; then
    echo "   ⚠️  No Redis instances found"
    echo ""
    echo "   To create a Redis instance:"
    echo "   fly redis create"
else
    echo "   ✅ Redis instances found:"
    echo "$REDIS_INSTANCES"
fi

echo ""
echo "3. Testing Redis connection via API..."
API_URL="https://nba-stat-spot-ai.fly.dev/api/v1/admin/cache/redis/test"
RESPONSE=$(curl -s "$API_URL" 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "   ✅ API endpoint accessible"
    echo ""
    echo "   Response:"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
else
    echo "   ❌ Could not reach API endpoint"
    echo "   Make sure your app is deployed and running"
fi

echo ""
echo "=========================================="
echo "✅ Check complete!"
echo ""
echo "If Redis is working, you should see:"
echo "  - redisAvailable: true"
echo "  - redisConnected: true"
echo "  - redisKeys: [number]"


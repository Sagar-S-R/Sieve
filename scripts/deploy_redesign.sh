#!/bin/bash
# Deploy script for system redesign
# Run this after pulling the redesign code

set -e  # Exit on error

echo "======================================"
echo "  Sieve System Redesign Deployment"
echo "======================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Step 1: Database migration
echo "📊 Step 1: Database Migration"
echo "------------------------------"
echo "Running migration script..."

# Check if postgres container is running
if ! docker ps | grep -q postgres; then
    echo "⚠️  PostgreSQL container not running. Starting services..."
    docker-compose up -d postgres
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
fi

# Run migration
docker exec -i sieve-postgres psql -U postgres -d sieve_db < database/migrations/001_add_redesign_columns.sql

if [ $? -eq 0 ]; then
    echo "✓ Database migration completed"
else
    echo "❌ Database migration failed"
    exit 1
fi
echo ""

# Step 2: Rebuild containers
echo "🔨 Step 2: Rebuild Containers"
echo "------------------------------"
echo "Rebuilding text_extractor and api_gateway..."

docker-compose build api_gateway text_extractor

if [ $? -eq 0 ]; then
    echo "✓ Containers rebuilt"
else
    echo "❌ Container build failed"
    exit 1
fi
echo ""

# Step 3: Restart services
echo "🔄 Step 3: Restart Services"
echo "------------------------------"
echo "Restarting all services..."

docker-compose down
docker-compose up -d

if [ $? -eq 0 ]; then
    echo "✓ Services restarted"
else
    echo "❌ Service restart failed"
    exit 1
fi
echo ""

# Step 4: Wait for services to be healthy
echo "⏳ Step 4: Health Check"
echo "------------------------------"
echo "Waiting for services to be ready..."
sleep 10

# Check API Gateway
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ API Gateway is healthy"
else
    echo "⚠️  API Gateway health check failed (this might be normal if no /health endpoint)"
fi

# Check if text_extractor is running
if docker ps | grep -q text_extractor; then
    echo "✓ Text Extractor is running"
else
    echo "❌ Text Extractor is not running"
    exit 1
fi

echo ""

# Step 5: Verification
echo "🔍 Step 5: Verification"
echo "------------------------------"

# Check new columns exist
echo "Checking database schema..."
COLUMN_CHECK=$(docker exec -i sieve-postgres psql -U postgres -d sieve_db -t -c "SELECT column_name FROM information_schema.columns WHERE table_name='tasks' AND column_name='message_type';" | xargs)

if [ "$COLUMN_CHECK" = "message_type" ]; then
    echo "✓ New columns verified in database"
else
    echo "❌ New columns not found in database"
    exit 1
fi

# Check Redis
echo "Checking Redis connection..."
if docker exec -i redis redis-cli PING | grep -q PONG; then
    echo "✓ Redis is responding"
else
    echo "❌ Redis connection failed"
    exit 1
fi

echo ""
echo "======================================"
echo "  ✅ Deployment Complete!"
echo "======================================"
echo ""
echo "📋 Next Steps:"
echo "1. Check logs: docker-compose logs -f text_extractor"
echo "2. Test message buffer: docker exec -i redis redis-cli LRANGE buffer:messages:-GROUP_ID 0 -1"
echo "3. Send test messages to verify new features"
echo ""
echo "📚 Documentation: docs/REDESIGN_IMPLEMENTATION.md"
echo ""

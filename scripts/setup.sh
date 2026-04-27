#!/bin/bash

# Sieve Setup Script
# This script helps you set up the Sieve system quickly

set -e

echo "🚀 Sieve Setup Script"
echo "===================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your tokens:"
    echo "   - TELEGRAM_BOT_TOKEN (from @BotFather)"
    echo "   - GOOGLE_API_KEY (from Google AI Studio)"
    echo ""
    read -p "Press Enter after you've updated .env..."
else
    echo "✅ .env file already exists"
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo ""
echo "🐳 Starting Docker services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "🔍 Checking service health..."

# Check PostgreSQL
if docker exec sieve_postgres pg_isready -U user -d sieve > /dev/null 2>&1; then
    echo "✅ PostgreSQL is healthy"
else
    echo "⚠️  PostgreSQL is not ready yet"
fi

# Check Redis
if docker exec sieve_redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is healthy"
else
    echo "⚠️  Redis is not ready yet"
fi

# Check RabbitMQ
if docker exec sieve_rabbitmq rabbitmq-diagnostics ping > /dev/null 2>&1; then
    echo "✅ RabbitMQ is healthy"
else
    echo "⚠️  RabbitMQ is not ready yet"
fi

# Check API Gateway
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API Gateway is healthy"
else
    echo "⚠️  API Gateway is not ready yet"
fi

echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Set your Telegram webhook:"
echo "   curl -X POST \"https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook\" \\"
echo "     -d '{\"url\": \"https://your-domain.com/webhook\"}'"
echo ""
echo "2. View logs:"
echo "   docker-compose logs -f"
echo ""
echo "3. Test the system:"
echo "   - Add bot to a Telegram group"
echo "   - Send a message with 'assignment' or 'deadline'"
echo "   - Check logs: docker-compose logs -f text_extractor"
echo ""
echo "4. Access services:"
echo "   - API Gateway: http://localhost:8000"
echo "   - RabbitMQ Management: http://localhost:15672 (guest/guest)"
echo "   - PostgreSQL: localhost:5432 (user/password)"
echo ""

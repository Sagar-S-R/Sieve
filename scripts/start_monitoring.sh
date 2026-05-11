#!/bin/bash

# Sieve Monitoring Stack Startup Script

echo "🚀 Starting Sieve Monitoring Stack..."
echo ""

# Start Prometheus and Grafana
echo "📊 Starting Prometheus..."
docker-compose up -d prometheus

echo "📈 Starting Grafana..."
docker-compose up -d grafana

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

echo ""
echo "✅ Monitoring stack is ready!"
echo ""
echo "📊 Prometheus: http://localhost:9090"
echo "📈 Grafana: http://localhost:3000"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "🐰 RabbitMQ Management: http://localhost:15672"
echo "   Username: guest"
echo "   Password: guest"
echo ""
echo "📋 Available Dashboards:"
echo "   - Sieve Overview: http://localhost:3000/d/sieve_overview"
echo "   - RabbitMQ Queues: http://localhost:3000/d/rabbitmq_queues"
echo ""
echo "💡 Tip: Check docs/MONITORING.md for detailed guide"

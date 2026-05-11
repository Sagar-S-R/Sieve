# Sieve Monitoring Guide

This document explains how to use Prometheus and Grafana to monitor the Sieve reminder bot system.

## Overview

The monitoring stack consists of:
- **Prometheus** - Metrics collection and storage
- **Grafana** - Visualization and dashboards
- **RabbitMQ Exporter** - Queue metrics
- **Application Metrics** - Custom metrics from text_extractor

## Quick Start

### 1. Start Monitoring Stack

```bash
docker-compose up -d prometheus grafana
```

### 2. Access Dashboards

**Grafana:**
- URL: http://localhost:3000
- Username: `admin`
- Password: `admin` (change on first login)

**Prometheus:**
- URL: http://localhost:9090

**RabbitMQ Management:**
- URL: http://localhost:15672
- Username: `guest`
- Password: `guest`

## Dashboards

### Sieve Overview Dashboard

**URL:** http://localhost:3000/d/sieve_overview

**Panels:**
1. **Messages Processed/Min** - Throughput gauge
2. **Workflow Processing Time** - p50 and p95 latency
3. **HITL Triggers/Min** - How often clarification is needed
4. **HITL Triggers by Error Type** - Breakdown of why HITL triggers
5. **Database Operation Latency** - DB query performance
6. **Database Operations Rate** - DB operations per second

### RabbitMQ Queue Monitoring

**URL:** http://localhost:3000/d/rabbitmq_queues

**Panels:**
1. **Fast Text Queue Depth** - Messages waiting in text queue
2. **Heavy Media Queue Depth** - Messages waiting in media queue
3. **Queue Depth Over Time** - Historical queue depth
4. **Message Throughput** - Publish vs consume rates

## Metrics Reference

### Application Metrics (text_extractor:8001)

| Metric Name | Type | Description |
|-------------|------|-------------|
| `workflow_duration` | Histogram | Time to process one message through workflow |
| `db_operation_latency` | Histogram | Database query latency by operation |
| `hitl_triggers_total` | Counter | Number of HITL triggers by error type |

### RabbitMQ Metrics (rabbitmq:15692)

| Metric Name | Type | Description |
|-------------|------|-------------|
| `rabbitmq_queue_messages` | Gauge | Current queue depth |
| `rabbitmq_queue_messages_published_total` | Counter | Total messages published |
| `rabbitmq_queue_messages_delivered_total` | Counter | Total messages consumed |
| `rabbitmq_queue_consumers` | Gauge | Number of active consumers |

## Alerting (Future)

### Recommended Alerts

**High Priority:**
1. **Queue Depth > 100** - Messages piling up, worker may be down
2. **HITL Rate > 50%** - Too many clarifications, LLM needs tuning
3. **Workflow Latency > 10s** - System is slow
4. **No Messages Processed for 5min** - Worker is down

**Medium Priority:**
5. **DB Latency > 1s** - Database performance issue
6. **Error Rate > 10%** - High failure rate

### Setting Up Alerts (Optional)

To enable alerts, you need to:

1. **Install Alertmanager:**
```yaml
# Add to docker-compose.yml
alertmanager:
  image: prom/alertmanager:latest
  ports:
    - "9093:9093"
  volumes:
    - ./monitoring/alertmanager/config.yml:/etc/alertmanager/config.yml
```

2. **Create Alert Rules:**
```yaml
# monitoring/prometheus/alerts.yml
groups:
  - name: sieve_alerts
    interval: 30s
    rules:
      - alert: HighQueueDepth
        expr: rabbitmq_queue_messages > 100
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Queue depth is high"
          description: "{{ $labels.queue }} has {{ $value }} messages"
```

3. **Configure Notifications:**
- Email
- Telegram
- Slack
- PagerDuty

## Troubleshooting

### Prometheus Not Scraping Metrics

**Check target status:**
```
http://localhost:9090/targets
```

All targets should show "UP" status.

**If text_extractor is DOWN:**
```bash
# Check if metrics endpoint is accessible
curl http://localhost:8001/metrics

# Check text_extractor logs
docker-compose logs text_extractor
```

**If RabbitMQ is DOWN:**
```bash
# Check if Prometheus plugin is enabled
docker exec sieve_rabbitmq rabbitmq-plugins list

# Should show: [E*] rabbitmq_prometheus

# Check metrics endpoint
curl http://localhost:15692/metrics
```

### Grafana Dashboard Not Loading

**Check Prometheus datasource:**
1. Go to Configuration → Data Sources
2. Click "Prometheus"
3. Click "Test" button
4. Should show "Data source is working"

**If test fails:**
```bash
# Check if Prometheus is running
docker-compose ps prometheus

# Check Prometheus logs
docker-compose logs prometheus
```

### No Data in Dashboards

**Possible causes:**
1. **No traffic** - Send some test messages
2. **Time range** - Check dashboard time range (top right)
3. **Metrics not exposed** - Check Prometheus targets

## Performance Tuning

### Prometheus Storage

By default, Prometheus keeps 15 days of data. To change:

```yaml
# In docker-compose.yml
prometheus:
  command:
    - '--storage.tsdb.retention.time=30d'  # Keep 30 days
```

### Scrape Interval

Default is 15 seconds. To change:

```yaml
# In monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 30s  # Scrape every 30 seconds
```

## Best Practices

1. **Monitor regularly** - Check dashboards daily
2. **Set up alerts** - Don't rely on manual checking
3. **Baseline metrics** - Know your normal values
4. **Investigate spikes** - Sudden changes indicate issues
5. **Capacity planning** - Watch trends over time

## Metrics to Watch

### Daily Checks:
- ✅ Message processing rate
- ✅ Queue depth
- ✅ HITL trigger rate
- ✅ Error rate

### Weekly Checks:
- ✅ Workflow latency trends
- ✅ Database performance
- ✅ Storage usage
- ✅ Memory/CPU usage

## Advanced: Custom Metrics

To add new metrics to text_extractor:

```python
# In workers/text_extractor/core/metrics.py
from prometheus_client import Counter, Histogram

# Add new metric
llm_api_calls = Counter(
    'llm_api_calls_total',
    'Total LLM API calls',
    ['model', 'status']
)

# Use in code
llm_api_calls.labels(model='groq', status='success').inc()
```

Metric will automatically appear in Prometheus and Grafana.

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [RabbitMQ Prometheus Plugin](https://www.rabbitmq.com/prometheus.html)

---

Last Updated: 2026-05-11

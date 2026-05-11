# Monitoring Configuration

This folder contains configuration files for Prometheus and Grafana monitoring.

## Structure

```
monitoring/
├── prometheus/
│   └── prometheus.yml          # Prometheus scrape configuration
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/        # Auto-configure Prometheus datasource
│   │   └── dashboards/         # Auto-load dashboards
│   └── dashboards/
│       ├── sieve_overview.json      # Main application dashboard
│       └── rabbitmq_dashboard.json  # RabbitMQ queue monitoring
└── README.md
```

## Quick Start

```bash
# Start monitoring stack
docker-compose up -d prometheus grafana

# Access Grafana
open http://localhost:3000
# Login: admin / admin
```

## Adding New Metrics

### 1. Expose Metrics from Your Service

```python
from prometheus_client import Counter, start_http_server

# Define metric
my_metric = Counter('my_metric_total', 'Description')

# Expose on port
start_http_server(8001)

# Increment metric
my_metric.inc()
```

### 2. Add Scrape Target to Prometheus

Edit `prometheus/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'my_service'
    static_configs:
      - targets: ['my_service:8001']
```

### 3. Visualize in Grafana

1. Go to http://localhost:3000
2. Create new dashboard
3. Add panel with query: `rate(my_metric_total[5m])`

## Dashboards

### Sieve Overview
- Message processing rate
- Workflow latency (p50, p95)
- HITL trigger rate
- Database performance

### RabbitMQ Queues
- Queue depth
- Message throughput
- Consumer count

## Troubleshooting

**Prometheus not scraping:**
```bash
# Check targets
curl http://localhost:9090/targets

# Check if service exposes metrics
curl http://localhost:8001/metrics
```

**Grafana dashboard not loading:**
```bash
# Check Grafana logs
docker-compose logs grafana

# Restart Grafana
docker-compose restart grafana
```

## Resources

- [Prometheus Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)

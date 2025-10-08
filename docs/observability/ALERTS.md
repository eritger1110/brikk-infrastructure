# Prometheus Alert Rules & Alertmanager Setup

## Overview

This document describes the baseline Prometheus alert rules for monitoring the Brikk platform and provides instructions for setting up Alertmanager with Slack notifications.

## Alert Rules

The alert rules are defined in `ops/prometheus/alerts.yml` and cover critical operational metrics:

### High Error Rate
- **Metric**: `http_requests_total{status_code=~"5.."}`
- **Threshold**: > 1% error rate for 5 minutes
- **Severity**: Critical
- **Description**: Triggers when the API experiences more than 1% 5xx errors

### High Request Latency
- **Metric**: `http_request_latency_seconds{quantile="0.95"}`
- **Threshold**: > 100ms for 5 minutes
- **Severity**: Warning
- **Description**: Triggers when 95th percentile latency exceeds 100ms

### Authentication Failures Spike
- **Metric**: `auth_failures_total`
- **Threshold**: > 25 failures in 5 minutes
- **Severity**: Warning
- **Description**: Detects potential security issues or misconfigurations

### High Queue Depth
- **Metric**: `rq_queue_depth`
- **Threshold**: > 100 jobs for 5 minutes
- **Severity**: Critical
- **Description**: Indicates processing bottlenecks in the Redis Queue

## Required Metrics

The following metrics must be exposed by the application:

```python
# In your Flask app
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
requests_total = Counter('http_requests_total', 'Total HTTP requests', ['method', 'route', 'status_code'])
request_latency = Histogram('http_request_latency_seconds', 'HTTP request latency')

# Auth metrics
auth_failures_total = Counter('auth_failures_total', 'Total authentication failures')

# Queue metrics
rq_queue_depth = Gauge('rq_queue_depth', 'Current Redis Queue depth')
```

## Slack Integration

### Setup Slack Webhook

1. Go to your Slack workspace settings
2. Navigate to "Apps" → "Incoming Webhooks"
3. Create a new webhook for your alerts channel
4. Copy the webhook URL

### Configure Alertmanager

1. Copy the template configuration:
   ```bash
   cp ops/alertmanager/config.tmpl.yml ops/alertmanager/config.yml
   ```

2. Set your Slack webhook URL:
   ```bash
   export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
   ```

3. Uncomment the Slack configuration sections in `config.yml`

4. Update the channel names to match your Slack setup

## Local Testing with Docker Compose

Use this docker-compose snippet to test Prometheus and Alertmanager locally:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./ops/prometheus/alerts.yml:/etc/prometheus/alerts.yml
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'

  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./ops/alertmanager/config.yml:/etc/alertmanager/config.yml

  # Your Brikk app (adjust as needed)
  brikk-app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=development
    depends_on:
      - prometheus
```

Create a minimal `prometheus.yml` configuration:

```yaml
global:
  scrape_interval: 15s

rule_files:
  - "/etc/prometheus/alerts.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'brikk-app'
    static_configs:
      - targets: ['brikk-app:5000']
    metrics_path: '/metrics'
```

### Running the Stack

```bash
# Start the monitoring stack
docker-compose up -d

# Check Prometheus targets
open http://localhost:9090/targets

# Check Alertmanager
open http://localhost:9093

# Generate test metrics
curl http://localhost:5000/metrics
```

## Troubleshooting

### Common Issues

1. **Metrics not appearing**: Ensure your Flask app exposes `/metrics` endpoint
2. **Alerts not firing**: Check Prometheus rule evaluation at `/rules`
3. **Slack not working**: Verify webhook URL and channel permissions

### Testing Alerts

Force an alert by temporarily lowering thresholds:

```yaml
# In alerts.yml - for testing only
- alert: HighErrorRate
  expr: sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.001  # 0.1% instead of 1%
```

## Production Deployment

For production deployment:

1. Use persistent volumes for Prometheus data
2. Configure proper retention policies
3. Set up high availability for Alertmanager
4. Use service discovery instead of static configs
5. Implement proper security (TLS, authentication)

## References

- [Prometheus Alerting Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)

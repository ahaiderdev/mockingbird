# Deployment Guide

Options for deploying the Synthetic Metrics Generator.

## Deployment Options

1. **Local Development** - Python virtual environment
2. **Docker Compose** - Full observability stack
3. **Docker Standalone** - Just the generator
4. **Kubernetes** - Production deployment (coming soon)

## Local Development Deployment

### Prerequisites

- Python 3.11+
- pip
- Virtual environment tool

### Setup

```bash
# Clone/download repository
cd synthetic_metrics_generator

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create configuration
cp configs/baseline.example.yaml configs/baseline.yaml

# Edit configuration if needed
vim configs/baseline.yaml
```

### Run

```bash
# Run with default config
python -m src.main --config configs/baseline.yaml

# Run with different config
python -m src.main --config configs/production_sim.yaml

# Run with custom log level
python -m src.main --config configs/baseline.yaml --log-level DEBUG
```

### Stop

Press `Ctrl+C` to stop gracefully.

### Pros & Cons

**Pros**:
- Fast iteration
- Easy debugging
- No Docker required
- Direct access to logs

**Cons**:
- Manual dependency management
- No automatic restart
- Requires OTEL collector separately
- Platform-specific setup

## Docker Compose Deployment

### Prerequisites

- Docker
- Docker Compose

### Setup

```bash
# Create configuration files
cp configs/baseline.example.yaml configs/baseline.yaml
cp compose/prometheus.example.yml compose/prometheus.yml
cp compose/alloy-config.example.alloy compose/alloy-config.alloy

# Edit configs (optional for local testing)
vim compose/alloy-config.alloy
vim compose/prometheus.yml
```

### Run

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f generator

# Check status
docker-compose ps
```

### Services

The compose stack includes:

- **generator** - Metrics generator (port 8000, 8081)
- **prometheus** - Prometheus server (port 9090)
- **grafana** - Grafana dashboard (port 3000)
- **alloy** - OTEL Collector (port 4317, 4318, 12345)

### Access

- Generator Metrics: http://localhost:8000/metrics
- Generator API: http://localhost:8081/status
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Alloy UI: http://localhost:12345

### Stop

```bash
# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove volumes (deletes data)
docker-compose down -v
```

### Update

```bash
# Rebuild after code changes
docker-compose build generator

# Restart specific service
docker-compose restart generator

# Pull latest images
docker-compose pull
```

### Pros & Cons

**Pros**:
- Complete observability stack
- Easy to start/stop
- Consistent environment
- Good for testing full pipeline

**Cons**:
- Higher resource usage
- More complex setup
- Slower iteration

## Docker Standalone Deployment

Run just the generator container.

### Build

```bash
# Build image
docker build -t synthetic-metrics-generator .

# Or use specific tag
docker build -t synthetic-metrics-generator:v1.0 .
```

### Run

```bash
# Run with default config
docker run -d \
  --name metrics-generator \
  -p 8000:8000 \
  -p 8081:8081 \
  -v $(pwd)/configs:/app/configs \
  synthetic-metrics-generator

# Run with custom config
docker run -d \
  --name metrics-generator \
  -p 8000:8000 \
  -p 8081:8081 \
  -v $(pwd)/configs:/app/configs \
  -e CONFIG_FILE=/app/configs/production_sim.yaml \
  synthetic-metrics-generator

# Run with environment variables
docker run -d \
  --name metrics-generator \
  -p 8000:8000 \
  -p 8081:8081 \
  -e OTEL_ENDPOINT=collector:4317 \
  -e LOG_LEVEL=DEBUG \
  synthetic-metrics-generator
```

### Manage

```bash
# View logs
docker logs -f metrics-generator

# Stop
docker stop metrics-generator

# Start
docker start metrics-generator

# Remove
docker rm metrics-generator

# Execute commands inside container
docker exec -it metrics-generator /bin/sh
```

### Networking

Connect to external OTEL collector:

```bash
# Create network
docker network create metrics-net

# Run collector
docker run -d \
  --name otel-collector \
  --network metrics-net \
  -p 4317:4317 \
  otel/opentelemetry-collector

# Run generator
docker run -d \
  --name metrics-generator \
  --network metrics-net \
  -p 8000:8000 \
  -p 8081:8081 \
  -e OTEL_ENDPOINT=otel-collector:4317 \
  synthetic-metrics-generator
```

### Pros & Cons

**Pros**:
- Lightweight
- Flexible networking
- Easy to integrate
- Portable

**Cons**:
- Manual networking
- No automatic collector
- More manual setup

## Cloud Deployment

### Grafana Cloud

Send metrics directly to Grafana Cloud.

#### Configuration

```yaml
# configs/baseline.yaml
exporters:
  otel:
    enabled: true
    endpoint: "otlp-gateway-prod-<region>.grafana.net:443"
    insecure: false
    headers:
      Authorization: "Basic <base64(username:token)>"
```

Or use Alloy as intermediary:

```alloy
// compose/alloy-config.alloy
otelcol.exporter.otlphttp "grafana_cloud" {
  client {
    endpoint = "https://otlp-gateway-prod-<region>.grafana.net/otlp"
    auth = otelcol.auth.basic.grafana_cloud.handler
  }
}

otelcol.auth.basic "grafana_cloud" {
  username = "<instance-id>"
  password = "<api-token>"
}
```

#### Prometheus Remote Write

```yaml
# compose/prometheus.yml
remote_write:
  - url: https://prometheus-prod-<region>.grafana.net/api/prom/push
    basic_auth:
      username: <instance-id>
      password: <api-token>
    write_relabel_configs:
      - source_labels: [__name__]
        regex: 'synthetic_prom_.*'
        action: keep
```

### SigNoz Cloud

Send metrics to SigNoz Cloud.

```alloy
// compose/alloy-config.alloy
otelcol.exporter.otlphttp "signoz_cloud" {
  client {
    endpoint = "https://ingest.<region>.signoz.cloud:443"
    headers = {
      "signoz-access-token" = "<your-token>",
    }
  }
}
```

### AWS/GCP/Azure

Deploy using container services:

- **AWS ECS/Fargate**
- **GCP Cloud Run**
- **Azure Container Instances**

Example ECS task definition:

```json
{
  "family": "synthetic-metrics-generator",
  "containerDefinitions": [
    {
      "name": "generator",
      "image": "synthetic-metrics-generator:latest",
      "portMappings": [
        {"containerPort": 8000, "protocol": "tcp"},
        {"containerPort": 8081, "protocol": "tcp"}
      ],
      "environment": [
        {"name": "OTEL_ENDPOINT", "value": "collector.internal:4317"},
        {"name": "LOG_LEVEL", "value": "INFO"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/metrics-generator",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024"
}
```

## Kubernetes Deployment (Coming Soon)

Example manifests for Kubernetes deployment.

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: synthetic-metrics-generator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: metrics-generator
  template:
    metadata:
      labels:
        app: metrics-generator
    spec:
      containers:
      - name: generator
        image: synthetic-metrics-generator:latest
        ports:
        - containerPort: 8000
          name: metrics
        - containerPort: 8081
          name: api
        env:
        - name: OTEL_ENDPOINT
          value: "otel-collector:4317"
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8081
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8081
          initialDelaySeconds: 5
          periodSeconds: 10
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: metrics-generator
spec:
  selector:
    app: metrics-generator
  ports:
  - name: metrics
    port: 8000
    targetPort: 8000
  - name: api
    port: 8081
    targetPort: 8081
```

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: generator-config
data:
  baseline.yaml: |
    global:
      tick_interval_s: 1
      seed: 42
    # ... rest of config
```

## Resource Requirements

### Baseline Config (~100 series)

- **CPU**: 0.1-0.2 cores
- **Memory**: 150-200 MB
- **Disk**: Minimal (logs only)
- **Network**: ~10 KB/s

### Production Sim (~5,000 series)

- **CPU**: 0.5-1.0 cores
- **Memory**: 500-800 MB
- **Disk**: Minimal
- **Network**: ~50 KB/s

### High Cardinality (~150,000 series)

- **CPU**: 2-4 cores
- **Memory**: 2.5-4 GB
- **Disk**: Minimal
- **Network**: ~500 KB/s

### Scaling Factors

Series count scales roughly linearly with:
- Memory usage
- CPU usage
- Network bandwidth
- Tick duration

## Monitoring the Generator

### Health Checks

```bash
# Liveness probe
curl http://localhost:8081/healthz

# Readiness probe
curl http://localhost:8081/status
```

### Metrics

Monitor generator performance:

```promql
# Tick duration
histogram_quantile(0.95, 
  rate(synthetic_prom_gen_tick_duration_seconds_bucket[5m])
)

# Export errors
rate(synthetic_prom_gen_export_errors_total[5m])

# Active series
sum(synthetic_prom_gen_active_series)
```

### Logs

```bash
# Docker Compose
docker-compose logs -f generator

# Docker
docker logs -f metrics-generator

# Kubernetes
kubectl logs -f deployment/synthetic-metrics-generator
```

## Troubleshooting

### High Memory Usage

1. Check series count: `curl localhost:8081/status | jq '.total_series'`
2. Reduce `series_cap` in config
3. Increase `tick_interval_s`
4. Reduce number of metrics

### Slow Tick Duration

1. Check tick duration: `synthetic_prom_gen_tick_duration_seconds`
2. Increase CPU allocation
3. Reduce series count
4. Increase `tick_interval_s`

### Export Errors

1. Check logs: `docker-compose logs generator`
2. Verify OTEL endpoint: `curl http://collector:4317`
3. Check network connectivity
4. Verify authentication

### Container Crashes

1. Check logs: `docker logs metrics-generator`
2. Verify configuration is valid
3. Check resource limits
4. Review error messages

## Security Considerations

### Network Security

- Expose only necessary ports
- Use internal networks for inter-service communication
- Add authentication to Control API if exposed

### Configuration Security

- Store credentials in secrets/environment variables
- Don't commit credentials to git
- Use `.gitignore` for config files
- Rotate credentials regularly

### Container Security

- Run as non-root user
- Use minimal base images
- Scan for vulnerabilities
- Keep dependencies updated

## Next Steps

- **[Getting Started](02-getting-started.md)** - Quick start guide
- **[Configuration](03-configuration.md)** - Configuration reference
- **[Control API](05-control-api.md)** - Runtime controls
- **[Examples](../examples/)** - Example configurations


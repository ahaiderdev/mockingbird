# Getting Started

This guide will help you install and run the Synthetic Metrics Generator for the first time.

## Prerequisites

### Required
- **Python 3.11+** - The generator is written in Python
- **pip** - Python package manager

### Optional (for full stack)
- **Docker** - For containerized deployment
- **Docker Compose** - For running the complete observability stack

## Installation Methods

### Method 1: Local Development (Quick Start)

Perfect for development and testing on your local machine.

#### Step 1: Clone or Download

```bash
# If you have the repository
cd synthetic_metrics_generator

# Or download and extract the files
```

#### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

#### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

#### Step 4: Create Configuration

```bash
# Copy the example config
cp configs/baseline.example.yaml configs/baseline.yaml

# Edit if needed (optional for local testing)
# The defaults work fine for getting started
```

#### Step 5: Run the Generator

```bash
python -m src.main --config configs/baseline.yaml
```

You should see output like:
```
INFO | Synthetic Metrics Generator
INFO | Configuration loaded from: configs/baseline.yaml
INFO | Tick interval: 1s
INFO | Metrics configured: 4
INFO | Prometheus exporter listening on 0.0.0.0:8000/metrics
INFO | OTEL exporter initialized, pushing to localhost:4317
INFO | Generator engine started
```

#### Step 6: Verify Metrics

Open your browser or use curl:

```bash
# View Prometheus metrics
curl http://localhost:8000/metrics

# Check generator status
curl http://localhost:8081/status
```

You should see metrics like:
```
# HELP synthetic_prom_requests_total Generated counter metric: requests_total
# TYPE synthetic_prom_requests_total counter
synthetic_prom_requests_total{endpoint="/",instance="i-01",region="us-east-1"} 42.0
synthetic_prom_requests_total{endpoint="/",instance="i-02",region="us-east-1"} 38.0
...
```

### Method 2: Docker Compose (Recommended for Full Stack)

Run the complete stack with Prometheus, Grafana, and OTEL Collector.

#### Step 1: Create Configuration Files

```bash
# Create configs from examples
cp configs/baseline.example.yaml configs/baseline.yaml
cp compose/prometheus.example.yml compose/prometheus.yml
cp compose/alloy-config.example.alloy compose/alloy-config.alloy

# Edit alloy-config.alloy and prometheus.yml if you want to send to cloud backends
# Otherwise, the local setup works out of the box
```

#### Step 2: Start the Stack

```bash
docker-compose -f compose/docker-compose.yaml up -d
```

This starts:
- **Generator** - Generating metrics
- **Prometheus** - Scraping and storing metrics
- **Grafana** - Visualizing metrics
- **Alloy** - OTEL Collector for OTLP metrics

#### Step 3: Access the Services

- **Generator Metrics**: http://localhost:8000/metrics
- **Generator API**: http://localhost:8081/status
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Alloy UI**: http://localhost:12345

#### Step 4: View Metrics in Grafana

1. Open Grafana at http://localhost:3000
2. Login with `admin` / `admin`
3. Go to **Explore**
4. Select **Prometheus** datasource
5. Try queries like:
   ```promql
   rate(synthetic_prom_requests_total[1m])
   synthetic_prom_cpu_usage
   histogram_quantile(0.95, rate(synthetic_prom_req_latency_seconds_bucket[1m]))
   ```

## First Queries

### Prometheus Queries

```promql
# Request rate per endpoint
rate(synthetic_prom_requests_total[1m])

# Average CPU usage by region
avg by (region) (synthetic_prom_cpu_usage)

# 95th percentile latency
histogram_quantile(0.95, rate(synthetic_prom_req_latency_seconds_bucket[1m]))

# Total active series
count({__name__=~"synthetic_prom_.*"})
```

### Generator Self-Monitoring

```promql
# Points generated per second
rate(synthetic_prom_gen_points_total[1m])

# Generator tick duration (how long each tick takes)
synthetic_prom_gen_tick_duration_seconds

# Active series count
synthetic_prom_gen_active_series
```

## Verifying Dual Export

The generator exports to **both** Prometheus and OTEL simultaneously.

### Check Prometheus Export

```bash
curl http://localhost:8000/metrics | grep synthetic_prom_requests_total
```

### Check OTEL Export

If using Docker Compose with Alloy:

1. Open Alloy UI: http://localhost:12345
2. Navigate to Components
3. Check `otelcol.receiver.otlp` - should show metrics received
4. Check metrics are being forwarded

Or check the logs:
```bash
docker-compose -f compose/docker-compose.yaml logs alloy | grep -i metric
```

## Quick Configuration Changes

### Change Metric Generation Rate

Edit `configs/baseline.yaml`:

```yaml
global:
  tick_interval_s: 5  # Change from 1 to 5 seconds
```

Restart the generator to apply changes.

### Add More Endpoints

Edit `configs/baseline.yaml`:

```yaml
metrics:
  - name: requests_total
    labels:
      endpoint:
        values: ["/", "/login", "/search", "/checkout", "/api"]  # Added 2 more
```

This increases series count from 18 to 30.

### Change Log Level

Without restart, use the API:

```bash
curl -X POST http://localhost:8081/control/loglevel \
  -H 'Content-Type: application/json' \
  -d '{"level": "DEBUG"}'
```

## Testing Runtime Controls

### Trigger a Load Spike

The generator supports runtime spikes to simulate traffic increases without changing configuration.

**Step 1: Check available metrics**

```bash
curl -s http://localhost:8081/status | jq '.available_metrics'
```

Returns:
```json
[
  "requests_total",
  "cpu_usage",
  "req_latency_seconds",
  "payload_size_bytes"
]
```

**Step 2: Trigger a spike**

Use the **base metric name** (without the `synthetic_prom_` or `synthetic_otel_` prefix):

```bash
# Trigger a 10x spike for 2 minutes
curl -X POST http://localhost:8081/control/spike \
  -H 'Content-Type: application/json' \
  -d '{
    "metric": "requests_total",
    "multiplier": 10,
    "duration_s": 120
  }'
```

**Step 3: Verify the spike**

```bash
# Check active spikes
curl -s http://localhost:8081/status | jq '.active_spikes'

# Watch metrics increase in Prometheus
# Open http://localhost:9090 and query:
# rate(synthetic_prom_requests_total[1m])
```

**Step 4: Wait for expiry**

The spike automatically expires after the specified duration. Metrics return to normal levels.

**Common Spike Examples:**

```bash
# 5x traffic spike for 5 minutes
{"metric": "requests_total", "multiplier": 5, "duration_s": 300}

# 50% CPU reduction (testing low load)
{"metric": "cpu_usage", "multiplier": 0.5, "duration_s": 180}

# 100x latency spike (simulating degradation)
{"metric": "req_latency_seconds", "multiplier": 100, "duration_s": 60}
```

**Important Notes:**
- ✅ Use base metric name (e.g., `"requests_total"`)
- ❌ Don't use prefixed name (e.g., `"synthetic_prom_requests_total"`)
- The spike applies to **all series** of that metric (all label combinations)
- Multiple spikes can be active simultaneously on different metrics
- Spikes cannot be cancelled early - they must expire naturally

## Troubleshooting

### "Address already in use" Error

Port 8000 or 8081 is already taken:

```bash
# Check what's using the port
lsof -i :8000
lsof -i :8081

# Change ports in config
exporters:
  prometheus:
    port: 8001  # Changed from 8000
```

### OTEL Connection Refused

If you see "connection refused" for OTEL endpoint:

1. **Local mode**: Make sure you have an OTEL collector running on `localhost:4317`
2. **Docker mode**: Use `alloy:4317` as the endpoint (container name)
3. **Disable OTEL**: Set `enabled: false` in config

```yaml
exporters:
  otel:
    enabled: false  # Disable if you don't have a collector
```

### No Metrics Appearing

Check the generator logs:

```bash
# Local mode
# Logs appear in terminal

# Docker mode
docker-compose logs generator
```

Look for errors like:
- Configuration validation errors
- Export errors
- Connection issues

### High Memory Usage

For the baseline config, memory usage should be ~150MB. If higher:

1. Check `series_cap` in your profile
2. Reduce number of metrics
3. Increase `tick_interval_s`

```bash
# Check memory usage
docker stats generator  # Docker mode
ps aux | grep python    # Local mode
```

## Next Steps

Now that you have the generator running:

1. **[Configuration Guide](03-configuration.md)** - Learn about all configuration options
2. **[Features](04-features.md)** - Explore all features and algorithms
3. **[Control API](05-control-api.md)** - Use runtime controls
4. **[Metrics Reference](06-metrics-reference.md)** - Understand generated metrics

## Quick Tips

- Start with `baseline.yaml` - it's safe and uses minimal resources
- Use `docker-compose logs -f generator` to watch logs in real-time
- The generator is deterministic - same seed = same patterns
- Self-monitoring metrics use `gen_` prefix
- Ctrl+C to stop gracefully (local mode)
- `docker-compose down` to stop all services (Docker mode)

## Common First Tasks

### 1. Generate Traffic Spike

```bash
curl -X POST http://localhost:8081/control/spike \
  -H 'Content-Type: application/json' \
  -d '{
    "metric": "requests_total",
    "multiplier": 5,
    "duration_s": 300
  }'
```

### 2. Check Generator Health

```bash
curl http://localhost:8081/healthz
```

### 3. View Current Status

```bash
curl http://localhost:8081/status | jq
```

### 4. Export Metrics to File

```bash
curl http://localhost:8000/metrics > metrics_snapshot.txt
```

You're now ready to explore the full capabilities of the generator!


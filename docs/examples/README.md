# Configuration Examples

This directory contains example configurations for common use cases.

## Available Examples

All example configurations are in the `configs/` directory at the repository root.

### baseline.example.yaml

**Use Case**: Getting started, learning, basic testing

**Characteristics**:
- Low cardinality (~100 series)
- All metric types (counter, gauge, histogram, summary)
- Minimal resource usage (~150MB RAM)
- Fast tick duration (<10ms)

**Series Breakdown**:
- Counter: 18 series (2 regions × 3 instances × 3 endpoints)
- Gauge: 6 series (2 regions × 3 instances)
- Histogram: 48 series (2 regions × 3 instances × 8 buckets)
- Summary: 30 series (2 regions × 3 instances × 5 quantiles)

**Setup**:
```bash
cp configs/baseline.example.yaml configs/baseline.yaml
python -m src.main --config configs/baseline.yaml
```

**Queries**:
```promql
# Request rate
rate(synthetic_prom_requests_total[1m])

# CPU usage
synthetic_prom_cpu_usage

# Latency p95
histogram_quantile(0.95, rate(synthetic_prom_req_latency_seconds_bucket[1m]))
```

---

### high_cardinality.example.yaml

**Use Case**: Stress testing, cardinality limits, backend performance

**Characteristics**:
- High cardinality (150,000 series)
- Simulates per-user metrics
- Heavy resource usage (~2.5GB RAM)
- Longer tick duration (~800ms)

**Series Breakdown**:
- Counter: 150k series (100k users × 5 endpoints × 3 regions, sampled)
- Histogram: 1.35M histogram series
- Gauge: 150k series

**⚠️ Warning**: Requires adequate resources!

**Setup**:
```bash
cp configs/high_cardinality.example.yaml configs/high_cardinality.yaml
# Adjust series_cap based on your system
vim configs/high_cardinality.yaml
python -m src.main --config configs/high_cardinality.yaml
```

**Use For**:
- Testing cardinality limits
- Backend stress testing
- Performance benchmarking
- Understanding cardinality impact

---

### production_sim.example.yaml

**Use Case**: Realistic production simulation, demo environments

**Characteristics**:
- Moderate cardinality (~5,500 series)
- Realistic patterns (diurnal, bimodal latencies)
- Multiple services and availability zones
- Moderate resource usage (~500MB RAM)

**Series Breakdown**:
- Counter: 2,700 series (3 services × 20 instances × 3 AZs × 5 routes × 3 statuses)
- Histogram: 1,800 series (with bimodal distribution)
- Gauge: 180 series (sawtooth pattern)
- Summary: 900 series

**Setup**:
```bash
cp configs/production_sim.example.yaml configs/production_sim.yaml
python -m src.main --config configs/production_sim.yaml
```

**Features**:
- Diurnal traffic patterns (35% variation)
- Bimodal latency (90% fast, 10% slow)
- Sawtooth queue patterns
- Realistic label combinations

**Queries**:
```promql
# HTTP request rate by route
sum by (route) (rate(synthetic_prom_http_requests_total[1m]))

# Request rate by status code
sum by (status) (rate(synthetic_prom_http_requests_total[1m]))

# Latency percentiles
histogram_quantile(0.95, rate(synthetic_prom_http_request_duration_seconds_bucket[1m]))
histogram_quantile(0.99, rate(synthetic_prom_http_request_duration_seconds_bucket[1m]))

# Queue depth pattern
synthetic_prom_queue_depth
```

---

## Customizing Examples

### 1. Change Cardinality

Adjust series count by modifying label values:

```yaml
profiles:
  app:
    labels:
      instance:
        range: [1, 50]  # Increase from 20 to 50
```

Or adjust the series cap:

```yaml
profiles:
  app:
    series_cap: 5000  # Limit total series
```

### 2. Change Generation Rate

Adjust tick interval:

```yaml
global:
  tick_interval_s: 5  # Generate every 5 seconds instead of 1
```

### 3. Change Metric Patterns

Modify algorithm parameters:

```yaml
metrics:
  - name: requests_total
    algorithm: poisson
    base_rate: 50      # Increase from 5 to 50 req/s
    diurnal_amp: 0.5   # Increase variation to 50%
```

### 4. Add More Metrics

Copy and modify existing metric definitions:

```yaml
metrics:
  # ... existing metrics ...
  
  # Add new metric
  - name: cache_hits_total
    type: counter
    profile: app
    algorithm: poisson
    base_rate: 100
```

### 5. Change Export Destinations

Update exporter endpoints:

```yaml
exporters:
  otel:
    endpoint: "my-collector:4317"
    prefix: "myapp_"
```

## Common Patterns

### Pattern 1: Gradual Load Increase

Create configs with increasing cardinality:

```bash
# Start with baseline
python -m src.main --config configs/baseline.yaml

# After 10 minutes, switch to medium
python -m src.main --config configs/production_sim.yaml

# After 10 more minutes, switch to high
python -m src.main --config configs/high_cardinality.yaml
```

### Pattern 2: A/B Testing

Run two generators with different prefixes:

```yaml
# config-a.yaml
exporters:
  prometheus:
    port: 8000
    prefix: "test_a_"
  otel:
    prefix: "test_a_"

# config-b.yaml
exporters:
  prometheus:
    port: 8001
    prefix: "test_b_"
  otel:
    prefix: "test_b_"
```

### Pattern 3: Multi-Region Simulation

Create configs for different regions:

```yaml
# us-east.yaml
profiles:
  app:
    labels:
      region:
        values: ["us-east-1"]
      az:
        values: ["a", "b", "c"]

# eu-west.yaml
profiles:
  app:
    labels:
      region:
        values: ["eu-west-1"]
      az:
        values: ["a", "b", "c"]
```

Run multiple generators:
```bash
python -m src.main --config configs/us-east.yaml &
python -m src.main --config configs/eu-west.yaml &
```

### Pattern 4: Spike Testing

Use baseline config + Control API:

```bash
# Start generator
python -m src.main --config configs/baseline.yaml

# Trigger spike via API
curl -X POST http://localhost:8081/control/spike \
  -H 'Content-Type: application/json' \
  -d '{
    "metric": "requests_total",
    "multiplier": 10,
    "duration_s": 300
  }'
```

## Performance Guidelines

### Resource Estimation

| Series Count | Memory | CPU | Tick Duration |
|--------------|--------|-----|---------------|
| 100 | 150 MB | 0.1 core | <10ms |
| 1,000 | 200 MB | 0.2 core | ~20ms |
| 10,000 | 500 MB | 0.5 core | ~100ms |
| 100,000 | 2 GB | 2 cores | ~500ms |
| 150,000 | 2.5 GB | 3 cores | ~800ms |

### Optimization Tips

1. **Increase tick_interval_s** if tick duration > tick interval
2. **Reduce series_cap** if memory usage is high
3. **Use hash sampling** for better distribution
4. **Disable unused exporters** to reduce overhead
5. **Increase export_interval_s** for OTEL to reduce network traffic

## Validation

### Check Configuration

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('configs/baseline.yaml'))"

# Check series count
curl http://localhost:8081/status | jq '.total_series'

# Monitor performance
curl http://localhost:8000/metrics | grep gen_tick_duration
```

### Verify Metrics

```bash
# Check Prometheus metrics
curl http://localhost:8000/metrics | grep synthetic_prom_requests_total

# Count series
curl http://localhost:8000/metrics | grep -c synthetic_prom_requests_total

# Check OTEL export (via Alloy UI)
open http://localhost:12345
```

## Troubleshooting

### "Too many series" Error

Reduce `series_cap`:
```yaml
profiles:
  app:
    series_cap: 1000  # Lower this value
```

### High Memory Usage

1. Check actual series count
2. Reduce cardinality
3. Increase tick interval

### Slow Tick Duration

1. Increase `tick_interval_s`
2. Reduce series count
3. Allocate more CPU

### OTEL Connection Refused

Check endpoint configuration:
```yaml
exporters:
  otel:
    endpoint: "localhost:4317"  # Verify this is correct
    insecure: true              # Use true for local testing
```

## Next Steps

- **[Configuration Reference](../user-guide/03-configuration.md)** - Complete config documentation
- **[Features](../user-guide/04-features.md)** - Understanding all features
- **[Getting Started](../user-guide/02-getting-started.md)** - Quick start guide


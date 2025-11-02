# Configuration Reference

Complete reference for configuring the Synthetic Metrics Generator.

## Configuration File Structure

The generator uses YAML configuration files with the following top-level sections:

```yaml
global:          # Global settings
exporters:       # Prometheus and OTEL export configuration
profiles:        # Cardinality profiles (label combinations)
metrics:         # Metric definitions
```

## Global Settings

Controls generator-wide behavior.

```yaml
global:
  tick_interval_s: 1      # How often to generate new values (seconds)
  seed: 42                # Random seed for reproducibility
  log_level: INFO         # Logging level
  log_format: text        # Log format: text or json
  control_api_port: 8081  # Port for control API
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tick_interval_s` | float | 1 | Interval between metric generation cycles |
| `seed` | int | 42 | Random seed for deterministic generation |
| `log_level` | string | INFO | DEBUG, INFO, WARNING, ERROR |
| `log_format` | string | text | text or json |
| `control_api_port` | int | 8081 | HTTP API port |

## Exporters

Configure Prometheus and OpenTelemetry exporters.

### Prometheus Exporter

```yaml
exporters:
  prometheus:
    enabled: true
    port: 8000
    prefix: "synthetic_prom_"
    bind_address: "0.0.0.0"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `enabled` | bool | Yes | Enable/disable Prometheus export |
| `port` | int | Yes | HTTP port for /metrics endpoint |
| `prefix` | string | Yes | Prefix for all metric names |
| `bind_address` | string | No | Bind address (default: 0.0.0.0) |

**Metric Naming**: Use underscores in prefix for PromQL compatibility (e.g., `synthetic_prom_`)

### OpenTelemetry Exporter

```yaml
exporters:
  otel:
    enabled: true
    endpoint: "localhost:4317"
    insecure: true
    prefix: "synthetic_otel_"
    export_interval_s: 10
    protocol: grpc
    resource:
      service.name: synthetic-metrics-generator
      deployment.environment: dev
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `enabled` | bool | Yes | Enable/disable OTEL export |
| `endpoint` | string | Yes | OTLP collector endpoint (host:port) |
| `insecure` | bool | No | Use insecure connection (no TLS) |
| `prefix` | string | Yes | Prefix for all metric names |
| `export_interval_s` | int | No | Push interval in seconds (default: 10) |
| `protocol` | string | No | grpc or http (default: grpc) |
| `resource` | map | No | OTEL resource attributes |

**Metric Naming**: Use underscores in prefix for PromQL compatibility (e.g., `synthetic_otel_`)

**Note**: Some backends (like SigNoz) add suffixes like `.bucket`, `.sum`, `.count` to histogram metrics, which can break PromQL queries if your metric names contain dots.

## Profiles

Profiles define label combinations and cardinality limits.

```yaml
profiles:
  low:
    labels:
      region:
        values: ["us-east-1", "eu-west-1"]
      instance:
        range: [1, 3]
        fmt: "i-%02d"
    series_cap: 1000
    sampling_strategy: first_n
```

### Label Definition

#### Static Values

```yaml
labels:
  region:
    values: ["us-east-1", "eu-west-1", "ap-south-1"]
```

#### Range-Based

```yaml
labels:
  instance:
    range: [1, 100]      # Generate 100 instances
    fmt: "i-%02d"        # Format: i-01, i-02, ..., i-99
```

Format strings use Python's % formatting:
- `%d` - Integer
- `%02d` - Zero-padded 2-digit integer
- `%05d` - Zero-padded 5-digit integer
- `%s` - String

### Cardinality Control

| Parameter | Type | Description |
|-----------|------|-------------|
| `series_cap` | int | Maximum number of series to generate |
| `sampling_strategy` | string | How to limit series: `first_n` or `hash` |

**Sampling Strategies**:
- `first_n`: Take first N series (deterministic, simple)
- `hash`: Hash-based sampling (deterministic, distributed)

### Series Count Calculation

Series count = Product of all label cardinalities

Example:
```yaml
labels:
  region: ["us", "eu"]           # 2 values
  instance: range [1, 10]        # 10 values
  endpoint: ["/", "/api"]        # 2 values
```

Total possible series: 2 × 10 × 2 = **40 series**

If `series_cap: 30`, only 30 series will be generated.

## Metrics

Define the metrics to generate.

### Basic Structure

```yaml
metrics:
  - name: metric_name
    type: counter|gauge|histogram|summary
    profile: profile_name
    algorithm: algorithm_name
    # ... algorithm-specific parameters
    labels:  # Optional: additional labels beyond profile
      label_name:
        values: [...]
```

### Metric Types

#### Counter

Monotonically increasing values.

```yaml
- name: requests_total
  type: counter
  profile: low
  algorithm: poisson
  base_rate: 5
  diurnal_amp: 0.2
```

**Algorithms**:

1. **poisson**: Poisson-distributed increments
   ```yaml
   algorithm: poisson
   base_rate: 5          # Average increments per tick
   diurnal_amp: 0.2      # Daily variation (0-1)
   ```

2. **constant**: Fixed increment
   ```yaml
   algorithm: constant
   increment: 1          # Fixed increment per tick
   ```

#### Gauge

Point-in-time values.

```yaml
- name: cpu_usage
  type: gauge
  profile: low
  algorithm: random_walk
  start: 0.5
  step: 0.02
  clamp: [0.0, 1.0]
```

**Algorithms**:

1. **random_walk**: Brownian motion
   ```yaml
   algorithm: random_walk
   start: 0.5            # Starting value
   step: 0.02            # Max change per tick
   clamp: [0.0, 1.0]     # Min/max bounds
   ```

2. **sine**: Sinusoidal wave
   ```yaml
   algorithm: sine
   amplitude: 0.5        # Wave amplitude
   period_s: 3600        # Period in seconds
   offset: 0.5           # Vertical offset
   ```

3. **bernoulli**: Binary 0/1 values
   ```yaml
   algorithm: bernoulli
   p: 0.9                # Probability of 1
   ```

4. **sawtooth**: Linear ramp
   ```yaml
   algorithm: sawtooth
   min: 0
   max: 1000
   period_s: 600         # Ramp duration
   ```

#### Histogram

Distribution with buckets.

```yaml
- name: request_duration_seconds
  type: histogram
  profile: low
  buckets: [0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
  algorithm: lognormal
  mu: -2.0
  sigma: 0.9
```

**Bucket Definition**:
```yaml
buckets: [0.01, 0.05, 0.1, 0.5, 1.0]  # Upper bounds
# Automatically includes +Inf bucket
```

**Algorithms**:

1. **lognormal**: Log-normal distribution
   ```yaml
   algorithm: lognormal
   mu: -2.0              # Log mean
   sigma: 0.9            # Log std dev
   ```

2. **exponential**: Exponential distribution
   ```yaml
   algorithm: exponential
   lambda: 0.5           # Rate parameter
   ```

3. **mixture**: Mixture of distributions
   ```yaml
   algorithm: mixture
   components:
     - type: lognormal
       weight: 0.9       # 90% of samples
       mu: -3.0
       sigma: 0.6
     - type: lognormal
       weight: 0.1       # 10% of samples
       mu: -0.5
       sigma: 0.8
   ```

#### Summary

Distribution with quantiles (Prometheus only).

```yaml
- name: payload_size_bytes
  type: summary
  profile: low
  objectives:
    0.5: 0.01           # p50 with 1% error
    0.9: 0.01           # p90 with 1% error
    0.99: 0.001         # p99 with 0.1% error
  algorithm: lognormal
  mu: 7.0
  sigma: 1.2
```

**Note**: OTEL doesn't have native Summary type, so these are exported as Histograms.

### Additional Labels

Add labels beyond the profile:

```yaml
- name: http_requests_total
  type: counter
  profile: app
  algorithm: poisson
  base_rate: 10
  labels:
    method:
      values: ["GET", "POST", "PUT", "DELETE"]
    status:
      values: ["200", "400", "404", "500"]
```

This multiplies series count:
- Profile series × method (4) × status (4) = Profile series × 16

## Complete Example

```yaml
global:
  tick_interval_s: 1
  seed: 42
  log_level: INFO
  control_api_port: 8081

exporters:
  prometheus:
    enabled: true
    port: 8000
    prefix: "app_"
  
  otel:
    enabled: true
    endpoint: "localhost:4317"
    insecure: true
    prefix: "app_"
    export_interval_s: 10

profiles:
  production:
    labels:
      service:
        values: ["api", "worker"]
      instance:
        range: [1, 5]
        fmt: "i-%02d"
      az:
        values: ["a", "b"]
    series_cap: 1000

metrics:
  # Counter: HTTP requests
  - name: http_requests_total
    type: counter
    profile: production
    algorithm: poisson
    base_rate: 20
    diurnal_amp: 0.3
    labels:
      status:
        values: ["200", "500"]
  
  # Gauge: CPU usage
  - name: cpu_usage_percent
    type: gauge
    profile: production
    algorithm: random_walk
    start: 0.4
    step: 0.05
    clamp: [0.0, 1.0]
  
  # Histogram: Request latency
  - name: http_duration_seconds
    type: histogram
    profile: production
    buckets: [0.01, 0.05, 0.1, 0.5, 1.0]
    algorithm: lognormal
    mu: -3.0
    sigma: 0.8
```

## Configuration Tips

### 1. Start Small
Begin with low cardinality (100-1000 series) and increase gradually.

### 2. Use Prefixes Wisely
- Use underscores for PromQL compatibility
- Use descriptive prefixes to avoid conflicts
- Keep prefixes short

### 3. Monitor Resource Usage
```promql
# Check generator performance
synthetic_prom_gen_tick_duration_seconds
synthetic_prom_gen_active_series
```

### 4. Test Configuration
```bash
# Validate config without running
python -m src.main --config configs/test.yaml --validate
```

### 5. Use Realistic Patterns
- `poisson` for requests
- `lognormal` for latencies
- `random_walk` for resource usage
- `diurnal_amp` for daily patterns

## Next Steps

- **[Features](04-features.md)** - Detailed feature explanations
- **[Control API](05-control-api.md)** - Runtime controls
- **[Examples](../examples/)** - Example configurations


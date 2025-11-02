# Features

Detailed explanation of all Synthetic Metrics Generator features.

## Dual Export

The generator's primary feature: **identical metrics exported to both Prometheus and OpenTelemetry simultaneously**.

### How It Works

```
┌─────────────────────────────────────┐
│ Generator Engine                     │
│ Generates value: 42.5               │
└──────────────┬──────────────────────┘
               │
      ┌────────┴────────┐
      │                 │
      ▼                 ▼
┌──────────┐      ┌──────────┐
│Prometheus│      │   OTEL   │
│ Gauge    │      │ Gauge    │
│ .set(42.5)│      │.record(42.5)│
└──────────┘      └──────────┘
```

**Same timestamp, same value, same labels** - perfect for comparing backends.

### Use Cases

1. **Migration Validation**: Verify both systems show identical data
2. **Backend Comparison**: Compare query performance, storage, costs
3. **Parity Testing**: Ensure alerting rules work the same way
4. **A/B Testing**: Test new backend before full migration

### Configuration

```yaml
exporters:
  prometheus:
    enabled: true      # Can disable independently
    prefix: "prom_"
  
  otel:
    enabled: true      # Can disable independently
    prefix: "otel_"
```

## Metric Types

### Counter

Monotonically increasing values (never decreases).

**Examples**: Request counts, error counts, bytes sent

```yaml
- name: requests_total
  type: counter
  algorithm: poisson
  base_rate: 5
```

**Behavior**:
- Starts at 0
- Increases each tick based on algorithm
- Prometheus: Exported as Counter
- OTEL: Exported as Sum (monotonic)

**Best Practices**:
- Use `_total` suffix by convention
- Use `poisson` algorithm for realistic request patterns
- Add `diurnal_amp` for daily traffic variation

### Gauge

Point-in-time values (can increase or decrease).

**Examples**: CPU usage, memory, queue depth, temperature

```yaml
- name: cpu_usage
  type: gauge
  algorithm: random_walk
  start: 0.5
  step: 0.02
  clamp: [0.0, 1.0]
```

**Behavior**:
- Can go up or down
- Represents current state
- Prometheus: Exported as Gauge
- OTEL: Exported as Gauge

**Best Practices**:
- Use `random_walk` for resource metrics
- Use `sine` for cyclical patterns
- Use `bernoulli` for binary states (0/1)
- Always set `clamp` for bounded values

### Histogram

Distribution of values with predefined buckets.

**Examples**: Request latencies, response sizes, processing times

```yaml
- name: request_duration_seconds
  type: histogram
  buckets: [0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
  algorithm: lognormal
  mu: -2.0
  sigma: 0.9
```

**Behavior**:
- Generates observations
- Counts observations per bucket
- Tracks sum and count
- Prometheus: Histogram with `_bucket`, `_sum`, `_count`
- OTEL: Histogram with same structure

**Best Practices**:
- Use `lognormal` for latencies (realistic distribution)
- Define buckets matching your SLOs
- Include enough buckets for accurate quantiles
- Use `mixture` for bimodal distributions (fast + slow requests)

**Bucket Selection**:
```yaml
# For latencies (milliseconds to seconds)
buckets: [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]

# For sizes (bytes to megabytes)
buckets: [1000, 10000, 100000, 1000000, 10000000]
```

### Summary

Distribution with client-side quantile calculation (Prometheus only).

**Examples**: Similar to histogram but with quantiles

```yaml
- name: payload_size_bytes
  type: summary
  objectives:
    0.5: 0.01      # p50 with 1% error
    0.9: 0.01      # p90 with 1% error
    0.99: 0.001    # p99 with 0.1% error
  algorithm: lognormal
  mu: 7.0
  sigma: 1.2
```

**Behavior**:
- Calculates quantiles client-side
- Exports quantiles, sum, count
- Prometheus: Summary with quantile labels
- OTEL: Converted to Histogram (no native Summary)

**Histogram vs Summary**:
- Histogram: Server-side quantiles, aggregatable
- Summary: Client-side quantiles, not aggregatable
- **Recommendation**: Use Histogram for most cases

## Algorithms

### Counter Algorithms

#### Poisson

Realistic request arrival patterns.

```yaml
algorithm: poisson
base_rate: 5          # Average arrivals per tick
diurnal_amp: 0.2      # Daily variation (0-1)
```

**Characteristics**:
- Random but realistic
- Models independent events
- Can have bursts
- Diurnal modulation for time-of-day patterns

**When to Use**: HTTP requests, API calls, events

#### Constant

Fixed increment per tick.

```yaml
algorithm: constant
increment: 1
```

**When to Use**: Testing, debugging, predictable patterns

### Gauge Algorithms

#### Random Walk

Brownian motion with optional bounds.

```yaml
algorithm: random_walk
start: 0.5            # Starting value
step: 0.02            # Max change per tick
clamp: [0.0, 1.0]     # Bounds
```

**Characteristics**:
- Smooth changes
- Can trend up or down
- Realistic for resource metrics

**When to Use**: CPU, memory, disk usage

#### Sine

Sinusoidal wave pattern.

```yaml
algorithm: sine
amplitude: 0.3        # Wave height
period_s: 3600        # Period (1 hour)
offset: 0.5           # Center point
```

**Characteristics**:
- Perfectly cyclical
- Predictable
- Good for testing

**When to Use**: Daily patterns, testing, demonstrations

#### Bernoulli

Binary 0 or 1 values.

```yaml
algorithm: bernoulli
p: 0.9                # Probability of 1
```

**When to Use**: Cache hits, boolean flags, on/off states

#### Sawtooth

Linear ramp up, then reset.

```yaml
algorithm: sawtooth
min: 0
max: 1000
period_s: 600         # 10-minute cycle
```

**When to Use**: Queue buildup and drain, batch processing

### Histogram/Summary Algorithms

#### Lognormal

Log-normal distribution (most common for latencies).

```yaml
algorithm: lognormal
mu: -2.0              # Log mean (controls center)
sigma: 0.9            # Log std dev (controls spread)
```

**Characteristics**:
- Right-skewed (long tail)
- Realistic for latencies
- Most values near mean, few outliers

**Parameter Guide**:
- `mu = -3.0`: ~50ms average
- `mu = -2.0`: ~135ms average
- `mu = -1.0`: ~370ms average
- Larger `sigma`: More spread/variance

#### Exponential

Exponential distribution.

```yaml
algorithm: exponential
lambda: 0.5           # Rate parameter
```

**When to Use**: Inter-arrival times, simple distributions

#### Mixture

Mixture of multiple distributions.

```yaml
algorithm: mixture
components:
  - type: lognormal
    weight: 0.9       # 90% fast requests
    mu: -3.0
    sigma: 0.6
  - type: lognormal
    weight: 0.1       # 10% slow requests
    mu: -0.5
    sigma: 0.8
```

**When to Use**: Bimodal latencies (cache hit/miss, fast/slow paths)

## Cardinality Management

### Understanding Cardinality

**Cardinality** = Number of unique time series

```yaml
labels:
  region: ["us", "eu", "asia"]     # 3 values
  instance: range [1, 10]          # 10 values
  endpoint: ["/", "/api"]          # 2 values
```

Cardinality: 3 × 10 × 2 = **60 series**

### Series Cap

Limit total series to prevent runaway cardinality:

```yaml
profiles:
  high:
    series_cap: 10000    # Maximum 10k series
    sampling_strategy: hash
```

### Sampling Strategies

#### first_n

Take first N series (simple, deterministic):

```yaml
sampling_strategy: first_n
series_cap: 1000
```

**Behavior**: Generates label combinations in order, takes first 1000.

#### hash

Hash-based sampling (distributed, deterministic):

```yaml
sampling_strategy: hash
series_cap: 1000
```

**Behavior**: Hashes each label combination, keeps if hash < threshold.

**Advantage**: More evenly distributed across label space.

### Cardinality Best Practices

1. **Start Low**: Begin with 100-1000 series
2. **Monitor**: Watch `gen_active_series` metric
3. **Set Caps**: Always set `series_cap` to prevent accidents
4. **Test Gradually**: Increase cardinality in steps
5. **Know Your Limits**: Test backend cardinality limits

## Deterministic Generation

### Seed-Based

Same seed = same patterns every time:

```yaml
global:
  seed: 42
```

**Benefits**:
- Reproducible tests
- Compare runs
- Debug issues
- Regression testing

**Different Seeds**:
```yaml
seed: 42    # Pattern A
seed: 123   # Pattern B (different but reproducible)
```

## Self-Monitoring

The generator monitors itself with `gen_*` metrics.

### Available Metrics

```promql
# Points generated per metric
synthetic_prom_gen_points_total{metric="requests_total"}

# Export errors
synthetic_prom_gen_export_errors_total{exporter="prometheus",metric="..."}

# Tick duration (how long each cycle takes)
synthetic_prom_gen_tick_duration_seconds

# Active series count
synthetic_prom_gen_active_series{metric="requests_total"}

# Export queue depth
synthetic_prom_gen_export_queue_depth{exporter="otel"}
```

### Monitoring the Generator

```promql
# Generation rate
rate(synthetic_prom_gen_points_total[1m])

# 95th percentile tick duration
histogram_quantile(0.95, rate(synthetic_prom_gen_tick_duration_seconds_bucket[1m]))

# Total active series
sum(synthetic_prom_gen_active_series)

# Export error rate
rate(synthetic_prom_gen_export_errors_total[5m])
```

### Performance Indicators

- **Tick duration < tick_interval**: Generator keeping up ✅
- **Tick duration > tick_interval**: Generator falling behind ⚠️
- **Export errors > 0**: Connection or backend issues ❌
- **Queue depth growing**: Export backlog ⚠️

## Diurnal Patterns

Simulate daily traffic variations:

```yaml
- name: requests_total
  type: counter
  algorithm: poisson
  base_rate: 10
  diurnal_amp: 0.3    # ±30% variation
```

**Behavior**:
- Low traffic at night
- High traffic during business hours
- Smooth sinusoidal variation
- 24-hour cycle

**Amplitude Guide**:
- `0.0`: No variation (flat)
- `0.2`: Subtle variation (±20%)
- `0.5`: Moderate variation (±50%)
- `1.0`: Extreme variation (0-200%)

## Runtime Controls

See [Control API](05-control-api.md) for details.

**Quick Examples**:

```bash
# Trigger traffic spike
curl -X POST localhost:8081/control/spike \
  -d '{"metric":"requests_total","multiplier":5,"duration_s":300}'

# Change log level
curl -X POST localhost:8081/control/loglevel \
  -d '{"level":"DEBUG"}'

# Check status
curl localhost:8081/status
```

## Next Steps

- **[Control API](05-control-api.md)** - Runtime control endpoints
- **[Metrics Reference](06-metrics-reference.md)** - All generated metrics
- **[Deployment](07-deployment.md)** - Deployment options


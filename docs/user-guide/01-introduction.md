# Introduction to Synthetic Metrics Generator

## ⚠️ Disclaimer

**This application was generated with assistance from Large Language Models (LLMs) for rapid prototyping and testing purposes.**

While functional and useful for its intended purpose, please be aware:

- ✅ **Recommended for**: Testing, learning, prototyping, and comparing observability backends
- ❌ **Not recommended for**: Production deployments without thorough review and hardening
- ⚠️ Code has not been professionally audited
- ⚠️ May contain security vulnerabilities
- ⚠️ Designed primarily for testing/development environments
- ⚠️ Use at your own risk

**Contributions and improvements are welcome!** If you find issues or have suggestions, please open an issue or submit a pull request.

---

## What is This?

The **Synthetic Metrics Generator** is a Python-based tool that generates realistic, controllable metric workloads for testing and comparing observability backends. It's designed to help you:

- **Test** your monitoring infrastructure under various load conditions
- **Compare** different metric backends (Prometheus, Grafana Cloud, SigNoz, etc.)
- **Validate** metric parity between systems during migrations
- **Benchmark** performance and cardinality limits
- **Learn** about metrics, cardinality, and observability patterns

## Key Features

### 🔄 Dual Export
- Generates **identical metric data** to both Prometheus (pull) and OpenTelemetry (push) simultaneously
- Perfect for comparing backends or validating migrations
- Ensures data parity for accurate comparisons

### 📊 Multiple Metric Types
- **Counter**: Monotonically increasing values (requests, errors, etc.)
- **Gauge**: Point-in-time values (CPU usage, queue depth, etc.)
- **Histogram**: Distribution of values with buckets (latencies, sizes, etc.)
- **Summary**: Distribution with quantiles (similar to histogram)

### 🎲 Realistic Patterns
- **Poisson arrivals**: Realistic request rate patterns
- **Random walk**: CPU usage, memory, etc.
- **Lognormal distributions**: Latencies and payload sizes
- **Diurnal modulation**: Time-of-day traffic patterns
- **Mixture distributions**: Bimodal latencies (fast + slow requests)
- **Sawtooth patterns**: Queue buildup and drain cycles

### 🎚️ Configurable Cardinality
- Test from **low** (100 series) to **extremely high** (100k+ series) cardinality
- Understand cardinality limits of your backends
- Simulate realistic production label combinations
- Deterministic sampling for consistent tests

### 🎮 Runtime Controls
- HTTP API for triggering traffic spikes
- Reload configuration without restart
- Change log levels dynamically
- Health checks and status endpoints

### 📈 Self-Monitoring
- Built-in metrics for observing generator performance
- Track points generated, export errors, tick duration
- Monitor active series count and export queue depth

### 🔁 Deterministic Generation
- Seed-based generation for reproducible tests
- Same seed = same metric patterns every time
- Perfect for regression testing

## Use Cases

### 1. Backend Comparison
Compare performance, query capabilities, and resource usage between:
- Prometheus vs VictoriaMetrics
- Prometheus vs OpenTelemetry Collector
- Grafana Cloud vs SigNoz
- Self-hosted vs cloud-hosted solutions

### 2. Migration Validation
When migrating between observability backends:
- Generate identical data to both systems
- Validate metric parity
- Test query compatibility
- Verify alerting rules work the same way

### 3. Load Testing
Test your monitoring infrastructure:
- Gradually increase cardinality
- Find breaking points
- Measure query performance under load
- Validate auto-scaling behavior

### 4. Cardinality Analysis
Understand cardinality impact:
- Test different label combinations
- Measure memory and storage growth
- Validate cardinality limits
- Optimize label strategies

### 5. Learning and Experimentation
- Learn about metrics and observability
- Experiment with different metric types
- Understand histogram buckets and quantiles
- Practice PromQL and other query languages

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ Configuration (YAML)                                         │
│ - Metric definitions                                         │
│ - Cardinality profiles                                       │
│ - Export settings                                            │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Generator Engine                                             │
│ - Tick scheduler (configurable interval)                    │
│ - Deterministic value generation                            │
│ - Label space management                                     │
└─────────────────┬───────────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
┌──────────────┐    ┌──────────────┐
│ Prometheus   │    │ OpenTelemetry│
│ Exporter     │    │ Exporter     │
│              │    │              │
│ /metrics     │    │ OTLP gRPC    │
│ HTTP:8000    │    │ :4317        │
└──────────────┘    └──────────────┘
        │                   │
        ▼                   ▼
┌──────────────┐    ┌──────────────┐
│ Prometheus   │    │ OTEL         │
│ (scrape)     │    │ Collector    │
└──────────────┘    └──────────────┘
```

## How It Works

1. **Configuration**: Define metrics, cardinality, and algorithms in YAML
2. **Label Generation**: Generate label combinations based on profiles
3. **Value Generation**: Use algorithms to generate realistic values each tick
4. **Dual Export**: 
   - Prometheus: Expose metrics on HTTP endpoint for scraping
   - OTEL: Push metrics via OTLP protocol
5. **Self-Monitoring**: Track generator performance and health

## Quick Example

Generate 100 time series with realistic HTTP request patterns:

```yaml
metrics:
  - name: http_requests_total
    type: counter
    algorithm: poisson
    base_rate: 5              # 5 req/s average
    diurnal_amp: 0.2          # ±20% daily variation
    labels:
      endpoint: ["/", "/api"]
      region: ["us", "eu"]
      instance: ["i-01", "i-02"]
```

This creates:
- 2 endpoints × 2 regions × 2 instances = **8 time series**
- Each series increments ~5 times per second (Poisson distribution)
- Traffic varies by time of day (diurnal pattern)

## What's Next?

- **[Getting Started](02-getting-started.md)**: Install and run your first test
- **[Configuration](03-configuration.md)**: Complete configuration reference
- **[Features](04-features.md)**: Detailed feature explanations
- **[Control API](05-control-api.md)**: Runtime control endpoints
- **[Metrics Reference](06-metrics-reference.md)**: All generated metrics
- **[Deployment](07-deployment.md)**: Deployment options

## Support and Contributing

This is an open-source project. Contributions, bug reports, and feature requests are welcome!

- **Issues**: Report bugs or request features on GitHub
- **Pull Requests**: Improvements and fixes are appreciated
- **Documentation**: Help improve these docs

Remember: This tool is for **testing and learning**. Always review and harden code before any production use.


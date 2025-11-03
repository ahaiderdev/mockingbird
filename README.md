# Mockingbird 🐦

**Sing the metrics you need to hear**

A Python-based synthetic metrics generator for testing and comparing observability backends. Generate realistic, controllable metric workloads to validate Prometheus / OpenTelemetry based monitoring backends under varied cardinality and patterns.

## ⚠️ Important Disclaimer

**This application was generated for rapid prototyping and testing purposes.**

- ✅ **Recommended for**: Testing, learning, prototyping, and comparing observability backends
- ❌ **Not recommended for**: Production deployments without thorough review and hardening
- ⚠️ Code has not been professionally audited
- ⚠️ May contain security vulnerabilities
- ⚠️ Designed primarily for testing/development environments
- ⚠️ Use at your own risk

**Contributions and improvements are welcome!** If you find issues or have suggestions, please open an issue or submit a pull request.

## Features

- **Dual Export**: Generates identical metric data to both Prometheus (pull) and OpenTelemetry (push) simultaneously
- **Multiple Metric Types**: Supports Counter, Gauge, Histogram, and Summary metrics
- **Realistic Patterns**: Time-of-day modulation, random walks, Poisson arrivals, lognormal distributions, and more
- **Configurable Cardinality**: Test low to extremely high cardinality scenarios (100k+ series)
- **Runtime Controls**: HTTP API for triggering spikes, scenarios, and config reloads
- **Self-Monitoring**: Built-in metrics for observing generator performance
- **Deterministic**: Seed-based generation for reproducible tests

## Quick Start

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run with baseline config
python -m src.main --config configs/baseline.yaml
```

The generator will start and expose:
- Prometheus metrics at `http://localhost:8000/metrics`
- Control API at `http://localhost:8081`

### Docker Compose (Recommended)

Run the complete stack with Prometheus, OTEL Collector, and Grafana:

```bash
docker-compose -f compose/docker-compose.yaml up -d
```

Access:
- Generator metrics: http://localhost:8000/metrics
- Generator control API: http://localhost:8081/status
- Prometheus UI: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## Configuration

Configuration is done via YAML files. See `configs/` directory for examples:

- **baseline.yaml**: Low cardinality baseline for initial testing
- **high_cardinality.yaml**: High cardinality stress test (100k+ series)
- **production_sim.yaml**: Realistic production workload simulation

### Configuration Structure

```yaml
global:
  tick_interval_s: 1      # How often to generate new values
  seed: 42                # Random seed for reproducibility
  log_level: INFO
  control_api_port: 8081

exporters:
  prometheus:
    enabled: true
    port: 8000
    prefix: "prom_"
  
  otel:
    enabled: true
    endpoint: "localhost:4317"
    prefix: "otel_"
    export_interval_s: 10

profiles:
  low:
    labels:
      region:
        values: ["us-east-1", "eu-west-1"]
      instance:
        range: [1, 3]
        fmt: "i-%02d"
    series_cap: 1000

metrics:
  - name: requests_total
    type: counter
    profile: low
    algorithm: poisson
    base_rate: 5
    diurnal_amp: 0.2
```

## Metric Types and Algorithms

### Counter
- **poisson**: Poisson-distributed increments (realistic request rates)
- **constant**: Fixed increment per tick

### Gauge
- **random_walk**: Brownian motion with optional clamping
- **sine**: Sinusoidal wave (diurnal patterns)
- **bernoulli**: Binary 0/1 values (flags, cache hits)
- **sawtooth**: Linear ramp up, then reset

### Histogram
- **lognormal**: Lognormal distribution (latencies)
- **exponential**: Exponential distribution
- **mixture**: Mixture of distributions (bimodal latencies)

### Summary
- **lognormal**: Lognormal distribution with quantiles
- **exponential**: Exponential distribution with quantiles

## Control API

The control API provides runtime management capabilities:

### Get Status
```bash
curl http://localhost:8081/status
```

**Response includes:**
- `available_metrics`: List of metric names you can use for spikes
- `active_spikes`: Currently active spikes with remaining time
- `tick_count`: Number of ticks completed
- `total_series`: Total number of active time series

### Trigger Spike

Temporarily multiply metric values by a factor for testing load spikes.

**Important:** Use the **base metric name** (without prefix) as shown in `available_metrics`.

```bash
# First, check available metrics
curl -s http://localhost:8081/status | jq '.available_metrics'
# Returns: ["requests_total", "cpu_usage", "req_latency_seconds", "payload_size_bytes"]

# Trigger a 5x spike for 5 minutes
curl -X POST http://localhost:8081/control/spike \
  -H 'Content-Type: application/json' \
  -d '{
    "metric": "requests_total",
    "multiplier": 5,
    "duration_s": 300
  }'
```

**Parameters:**
- `metric` (string): Base metric name **without prefix** (e.g., `"requests_total"`, not `"synthetic_prom_requests_total"`)
- `multiplier` (float): Multiplication factor (e.g., `5.0` for 5x increase, `0.5` for 50% reduction)
- `duration_s` (int): Duration in seconds before spike automatically expires

### Reload Configuration
```bash
curl -X POST http://localhost:8081/control/reload
```

### Change Log Level
```bash
curl -X POST http://localhost:8081/control/loglevel \
  -H 'Content-Type: application/json' \
  -d '{"level": "DEBUG"}'
```

### Health Check
```bash
curl http://localhost:8081/healthz
```

## Use Cases

### Compare Backend Performance

Run identical workloads against different backends:

```bash
# Start generator
docker-compose -f compose/docker-compose.yaml up -d

# Prometheus scrapes from :8000/metrics
# OTEL Collector receives push on :4317

# Compare query performance, memory usage, etc.
```

### Test High Cardinality

```bash
python -m src.main --config configs/high_cardinality.yaml
```

This generates 100k+ unique series to test cardinality limits.

### Simulate Production Patterns

```bash
python -m src.main --config configs/production_sim.yaml
```

Includes:
- Diurnal traffic patterns
- Mixed latency distributions
- Realistic label cardinality

### Test Migration Strategies

Generate identical data to both systems, then:
1. Validate data parity
2. Test query compatibility
3. Measure performance differences
4. Verify alerting rules

## Observability

The generator exposes self-monitoring metrics under the `gen_*` prefix:

- `gen_points_total`: Total points generated per metric
- `gen_export_errors_total`: Export errors by exporter and metric
- `gen_tick_duration_seconds`: Time taken per tick (histogram)
- `gen_active_series`: Number of active time series per metric
- `gen_export_queue_depth`: Export queue depth per exporter

Query example in Prometheus:
```promql
rate(gen_points_total[1m])
histogram_quantile(0.95, rate(gen_tick_duration_seconds_bucket[1m]))
```

## Architecture

```
┌─────────────────┐
│   Config YAML   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ Generator Engine│────▶│ Prom Registry    │
│ (Tick Scheduler)│     │ /metrics HTTP    │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ OTEL Instruments│────▶│ OTEL Collector   │
│ (MeterProvider) │     │ (OTLP gRPC)      │
└─────────────────┘     └──────────────────┘
```

**Data Flow**:
1. Config loaded and validated (Pydantic)
2. Label spaces generated (Cartesian product with capping)
3. Generators initialized with deterministic seeds
4. Each tick:
   - Generate values using algorithms
   - Export to Prometheus (set/inc/observe)
   - Export to OTEL (add/record with attributes)
5. Self-metrics updated

## Development

### Project Structure

```
mockingbird/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── config.py            # Pydantic config models
│   ├── engine.py            # Main generator engine
│   ├── generators.py        # Metric value generators
│   ├── cardinality.py       # Label space generation
│   ├── prom_exporter.py     # Prometheus exporter
│   ├── otel_exporter.py     # OTEL exporter
│   ├── control_api.py       # FastAPI control endpoints
│   └── series.py            # Data structures
├── configs/
│   ├── baseline.example.yaml
│   ├── high_cardinality.example.yaml
│   └── production_sim.example.yaml
├── compose/
│   ├── docker-compose.yaml  # Docker orchestration
│   ├── alloy-config.example.alloy
│   ├── prometheus.example.yml
│   ├── otel-config.yaml
│   └── dashboards/
├── scripts/
│   ├── start.sh             # Quick start script
│   └── run.sh               # Local run script
├── tests/
├── Dockerfile
├── requirements.txt
└── README.md
```

### Running Tests

```bash
# Install dev dependencies
pip install pytest hypothesis

# Run tests (when implemented)
pytest tests/
```

### Adding New Algorithms

1. Add algorithm to `generators.py` in appropriate generator class
2. Update config schema in `config.py` with new parameters
3. Document in README
4. Add example config

## 📚 Documentation

**Complete documentation is available in the [docs/](docs/) directory.**

### For Users
- **[User Guide](docs/user-guide/)** - Complete guide from introduction to deployment
  - [Introduction](docs/user-guide/01-introduction.md) - What is this? Features and use cases
  - [Getting Started](docs/user-guide/02-getting-started.md) - Install and run your first test
  - [Configuration](docs/user-guide/03-configuration.md) - Complete configuration reference
  - [Features](docs/user-guide/04-features.md) - Detailed feature explanations
  - [Control API](docs/user-guide/05-control-api.md) - Runtime control endpoints
  - [Metrics Reference](docs/user-guide/06-metrics-reference.md) - All generated metrics
  - [Deployment](docs/user-guide/07-deployment.md) - Deployment options
- **[Examples](docs/examples/)** - Configuration examples and patterns

**Quick Links**:
- 🚀 [Getting Started Guide](docs/user-guide/02-getting-started.md)
- ⚙️ [Configuration Examples](docs/examples/README.md)
- 🎮 [Control API Reference](docs/user-guide/05-control-api.md)
- 📊 [Metrics Reference](docs/user-guide/06-metrics-reference.md)

## Troubleshooting

### OTEL Exporter Not Connecting

Check that the collector is running and accessible:
```bash
docker-compose -f compose/docker-compose.yaml logs alloy
```

Verify endpoint in config matches collector address.

### High Memory Usage

For high cardinality configs:
- Reduce `series_cap` in profile
- Increase `tick_interval_s`
- Use `sampling_strategy: hash` for deterministic sampling

### Tick Duration Too Long

If ticks take longer than `tick_interval_s`:
- Reduce number of series
- Simplify algorithms
- Increase tick interval

Check self-metrics:
```promql
gen_tick_duration_seconds{quantile="0.95"}
```

### Metrics Not Appearing

1. Check logs for errors: `docker-compose -f compose/docker-compose.yaml logs generator`
2. Verify exporters enabled in config
3. Check Prometheus targets: http://localhost:9090/targets
4. Verify OTEL collector receiving: `docker-compose -f compose/docker-compose.yaml logs alloy`

## Performance Characteristics

Tested on MacBook Pro M1 (8 cores, 16GB RAM):

| Cardinality | Series Count | Tick Duration (p95) | Memory (RSS) |
|-------------|--------------|---------------------|--------------|
| Low         | 100          | 5ms                 | 150MB        |
| Medium      | 10,000       | 50ms                | 500MB        |
| High        | 100,000      | 800ms               | 2.5GB        |

*Note: Actual performance depends on algorithm complexity and export configuration.*

## Limitations

- Single-node only (no distributed deployment)
- Summary metrics exported as Gauges in OTEL (no native Summary type)
- Config reload not fully implemented (requires restart)
- No built-in TLS/mTLS (use reverse proxy if needed)

## Future Enhancements (Out of Scope for v1)

- DogStatsD/StatsD exporters
- Remote write to Prometheus/VictoriaMetrics
- Distributed deployment with sharding
- Web UI for configuration
- Advanced failure injection modes
- Trace generation (OpenTelemetry traces)

## License

MIT License - feel free to use for testing and research.

## Contributing

This is a personal research tool, but suggestions and improvements are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Acknowledgments

Built with:
- [prometheus_client](https://github.com/prometheus/client_python)
- [OpenTelemetry Python](https://github.com/open-telemetry/opentelemetry-python)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic](https://docs.pydantic.dev/)


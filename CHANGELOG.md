# Changelog

All notable changes to the Synthetic Metrics Generator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-01

### Added - Initial Release

#### Core Features
- Metric generation engine with configurable tick interval
- Support for Counter, Gauge, Histogram, and Summary metric types
- Dual export to Prometheus (pull) and OpenTelemetry (push) simultaneously
- Deterministic seed-based generation for reproducibility
- Configurable cardinality profiles (low/medium/high/custom)

#### Metric Algorithms
- **Counter**: Poisson arrivals, constant increments
- **Gauge**: Random walk, sine wave, bernoulli, sawtooth
- **Histogram**: Lognormal, exponential, mixture distributions
- **Summary**: Lognormal, exponential with quantiles
- Time-of-day (diurnal) modulation for realistic patterns

#### Exporters
- Prometheus exporter with HTTP `/metrics` endpoint
- OpenTelemetry OTLP/gRPC exporter with configurable resource attributes
- Identical data exported to both systems with different prefixes
- Explicit histogram buckets for fair comparison

#### Configuration
- YAML-based configuration with Pydantic validation
- Environment variable overrides (OTEL_ENDPOINT, LOG_LEVEL)
- Three example configs: baseline, high_cardinality, production_sim
- Comprehensive validation with actionable error messages

#### Control API
- FastAPI-based HTTP control API on port 8081
- Endpoints: `/status`, `/healthz`, `/control/spike`, `/control/loglevel`
- Runtime spike triggering with multiplier and duration
- Dynamic log level changes

#### Observability
- Self-monitoring metrics: `gen_points_total`, `gen_export_errors_total`, `gen_tick_duration_seconds`, `gen_active_series`, `gen_export_queue_depth`
- Structured logging with configurable level (INFO, DEBUG, etc.)
- Contextual log fields for debugging

#### Deployment
- Docker containerization with health checks
- Docker Compose setup with Prometheus, OTEL Collector, and Grafana
- Local development quick start script (`run.sh`)
- Pre-configured OTEL Collector and Prometheus configs

#### Documentation
- Comprehensive README with features, quick start, and configuration
- USAGE_EXAMPLES.md with common scenarios and patterns
- QUICK_REFERENCE.md for one-page command reference
- IMPLEMENTATION_SUMMARY.md documenting implementation status
- Inline code documentation and type hints

#### Testing
- Basic validation test suite (`test_basic.py`)
- Config loading tests
- Label generation tests
- Generator creation tests
- Determinism validation tests

#### Cardinality Management
- Cartesian product label space generation
- Series cap with sampling strategies (first_n, hash)
- Label value pools (static lists and ranges with formatting)
- Prometheus-safe label name validation

### Technical Details

#### Dependencies
- Python 3.11+
- prometheus-client 0.20.0
- opentelemetry-sdk 1.24.0
- opentelemetry-exporter-otlp-proto-grpc 1.24.0
- fastapi 0.110.0
- uvicorn 0.29.0
- pydantic 2.6.4
- pyyaml 6.0.1
- numpy 1.26.4

#### Architecture
- Threading model: main generator thread + control API thread
- Deterministic RNG with per-metric and global seeds
- Component-based design with clear separation of concerns
- ~1,800 lines of Python code

### Known Limitations

- Config hot-reload endpoint exists but full implementation pending
- OTEL Summary metrics exported as Histograms (OTEL limitation)
- Single-node deployment only (no distributed mode)
- Gauge implementation in OTEL uses UpDownCounter workaround
- Counter export to Prometheus uses internal `_value.set()` workaround

### Performance Characteristics

Tested on MacBook Pro M1 (8 cores, 16GB RAM):
- Low cardinality (100 series): ~5ms tick, ~150MB memory
- Medium cardinality (10k series): ~50ms tick, ~500MB memory
- High cardinality (100k series): ~800ms tick, ~2.5GB memory

## [Unreleased]

### Planned Features

#### Short-term
- Full config hot-reload implementation
- Comprehensive unit test suite with pytest
- Debug tracing for point sampling
- OTEL backpressure metrics wiring
- Parity validation script

#### Medium-term
- Zipfian distribution for hot/cold skew
- OTLP/HTTP protocol support
- Enhanced scenario system
- Grafana dashboard templates
- Performance benchmarking suite

#### Long-term (v2.0)
- DogStatsD/StatsD exporters
- Remote write support (Prometheus, VictoriaMetrics, Mimir)
- Distributed deployment with sharding
- Web UI for configuration
- Trace generation (OpenTelemetry traces)
- TLS/mTLS support for exporters

### Ideas Under Consideration
- Exemplar support for histograms
- Custom metric plugins
- Metric correlation patterns
- Anomaly injection modes
- Time-series forecasting validation
- Multi-region simulation

## Contributing

See the main README for contribution guidelines.

## License

MIT License - See LICENSE file for details.


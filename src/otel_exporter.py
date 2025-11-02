"""OpenTelemetry push exporter using OTLP."""
from typing import Dict, List
import logging

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.metrics._internal.aggregation import ExplicitBucketHistogramAggregation
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource

from src.config import MetricConfig, OTELExporterConfig
from src.series import SeriesPoint

logger = logging.getLogger(__name__)


class OTELExporter:
    """Manages OpenTelemetry metrics and OTLP export."""
    
    def __init__(self, config: OTELExporterConfig, metrics_config: List[MetricConfig]):
        self.config = config
        self.metrics_config = metrics_config
        
        # Store instrument objects
        self.instruments: Dict[str, any] = {}
        self.instrument_types: Dict[str, str] = {}
        
        # State tracking for cumulative metrics (counters)
        # Key format: "metric_name:label1=val1,label2=val2"
        self.counter_state: Dict[str, float] = {}
        
        # State tracking for gauges (cumulative value in OTEL)
        # We track what OTEL thinks the cumulative value is, so we can calculate deltas
        self.gauge_cumulative: Dict[str, float] = {}
        
        # Initialize OTEL
        if config.enabled:
            self._initialize_otel()
    
    def _initialize_otel(self):
        """Initialize OpenTelemetry SDK."""
        # Create resource with attributes
        resource_attrs = {
            "service.name": "synthetic-metrics-generator",
            "deployment.environment": "dev",
        }
        resource_attrs.update(self.config.resource)
        
        resource = Resource.create(resource_attrs)
        
        # Create OTLP exporter
        exporter = OTLPMetricExporter(
            endpoint=self.config.endpoint,
            insecure=self.config.insecure,
            headers=tuple(self.config.headers.items()) if self.config.headers else None
        )
        
        # Create metric reader with export interval
        reader = PeriodicExportingMetricReader(
            exporter,
            export_interval_millis=self.config.export_interval_s * 1000
        )
        
        # Create Views for histograms with custom buckets
        views = self._create_histogram_views()
        
        # Create meter provider with views
        self.meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[reader],
            views=views
        )
        
        # Set global meter provider
        metrics.set_meter_provider(self.meter_provider)
        
        # Get meter
        self.meter = metrics.get_meter(__name__)
        
        logger.info(f"OTEL exporter initialized, pushing to {self.config.endpoint}")
    
    def _create_histogram_views(self) -> List[View]:
        """Create Views for histogram metrics with custom bucket boundaries."""
        views = []
        
        # Create Views for user-defined histogram metrics
        for metric_config in self.metrics_config:
            if metric_config.type == "histogram" and metric_config.buckets:
                otel_metric_name = f"{self.config.prefix}{metric_config.name}"
                
                # Create View with explicit bucket boundaries
                view = View(
                    instrument_name=otel_metric_name,
                    aggregation=ExplicitBucketHistogramAggregation(
                        boundaries=metric_config.buckets
                    )
                )
                views.append(view)
                logger.info(
                    f"Created OTEL View for {otel_metric_name} with buckets: {metric_config.buckets}"
                )
            elif metric_config.type == "summary":
                # Summary metrics: OTEL doesn't have Summary, so we use Histogram
                # If buckets are defined, use them; otherwise use minimal buckets to reduce series count
                otel_metric_name = f"{self.config.prefix}{metric_config.name}"
                
                if metric_config.buckets:
                    buckets = metric_config.buckets
                else:
                    # Use minimal buckets for Summary to match Prometheus behavior
                    # Prometheus Summary only exports _count and _sum (no buckets)
                    # OTEL requires at least one bucket, so use a single bucket at +Inf
                    buckets = []  # Empty list means only +Inf bucket
                
                view = View(
                    instrument_name=otel_metric_name,
                    aggregation=ExplicitBucketHistogramAggregation(
                        boundaries=buckets
                    )
                )
                views.append(view)
                logger.info(
                    f"Created OTEL View for Summary {otel_metric_name} with buckets: {buckets if buckets else '[+Inf only]'}"
                )
        
        # Create View for self-monitoring tick duration histogram
        # Use same buckets as Prometheus self-monitoring
        tick_duration_buckets = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
        tick_duration_view = View(
            instrument_name=f"{self.config.prefix}gen_tick_duration_seconds",
            aggregation=ExplicitBucketHistogramAggregation(
                boundaries=tick_duration_buckets
            )
        )
        views.append(tick_duration_view)
        logger.info(
            f"Created OTEL View for {self.config.prefix}gen_tick_duration_seconds with buckets: {tick_duration_buckets}"
        )
        
        return views
    
    def register_metric(self, metric_name: str, metric_type: str, label_names: List[str], buckets: List[float] = None):
        """Register a metric with its label names."""
        otel_metric_name = f"{self.config.prefix}{metric_name}"
        
        try:
            if metric_type == "counter":
                instrument = self.meter.create_counter(
                    name=otel_metric_name,
                    description=f"Generated counter metric: {metric_name}",
                    unit="1"
                )
                self.instruments[metric_name] = instrument
                self.instrument_types[metric_name] = "counter"
            
            elif metric_type == "gauge":
                # Use UpDownCounter for gauges
                # We'll track cumulative state and send deltas to reach absolute values
                instrument = self.meter.create_up_down_counter(
                    name=otel_metric_name,
                    description=f"Generated gauge metric: {metric_name}",
                    unit="1"
                )
                self.instruments[metric_name] = instrument
                self.instrument_types[metric_name] = "gauge"
            
            elif metric_type == "histogram":
                # Create histogram - bucket boundaries are configured via Views
                instrument = self.meter.create_histogram(
                    name=otel_metric_name,
                    description=f"Generated histogram metric: {metric_name}",
                    unit="1"
                )
                self.instruments[metric_name] = instrument
                self.instrument_types[metric_name] = "histogram"
            
            elif metric_type == "summary":
                # OTEL doesn't have native Summary, use histogram
                instrument = self.meter.create_histogram(
                    name=otel_metric_name,
                    description=f"Generated summary metric: {metric_name}",
                    unit="1"
                )
                self.instruments[metric_name] = instrument
                self.instrument_types[metric_name] = "summary"
            
            logger.info(f"Registered OTEL instrument: {otel_metric_name} with labels {label_names}")
        
        except Exception as e:
            logger.error(f"Failed to register instrument {otel_metric_name}: {e}")
            raise
    
    def export_point(self, point: SeriesPoint, metric_type: str):
        """Export a single series point to OTEL.
        
        Handles the semantic differences between Prometheus and OTEL:
        - Counter: Generator produces cumulative values, OTEL needs deltas
        - Gauge: Generator produces absolute values, OTEL needs deltas
        - Histogram: Generator produces observations (correct for both)
        - Summary: Generator produces observations (correct for both)
        """
        # Strip prefix from point name to get base name
        base_name = point.name
        if base_name.startswith(self.config.prefix):
            base_name = base_name[len(self.config.prefix):]
        
        if base_name not in self.instruments:
            logger.warning(f"Instrument {base_name} not found in OTEL registry")
            return
        
        instrument = self.instruments[base_name]
        
        try:
            if metric_type == "counter":
                # Generator produces CUMULATIVE counter values
                # OTEL Counter.add() expects DELTA (increment)
                # We need to track state and calculate delta
                
                series_key = self._series_key(base_name, point.labels)
                prev_value = self.counter_state.get(series_key, 0.0)
                
                # Calculate delta
                delta = point.value - prev_value
                
                # Only add positive deltas (counters can't decrease)
                if delta > 0:
                    instrument.add(delta, attributes=point.labels)
                    self.counter_state[series_key] = point.value
                elif delta < 0:
                    # Counter reset detected - treat current value as delta
                    logger.debug(f"Counter reset detected for {series_key}, using full value")
                    instrument.add(point.value, attributes=point.labels)
                    self.counter_state[series_key] = point.value
                # If delta == 0, don't add anything
            
            elif metric_type == "gauge":
                # Generator produces ABSOLUTE gauge values (e.g., CPU = 50%)
                # OTEL UpDownCounter is CUMULATIVE and expects deltas
                # We track the cumulative value OTEL has and send delta to reach target
                
                series_key = self._series_key(base_name, point.labels)
                current_cumulative = self.gauge_cumulative.get(series_key, 0.0)
                
                # Calculate delta needed to reach the target absolute value
                # Target absolute value = point.value
                # Current OTEL cumulative = current_cumulative
                # Delta needed = target - current
                delta = point.value - current_cumulative
                
                if delta != 0:
                    instrument.add(delta, attributes=point.labels)
                    # Update our tracking of what OTEL's cumulative value is now
                    self.gauge_cumulative[series_key] = point.value
            
            elif metric_type == "histogram":
                # Generator produces OBSERVATIONS (individual samples)
                # OTEL Histogram.record() expects observations
                # This is semantically correct - no conversion needed
                instrument.record(point.value, attributes=point.labels)
            
            elif metric_type == "summary":
                # Generator produces OBSERVATIONS (individual samples)
                # OTEL doesn't have native Summary, we use Histogram
                # This is semantically correct - no conversion needed
                instrument.record(point.value, attributes=point.labels)
        
        except Exception as e:
            logger.error(f"Failed to export point {point.name} to OTEL: {e}")
    
    def _series_key(self, metric_name: str, labels: Dict[str, str]) -> str:
        """Generate unique key for a time series (metric + labels)."""
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{metric_name}:{label_str}"
    
    def export_points(self, points: List[SeriesPoint], metric_types: Dict[str, str]):
        """Export multiple series points."""
        for point in points:
            # Strip prefix to get base name for lookup
            base_name = point.name
            if base_name.startswith(self.config.prefix):
                base_name = base_name[len(self.config.prefix):]
            
            metric_type = metric_types.get(base_name)
            if metric_type:
                self.export_point(point, metric_type)
    
    def shutdown(self):
        """Shutdown OTEL exporter."""
        if hasattr(self, 'meter_provider'):
            self.meter_provider.shutdown()
            logger.info("OTEL exporter shutdown complete")


class OTELGaugeManager:
    """
    Manager for OTEL gauge values using observable gauges.
    This is a more proper implementation for gauges.
    """
    
    def __init__(self, meter):
        self.meter = meter
        self.gauge_values: Dict[str, Dict[str, float]] = {}  # metric_name -> {label_key -> value}
        self.gauges: Dict[str, any] = {}
    
    def create_gauge(self, name: str, description: str):
        """Create an observable gauge."""
        def callback(options):
            observations = []
            if name in self.gauge_values:
                for label_key, value in self.gauge_values[name].items():
                    # Parse label_key back to dict
                    labels = self._parse_label_key(label_key)
                    observations.append(metrics.Observation(value, attributes=labels))
            return observations
        
        gauge = self.meter.create_observable_gauge(
            name=name,
            callbacks=[callback],
            description=description,
            unit="1"
        )
        self.gauges[name] = gauge
    
    def set_value(self, metric_name: str, labels: Dict[str, str], value: float):
        """Set gauge value."""
        label_key = self._label_key(labels)
        
        if metric_name not in self.gauge_values:
            self.gauge_values[metric_name] = {}
        
        self.gauge_values[metric_name][label_key] = value
    
    def _label_key(self, labels: Dict[str, str]) -> str:
        """Generate stable key from labels."""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
    
    def _parse_label_key(self, label_key: str) -> Dict[str, str]:
        """Parse label key back to dict."""
        if not label_key:
            return {}
        
        labels = {}
        for pair in label_key.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                labels[k] = v
        return labels


class OTELSelfMetrics:
    """Self-monitoring metrics for OTEL exporter."""
    
    def __init__(self, meter, prefix=""):
        self.prefix = prefix
        
        # Create OTEL instruments for self-monitoring
        self.points_counter = meter.create_counter(
            name=f"{prefix}gen_points_total",
            description="Total number of metric points generated",
            unit="1"
        )
        
        self.export_errors_counter = meter.create_counter(
            name=f"{prefix}gen_export_errors_total",
            description="Total number of export errors",
            unit="1"
        )
        
        self.tick_duration_histogram = meter.create_histogram(
            name=f"{prefix}gen_tick_duration_seconds",
            description="Duration of each tick in seconds",
            unit="s"
        )
        
        self.active_series_gauge = meter.create_up_down_counter(
            name=f"{prefix}gen_active_series",
            description="Number of active time series",
            unit="1"
        )
    
    def record_points(self, metric_name: str, count: int):
        """Record generated points."""
        self.points_counter.add(count, {"metric_name": metric_name})
    
    def record_export_error(self, exporter: str, metric_name: str):
        """Record export error."""
        self.export_errors_counter.add(1, {"exporter": exporter, "metric_name": metric_name})
    
    def record_tick_duration(self, duration: float):
        """Record tick duration."""
        self.tick_duration_histogram.record(duration)
    
    def set_active_series(self, metric_name: str, count: int):
        """Set active series count."""
        # Note: OTEL doesn't have direct gauge support, using up_down_counter
        # This is a limitation - we can only add/subtract, not set directly
        # For now, we'll just record it once during initialization
        self.active_series_gauge.add(count, {"metric_name": metric_name})


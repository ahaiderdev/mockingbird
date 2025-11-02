"""Prometheus pull exporter using prometheus_client."""
from typing import Dict, List, Optional
from prometheus_client import (
    Counter, Gauge, Histogram, Summary,
    CollectorRegistry, start_http_server, REGISTRY
)
import logging

from src.config import MetricConfig, PrometheusExporterConfig
from src.series import SeriesPoint

logger = logging.getLogger(__name__)


class PrometheusExporter:
    """Manages Prometheus metrics and HTTP server."""
    
    def __init__(self, config: PrometheusExporterConfig, metrics_config: List[MetricConfig]):
        self.config = config
        self.metrics_config = metrics_config
        # Use a custom registry to avoid exporting default Python/process metrics
        self.registry = CollectorRegistry()
        
        # Store metric objects
        self.metrics: Dict[str, any] = {}
        
        # Store label names per metric (will be set by engine)
        self.label_names: Dict[str, List[str]] = {}
        
        # Start HTTP server
        if config.enabled:
            self._start_server()
    
    def register_metric(self, metric_name: str, metric_type: str, label_names: List[str], buckets: List[float] = None):
        """Register a metric with its label names."""
        prom_metric_name = f"{self.config.prefix}{metric_name}"
        
        # Find the config for this metric
        metric_config = None
        for cfg in self.metrics_config:
            if cfg.name == metric_name:
                metric_config = cfg
                break
        
        if not metric_config:
            logger.error(f"No config found for metric {metric_name}")
            return
        
        try:
            if metric_type == "counter":
                self.metrics[metric_name] = Counter(
                    prom_metric_name,
                    f"Generated counter metric: {metric_name}",
                    label_names,
                    registry=self.registry
                )
            
            elif metric_type == "gauge":
                self.metrics[metric_name] = Gauge(
                    prom_metric_name,
                    f"Generated gauge metric: {metric_name}",
                    label_names,
                    registry=self.registry
                )
            
            elif metric_type == "histogram":
                buckets = buckets or metric_config.buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
                self.metrics[metric_name] = Histogram(
                    prom_metric_name,
                    f"Generated histogram metric: {metric_name}",
                    label_names,
                    buckets=buckets,
                    registry=self.registry
                )
            
            elif metric_type == "summary":
                # Note: prometheus_client Summary only exports _count and _sum
                # Quantiles are not supported in the Python client library
                self.metrics[metric_name] = Summary(
                    prom_metric_name,
                    f"Generated summary metric: {metric_name}",
                    label_names,
                    registry=self.registry
                )
            
            self.label_names[metric_name] = label_names
            logger.info(f"Registered Prometheus metric: {prom_metric_name} with labels {label_names}")
        
        except Exception as e:
            logger.error(f"Failed to register metric {prom_metric_name}: {e}")
            raise
    
    def _start_server(self):
        """Start Prometheus HTTP server."""
        try:
            start_http_server(
                self.config.port,
                addr=self.config.bind_address,
                registry=self.registry
            )
            logger.info(
                f"Prometheus exporter listening on "
                f"{self.config.bind_address}:{self.config.port}/metrics"
            )
        except Exception as e:
            logger.error(f"Failed to start Prometheus HTTP server: {e}")
            raise
    
    def export_point(self, point: SeriesPoint, metric_type: str):
        """Export a single series point to Prometheus."""
        # Strip prefix from point name to get base name
        base_name = point.name
        if base_name.startswith(self.config.prefix):
            base_name = base_name[len(self.config.prefix):]
        
        if base_name not in self.metrics:
            logger.warning(f"Metric {base_name} not found in Prometheus registry")
            return
        
        metric = self.metrics[base_name]
        
        try:
            if metric_type == "counter":
                # For counters, we need to set to the cumulative value
                # prometheus_client Counter doesn't have a direct set method
                # We track state in the generator and use inc() appropriately
                # However, for simplicity, we'll use the internal _value
                labeled_metric = metric.labels(**point.labels)
                # Set the counter value directly (this is a workaround)
                labeled_metric._value.set(point.value)
            
            elif metric_type == "gauge":
                metric.labels(**point.labels).set(point.value)
            
            elif metric_type == "histogram":
                metric.labels(**point.labels).observe(point.value)
            
            elif metric_type == "summary":
                metric.labels(**point.labels).observe(point.value)
        
        except Exception as e:
            logger.error(f"Failed to export point {point.name}: {e}")
    
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


class SelfMetrics:
    """Self-monitoring metrics for the generator."""
    
    def __init__(self, registry=None, prefix=""):
        if registry is None:
            registry = CollectorRegistry()
        
        self.points_total = Counter(
            f"{prefix}gen_points_total",
            "Total number of metric points generated",
            ["metric_name"],
            registry=registry
        )
        
        self.export_errors_total = Counter(
            f"{prefix}gen_export_errors_total",
            "Total number of export errors",
            ["exporter", "metric_name"],
            registry=registry
        )
        
        self.tick_duration_seconds = Histogram(
            f"{prefix}gen_tick_duration_seconds",
            "Duration of each tick in seconds",
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
            registry=registry
        )
        
        self.active_series = Gauge(
            f"{prefix}gen_active_series",
            "Number of active time series",
            ["metric_name"],
            registry=registry
        )
        
        self.export_queue_depth = Gauge(
            f"{prefix}gen_export_queue_depth",
            "Depth of export queue",
            ["exporter"],
            registry=registry
        )
    
    def record_points(self, metric_name: str, count: int):
        """Record generated points."""
        self.points_total.labels(metric_name=metric_name).inc(count)
    
    def record_export_error(self, exporter: str, metric_name: str):
        """Record export error."""
        self.export_errors_total.labels(exporter=exporter, metric_name=metric_name).inc()
    
    def record_tick_duration(self, duration: float):
        """Record tick duration."""
        self.tick_duration_seconds.observe(duration)
    
    def set_active_series(self, metric_name: str, count: int):
        """Set active series count."""
        self.active_series.labels(metric_name=metric_name).set(count)
    
    def set_queue_depth(self, exporter: str, depth: int):
        """Set export queue depth."""
        self.export_queue_depth.labels(exporter=exporter).set(depth)


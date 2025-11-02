"""Main generator engine and scheduler."""
import time
import logging
from typing import Dict, List

from src.config import Config
from src.generators import create_generator, MetricGenerator
from src.cardinality import generate_label_space
from src.prom_exporter import PrometheusExporter, SelfMetrics
from src.otel_exporter import OTELExporter, OTELSelfMetrics
from src.series import SeriesPoint

logger = logging.getLogger(__name__)


class GeneratorEngine:
    """Main engine that orchestrates metric generation and export."""
    
    def __init__(self, config: Config, control_api=None):
        self.config = config
        self.control_api = control_api
        self.generators: Dict[str, MetricGenerator] = {}
        self.metric_types: Dict[str, str] = {}
        self.running = False
        self.tick_count = 0
        self.start_time = time.time()
        
        # Initialize self-metrics (will be set up after exporters)
        self.self_metrics = None
        self.otel_self_metrics = None
        
        # Initialize exporters
        self._initialize_exporters()
        
        # Initialize self-metrics with Prometheus registry and prefix
        if self.prom_exporter:
            self.self_metrics = SelfMetrics(
                registry=self.prom_exporter.registry,
                prefix=self.config.exporters.prometheus.prefix
            )
        
        # Initialize OTEL self-metrics
        if self.otel_exporter:
            self.otel_self_metrics = OTELSelfMetrics(
                meter=self.otel_exporter.meter,
                prefix=self.config.exporters.otel.prefix
            )
        
        # Initialize generators
        self._initialize_generators()
        
        logger.info("Generator engine initialized")
    
    def _initialize_exporters(self):
        """Initialize Prometheus and OTEL exporters."""
        # Prometheus exporter
        if self.config.exporters.prometheus.enabled:
            self.prom_exporter = PrometheusExporter(
                self.config.exporters.prometheus,
                self.config.metrics
            )
            logger.info("Prometheus exporter initialized")
        else:
            self.prom_exporter = None
            logger.info("Prometheus exporter disabled")
        
        # OTEL exporter
        if self.config.exporters.otel.enabled:
            self.otel_exporter = OTELExporter(
                self.config.exporters.otel,
                self.config.metrics
            )
            logger.info("OTEL exporter initialized")
        else:
            self.otel_exporter = None
            logger.info("OTEL exporter disabled")
    
    def _initialize_generators(self):
        """Initialize metric generators."""
        for metric_config in self.config.metrics:
            # Get profile
            profile = self.config.profiles.get(metric_config.profile)
            if not profile:
                logger.error(f"Profile '{metric_config.profile}' not found for metric '{metric_config.name}'")
                continue
            
            # Generate label space
            label_combinations = generate_label_space(profile, metric_config.labels)
            
            logger.info(
                f"Metric '{metric_config.name}': "
                f"{len(label_combinations)} series (profile: {metric_config.profile})"
            )
            
            # Get label names from first combination (all have same keys)
            label_names = list(label_combinations[0].keys()) if label_combinations else []
            
            # Register metric with exporters
            if self.prom_exporter:
                self.prom_exporter.register_metric(
                    metric_config.name,
                    metric_config.type,
                    label_names,
                    metric_config.buckets
                )
            
            if self.otel_exporter:
                self.otel_exporter.register_metric(
                    metric_config.name,
                    metric_config.type,
                    label_names,
                    metric_config.buckets
                )
            
            # Create generator
            generator = create_generator(
                metric_config,
                label_combinations,
                self.config.global_.seed
            )
            
            self.generators[metric_config.name] = generator
            self.metric_types[metric_config.name] = metric_config.type
            
            # Update self-metrics (if enabled)
            if self.self_metrics:
                self.self_metrics.set_active_series(metric_config.name, len(label_combinations))
            if self.otel_self_metrics:
                self.otel_self_metrics.set_active_series(metric_config.name, len(label_combinations))
        
        logger.info(f"Initialized {len(self.generators)} metric generators")
    
    def tick(self):
        """Execute one tick of metric generation."""
        tick_start = time.time()
        current_time = int(time.time())
        
        all_points: List[SeriesPoint] = []
        
        # Generate points from all generators
        for metric_name, generator in self.generators.items():
            try:
                points = list(generator.tick(current_time))
                
                # Apply spike multiplier if control_api is available
                if self.control_api:
                    spike_multiplier = self.control_api.get_spike_multiplier(metric_name)
                    
                    if spike_multiplier != 1.0:
                        logger.info(
                            f"🔥 Applying {spike_multiplier}x spike to {metric_name} "
                            f"({len(points)} points)"
                        )
                        # Apply multiplier to all points for this metric
                        for point in points:
                            point.value *= spike_multiplier
                else:
                    # Log once at startup if control_api is not connected
                    if self.tick_count == 1:
                        logger.warning("Control API not connected to engine - spikes will not work!")
                
                all_points.extend(points)
                
                # Record self-metrics (if enabled)
                if self.self_metrics:
                    self.self_metrics.record_points(metric_name, len(points))
                if self.otel_self_metrics:
                    self.otel_self_metrics.record_points(metric_name, len(points))
                
            except Exception as e:
                logger.error(f"Error generating metric '{metric_name}': {e}")
                if self.self_metrics:
                    self.self_metrics.record_export_error("generator", metric_name)
                if self.otel_self_metrics:
                    self.otel_self_metrics.record_export_error("generator", metric_name)
        
        # Export to Prometheus
        if self.prom_exporter:
            try:
                # Create prefixed points for Prometheus
                prom_points = [
                    SeriesPoint(
                        f"{self.config.exporters.prometheus.prefix}{p.name}",
                        p.labels,
                        p.value
                    )
                    for p in all_points
                ]
                
                self.prom_exporter.export_points(prom_points, self.metric_types)
                
            except Exception as e:
                logger.error(f"Error exporting to Prometheus: {e}")
                if self.self_metrics:
                    for metric_name in self.metric_types.keys():
                        self.self_metrics.record_export_error("prometheus", metric_name)
        
        # Export to OTEL
        if self.otel_exporter:
            try:
                # Create prefixed points for OTEL
                otel_points = [
                    SeriesPoint(
                        f"{self.config.exporters.otel.prefix}{p.name}",
                        p.labels,
                        p.value
                    )
                    for p in all_points
                ]
                
                self.otel_exporter.export_points(otel_points, self.metric_types)
                
            except Exception as e:
                logger.error(f"Error exporting to OTEL: {e}")
                if self.self_metrics:
                    for metric_name in self.metric_types.keys():
                        self.self_metrics.record_export_error("otel", metric_name)
        
        # Record tick duration (if self-metrics enabled)
        if self.self_metrics or self.otel_self_metrics:
            tick_duration = time.time() - tick_start
            if self.self_metrics:
                self.self_metrics.record_tick_duration(tick_duration)
            if self.otel_self_metrics:
                self.otel_self_metrics.record_tick_duration(tick_duration)
        
        self.tick_count += 1
        
        if self.tick_count % 60 == 0:  # Log every 60 ticks
            logger.info(
                f"Tick {self.tick_count}: generated {len(all_points)} points "
                f"in {tick_duration:.3f}s"
            )
    
    def run(self):
        """Run the generator engine."""
        self.running = True
        self.start_time = time.time()
        
        logger.info("Starting generator engine")
        
        tick_interval = self.config.global_.tick_interval_s
        
        while self.running:
            tick_start = time.time()
            
            try:
                self.tick()
            except Exception as e:
                logger.error(f"Error in tick: {e}", exc_info=True)
            
            # Sleep for remaining time in tick interval
            tick_duration = time.time() - tick_start
            sleep_time = max(0, tick_interval - tick_duration)
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                logger.warning(
                    f"Tick took {tick_duration:.3f}s, longer than interval {tick_interval}s"
                )
    
    def stop(self):
        """Stop the generator engine."""
        logger.info("Stopping generator engine")
        self.running = False
        
        # Shutdown exporters
        if self.otel_exporter:
            self.otel_exporter.shutdown()
    
    def reload_config(self):
        """Reload configuration (placeholder for future implementation)."""
        logger.warning("Config reload not yet implemented")
        # TODO: Implement safe config reload
        # 1. Load new config
        # 2. Validate
        # 3. Stop current generators
        # 4. Re-initialize with new config
        # 5. Preserve or reset seeds based on config


def run_engine_thread(engine: GeneratorEngine):
    """Run engine in a separate thread."""
    try:
        engine.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        engine.stop()
    except Exception as e:
        logger.error(f"Engine thread error: {e}", exc_info=True)
        engine.stop()


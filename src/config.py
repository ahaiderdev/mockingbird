"""Configuration models using Pydantic for validation."""
from typing import Dict, List, Optional, Union, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
import os


class LabelValueSpec(BaseModel):
    """Specification for label value generation."""
    values: Optional[List[str]] = None
    range: Optional[List[int]] = None  # [start, end]
    fmt: Optional[str] = None  # Format string for range values


class CardinalityProfile(BaseModel):
    """Cardinality profile defining label spaces."""
    labels: Dict[str, LabelValueSpec] = Field(default_factory=dict)
    series_cap: Optional[int] = None
    sampling_strategy: Literal["first_n", "hash"] = "first_n"
    zipf_alpha: Optional[float] = None  # For hot/cold skew


class PrometheusExporterConfig(BaseModel):
    """Prometheus pull exporter configuration."""
    enabled: bool = True
    port: int = 8000
    prefix: str = "prom_"
    bind_address: str = "0.0.0.0"


class OTELResourceAttribute(BaseModel):
    """OTEL resource attributes."""
    pass


class OTELExporterConfig(BaseModel):
    """OpenTelemetry push exporter configuration."""
    enabled: bool = True
    endpoint: str = "localhost:4317"
    insecure: bool = True
    prefix: str = "otel_"
    export_interval_s: int = 10
    protocol: Literal["grpc", "http"] = "grpc"
    headers: Dict[str, str] = Field(default_factory=dict)
    resource: Dict[str, str] = Field(default_factory=dict)


class ExportersConfig(BaseModel):
    """Configuration for all exporters."""
    prometheus: PrometheusExporterConfig = Field(default_factory=PrometheusExporterConfig)
    otel: OTELExporterConfig = Field(default_factory=OTELExporterConfig)


class MixtureComponent(BaseModel):
    """Component of a mixture distribution."""
    type: str
    weight: float
    mu: Optional[float] = None
    sigma: Optional[float] = None
    lam: Optional[float] = None  # For exponential


class MetricConfig(BaseModel):
    """Configuration for a single metric."""
    name: str
    type: Literal["counter", "gauge", "histogram", "summary"]
    profile: str
    algorithm: str
    labels: Optional[Dict[str, LabelValueSpec]] = None
    seed: Optional[int] = None
    
    # Algorithm-specific parameters
    base_rate: Optional[float] = None
    diurnal_amp: Optional[float] = None
    diurnal_phase: Optional[float] = 0.0
    
    # Random walk
    start: Optional[float] = None
    step: Optional[float] = None
    clamp: Optional[List[float]] = None
    
    # Distributions
    mu: Optional[float] = None
    sigma: Optional[float] = None
    lam: Optional[float] = None
    p: Optional[float] = None  # Bernoulli
    
    # Histogram
    buckets: Optional[List[float]] = None
    
    # Summary
    objectives: Optional[Dict[float, float]] = None
    
    # Mixture
    components: Optional[List[MixtureComponent]] = None
    
    # Sawtooth/periodic
    min: Optional[float] = None
    max: Optional[float] = None
    period_s: Optional[int] = None
    
    # Error handling
    allow_nan: bool = False


class RuntimeAction(BaseModel):
    """Runtime action to execute on start."""
    action: str
    metric: Optional[str] = None
    multiplier: Optional[float] = None
    duration_s: Optional[int] = None
    rate: Optional[float] = None


class RuntimeConfig(BaseModel):
    """Runtime behavior configuration."""
    on_start: List[RuntimeAction] = Field(default_factory=list)
    failure_modes: Dict[str, Any] = Field(default_factory=dict)


class GlobalConfig(BaseModel):
    """Global configuration settings."""
    tick_interval_s: int = 1
    seed: int = 42
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "text"
    control_api_port: int = 8081


class Config(BaseModel):
    """Root configuration model."""
    global_: GlobalConfig = Field(default_factory=GlobalConfig, alias="global")
    exporters: ExportersConfig = Field(default_factory=ExportersConfig)
    profiles: Dict[str, CardinalityProfile] = Field(default_factory=dict)
    metrics: List[MetricConfig] = Field(default_factory=list)
    runtime: Optional[RuntimeConfig] = None
    
    class Config:
        populate_by_name = True
    
    @field_validator('metrics')
    @classmethod
    def validate_metrics(cls, v):
        """Validate metric configurations."""
        if not v:
            raise ValueError("At least one metric must be defined")
        
        names = [m.name for m in v]
        if len(names) != len(set(names)):
            raise ValueError("Metric names must be unique")
        
        return v
    
    @model_validator(mode='after')
    def validate_profiles_referenced(self):
        """Ensure all referenced profiles exist."""
        profile_names = set(self.profiles.keys())
        for metric in self.metrics:
            if metric.profile not in profile_names:
                raise ValueError(f"Metric '{metric.name}' references undefined profile '{metric.profile}'")
        return self


def load_config(config_path: str) -> Config:
    """Load and validate configuration from YAML file."""
    import yaml
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        raw_config = yaml.safe_load(f)
    
    # Apply environment variable overrides
    if env_endpoint := os.getenv('OTEL_ENDPOINT'):
        if 'exporters' not in raw_config:
            raw_config['exporters'] = {}
        if 'otel' not in raw_config['exporters']:
            raw_config['exporters']['otel'] = {}
        raw_config['exporters']['otel']['endpoint'] = env_endpoint
    
    if env_log_level := os.getenv('LOG_LEVEL'):
        if 'global' not in raw_config:
            raw_config['global'] = {}
        raw_config['global']['log_level'] = env_log_level
    
    try:
        config = Config(**raw_config)
        return config
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")


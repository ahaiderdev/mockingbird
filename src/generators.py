"""Metric value generators with various algorithms."""
from typing import Dict, List, Iterable, Optional
import numpy as np
from abc import ABC, abstractmethod

from src.series import SeriesPoint
from src.config import MetricConfig


class MetricGenerator(ABC):
    """Base class for metric generators."""
    
    def __init__(
        self,
        name: str,
        metric_type: str,
        label_combinations: List[Dict[str, str]],
        config: MetricConfig,
        global_seed: int
    ):
        self.name = name
        self.metric_type = metric_type
        self.label_combinations = label_combinations
        self.config = config
        
        # Initialize RNG with deterministic seed
        seed = config.seed if config.seed is not None else global_seed
        self.rng = np.random.default_rng(seed)
        
        # State tracking per series
        self.state: Dict[str, float] = {}
    
    @abstractmethod
    def tick(self, t_s: int) -> Iterable[SeriesPoint]:
        """Generate values for current tick."""
        pass
    
    def _apply_diurnal_modulation(self, t_s: int, base_value: float) -> float:
        """Apply time-of-day sinusoidal modulation."""
        if not self.config.diurnal_amp:
            return base_value
        
        phase = (t_s % 86400) / 86400.0  # Normalized to [0, 1]
        phase_offset = self.config.diurnal_phase or 0.0
        modulation = 1 + self.config.diurnal_amp * np.sin(
            2 * np.pi * (phase + phase_offset)
        )
        return base_value * modulation
    
    def _clamp_value(self, value: float) -> float:
        """Clamp value to configured range."""
        if self.config.clamp:
            min_val, max_val = self.config.clamp
            return np.clip(value, min_val, max_val)
        return value
    
    def _handle_nan(self, value: float) -> Optional[float]:
        """Handle NaN values according to config."""
        if np.isnan(value):
            if self.config.allow_nan:
                return value
            return None  # Drop the point
        return value


class CounterGenerator(MetricGenerator):
    """Counter metric generator with various increment algorithms."""
    
    def tick(self, t_s: int) -> Iterable[SeriesPoint]:
        """Generate counter increments."""
        algorithm = self.config.algorithm
        
        for labels in self.label_combinations:
            label_key = self._label_key(labels)
            
            if algorithm == "poisson":
                increment = self._generate_poisson(t_s)
            elif algorithm == "constant":
                increment = self.config.base_rate or 1.0
            else:
                increment = self._generate_poisson(t_s)
            
            # Ensure non-negative (counters can't decrease)
            increment = max(0, increment)
            
            # Update cumulative state
            current = self.state.get(label_key, 0.0)
            new_value = current + increment
            self.state[label_key] = new_value
            
            yield SeriesPoint(self.name, labels, new_value)
    
    def _generate_poisson(self, t_s: int) -> float:
        """Generate Poisson-distributed increment."""
        base_rate = self.config.base_rate or 1.0
        rate = self._apply_diurnal_modulation(t_s, base_rate)
        return float(self.rng.poisson(rate))
    
    def _label_key(self, labels: Dict[str, str]) -> str:
        """Generate stable key from labels."""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class GaugeGenerator(MetricGenerator):
    """Gauge metric generator with various value algorithms."""
    
    def tick(self, t_s: int) -> Iterable[SeriesPoint]:
        """Generate gauge values."""
        algorithm = self.config.algorithm
        
        for labels in self.label_combinations:
            label_key = self._label_key(labels)
            
            if algorithm == "random_walk":
                value = self._generate_random_walk(label_key)
            elif algorithm == "sine":
                value = self._generate_sine(t_s)
            elif algorithm == "bernoulli":
                value = self._generate_bernoulli()
            elif algorithm == "sawtooth":
                value = self._generate_sawtooth(t_s)
            elif algorithm == "constant":
                value = self.config.start or 0.0
            else:
                value = self._generate_random_walk(label_key)
            
            value = self._clamp_value(value)
            value = self._handle_nan(value)
            
            if value is not None:
                yield SeriesPoint(self.name, labels, value)
    
    def _generate_random_walk(self, label_key: str) -> float:
        """Generate random walk value."""
        if label_key not in self.state:
            self.state[label_key] = self.config.start or 0.0
        
        step = self.config.step or 0.1
        delta = self.rng.normal(0, step)
        new_value = self.state[label_key] + delta
        self.state[label_key] = new_value
        return new_value
    
    def _generate_sine(self, t_s: int) -> float:
        """Generate sinusoidal value."""
        period = self.config.period_s or 3600
        amplitude = (self.config.max or 1.0) - (self.config.min or 0.0)
        baseline = (self.config.max or 1.0) + (self.config.min or 0.0)
        baseline /= 2
        
        phase = (t_s % period) / period
        return baseline + (amplitude / 2) * np.sin(2 * np.pi * phase)
    
    def _generate_bernoulli(self) -> float:
        """Generate Bernoulli (0 or 1) value."""
        p = self.config.p or 0.5
        return float(self.rng.binomial(1, p))
    
    def _generate_sawtooth(self, t_s: int) -> float:
        """Generate sawtooth wave value."""
        period = self.config.period_s or 3600
        min_val = self.config.min or 0.0
        max_val = self.config.max or 1.0
        
        phase = (t_s % period) / period
        return min_val + (max_val - min_val) * phase
    
    def _label_key(self, labels: Dict[str, str]) -> str:
        """Generate stable key from labels."""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class HistogramGenerator(MetricGenerator):
    """Histogram metric generator."""
    
    def tick(self, t_s: int) -> Iterable[SeriesPoint]:
        """Generate histogram observations."""
        algorithm = self.config.algorithm
        
        for labels in self.label_combinations:
            if algorithm == "lognormal":
                value = self._generate_lognormal()
            elif algorithm == "exponential":
                value = self._generate_exponential()
            elif algorithm == "mixture":
                value = self._generate_mixture()
            else:
                value = self._generate_lognormal()
            
            value = self._handle_nan(value)
            
            if value is not None and value >= 0:
                yield SeriesPoint(self.name, labels, value)
    
    def _generate_lognormal(self) -> float:
        """Generate lognormal-distributed value."""
        mu = self.config.mu or 0.0
        sigma = self.config.sigma or 1.0
        return float(self.rng.lognormal(mu, sigma))
    
    def _generate_exponential(self) -> float:
        """Generate exponential-distributed value."""
        lam = self.config.lam or 1.0
        return float(self.rng.exponential(1.0 / lam))
    
    def _generate_mixture(self) -> float:
        """Generate value from mixture distribution."""
        if not self.config.components:
            return self._generate_lognormal()
        
        # Select component based on weights
        weights = [c.weight for c in self.config.components]
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        component_idx = self.rng.choice(
            len(self.config.components),
            p=normalized_weights
        )
        component = self.config.components[component_idx]
        
        if component.type == "lognormal":
            mu = component.mu or 0.0
            sigma = component.sigma or 1.0
            return float(self.rng.lognormal(mu, sigma))
        elif component.type == "exponential":
            lam = component.lam or 1.0
            return float(self.rng.exponential(1.0 / lam))
        
        return self._generate_lognormal()


class SummaryGenerator(MetricGenerator):
    """Summary metric generator (similar to histogram but with quantiles)."""
    
    def tick(self, t_s: int) -> Iterable[SeriesPoint]:
        """Generate summary observations."""
        algorithm = self.config.algorithm
        
        for labels in self.label_combinations:
            if algorithm == "lognormal":
                value = self._generate_lognormal()
            elif algorithm == "exponential":
                value = self._generate_exponential()
            else:
                value = self._generate_lognormal()
            
            value = self._handle_nan(value)
            
            if value is not None and value >= 0:
                yield SeriesPoint(self.name, labels, value)
    
    def _generate_lognormal(self) -> float:
        """Generate lognormal-distributed value."""
        mu = self.config.mu or 0.0
        sigma = self.config.sigma or 1.0
        return float(self.rng.lognormal(mu, sigma))
    
    def _generate_exponential(self) -> float:
        """Generate exponential-distributed value."""
        lam = self.config.lam or 1.0
        return float(self.rng.exponential(1.0 / lam))


def create_generator(
    config: MetricConfig,
    label_combinations: List[Dict[str, str]],
    global_seed: int
) -> MetricGenerator:
    """Factory function to create appropriate generator."""
    metric_type = config.type
    name = config.name
    
    if metric_type == "counter":
        return CounterGenerator(name, metric_type, label_combinations, config, global_seed)
    elif metric_type == "gauge":
        return GaugeGenerator(name, metric_type, label_combinations, config, global_seed)
    elif metric_type == "histogram":
        return HistogramGenerator(name, metric_type, label_combinations, config, global_seed)
    elif metric_type == "summary":
        return SummaryGenerator(name, metric_type, label_combinations, config, global_seed)
    else:
        raise ValueError(f"Unknown metric type: {metric_type}")


"""Data structures for metric series points."""
from dataclasses import dataclass
from typing import Dict


@dataclass
class SeriesPoint:
    """A single metric data point with labels."""
    name: str
    labels: Dict[str, str]
    value: float
    
    def label_key(self) -> str:
        """Generate a stable key from sorted labels."""
        items = sorted(self.labels.items())
        return ",".join(f"{k}={v}" for k, v in items)


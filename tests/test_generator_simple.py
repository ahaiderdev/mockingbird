#!/usr/bin/env python3
"""Simple test of the generator."""
import sys
sys.path.insert(0, ".")

from src.config import load_config
from src.cardinality import generate_label_space
from src.generators import create_generator

# Load config
config = load_config("configs/baseline.yaml")

# Get first metric
metric_config = config.metrics[0]
print(f"Metric: {metric_config.name}")
print(f"Type: {metric_config.type}")
print(f"Profile: {metric_config.profile}")

# Get profile
profile = config.profiles[metric_config.profile]
print(f"\nProfile labels: {list(profile.labels.keys())}")

# Generate label space
label_combinations = generate_label_space(profile, metric_config.labels)
print(f"Generated {len(label_combinations)} label combinations")
print(f"First 3: {label_combinations[:3]}")

# Create generator
gen = create_generator(metric_config, label_combinations, config.global_.seed)

# Generate some points
points = list(gen.tick(0))
print(f"\nGenerated {len(points)} points")
for i, point in enumerate(points[:3]):
    print(f"  Point {i}: name={point.name}, labels={point.labels}, value={point.value}")


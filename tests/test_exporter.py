#!/usr/bin/env python3
"""Test the Prometheus exporter directly."""
import sys
sys.path.insert(0, ".")

from prometheus_client import Counter, REGISTRY, generate_latest

# Create a counter with labels
test_counter = Counter(
    "test_requests_total",
    "Test counter",
    ["region", "endpoint"],
    registry=REGISTRY
)

# Set some values
test_counter.labels(region="us", endpoint="/api").inc(5)
test_counter.labels(region="eu", endpoint="/api").inc(3)

# Generate metrics
output = generate_latest(REGISTRY).decode('utf-8')
print(output)

# Check if our metrics are there
if "test_requests_total" in output:
    print("\n✓ Metrics found!")
    for line in output.split('\n'):
        if 'test_requests_total{' in line:
            print(f"  {line}")
else:
    print("\n✗ Metrics NOT found!")


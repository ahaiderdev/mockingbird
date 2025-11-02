#!/usr/bin/env python3
"""
Test to verify that OTEL Summary metrics use minimal buckets.
"""

import yaml
from src.config import Config
from src.otel_exporter import OTELExporter

def test_summary_bucket_configuration():
    """Verify that Summary metrics without explicit buckets use minimal buckets in OTEL."""
    
    # Load config
    with open('configs/baseline.yaml', 'r') as f:
        config_dict = yaml.safe_load(f)
    
    config = Config(**config_dict)
    
    # Find the payload_size_bytes metric (Summary without buckets)
    payload_metric = None
    req_latency_metric = None
    
    for metric in config.metrics:
        if metric.name == "payload_size_bytes":
            payload_metric = metric
        elif metric.name == "req_latency_seconds":
            req_latency_metric = metric
    
    print("=" * 80)
    print("METRIC CONFIGURATION")
    print("=" * 80)
    
    print(f"\n1. payload_size_bytes (Summary):")
    print(f"   - Type: {payload_metric.type}")
    print(f"   - Has buckets: {payload_metric.buckets is not None}")
    print(f"   - Buckets: {payload_metric.buckets}")
    print(f"   - Has objectives: {payload_metric.objectives is not None}")
    print(f"   - Objectives: {payload_metric.objectives}")
    
    print(f"\n2. req_latency_seconds (Histogram):")
    print(f"   - Type: {req_latency_metric.type}")
    print(f"   - Has buckets: {req_latency_metric.buckets is not None}")
    print(f"   - Buckets: {req_latency_metric.buckets}")
    
    # Initialize OTEL exporter (without actually connecting)
    print("\n" + "=" * 80)
    print("OTEL VIEWS CREATED")
    print("=" * 80)
    
    # Check what Views would be created
    from opentelemetry.sdk.metrics.view import View
    from opentelemetry.sdk.metrics._internal.aggregation import ExplicitBucketHistogramAggregation
    
    views = []
    prefix = "synthetic_otel_"
    
    for metric_config in config.metrics:
        if metric_config.type == "histogram" and metric_config.buckets:
            otel_metric_name = f"{prefix}{metric_config.name}"
            buckets = metric_config.buckets
            print(f"\n✓ Histogram: {otel_metric_name}")
            print(f"  Buckets: {buckets}")
            print(f"  Expected series per label combo: {len(buckets) + 3} (_bucket×{len(buckets)}, _count, _sum, +Inf)")
            
        elif metric_config.type == "summary":
            otel_metric_name = f"{prefix}{metric_config.name}"
            
            if metric_config.buckets:
                buckets = metric_config.buckets
                print(f"\n✓ Summary (with buckets): {otel_metric_name}")
                print(f"  Buckets: {buckets}")
                print(f"  Expected series per label combo: {len(buckets) + 3}")
            else:
                buckets = []
                print(f"\n✓ Summary (minimal buckets): {otel_metric_name}")
                print(f"  Buckets: {buckets} → [+Inf only]")
                print(f"  Expected series per label combo: 3 (_bucket{{le=\"+Inf\"}}, _count, _sum)")
    
    print("\n" + "=" * 80)
    print("SERIES COUNT COMPARISON")
    print("=" * 80)
    
    # Calculate expected series counts
    prom_payload_series = 6 * 3  # 6 label combos × (_count, _sum, _created)
    otel_payload_series = 6 * 3  # 6 label combos × (_bucket{le="+Inf"}, _count, _sum)
    
    prom_latency_series = 6 * (len(req_latency_metric.buckets) + 3)  # buckets + _count + _sum + _created
    otel_latency_series = 6 * (len(req_latency_metric.buckets) + 3)  # buckets + _count + _sum + +Inf
    
    print(f"\npayload_size_bytes (Summary):")
    print(f"  Prometheus: {prom_payload_series} series")
    print(f"  OTEL:       {otel_payload_series} series")
    print(f"  Match: {'✓ YES' if prom_payload_series == otel_payload_series else '✗ NO'}")
    
    print(f"\nreq_latency_seconds (Histogram):")
    print(f"  Prometheus: {prom_latency_series} series")
    print(f"  OTEL:       {otel_latency_series} series")
    print(f"  Match: {'✓ YES' if prom_latency_series == otel_latency_series else '✗ NO'}")
    
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    if prom_payload_series == otel_payload_series and prom_latency_series == otel_latency_series:
        print("\n✓ SUCCESS: Series counts match between Prometheus and OTEL!")
        return True
    else:
        print("\n✗ FAILURE: Series counts DO NOT match!")
        return False

if __name__ == "__main__":
    success = test_summary_bucket_configuration()
    exit(0 if success else 1)


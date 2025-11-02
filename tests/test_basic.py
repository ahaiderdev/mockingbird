#!/usr/bin/env python3
"""Basic validation tests for the synthetic metrics generator."""
import sys
import yaml
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config, Config
from src.cardinality import generate_label_space, generate_label_values
from src.generators import create_generator
from src.series import SeriesPoint


def test_config_loading():
    """Test that all example configs load successfully."""
    print("Testing config loading...")
    
    configs = [
        "configs/baseline.yaml",
        "configs/high_cardinality.yaml",
        "configs/production_sim.yaml"
    ]
    
    for config_path in configs:
        try:
            config = load_config(config_path)
            assert isinstance(config, Config)
            assert len(config.metrics) > 0
            print(f"  ✓ {config_path}")
        except Exception as e:
            print(f"  ✗ {config_path}: {e}")
            return False
    
    return True


def test_label_generation():
    """Test label space generation."""
    print("\nTesting label generation...")
    
    from src.config import CardinalityProfile, LabelValueSpec
    
    # Test simple values
    spec = LabelValueSpec(values=["a", "b", "c"])
    values = generate_label_values(spec)
    assert values == ["a", "b", "c"]
    print("  ✓ Simple values")
    
    # Test range
    spec = LabelValueSpec(range=[1, 5], fmt="i-%02d")
    values = generate_label_values(spec)
    expected = ["i-01", "i-02", "i-03", "i-04", "i-05"]
    assert values == expected, f"Expected {expected}, got {values}"
    print("  ✓ Range with format")
    
    # Test Cartesian product
    profile = CardinalityProfile(
        labels={
            "region": LabelValueSpec(values=["us", "eu"]),
            "az": LabelValueSpec(values=["a", "b"])
        }
    )
    combinations = generate_label_space(profile)
    assert len(combinations) == 4  # 2 * 2
    print(f"  ✓ Cartesian product: {len(combinations)} combinations")
    
    # Test with cap
    profile = CardinalityProfile(
        labels={
            "id": LabelValueSpec(range=[1, 100])
        },
        series_cap=10
    )
    combinations = generate_label_space(profile)
    assert len(combinations) == 10
    print(f"  ✓ Series cap: limited to {len(combinations)}")
    
    return True


def test_generator_creation():
    """Test that generators can be created and produce values."""
    print("\nTesting generator creation...")
    
    from src.config import MetricConfig
    
    # Test counter
    config = MetricConfig(
        name="test_counter",
        type="counter",
        profile="test",
        algorithm="poisson",
        base_rate=5.0
    )
    labels = [{"region": "us"}, {"region": "eu"}]
    gen = create_generator(config, labels, global_seed=42)
    points = list(gen.tick(0))
    assert len(points) == 2
    assert all(isinstance(p, SeriesPoint) for p in points)
    print("  ✓ Counter generator")
    
    # Test gauge
    config = MetricConfig(
        name="test_gauge",
        type="gauge",
        profile="test",
        algorithm="random_walk",
        start=0.5,
        step=0.1
    )
    gen = create_generator(config, labels, global_seed=42)
    points = list(gen.tick(0))
    assert len(points) == 2
    print("  ✓ Gauge generator")
    
    # Test histogram
    config = MetricConfig(
        name="test_histogram",
        type="histogram",
        profile="test",
        algorithm="lognormal",
        mu=-2.0,
        sigma=0.5,
        buckets=[0.1, 0.5, 1.0]
    )
    gen = create_generator(config, labels, global_seed=42)
    points = list(gen.tick(0))
    assert len(points) == 2
    print("  ✓ Histogram generator")
    
    # Test summary
    config = MetricConfig(
        name="test_summary",
        type="summary",
        profile="test",
        algorithm="lognormal",
        mu=7.0,
        sigma=1.0,
        objectives={0.5: 0.01, 0.9: 0.01}
    )
    gen = create_generator(config, labels, global_seed=42)
    points = list(gen.tick(0))
    assert len(points) == 2
    print("  ✓ Summary generator")
    
    return True


def test_determinism():
    """Test that generators produce deterministic output with same seed."""
    print("\nTesting determinism...")
    
    from src.config import MetricConfig
    
    config = MetricConfig(
        name="test_counter",
        type="counter",
        profile="test",
        algorithm="poisson",
        base_rate=5.0
    )
    labels = [{"region": "us"}]
    
    # Generate with seed 42
    gen1 = create_generator(config, labels, global_seed=42)
    points1 = [list(gen1.tick(t)) for t in range(10)]
    
    # Generate again with same seed
    gen2 = create_generator(config, labels, global_seed=42)
    points2 = [list(gen2.tick(t)) for t in range(10)]
    
    # Compare values
    for tick_idx in range(10):
        for point_idx in range(len(points1[tick_idx])):
            val1 = points1[tick_idx][point_idx].value
            val2 = points2[tick_idx][point_idx].value
            assert val1 == val2, f"Values differ at tick {tick_idx}: {val1} != {val2}"
    
    print("  ✓ Deterministic generation confirmed")
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Synthetic Metrics Generator - Basic Validation")
    print("=" * 60)
    
    tests = [
        test_config_loading,
        test_label_generation,
        test_generator_creation,
        test_determinism
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


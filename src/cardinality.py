"""Cardinality management and label space generation."""
from typing import Dict, List, Iterator
import hashlib
from src.config import CardinalityProfile, LabelValueSpec


def generate_label_values(spec: LabelValueSpec) -> List[str]:
    """Generate list of label values from specification."""
    if spec.values is not None:
        return spec.values

    if spec.range is not None:
        start, end = spec.range
        fmt = spec.fmt or "{}"
        # Support both % formatting and {} formatting
        if '%' in fmt:
            return [fmt % i for i in range(start, end + 1)]
        else:
            return [fmt.format(i) for i in range(start, end + 1)]

    return []


def generate_label_space(
    profile: CardinalityProfile,
    additional_labels: Dict[str, LabelValueSpec] = None
) -> List[Dict[str, str]]:
    """
    Generate Cartesian product of all label combinations.

    Args:
        profile: Cardinality profile with label specifications
        additional_labels: Additional metric-specific labels

    Returns:
        List of label dictionaries
    """
    # Merge profile labels with additional labels
    all_label_specs = dict(profile.labels)
    if additional_labels:
        all_label_specs.update(additional_labels)

    if not all_label_specs:
        return [{}]

    # Generate values for each label
    label_names = list(all_label_specs.keys())
    label_value_lists = [
        generate_label_values(all_label_specs[name])
        for name in label_names
    ]

    # Cartesian product
    def cartesian_product(lists: List[List[str]]) -> Iterator[List[str]]:
        if not lists:
            yield []
            return

        for item in lists[0]:
            for rest in cartesian_product(lists[1:]):
                yield [item] + rest

    label_combinations = []
    for value_combo in cartesian_product(label_value_lists):
        label_dict = dict(zip(label_names, value_combo))
        label_combinations.append(label_dict)

    # Apply series cap if specified
    if profile.series_cap and len(label_combinations) > profile.series_cap:
        label_combinations = apply_series_cap(
            label_combinations,
            profile.series_cap,
            profile.sampling_strategy
        )

    return label_combinations


def apply_series_cap(
    label_combinations: List[Dict[str, str]],
    cap: int,
    strategy: str
) -> List[Dict[str, str]]:
    """
    Apply series cap using specified sampling strategy.

    Args:
        label_combinations: Full list of label combinations
        cap: Maximum number of series
        strategy: Sampling strategy ("first_n" or "hash")

    Returns:
        Sampled list of label combinations
    """
    if strategy == "first_n":
        return label_combinations[:cap]

    elif strategy == "hash":
        # Hash-based sampling for deterministic selection
        def label_hash(labels: Dict[str, str]) -> int:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return int(hashlib.md5(label_str.encode()).hexdigest(), 16)

        # Sort by hash and take first N
        sorted_by_hash = sorted(label_combinations, key=label_hash)
        return sorted_by_hash[:cap]

    return label_combinations[:cap]


def validate_label_names(labels: Dict[str, str]) -> bool:
    """
    Validate label names are Prometheus-safe.

    Label names must match [a-zA-Z_][a-zA-Z0-9_]*
    """
    import re
    pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    for name in labels.keys():
        if not pattern.match(name):
            return False

    return True

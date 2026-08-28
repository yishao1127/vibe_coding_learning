"""Shared histogram construction and descriptive return statistics."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

DEFAULT_BIN_WIDTH = 0.05
DEFAULT_QUANTILES = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)


@dataclass(frozen=True)
class DistributionStats:
    count: int
    mean: float
    population_stddev: float
    minimum: float
    maximum: float
    quantiles: dict[float, float]
    loss_probability: float
    break_even_probability: float
    profit_probability: float
    bin_edges: tuple[float, ...]
    bin_counts: tuple[int, ...]
    bin_probabilities: tuple[float, ...]
    cdf: tuple[float, ...]


def _finite_values(values: Iterable[float]) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if not result:
        raise ValueError("at least one return is required")
    if not all(math.isfinite(value) for value in result):
        raise ValueError("returns must be finite")
    return result


def shared_histogram_edges(
    datasets: Iterable[Iterable[float]],
    bin_width: float = DEFAULT_BIN_WIDTH,
) -> tuple[float, ...]:
    """Build common bin edges aligned to zero at fixed-width intervals."""

    if not math.isfinite(bin_width) or bin_width <= 0:
        raise ValueError("bin_width must be finite and positive")
    flattened = tuple(float(value) for data in datasets for value in data)
    values = _finite_values(flattened)
    lower_steps = math.floor(min(values) / bin_width)
    upper_steps = math.ceil(max(values) / bin_width)
    # Ensure extrema on an edge still belong to a half-open final bin.
    if math.isclose(max(values), upper_steps * bin_width, rel_tol=0.0, abs_tol=1e-12):
        upper_steps += 1
    if lower_steps == upper_steps:
        upper_steps += 1
    return tuple(step * bin_width for step in range(lower_steps, upper_steps + 1))


def _quantile(sorted_values: Sequence[float], probability: float) -> float:
    if not 0 <= probability <= 1:
        raise ValueError("quantile probabilities must be between 0 and 1")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    fraction = position - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction


def summarize_distribution(
    values: Iterable[float],
    bin_edges: Sequence[float],
    quantile_probabilities: Sequence[float] = DEFAULT_QUANTILES,
) -> DistributionStats:
    """Compute moments, quantiles, sign probabilities, histogram, and CDF."""

    data = _finite_values(values)
    edges = tuple(float(edge) for edge in bin_edges)
    if len(edges) < 2 or any(right <= left for left, right in zip(edges, edges[1:])):
        raise ValueError("bin_edges must be strictly increasing")
    if min(data) < edges[0] or max(data) > edges[-1]:
        raise ValueError("bin_edges must cover all returns")

    counts = [0] * (len(edges) - 1)
    for value in data:
        index = min(bisect_bin(edges, value), len(counts) - 1)
        counts[index] += 1

    count = len(data)
    mean = math.fsum(data) / count
    variance = math.fsum((value - mean) ** 2 for value in data) / count
    probabilities = tuple(value / count for value in counts)
    cumulative = 0.0
    cdf_values = []
    for probability in probabilities:
        cumulative += probability
        cdf_values.append(cumulative)
    sorted_data = sorted(data)
    losses = sum(value < 0 for value in data)
    break_even = sum(value == 0 for value in data)
    profits = sum(value > 0 for value in data)
    return DistributionStats(
        count=count,
        mean=mean,
        population_stddev=math.sqrt(variance),
        minimum=sorted_data[0],
        maximum=sorted_data[-1],
        quantiles={
            probability: _quantile(sorted_data, probability)
            for probability in quantile_probabilities
        },
        loss_probability=losses / count,
        break_even_probability=break_even / count,
        profit_probability=profits / count,
        bin_edges=edges,
        bin_counts=tuple(counts),
        bin_probabilities=probabilities,
        cdf=tuple(cdf_values),
    )


def bisect_bin(edges: Sequence[float], value: float) -> int:
    """Locate a value in left-closed/right-open bins (last bin closed)."""

    from bisect import bisect_right

    return bisect_right(edges, value) - 1


def analyze_distributions(
    datasets: Mapping[object, Iterable[float]],
    bin_width: float = DEFAULT_BIN_WIDTH,
    quantile_probabilities: Sequence[float] = DEFAULT_QUANTILES,
) -> tuple[tuple[float, ...], dict[object, DistributionStats]]:
    """Analyze named datasets using one shared set of histogram boundaries."""

    materialized = {key: tuple(values) for key, values in datasets.items()}
    if not materialized:
        raise ValueError("at least one dataset is required")
    edges = shared_histogram_edges(materialized.values(), bin_width)
    return edges, {
        key: summarize_distribution(values, edges, quantile_probabilities)
        for key, values in materialized.items()
    }

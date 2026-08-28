"""NASDAQ-100 historical return analysis core API."""

from .backtest import (
    DEFAULT_HORIZONS_MONTHS,
    Backtester,
    BacktestSample,
    add_calendar_months,
    run_backtests,
)
from .data import (
    DEFAULT_START_DATE,
    DataMetadata,
    PriceSeries,
    file_sha256,
    load_csv_price_data,
    load_data,
    load_price_data,
)
from .distribution import (
    DEFAULT_BIN_WIDTH,
    DEFAULT_QUANTILES,
    DistributionStats,
    analyze_distributions,
    shared_histogram_edges,
    summarize_distribution,
)

__all__ = [
    "DEFAULT_BIN_WIDTH",
    "DEFAULT_HORIZONS_MONTHS",
    "DEFAULT_QUANTILES",
    "DEFAULT_START_DATE",
    "BacktestSample",
    "Backtester",
    "DataMetadata",
    "DistributionStats",
    "PriceSeries",
    "add_calendar_months",
    "analyze_distributions",
    "file_sha256",
    "load_csv_price_data",
    "load_data",
    "load_price_data",
    "run_backtests",
    "shared_histogram_edges",
    "summarize_distribution",
]

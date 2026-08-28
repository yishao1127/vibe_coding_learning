"""Shared payload and audit builders for one or more index price series."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from .backtest import DEFAULT_HORIZONS_MONTHS, run_backtests
from .data import PriceSeries
from .distribution import DEFAULT_QUANTILES

HORIZON_LABELS = {1: "1 个月", 3: "3 个月", 6: "6 个月", 12: "1 年", 36: "3 年", 60: "5 年"}
STRATEGY_LABELS = {"single_purchase": "一次性买入", "daily_investment": "每日定投"}


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def build_dataset(
    series: PriceSeries,
    *,
    dataset_id: str,
    market_id: str,
    market_label: str,
    price_label: str,
    title: str,
    subtitle: str,
    unit_amount: float,
    price_note: str,
    horizons: Sequence[int] = DEFAULT_HORIZONS_MONTHS,
) -> tuple[dict, dict]:
    """Run one isolated point series and return its report dataset and results."""

    if not series.dates:
        raise ValueError(f"{market_label} {price_label} 没有有效点位")
    results = run_backtests(series, horizons, daily_amount=unit_amount)
    horizon_samples = []
    for months in horizons:
        single_samples = results["single_purchase"][months]
        daily_samples = results["daily_investment"][months]
        if len(single_samples) != len(daily_samples):
            raise RuntimeError(f"{dataset_id} {months} 个月的两种策略样本未对齐")
        if any(single.start_date != daily.start_date for single, daily in zip(single_samples, daily_samples, strict=True)):
            raise RuntimeError(f"{dataset_id} {months} 个月的两种策略起点未对齐")
        horizon_samples.append({
            "horizon_months": months,
            "start_dates": [sample.start_date.isoformat() for sample in single_samples],
            "returns": {
                "single_purchase": [sample.return_rate for sample in single_samples],
                "daily_investment": [sample.return_rate for sample in daily_samples],
            },
            "maximum_losses": {
                "single_purchase": [sample.maximum_loss for sample in single_samples],
                "daily_investment": [sample.maximum_loss for sample in daily_samples],
            },
        })
    metadata = series.metadata
    start_dates = [value for horizon in horizon_samples for value in horizon["start_dates"]]
    dataset = {
        "id": dataset_id,
        "market_id": market_id,
        "market_label": market_label,
        "price_label": price_label,
        "title": title,
        "subtitle": subtitle,
        "price_note": price_note,
        "analysis_config": {
            "bin_width": 0.05,
            "quantile_probabilities": list(DEFAULT_QUANTILES),
            "date_filter_basis": "start_date",
            "date_interval": "closed",
            "minimum_date": _iso(metadata.first_date),
            "maximum_date": _iso(metadata.last_date),
            "default_start_date": min(start_dates) if start_dates else _iso(metadata.first_date),
            "default_end_date": _iso(metadata.last_date),
        },
        "horizon_samples": horizon_samples,
        "metadata": {
            "source_file": Path(metadata.source_path).name,
            "source_sha256": metadata.sha256,
            "source_rows": metadata.total_rows,
            "source_valid_prices": metadata.valid_price_rows,
            "source_missing_prices": metadata.missing_price_rows,
            "source_date_range": f"{_iso(metadata.source_first_date)} 至 {_iso(metadata.source_last_date)}",
            "analysis_start": _iso(metadata.first_date),
            "analysis_end": _iso(metadata.last_date),
            "analysis_trading_days": metadata.retained_price_rows,
            "unit_amount": unit_amount,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
    }
    return dataset, results


def build_report_payload(
    datasets: Sequence[Mapping[str, Any]],
    *,
    default_dataset_id: str,
    default_strategy: str = "single_purchase",
    default_horizon_months: int = 12,
) -> dict:
    """Build a multi-dataset payload while retaining legacy top-level fields."""

    materialized = [dict(dataset) for dataset in datasets]
    if not materialized:
        raise ValueError("at least one dataset is required")
    default = next((item for item in materialized if item["id"] == default_dataset_id), None)
    if default is None:
        raise ValueError("default_dataset_id is not present")
    payload = {
        "report_mode": "multi_market" if len(materialized) > 1 else "single_market",
        "default_dataset_id": default_dataset_id,
        "default_strategy": default_strategy,
        "default_horizon_months": default_horizon_months,
        "strategy_labels": STRATEGY_LABELS,
        "horizon_labels": {str(key): value for key, value in HORIZON_LABELS.items()},
        "datasets": materialized,
    }
    # Existing generated NDX consumers and tests can continue reading these keys.
    for key in ("title", "subtitle", "analysis_config", "horizon_samples", "metadata"):
        payload[key] = default[key]
    return payload


def write_dataset_audit_csv(
    results_by_dataset: Mapping[str, Mapping],
    dataset_labels: Mapping[str, Mapping[str, str]],
    output_path: str | Path,
    horizons: Sequence[int] = DEFAULT_HORIZONS_MONTHS,
) -> Path:
    """Write auditable samples, ordered by point series, horizon, then start date."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "dataset_id", "market", "price_basis", "horizon_months", "start_date", "target_end_date",
        "actual_end_date", "following_days", "start_price", "end_price", "daily_contribution_count",
        "daily_unit_amount", "daily_principal", "daily_ending_value", "single_purchase_return",
        "daily_investment_return", "single_maximum_loss", "single_maximum_loss_date",
        "single_maximum_loss_price", "single_maximum_loss_principal", "single_maximum_loss_units",
        "single_maximum_loss_value", "daily_maximum_loss", "daily_maximum_loss_date",
        "daily_maximum_loss_price", "daily_maximum_loss_contribution_count",
        "daily_maximum_loss_principal", "daily_maximum_loss_units", "daily_maximum_loss_value",
    ]
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for dataset_id, results in results_by_dataset.items():
            labels = dataset_labels[dataset_id]
            for months in horizons:
                single_samples = results["single_purchase"][months]
                daily_samples = results["daily_investment"][months]
                if len(single_samples) != len(daily_samples):
                    raise RuntimeError(f"{dataset_id} {months} 个月的两种策略样本未对齐")
                for single, daily in zip(single_samples, daily_samples, strict=True):
                    if (single.start_date, single.end_date) != (daily.start_date, daily.end_date):
                        raise RuntimeError(f"{dataset_id} {months} 个月的两种策略日期未对齐")
                    writer.writerow({
                        "dataset_id": dataset_id,
                        "market": labels["market"],
                        "price_basis": labels["price_basis"],
                        "horizon_months": months,
                        "start_date": single.start_date.isoformat(),
                        "target_end_date": single.target_end_date.isoformat(),
                        "actual_end_date": single.end_date.isoformat(),
                        "following_days": (single.end_date - single.target_end_date).days,
                        "start_price": f"{single.start_price:.10g}",
                        "end_price": f"{single.end_price:.10g}",
                        "daily_contribution_count": daily.contribution_count,
                        "daily_unit_amount": f"{daily.contribution:.10g}",
                        "daily_principal": f"{daily.principal:.10g}",
                        "daily_ending_value": f"{daily.ending_value:.10g}",
                        "single_purchase_return": f"{single.return_rate:.12g}",
                        "daily_investment_return": f"{daily.return_rate:.12g}",
                        "single_maximum_loss": f"{single.maximum_loss:.12g}",
                        "single_maximum_loss_date": single.maximum_loss_date.isoformat(),
                        "single_maximum_loss_price": f"{single.maximum_loss_price:.10g}",
                        "single_maximum_loss_principal": f"{single.maximum_loss_principal:.10g}",
                        "single_maximum_loss_units": f"{single.maximum_loss_units:.12g}",
                        "single_maximum_loss_value": f"{single.maximum_loss_value:.12g}",
                        "daily_maximum_loss": f"{daily.maximum_loss:.12g}",
                        "daily_maximum_loss_date": daily.maximum_loss_date.isoformat(),
                        "daily_maximum_loss_price": f"{daily.maximum_loss_price:.10g}",
                        "daily_maximum_loss_contribution_count": daily.maximum_loss_contribution_count,
                        "daily_maximum_loss_principal": f"{daily.maximum_loss_principal:.10g}",
                        "daily_maximum_loss_units": f"{daily.maximum_loss_units:.12g}",
                        "daily_maximum_loss_value": f"{daily.maximum_loss_value:.12g}",
                    })
    return output.resolve()

"""Generate the unified offline NASDAQ-100 and CSI 300 return report."""

from __future__ import annotations

import argparse
from pathlib import Path

from .core.data import load_csv_price_data
from .core.pipeline import build_dataset, build_report_payload, write_dataset_audit_csv
from .core.report import write_report

TASK_DIR = Path(__file__).parent

DEFAULT_NDX_INPUT = TASK_DIR / "data" / "NASDAQ100.csv"
DEFAULT_CSI300_INPUT = TASK_DIR / "data" / "沪深300_PE-TTM_市值加权_上市以来_20260803_161620.csv"
DEFAULT_OUTPUT = TASK_DIR / "output" / "index_return_backtest.html"
DEFAULT_AUDIT = TASK_DIR / "output" / "index_return_samples.csv"


def build_multi_market_analysis(
    ndx_input: str | Path = DEFAULT_NDX_INPUT,
    csi300_input: str | Path = DEFAULT_CSI300_INPUT,
    *,
    unit_amount: float = 100.0,
) -> tuple[dict, dict, dict]:
    """Load three isolated point series and build the unified payload."""

    if unit_amount <= 0:
        raise ValueError("unit_amount 必须为正数")
    ndx = load_csv_price_data(
        ndx_input, date_column="observation_date", price_column="NASDAQ100", sort_order="ascending"
    )
    csi_close = load_csv_price_data(
        csi300_input, date_column="日期", price_column="收盘点位", sort_order="descending",
        ignore_trailing_notes=True,
    )
    csi_total = load_csv_price_data(
        csi300_input, date_column="日期", price_column="全收益收盘点位(元)", sort_order="descending",
        ignore_trailing_notes=True,
    )
    definitions = [
        (ndx, "ndx_close", "ndx", "NASDAQ-100", "收盘点位", "NASDAQ-100 历史收益频率分布", "比较一次性买入与逐交易日等额定投。", "NASDAQ-100 收盘指数口径，不含股息再投资。"),
        (csi_close, "csi300_close", "csi300", "沪深300", "收盘点位", "沪深300历史收益频率分布", "普通收盘点位口径；比较一次性买入与逐交易日等额定投。", "普通收盘点位，不含股息再投资。"),
        (csi_total, "csi300_total_return", "csi300", "沪深300", "全收益收盘点位(元)", "沪深300历史收益频率分布", "全收益收盘点位口径；比较一次性买入与逐交易日等额定投。", "全收益收盘点位反映现金分红再投资；与普通收盘点位独立回测，不插值、不混算。"),
    ]
    datasets = []
    results_by_dataset = {}
    labels = {}
    series_by_dataset = {}
    for series, dataset_id, market_id, market_label, price_label, title, subtitle, price_note in definitions:
        dataset, results = build_dataset(
            series, dataset_id=dataset_id, market_id=market_id, market_label=market_label,
            price_label=price_label, title=title, subtitle=subtitle, unit_amount=unit_amount,
            price_note=price_note,
        )
        datasets.append(dataset)
        results_by_dataset[dataset_id] = results
        labels[dataset_id] = {"market": market_label, "price_basis": price_label}
        series_by_dataset[dataset_id] = series
    payload = build_report_payload(datasets, default_dataset_id="ndx_close")
    return payload, results_by_dataset, series_by_dataset


def generate_multi_market_analysis(
    ndx_input: str | Path = DEFAULT_NDX_INPUT,
    csi300_input: str | Path = DEFAULT_CSI300_INPUT,
    output_path: str | Path = DEFAULT_OUTPUT,
    audit_path: str | Path = DEFAULT_AUDIT,
    *,
    unit_amount: float = 100.0,
) -> tuple[Path, Path, dict, dict]:
    """Generate the unified report and audit CSV for all datasets."""

    payload, results, series = build_multi_market_analysis(ndx_input, csi300_input, unit_amount=unit_amount)
    report = write_report(payload, output_path)
    labels = {
        "ndx_close": {"market": "NASDAQ-100", "price_basis": "收盘点位"},
        "csi300_close": {"market": "沪深300", "price_basis": "收盘点位"},
        "csi300_total_return": {"market": "沪深300", "price_basis": "全收益收盘点位(元)"},
    }
    audit = write_dataset_audit_csv(results, labels, audit_path)
    return report, audit, payload, series


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 NASDAQ-100 与沪深300统一离线回测报告")
    parser.add_argument("--ndx-input", type=Path, default=DEFAULT_NDX_INPUT)
    parser.add_argument("--csi300-input", type=Path, default=DEFAULT_CSI300_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--unit-amount", type=float, default=100.0)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report, audit, payload, series = generate_multi_market_analysis(
        args.ndx_input, args.csi300_input, args.output, args.audit_output, unit_amount=args.unit_amount
    )
    print(f"HTML report: {report}")
    print(f"Audit CSV: {audit}")
    for dataset in payload["datasets"]:
        item = series[dataset["id"]]
        counts = {sample["horizon_months"]: len(sample["start_dates"]) for sample in dataset["horizon_samples"]}
        print(f"{dataset['id']}: prices={len(item)}, samples={counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

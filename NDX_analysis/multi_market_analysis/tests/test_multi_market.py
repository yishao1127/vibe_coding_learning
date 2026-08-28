import csv
import tempfile
import unittest
from pathlib import Path

from multi_market_analysis.run_analysis import build_multi_market_analysis, generate_multi_market_analysis


class MultiMarketTests(unittest.TestCase):
    def make_sources(self, root: Path) -> tuple[Path, Path]:
        ndx = root / "NASDAQ100.csv"
        csi = root / "csi.csv"
        dates = ["2020-01-02", "2020-02-03", "2020-04-02", "2021-01-04", "2023-01-03", "2025-01-02"]
        with ndx.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream); writer.writerow(["observation_date", "NASDAQ100"])
            writer.writerows((value, 100 + index * 10) for index, value in enumerate(dates))
        with csi.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream); writer.writerow(["日期", "收盘点位", "全收益收盘点位(元)"])
            for index, value in reversed(list(enumerate(dates))):
                writer.writerow([value, f"={3000 + index * 10}", "" if index == 0 else f"={4000 + index * 20}"])
            writer.writerow([]); writer.writerow(["数据来源于：测试"])
        return ndx, csi

    def test_builds_three_isolated_datasets_and_dynamic_ranges(self):
        with tempfile.TemporaryDirectory() as directory:
            ndx, csi = self.make_sources(Path(directory))
            payload, results, series = build_multi_market_analysis(ndx, csi)
            self.assertEqual([item["id"] for item in payload["datasets"]], ["ndx_close", "csi300_close", "csi300_total_return"])
            self.assertEqual(len(results), 3)
            self.assertEqual(len(series["csi300_close"]), 6)
            self.assertEqual(len(series["csi300_total_return"]), 5)
            total = payload["datasets"][2]
            self.assertEqual(total["analysis_config"]["minimum_date"], "2020-02-03")
            self.assertEqual(total["analysis_config"]["maximum_date"], "2025-01-02")

    def test_generates_single_offline_html_and_complete_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); ndx, csi = self.make_sources(root)
            report, audit, payload, _ = generate_multi_market_analysis(ndx, csi, root / "index.html", root / "audit.csv")
            html = report.read_text(encoding="utf-8")
            self.assertIn("market-filter", html)
            self.assertIn("全收益收盘点位(元)", html)
            self.assertNotRegex(html, r'(?i)(?:src|href)\s*=\s*["\']\s*https?://')
            with audit.open(encoding="utf-8-sig") as stream:
                rows = list(csv.DictReader(stream))
            self.assertGreater(len(rows), 0)
            self.assertEqual(
                {row["dataset_id"] for row in rows},
                {"ndx_close", "csi300_close", "csi300_total_return"},
            )
            self.assertEqual(len(payload["datasets"]), 3)
            self.assertIn("maximum_losses", payload["datasets"][0]["horizon_samples"][0])
            self.assertIn("daily_maximum_loss_value", rows[0])
            self.assertIn("历史最大亏损分布", html)
            self.assertIn("历史收益分布", html)
            self.assertIn('value === "历史收益分布" || value === "最大亏损频率分布" ? "distribution-column"', html)
            self.assertIn("最大亏损频率分布", html)
            self.assertIn("P100", html)
            self.assertNotIn("≥10%样本占比", html)


if __name__ == "__main__":
    unittest.main()

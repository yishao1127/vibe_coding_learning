import json
import re
import tempfile
import unittest
from pathlib import Path

from multi_market_analysis.core.report import build_report_html, write_report


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "title": "NDX 测试报告",
            "subtitle": "最小测试数据",
            "default_strategy": "single_purchase",
            "default_horizon_months": 1,
            "strategy_labels": {
                "single_purchase": "一次性买入",
                "daily_investment": "每日定投",
            },
            "analysis_config": {
                "bin_width": 0.05,
                "quantile_probabilities": [0.1, 0.5, 0.9],
                "default_start_date": "2020-01-02",
                "default_end_date": "2020-01-07",
            },
            "horizon_samples": [{
                "horizon_months": 1,
                "start_dates": ["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07"],
                "returns": {
                    "single_purchase": [-0.08, 0.0, 0.04, 0.2],
                    "daily_investment": [-0.04, 0.01, 0.03, 0.1],
                },
                "maximum_losses": {
                    "single_purchase": [0.08, 0.02, 0.0, 0.01],
                    "daily_investment": [0.04, 0.01, 0.0, 0.0],
                },
            }],
            "metadata": {"sha256": "abc123", "first_date": "2005-01-03"},
        }

    def test_builds_offline_chinese_report_with_required_mounts(self):
        html = build_report_html(self.payload)

        required_text = (
            "核心指标",
            "样本数",
            "平均收益率",
            "中位数",
            "盈利样本占比",
            "较差情景收益率（P10）",
            "较好情景收益率（P90）",
            "历史收益率频率分布",
            "累计概率（CDF）",
            "12 组合汇总表",
            "近2年",
            "近5年",
            "近10年",
            "近15年",
            "近20年",
            "累计收益率均值",
            "累计收益率中位数",
            "历史收益分布",
            "数据与回测口径",
            "投入金额 X",
            "不影响收益率",
            "历史最大亏损分布",
            "最大亏损平均值",
            "最大亏损中位数",
            "最大亏损P90",
            "P100",
            "最大亏损频率分布",
            "最大亏损口径与限制",
            "恢复默认",
        )
        for text in required_text:
            self.assertIn(text, html)

        required_ids = (
            "market-filter",
            "price-basis-filter",
            "strategy-filter",
            "horizon-filter",
            "start-date-filter",
            "end-date-filter",
            "date-presets",
            "date-filter-message",
            "theme-toggle",
            "kpi-grid",
            "histogram-chart",
            "cdf-chart",
            "summary-table-head",
            "summary-table-body",
            "risk-summary-table-body",
            "report-data",
        )
        for element_id in required_ids:
            self.assertIn(f'id="{element_id}"', html)

        self.assertIn("<svg", html)
        self.assertIn("tabindex", html)
        self.assertIn("textContent", html)
        self.assertIn("@media print", html)
        self.assertIn("@media (max-width:", html)
        self.assertIn("回测起点开始（含）", html)
        self.assertIn("computeAllStatistics", html)
        self.assertIn("module.exports", html)
        self.assertIn('<th scope="col">期限</th><th scope="col" class="strategy-column">策略</th>', html)
        self.assertIn("summary-row", html)
        self.assertIn("return-positive", html)
        self.assertIn("横轴按当前筛选结果的实际范围自动调整", html)
        self.assertNotIn("完整区间频率表", html)
        self.assertNotIn("分位数表", html)
        self.assertNotIn('id="interval-table-body"', html)
        self.assertNotIn('id="quantile-table-body"', html)
        summary_headers = re.search(r'<thead id="summary-table-head"><tr>(.*?)</tr></thead>', html).group(1)
        self.assertLess(summary_headers.index("样本数"), summary_headers.index("盈利样本占比"))
        self.assertLess(summary_headers.index("盈利样本占比"), summary_headers.index("累计收益率均值"))
        self.assertIn('class="strategy-column"', summary_headers)
        self.assertIn('class="distribution-column">历史收益分布</th>', summary_headers)
        self.assertTrue(summary_headers.endswith('class="distribution-column">历史收益分布</th>'))
        self.assertIn('node.appendChild(element("span", "strategy-badge"', html)
        self.assertIn('const labels = ["期限", "策略", "样本数", "盈利样本占比", "累计收益率均值", "累计收益率中位数", "较差情景收益率（P10）", "较好情景收益率（P90）", "历史收益分布"]', html)
        self.assertIn('viewBox: "0 0 96 28"', html)
        self.assertIn('class: "spark-histogram", tabindex: "0", role: "img"', html)
        self.assertNotIn('class: "spark-bar negative", tabindex:', html)
        self.assertNotIn('class: "spark-bar", tabindex:', html)
        self.assertIn('node.appendChild(element("span", "spark-empty", "—"))', html)
        self.assertIn("renderDatasetHeader(els.summary", html)
        self.assertIn("renderDatasetHeader(els.riskSummary", html)
        self.assertIn("els.summaryHead.hidden = marketDatasets.length > 1", html)
        self.assertIn("els.riskSummaryHead.hidden = marketDatasets.length > 1", html)
        self.assertIn('value === "历史收益分布" || value === "最大亏损频率分布" ? "distribution-column"', html)
        risk_headers = re.search(r'<thead id="risk-summary-table-head"><tr>(.*?)</tr></thead>', html).group(1)
        expected_risk_headers = ["期限", "策略", "样本数", "最大亏损平均值", "最大亏损中位数", "最大亏损P90", "P95", "P100", "最大亏损频率分布"]
        self.assertEqual(re.findall(r">([^<>]+)</th>", risk_headers), expected_risk_headers)
        self.assertIn('class="distribution-column">最大亏损频率分布</th>', risk_headers)
        self.assertIn('const labels = ["期限", "策略", "样本数", "最大亏损平均值", "最大亏损中位数", "最大亏损P90", "P95", "P100", "最大亏损频率分布"]', html)
        self.assertIn('class: "spark-histogram risk-spark-histogram", tabindex: "0", role: "img"', html)
        self.assertIn('class: "spark-loss-baseline"', html)
        self.assertIn('class: "spark-loss-bar"', html)
        self.assertIn('2% 区间从 0% 起', html)
        for removed in ("≥10%样本占比", "≥20%样本占比", "≥30%样本占比", "item.atLeast10", "item.atLeast20", "item.atLeast30", "item.worst"):
            self.assertNotIn(removed, html)

    def test_contains_no_external_http_or_cdn_resources(self):
        html = build_report_html(self.payload)
        self.assertNotRegex(html, r"(?i)(?:src|href)\s*=\s*[\"']\s*https?://")
        self.assertNotRegex(html, r"(?i)\b(?:cdn|unpkg|jsdelivr|cdnjs)\b")
        self.assertNotIn("<link ", html.lower())

    def test_json_script_escapes_script_terminator_and_html_characters(self):
        payload = dict(self.payload)
        payload["subtitle"] = "危险 </script><script>alert('x')</script> & 数据"
        html = build_report_html(payload)
        match = re.search(
            r'<script id="report-data" type="application/json">(.*?)</script>',
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        encoded = match.group(1)
        self.assertNotIn("</script", encoded.lower())
        self.assertNotIn("<script", encoded.lower())
        self.assertIn("\\u003c/script\\u003e", encoded)
        self.assertIn("\\u0026", encoded)
        self.assertEqual(json.loads(encoded)["subtitle"], payload["subtitle"])

    def test_rejects_non_mapping_payload(self):
        with self.assertRaises(TypeError):
            build_report_html([])

    def test_write_report_writes_utf8_single_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "report.html"
            resolved = write_report(self.payload, output)
            self.assertEqual(resolved, output.resolve())
            self.assertTrue(output.is_file())
            content = output.read_text(encoding="utf-8")
            self.assertIn("NDX 测试报告", content)
            self.assertIn("application/json", content)


if __name__ == "__main__":
    unittest.main()

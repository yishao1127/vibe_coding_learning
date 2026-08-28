import hashlib
import tempfile
import unittest
from datetime import date
from pathlib import Path

from multi_market_analysis.core.data import load_csv_price_data, load_price_data


class LoadPriceDataTests(unittest.TestCase):
    def write_csv(self, content: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "data.csv"
        path.write_text(content, encoding="utf-8")
        return path

    def test_loads_filters_and_audits_data(self):
        content = (
            "observation_date,NASDAQ100\n"
            "2004-12-31,100\n"
            "2005-01-01,.\n"
            "2005-01-03,102.5\n"
            "2005-01-04,\n"
            "2005-01-05,103\n"
        )
        path = self.write_csv(content)
        series = load_price_data(path)
        self.assertEqual(series.dates, (date(2005, 1, 3), date(2005, 1, 5)))
        self.assertEqual(series.prices, (102.5, 103.0))
        self.assertEqual(series.metadata.total_rows, 5)
        self.assertEqual(series.metadata.missing_price_rows, 2)
        self.assertEqual(series.metadata.filtered_before_start, 1)
        self.assertEqual(series.metadata.valid_price_rows, 3)
        self.assertEqual(series.metadata.retained_price_rows, 2)
        self.assertEqual(series.metadata.sha256, hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(series.metadata.source_first_date, date(2004, 12, 31))
        self.assertEqual(series.metadata.source_last_date, date(2005, 1, 5))
        self.assertEqual(series.metadata.first_date, date(2005, 1, 3))

    def test_rejects_duplicate_or_descending_dates_even_when_price_missing(self):
        path = self.write_csv(
            "observation_date,NASDAQ100\n"
            "2005-01-03,.\n"
            "2005-01-03,100\n"
        )
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            load_price_data(path)

    def test_requires_columns_and_positive_prices(self):
        path = self.write_csv("date,value\n2005-01-03,100\n")
        with self.assertRaisesRegex(ValueError, "must contain"):
            load_price_data(path)
        path = self.write_csv("observation_date,NASDAQ100\n2005-01-03,0\n")
        with self.assertRaisesRegex(ValueError, "positive"):
            load_price_data(path)

    def test_loads_descending_bom_equals_prefix_and_footer_without_interpolation(self):
        path = self.write_csv(
            "﻿日期,收盘点位,全收益收盘点位(元)\n"
            "2020-01-03,=103,=203\n"
            "2020-01-02,=102,\n"
            "2020-01-01,=101,=201\n"
            "\n"
            "数据来源于：示例\n"
        )
        series = load_csv_price_data(
            path, date_column="日期", price_column="全收益收盘点位(元)",
            sort_order="descending", ignore_trailing_notes=True,
        )
        self.assertEqual(series.dates, (date(2020, 1, 1), date(2020, 1, 3)))
        self.assertEqual(series.prices, (201.0, 203.0))
        self.assertEqual(series.metadata.total_rows, 3)
        self.assertEqual(series.metadata.valid_price_rows, 2)
        self.assertEqual(series.metadata.missing_price_rows, 1)


if __name__ == "__main__":
    unittest.main()

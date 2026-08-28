import unittest
from datetime import date

from multi_market_analysis.core.backtest import Backtester, add_calendar_months


class BacktestTests(unittest.TestCase):
    def test_calendar_month_clamps_to_month_end(self):
        self.assertEqual(add_calendar_months(date(2020, 1, 31), 1), date(2020, 2, 29))
        self.assertEqual(add_calendar_months(date(2021, 1, 31), 1), date(2021, 2, 28))
        self.assertEqual(add_calendar_months(date(2020, 2, 29), 12), date(2021, 2, 28))

    def test_following_endpoint_and_single_purchase(self):
        rows = [
            (date(2020, 1, 31), 100),
            (date(2020, 2, 28), 110),
            (date(2020, 3, 2), 120),
        ]
        sample = Backtester(rows).single_purchase(1)[0]
        self.assertEqual(sample.target_end_date, date(2020, 2, 29))
        self.assertEqual(sample.end_date, date(2020, 3, 2))
        self.assertEqual(sample.start_index, 0)
        self.assertEqual(sample.end_index, 2)
        self.assertAlmostEqual(sample.return_rate, 0.2)

    def test_daily_investment_includes_start_and_end(self):
        rows = [
            (date(2020, 1, 1), 10),
            (date(2020, 1, 15), 20),
            (date(2020, 2, 3), 40),
        ]
        tester = Backtester(rows)
        sample = tester.daily_investment(1, daily_amount=5)[0]
        self.assertEqual(sample.contribution_count, 3)
        self.assertEqual(sample.principal, 15)
        self.assertAlmostEqual(sample.ending_value, 35)
        self.assertAlmostEqual(sample.return_rate, 35 / 15 - 1)
        for actual, expected in zip(
            tester.reciprocal_price_prefix, (0.0, 0.1, 0.15, 0.175)
        ):
            self.assertAlmostEqual(actual, expected)

    def test_maximum_loss_uses_positive_loss_and_includes_actual_endpoint(self):
        rows = [
            (date(2020, 1, 1), 100),
            (date(2020, 1, 15), 80),
            (date(2020, 2, 3), 90),
        ]
        tester = Backtester(rows)
        single = tester.single_purchase(1)[0]
        daily = tester.daily_investment(1, daily_amount=10)[0]
        self.assertAlmostEqual(single.maximum_loss, 0.2)
        self.assertEqual(single.maximum_loss_date, date(2020, 1, 15))
        self.assertAlmostEqual(single.maximum_loss_value, 0.8)
        # At 2020-01-15, C=20, units=10/100+10/80=.225, V=18, loss=10%.
        self.assertAlmostEqual(daily.maximum_loss, 0.1)
        self.assertEqual(daily.maximum_loss_date, date(2020, 1, 15))
        self.assertEqual(daily.maximum_loss_contribution_count, 2)
        self.assertAlmostEqual(daily.maximum_loss_principal, 20)
        self.assertAlmostEqual(daily.maximum_loss_units, 0.225)
        self.assertAlmostEqual(daily.maximum_loss_value, 18)

    def test_daily_maximum_loss_matches_three_day_hand_calculation(self):
        rows = [
            (date(2020, 1, 1), 100),
            (date(2020, 1, 15), 80),
            (date(2020, 2, 3), 70),
        ]
        single = Backtester(rows).single_purchase(1)[0]
        daily = Backtester(rows).daily_investment(1, daily_amount=100)[0]
        self.assertAlmostEqual(single.maximum_loss, 0.30)
        expected_value = 70 * (100 / 100 + 100 / 80 + 100 / 70)
        self.assertAlmostEqual(daily.maximum_loss, 1 - expected_value / 300)
        self.assertAlmostEqual(daily.maximum_loss, 17 / 120)
        self.assertEqual(daily.maximum_loss_date, date(2020, 2, 3))
        self.assertEqual(daily.maximum_loss_contribution_count, 3)

    def test_never_below_principal_has_zero_maximum_loss(self):
        rows = [(date(2020, 1, 1), 10), (date(2020, 2, 3), 20)]
        for sample in (Backtester(rows).single_purchase(1)[0], Backtester(rows).daily_investment(1)[0]):
            self.assertEqual(sample.maximum_loss, 0)
            self.assertEqual(sample.maximum_loss_date, date(2020, 1, 1))

    def test_run_has_required_horizons_and_audit_fields(self):
        rows = [
            (date(2020, 1, 1), 10),
            (date(2025, 1, 2), 20),
        ]
        results = Backtester(rows).run()
        self.assertEqual(tuple(results["single_purchase"]), (1, 3, 6, 12, 36, 60))
        sample = results["daily_investment"][60][0]
        self.assertEqual(sample.strategy, "daily_investment")
        self.assertEqual(sample.horizon_months, 60)
        self.assertEqual(sample.start_price, 10)
        self.assertEqual(sample.end_price, 20)
        self.assertEqual(sample.maximum_loss, 0)
        self.assertEqual(sample.maximum_loss_contribution_count, 1)


if __name__ == "__main__":
    unittest.main()

"""Calendar-aware return and maximum-loss backtests over daily prices."""

from __future__ import annotations

import calendar
from bisect import bisect_left
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence

from .data import PriceSeries

DEFAULT_HORIZONS_MONTHS = (1, 3, 6, 12, 36, 60)


@dataclass(frozen=True)
class BacktestSample:
    """One auditable investment-window result."""

    strategy: str
    horizon_months: int
    start_index: int
    end_index: int
    start_date: date
    target_end_date: date
    end_date: date
    start_price: float
    end_price: float
    contribution: float
    contribution_count: int
    principal: float
    ending_value: float
    return_rate: float
    maximum_loss: float
    maximum_loss_index: int
    maximum_loss_date: date
    maximum_loss_price: float
    maximum_loss_contribution_count: int
    maximum_loss_principal: float
    maximum_loss_units: float
    maximum_loss_value: float


class Backtester:
    """Generate single-purchase and daily-investment samples efficiently."""

    def __init__(self, series: PriceSeries | Iterable[tuple[date, float]]) -> None:
        if isinstance(series, PriceSeries):
            self.dates = series.dates
            self.prices = series.prices
        else:
            rows = tuple(series)
            self.dates = tuple(row[0] for row in rows)
            self.prices = tuple(float(row[1]) for row in rows)
        if len(self.dates) != len(self.prices):
            raise ValueError("dates and prices must have equal lengths")
        if any(right <= left for left, right in zip(self.dates, self.dates[1:])):
            raise ValueError("dates must be strictly increasing")
        if any(price <= 0 for price in self.prices):
            raise ValueError("prices must be positive")
        prefix = [0.0]
        for price in self.prices:
            prefix.append(prefix[-1] + 1.0 / price)
        self.reciprocal_price_prefix = tuple(prefix)

    def following_index(self, target: date) -> int | None:
        """Return the first valid trading-day index on or after target."""

        index = bisect_left(self.dates, target)
        return index if index < len(self.dates) else None

    def single_purchase(self, horizon_months: int) -> list[BacktestSample]:
        return self._run_horizons((horizon_months,), 1.0)["single_purchase"][horizon_months]

    def daily_investment(self, horizon_months: int, daily_amount: float = 1.0) -> list[BacktestSample]:
        """Invest daily_amount at every close, including both endpoints."""

        return self._run_horizons((horizon_months,), daily_amount)["daily_investment"][horizon_months]

    def _run_horizons(
        self,
        horizons_months: Sequence[int],
        daily_amount: float,
    ) -> dict[str, dict[int, list[BacktestSample]]]:
        """Scan each start once and snapshot all requested horizon endpoints."""

        _validate_horizons(horizons_months)
        if daily_amount <= 0:
            raise ValueError("daily_amount must be positive")
        horizons = tuple(dict.fromkeys(horizons_months))
        output = {
            "single_purchase": {months: [] for months in horizons},
            "daily_investment": {months: [] for months in horizons},
        }
        for start_index, start_date in enumerate(self.dates):
            endpoints: dict[int, list[tuple[int, date]]] = {}
            for months in horizons:
                target = add_calendar_months(start_date, months)
                end_index = self.following_index(target)
                if end_index is not None:
                    endpoints.setdefault(end_index, []).append((months, target))
            if not endpoints:
                continue

            start_price = self.prices[start_index]
            reciprocal_sum = 0.0
            minimum_price = start_price
            minimum_index = start_index
            daily_maximum_loss = 0.0
            daily_loss_index = start_index
            daily_loss_count = 1
            daily_loss_units = daily_amount / start_price
            daily_loss_principal = daily_amount
            daily_loss_value = daily_amount

            for point_index in range(start_index, max(endpoints) + 1):
                price = self.prices[point_index]
                reciprocal_sum += 1.0 / price
                count = point_index - start_index + 1
                principal = daily_amount * count
                units = daily_amount * reciprocal_sum
                value = price * units
                loss = max(0.0, 1.0 - value / principal)
                if loss > daily_maximum_loss:
                    daily_maximum_loss = loss
                    daily_loss_index = point_index
                    daily_loss_count = count
                    daily_loss_units = units
                    daily_loss_principal = principal
                    daily_loss_value = value
                if price < minimum_price:
                    minimum_price = price
                    minimum_index = point_index

                for months, target in endpoints.get(point_index, ()):
                    single_units = 1.0 / start_price
                    single_loss_value = minimum_price * single_units
                    single_maximum_loss = max(0.0, 1.0 - minimum_price / start_price)
                    output["single_purchase"][months].append(
                        BacktestSample(
                            strategy="single_purchase",
                            horizon_months=months,
                            start_index=start_index,
                            end_index=point_index,
                            start_date=start_date,
                            target_end_date=target,
                            end_date=self.dates[point_index],
                            start_price=start_price,
                            end_price=price,
                            contribution=1.0,
                            contribution_count=1,
                            principal=1.0,
                            ending_value=price / start_price,
                            return_rate=price / start_price - 1.0,
                            maximum_loss=single_maximum_loss,
                            maximum_loss_index=minimum_index,
                            maximum_loss_date=self.dates[minimum_index],
                            maximum_loss_price=minimum_price,
                            maximum_loss_contribution_count=1,
                            maximum_loss_principal=1.0,
                            maximum_loss_units=single_units,
                            maximum_loss_value=single_loss_value,
                        )
                    )
                    output["daily_investment"][months].append(
                        BacktestSample(
                            strategy="daily_investment",
                            horizon_months=months,
                            start_index=start_index,
                            end_index=point_index,
                            start_date=start_date,
                            target_end_date=target,
                            end_date=self.dates[point_index],
                            start_price=start_price,
                            end_price=price,
                            contribution=daily_amount,
                            contribution_count=count,
                            principal=principal,
                            ending_value=value,
                            return_rate=value / principal - 1.0,
                            maximum_loss=daily_maximum_loss,
                            maximum_loss_index=daily_loss_index,
                            maximum_loss_date=self.dates[daily_loss_index],
                            maximum_loss_price=self.prices[daily_loss_index],
                            maximum_loss_contribution_count=daily_loss_count,
                            maximum_loss_principal=daily_loss_principal,
                            maximum_loss_units=daily_loss_units,
                            maximum_loss_value=daily_loss_value,
                        )
                    )
        return output

    def run(
        self,
        horizons_months: Sequence[int] = DEFAULT_HORIZONS_MONTHS,
        daily_amount: float = 1.0,
    ) -> dict[str, dict[int, list[BacktestSample]]]:
        """Run both strategies while reusing each start window across horizons."""

        return self._run_horizons(horizons_months, daily_amount)


def add_calendar_months(value: date, months: int) -> date:
    """Apply a calendar-month offset, clamping the day at month end."""

    if not isinstance(months, int) or months <= 0:
        raise ValueError("months must be a positive integer")
    month_index = value.year * 12 + value.month - 1 + months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _validate_horizons(horizons: Sequence[int]) -> None:
    if any(not isinstance(value, int) or value <= 0 for value in horizons):
        raise ValueError("all horizons must be positive integers")


def run_backtests(
    series: PriceSeries | Iterable[tuple[date, float]],
    horizons_months: Sequence[int] = DEFAULT_HORIZONS_MONTHS,
    daily_amount: float = 1.0,
) -> dict[str, dict[int, list[BacktestSample]]]:
    """Convenience function used by report and command-line callers."""

    return Backtester(series).run(horizons_months, daily_amount)

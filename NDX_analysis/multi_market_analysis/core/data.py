"""Load and validate index observations from CSV files."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator, Sequence

DEFAULT_START_DATE = date(2005, 1, 1)


@dataclass(frozen=True)
class DataMetadata:
    """Audit metadata for the source file and retained observations."""

    source_path: str
    sha256: str
    total_rows: int
    valid_price_rows: int
    retained_price_rows: int
    missing_price_rows: int
    filtered_before_start: int
    source_first_date: date | None
    source_last_date: date | None
    first_date: date | None
    last_date: date | None


@dataclass(frozen=True)
class PriceSeries(Sequence[tuple[date, float]]):
    """Validated dates and prices, stored in strictly increasing date order."""

    dates: tuple[date, ...]
    prices: tuple[float, ...]
    metadata: DataMetadata

    def __post_init__(self) -> None:
        if len(self.dates) != len(self.prices):
            raise ValueError("dates and prices must have equal lengths")

    def __len__(self) -> int:
        return len(self.dates)

    def __getitem__(self, index: int | slice) -> tuple[date, float] | tuple[tuple[date, float], ...]:
        if isinstance(index, slice):
            return tuple(zip(self.dates[index], self.prices[index]))
        return self.dates[index], self.prices[index]

    def __iter__(self) -> Iterator[tuple[date, float]]:
        return iter(zip(self.dates, self.prices))


def file_sha256(path: str | Path) -> str:
    """Return the lowercase SHA-256 digest of a file's exact bytes."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_price(raw: str, price_column: str) -> float | None:
    text = raw.strip()
    if text.startswith("="):
        text = text[1:].strip()
    if not text or text == ".":
        return None
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid {price_column} price: {raw!r}") from exc
    if not value.is_finite() or value <= 0:
        raise ValueError(f"{price_column} price must be finite and positive: {raw!r}")
    return float(value)


def load_csv_price_data(
    path: str | Path,
    *,
    date_column: str,
    price_column: str,
    start_date: date | None = None,
    sort_order: str = "ascending",
    ignore_trailing_notes: bool = False,
) -> PriceSeries:
    """Load one price column from a BOM-safe CSV without filling missing values.

    ``sort_order`` may be ``ascending``, ``descending`` or ``auto``. Rows that do
    not contain an ISO date can only be ignored after all dated rows when
    ``ignore_trailing_notes`` is true. This supports vendor footer notes without
    silently accepting malformed observations inside the data block.
    """

    if sort_order not in {"ascending", "descending", "auto"}:
        raise ValueError("sort_order must be ascending, descending, or auto")
    source = Path(path)
    sha256 = file_sha256(source)
    rows: list[tuple[date, float | None]] = []
    missing_rows = filtered_rows = valid_rows = 0
    direction: str | None = None

    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {date_column, price_column}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"CSV must contain {date_column} and {price_column} columns")
        footer_started = False
        for line_number, row in enumerate(reader, start=2):
            raw_date = (row.get(date_column) or "").strip()
            try:
                current_date = date.fromisoformat(raw_date)
            except ValueError as exc:
                if ignore_trailing_notes and rows:
                    footer_started = True
                    continue
                raise ValueError(f"invalid {date_column} at line {line_number}: {raw_date!r}") from exc
            if footer_started:
                raise ValueError(f"dated row found after footer at line {line_number}")
            if rows:
                if current_date == rows[-1][0]:
                    raise ValueError(f"{date_column} must be strictly increasing with unique dates; line {line_number} has {current_date}")
                observed = "ascending" if current_date > rows[-1][0] else "descending"
                direction = direction or observed
                if observed != direction:
                    raise ValueError(f"{date_column} must be strictly ordered; line {line_number} has {current_date}")
            try:
                price = _parse_price(row.get(price_column) or "", price_column)
            except ValueError as exc:
                raise ValueError(f"line {line_number}: {exc}") from exc
            rows.append((current_date, price))

    actual_order = direction or "ascending"
    if sort_order != "auto" and len(rows) > 1 and actual_order != sort_order:
        raise ValueError(f"{date_column} must be strictly {sort_order}")
    chronological = rows if actual_order == "ascending" else list(reversed(rows))
    dates: list[date] = []
    prices: list[float] = []
    for current_date, price in chronological:
        if price is None:
            missing_rows += 1
            continue
        valid_rows += 1
        if start_date is not None and current_date < start_date:
            filtered_rows += 1
            continue
        dates.append(current_date)
        prices.append(price)

    source_dates = [row[0] for row in chronological]
    metadata = DataMetadata(
        source_path=str(source.resolve()),
        sha256=sha256,
        total_rows=len(rows),
        valid_price_rows=valid_rows,
        retained_price_rows=len(dates),
        missing_price_rows=missing_rows,
        filtered_before_start=filtered_rows,
        source_first_date=source_dates[0] if source_dates else None,
        source_last_date=source_dates[-1] if source_dates else None,
        first_date=dates[0] if dates else None,
        last_date=dates[-1] if dates else None,
    )
    return PriceSeries(tuple(dates), tuple(prices), metadata)


def load_price_data(path: str | Path, start_date: date = DEFAULT_START_DATE) -> PriceSeries:
    """Compatibility loader for ascending ``observation_date,NASDAQ100`` data."""

    return load_csv_price_data(
        path,
        date_column="observation_date",
        price_column="NASDAQ100",
        start_date=start_date,
        sort_order="ascending",
    )


load_data = load_price_data

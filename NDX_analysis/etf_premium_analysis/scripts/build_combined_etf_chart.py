import csv
from html import escape
from pathlib import Path

CUTOFF = "2023-08-28"
TASK_DIR = Path(__file__).parent.parent
DERIVED_DIR = TASK_DIR / "data" / "derived"
OUTPUT_DIR = TASK_DIR / "output"
WIDTH = 1320
HEIGHT = 480
LEFT = 72
RIGHT = 72
TOP = 32
BOTTOM = 54
BLUE = "#2563eb"
ORANGE = "#ea580c"
VIOLET = "#7c3aed"
GRID = "#e5e7eb"
MUTED = "#64748b"


def load_premiums(code: str) -> list[dict]:
    with (DERIVED_DIR / f"{code}_过去三年_集思录口径溢价率.csv").open(
        encoding="utf-8-sig", newline=""
    ) as f:
        return [
            {
                "date": row["价格日期"],
                "close": float(row["收盘价"]),
                "nav_date": row["净值日期"],
                "nav": float(row["单位净值"]),
                "premium": float(row["溢价率%"]),
            }
            for row in csv.DictReader(f)
            if row["价格日期"] >= CUTOFF
        ]


def nice_step(span: float) -> float:
    candidates = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5]
    return next(step for step in candidates if span / step <= 6)


def svg_chart(code: str, name: str, data: list[dict]) -> str:
    inner_width = WIDTH - LEFT - RIGHT
    inner_height = HEIGHT - TOP - BOTTOM
    all_prices = [point[price] for point in data for price in ("close", "nav")]
    raw_low, raw_high = min(all_prices), max(all_prices)
    step = nice_step(raw_high - raw_low)
    price_low = int((raw_low - step) / step) * step
    price_high = (int((raw_high + step) / step) + 1) * step
    # 溢价率可能为负，右轴必须覆盖零点上下两侧；柱子也要从零轴向上/下绘制。
    premium_min = min(point["premium"] for point in data)
    premium_max = max(point["premium"] for point in data)
    premium_low = min(-2, int((premium_min - 1) / 2) * 2)
    premium_high = max(2, (int((premium_max + 1) / 2) + 1) * 2)

    def x(index: int) -> float:
        return LEFT + index / (len(data) - 1) * inner_width

    def y_price(value: float) -> float:
        return TOP + (price_high - value) / (price_high - price_low) * inner_height

    def y_premium(value: float) -> float:
        return TOP + (premium_high - value) / (premium_high - premium_low) * inner_height

    parts = [
        f'<section class="chart-section"><h2>{escape(code)}｜{escape(name)}</h2>',
        f'<p class="range">{data[0]["date"]} 至 {data[-1]["date"]} · {len(data)} 个交易日</p>',
        f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{escape(code)}的收盘价、单位净值与溢价率图">',
    ]

    for tick in range(6):
        price_value = price_low + (price_high - price_low) * tick / 5
        y = y_price(price_value)
        # 循环从价格左轴的低值（图底）到高值（图顶），右轴标签也须低→高。
        right_value = premium_low + (premium_high - premium_low) * tick / 5
        parts.extend(
            [
                f'<line x1="{LEFT}" y1="{y:.2f}" x2="{WIDTH - RIGHT}" y2="{y:.2f}" class="grid"/>',
                f'<text x="{LEFT - 10}" y="{y + 4:.2f}" text-anchor="end" class="axis">{price_value:.2f}</text>',
                f'<text x="{WIDTH - RIGHT + 10}" y="{y + 4:.2f}" class="axis">{right_value:.0f}%</text>',
            ]
        )

    parts.extend(
        [
            f'<text x="{LEFT}" y="17" class="axis-title">价格（元）</text>',
            f'<text x="{WIDTH - RIGHT}" y="17" text-anchor="end" class="axis-title">溢价率</text>',
        ]
    )

    bar_width = max(0.55, inner_width / len(data) * 0.7)
    baseline = y_premium(0)
    for index, point in enumerate(data):
        bar_y = y_premium(point["premium"])
        rect_y = min(bar_y, baseline)
        rect_height = abs(baseline - bar_y)
        tooltip = (
            f'{point["date"]}\n收盘价：{point["close"]:.4f}\n'
            f'单位净值（{point["nav_date"]}）：{point["nav"]:.4f}\n'
            f'溢价率：{point["premium"]:.2f}%'
        )
        parts.append(
            f'<rect x="{x(index) - bar_width / 2:.2f}" y="{rect_y:.2f}" '
            f'width="{bar_width:.2f}" height="{rect_height:.2f}" '
            f'fill="{VIOLET}" fill-opacity="0.42"><title>{escape(tooltip)}</title></rect>'
        )

    for field, color in (("close", BLUE), ("nav", ORANGE)):
        path = " ".join(
            f'{"M" if index == 0 else "L"}{x(index):.2f},{y_price(point[field]):.2f}'
            for index, point in enumerate(data)
        )
        parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>')

    tick_indexes = [0, round((len(data) - 1) * 0.25), round((len(data) - 1) * 0.5), round((len(data) - 1) * 0.75), len(data) - 1]
    for index in dict.fromkeys(tick_indexes):
        parts.append(
            f'<text x="{x(index):.2f}" y="{HEIGHT - 15}" text-anchor="middle" class="axis">{data[index]["date"]}</text>'
        )

    parts.append("</svg></section>")
    return "\n".join(parts)


fund_513390 = load_premiums("513390")
fund_513100 = load_premiums("513100")
html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>513390 与 513100｜三年溢价率</title>
<style>
:root {{ --ink:#172033; --muted:{MUTED}; --surface:#fcfcfb; --line:#e5e7eb; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:#f5f6f8; color:var(--ink); font-family:"Microsoft YaHei",system-ui,sans-serif; }}
main {{ max-width:1440px; margin:32px auto; padding:0 24px; }}
.card {{ background:var(--surface); border:1px solid #e8eaee; border-radius:14px; box-shadow:0 8px 28px rgba(15,23,42,.06); padding:24px; }}
h1 {{ margin:0; font-size:22px; }} .subtitle {{ margin:8px 0 18px; color:var(--muted); font-size:14px; }}
.legend {{ display:flex; flex-wrap:wrap; gap:18px; margin:0 0 16px; font-size:14px; }} .legend span {{ display:flex; align-items:center; gap:7px; }}
.line-key {{ width:22px; height:4px; border-radius:3px; }} .bar-key {{ width:14px; height:14px; border-radius:2px; opacity:.75; }}
.chart-section + .chart-section {{ border-top:1px solid var(--line); margin-top:28px; padding-top:28px; }} h2 {{ margin:0; font-size:17px; }} .range,.note {{ color:var(--muted); font-size:12px; }} .range {{ margin:4px 0 12px; }} .note {{ margin:16px 0 0; }}
svg {{ display:block; width:100%; height:auto; }} .grid {{ stroke:{GRID}; stroke-width:1; }} .axis {{ fill:{MUTED}; font-size:12px; }} .axis-title {{ fill:{MUTED}; font-size:12px; font-weight:600; }}
@media (max-width:700px) {{ main {{ margin:16px auto; padding:0 10px; }} .card {{ padding:14px; }} }}
</style>
</head>
<body><main><section class="card">
<h1>QDII ETF｜过去三年收盘价、基金净值与溢价率</h1>
<p class="subtitle">统一时间范围：2023-08-28 至 2026-08-28 · 溢价率采用集思录口径</p>
<div class="legend"><span><i class="line-key" style="background:{BLUE}"></i>收盘价（左轴）</span><span><i class="line-key" style="background:{ORANGE}"></i>单位净值（左轴）</span><span><i class="bar-key" style="background:{VIOLET}"></i>溢价率（右轴）</span></div>
{svg_chart("513390", "纳指100ETF博时", fund_513390)}
{svg_chart("513100", "纳指ETF", fund_513100)}
<p class="note">计算口径：溢价率 =（价格日收盘价 ÷ 该日之前最近已披露的单位净值 − 1）× 100%。悬停柱状条可查看该日数据。</p>
</section></main></body></html>"""

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "513390与513100_过去三年溢价率图.html").write_text(html, encoding="utf-8")
print("combined ETF chart created")

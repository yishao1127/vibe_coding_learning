"""Generate the fully offline interactive HTML analysis report."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_RUNTIME_PATH = Path(__file__).with_name("report_runtime.js")

_REPORT_CSS = r"""
:root {
  color-scheme: light;
  --bg: #f4f7fb;
  --surface: #ffffff;
  --surface-2: #edf3fa;
  --ink: #172033;
  --muted: #5c687d;
  --line: #cbd5e1;
  --grid: #dbe4ef;
  --accent: #2a78d6;
  --accent-soft: #dbeafe;
  --negative: #e34948;
  --positive: #2a78d6;
  --shadow: 0 12px 30px rgba(15, 23, 42, .08);
}
body[data-theme="dark"] {
  color-scheme: dark;
  --bg: #0b1220;
  --surface: #111c2f;
  --surface-2: #17243a;
  --ink: #edf4ff;
  --muted: #a9b7ca;
  --line: #40506a;
  --grid: #2b3b54;
  --accent: #3987e5;
  --accent-soft: #1e3a5f;
  --negative: #e66767;
  --positive: #3987e5;
  --shadow: 0 12px 30px rgba(0, 0, 0, .28);
}
* { box-sizing: border-box; }
html { background: var(--bg); }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font: 15px/1.55 system-ui, -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
}
button, select, input { font: inherit; }
button:focus-visible, select:focus-visible, input:focus-visible, [tabindex="0"]:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.container { width: min(1220px, calc(100% - 32px)); margin: 0 auto; }
.hero { padding: 40px 0 28px; }
.eyebrow { margin: 0 0 6px; color: var(--accent); font-weight: 750; letter-spacing: .08em; }
h1 { margin: 0; font-size: clamp(28px, 5vw, 48px); line-height: 1.12; letter-spacing: -.035em; }
.subtitle { max-width: 760px; margin: 12px 0 0; color: var(--muted); }
.toolbar {
  position: sticky; top: 0; z-index: 5; display: flex; flex-wrap: wrap; gap: 12px;
  align-items: end; padding: 14px; margin-bottom: 22px; border: 1px solid var(--line);
  border-radius: 16px; background: color-mix(in srgb, var(--surface) 94%, transparent); box-shadow: var(--shadow);
}
.control { display: grid; gap: 5px; min-width: 180px; }
.control label { color: var(--muted); font-size: 12px; font-weight: 700; }
select, input, button {
  min-height: 42px; border: 1px solid var(--line); border-radius: 10px; background: var(--surface);
  color: var(--ink); padding: 8px 12px;
}
input:invalid, .control-error input { border-color: var(--negative); }
.filter-message { width: 100%; margin: -2px 0 0; color: var(--negative); font-size: 12px; font-weight: 700; }
.filter-message:empty { display: none; }
button { cursor: pointer; font-weight: 700; }
button:hover { border-color: var(--accent); }
.date-presets { display: flex; flex-wrap: wrap; gap: 6px; align-self: end; }
.date-presets button { min-height: 42px; padding-inline: 10px; }
.toolbar-actions { display: flex; gap: 8px; margin-left: auto; }
.section { margin: 0 0 28px; }
.section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
h2 { margin: 0; font-size: 21px; letter-spacing: -.015em; }
h3 { margin: 0 0 4px; font-size: 16px; }
.context { color: var(--muted); font-size: 13px; }
.kpi-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; }
.kpi, .panel, .note {
  border: 1px solid var(--line); border-radius: 16px; background: var(--surface); box-shadow: var(--shadow);
}
.kpi { min-height: 114px; padding: 17px; }
.kpi-label { color: var(--muted); font-size: 13px; }
.kpi-value { margin-top: 7px; font-size: clamp(22px, 3vw, 31px); font-weight: 780; letter-spacing: -.03em; }
.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.panel { min-width: 0; padding: 18px; }
.panel-caption { margin-bottom: 12px; }
.panel-caption p { margin: 2px 0 0; color: var(--muted); font-size: 13px; }
.chart-wrap { position: relative; min-height: 310px; }
.chart { display: block; width: 100%; height: auto; overflow: visible; }
.axis, .grid-line { vector-effect: non-scaling-stroke; }
.axis { stroke: var(--line); stroke-width: 1; }
.grid-line { stroke: var(--grid); stroke-width: 1; }
.axis-label, .tick-label { fill: var(--muted); font-size: 11px; }
.bar { fill: var(--positive); stroke: var(--surface); stroke-width: 2; rx: 4px; }
.bar.negative { fill: var(--negative); }
.zero-line { stroke: var(--ink); stroke-width: 1.5; vector-effect: non-scaling-stroke; }
.bar:hover, .bar:focus { filter: brightness(1.12); }
.cdf-line { fill: none; stroke: var(--accent); stroke-width: 3; vector-effect: non-scaling-stroke; }
.cdf-point { fill: var(--accent); stroke: var(--surface); stroke-width: 2; vector-effect: non-scaling-stroke; }
.tooltip {
  position: absolute; z-index: 3; max-width: 240px; transform: translate(10px, -105%); pointer-events: none;
  border: 1px solid var(--line); border-radius: 9px; background: var(--surface); color: var(--ink);
  padding: 8px 10px; box-shadow: var(--shadow); font-size: 12px; white-space: pre-line;
}
.tooltip[hidden] { display: none; }
.table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 14px; background: var(--surface); }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { padding: 11px 13px; border-bottom: 1px solid var(--line); text-align: right; white-space: nowrap; }
th { background: var(--surface-2); color: var(--muted); font-size: 12px; }
th:first-child, td:first-child { text-align: left; }
tbody tr:last-child td { border-bottom: 0; }
tbody tr[aria-current="true"] { background: var(--accent-soft); }
.summary-row { border-left: 4px solid transparent; }
.summary-row.single-purchase { border-left-color: var(--accent); }
.summary-row.daily-investment { border-left-color: #1baf7a; }
.summary-row.single-purchase td { background: color-mix(in srgb, var(--accent) 4%, var(--surface)); }
.summary-row.daily-investment td { background: color-mix(in srgb, #1baf7a 5%, var(--surface)); }
.summary-row[aria-current="true"] td { background: var(--accent-soft); }
.strategy-column { width: 124px; max-width: 124px; }
.strategy-badge { display: inline-flex; align-items: center; gap: 7px; font-weight: 750; }
.strategy-badge::before { content: ""; flex: 0 0 auto; width: 9px; height: 9px; border-radius: 50%; background: var(--accent); }
.daily-investment .strategy-badge::before { background: #1baf7a; }
.group-column-header th { border-top: 1px solid var(--line); }
.return-positive { color: #006300; font-weight: 720; }
.return-negative { color: #b73535; font-weight: 720; }
.risk-value { color: var(--ink); font-weight: 650; }
body[data-theme="dark"] .return-positive { color: #50d48d; }
body[data-theme="dark"] .return-negative { color: #ff8585; }
.horizon-group { font-weight: 800; vertical-align: middle; background: var(--surface-2) !important; }
.distribution-column { width: 112px; min-width: 112px; text-align: center; }
.spark-cell { position: relative; width: 112px; min-width: 112px; padding: 4px 8px; text-align: center; }
.spark-histogram-wrap { position: relative; display: inline-block; width: 96px; height: 28px; vertical-align: middle; }
.spark-histogram { display: block; width: 96px; height: 28px; overflow: visible; }
.spark-bar { fill: var(--positive); }
.spark-bar.negative, .spark-loss-bar { fill: var(--negative); }
.spark-zero-line { stroke: var(--ink); stroke-width: 1; vector-effect: non-scaling-stroke; opacity: .72; }
.spark-loss-baseline { stroke: var(--ink); stroke-width: 1; vector-effect: non-scaling-stroke; opacity: .72; }
.spark-tooltip { left: 50%; top: 0; min-width: 176px; text-align: left; white-space: pre-line; }
.spark-empty { color: var(--muted); }
.tables-grid { display: grid; grid-template-columns: 1.35fr .65fr; gap: 16px; }
.notes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.note { padding: 18px; }
.note p { margin: 7px 0 0; color: var(--muted); }
.meta { margin: 18px 0 42px; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
.empty { padding: 30px; color: var(--muted); text-align: center; }
@media (max-width: 960px) {
  .kpi-grid { grid-template-columns: repeat(3, 1fr); }
  .chart-grid, .tables-grid { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .container { width: min(100% - 20px, 1220px); }
  .hero { padding-top: 26px; }
  .toolbar { position: static; align-items: stretch; }
  .control { min-width: 100%; }
  .toolbar-actions { width: 100%; margin-left: 0; }
  .toolbar-actions button { flex: 1; }
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .notes { grid-template-columns: 1fr; }
  .section-head { align-items: flex-start; flex-direction: column; }
}
@media print {
  :root, body[data-theme="dark"] { color-scheme: light; --bg: #fff; --surface: #fff; --surface-2: #f4f4f4; --ink: #000; --muted: #333; --line: #aaa; --grid: #ddd; --accent: #1d4ed8; --accent-soft: #e8eefc; --shadow: none; }
  @page { margin: 12mm; }
  body { font-size: 10pt; }
  .container { width: 100%; }
  .hero { padding: 0 0 16px; }
  .toolbar { display: none; }
  .kpi-grid { grid-template-columns: repeat(6, 1fr); }
  .chart-grid { grid-template-columns: 1fr 1fr; }
  .panel, .kpi, .note, .table-wrap { break-inside: avoid; box-shadow: none; }
  .tooltip { display: none !important; }
}
"""


def _json_for_script(payload: Mapping[str, Any]) -> str:
    """Serialize JSON without allowing user data to terminate the script element."""

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
    return (
        serialized.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )


def build_report_html(payload: Mapping[str, Any]) -> str:
    """Return a self-contained Chinese HTML report for a JSON-friendly payload.

    The current payload contains ``horizon_samples``. Each horizon shares one
    ``start_dates`` array across its two strategy return arrays. ``analysis_config``
    controls the fixed histogram width, quantiles, and default closed date range.
    """

    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    runtime = _RUNTIME_PATH.read_text(encoding="utf-8")
    # Keep the generated document safe if a future runtime comment/string happens
    # to contain an HTML closing-script sequence.
    runtime = runtime.replace("</script", r"<\/script").replace("</SCRIPT", r"<\/SCRIPT")
    data = _json_for_script(payload)
    title = "指数历史收益分布报告"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; font-src 'none'; connect-src 'none'">
<title>{title}</title>
<style>{_REPORT_CSS}</style>
</head>
<body data-theme="light">
<header class="hero container">
  <p class="eyebrow" id="report-eyebrow">指数 · 离线分析</p>
  <h1 id="report-title">{title}</h1>
  <p class="subtitle" id="report-subtitle">基于历史滚动窗口观察收益分布；筛选策略与持有期限以查看对应结果。</p>
</header>
<main class="container" id="report-root">
  <section class="toolbar" aria-label="全局筛选器">
    <div class="control" id="market-control"><label for="market-filter">市场</label><select id="market-filter"></select></div>
    <div class="control" id="price-basis-control"><label for="price-basis-filter">点位口径</label><select id="price-basis-filter"></select></div>
    <div class="control"><label for="strategy-filter">投资策略</label><select id="strategy-filter"></select></div>
    <div class="control"><label for="horizon-filter">持有期限</label><select id="horizon-filter"></select></div>
    <div class="control"><label for="start-date-filter">回测起点开始（含）</label><input id="start-date-filter" type="date"></div>
    <div class="control"><label for="end-date-filter">回测起点结束（含）</label><input id="end-date-filter" type="date"></div>
    <div class="date-presets" id="date-presets" aria-label="快速选择回测起点范围">
      <button type="button" data-years="2">近2年</button><button type="button" data-years="5">近5年</button><button type="button" data-years="10">近10年</button><button type="button" data-years="15">近15年</button><button type="button" data-years="20">近20年</button>
    </div>
    <div class="toolbar-actions">
      <button type="button" id="theme-toggle" aria-pressed="false">切换深色主题</button>
      <button type="button" id="reset-button">恢复默认</button>
    </div>
    <p class="filter-message" id="date-filter-message" role="status" aria-live="polite"></p>
  </section>

  <section class="section" aria-labelledby="kpi-title">
    <div class="section-head"><h2 id="kpi-title">核心指标</h2><span class="context" id="selection-context"></span></div>
    <div class="kpi-grid" id="kpi-grid"></div>
  </section>

  <section class="section chart-grid" aria-label="收益分布图表">
    <figure class="panel">
      <figcaption class="panel-caption"><h2>历史收益率频率分布</h2><p>每根柱表示历史收益率落入该区间的样本占比；横轴按当前筛选结果的实际范围自动调整。</p></figcaption>
      <div class="chart-wrap" id="histogram-wrap"><svg class="chart" id="histogram-chart" role="img" aria-label="收益率直方概率图"></svg><div class="tooltip" id="histogram-tooltip" role="tooltip" hidden></div></div>
    </figure>
    <figure class="panel">
      <figcaption class="panel-caption"><h2>累计概率（CDF）</h2><p>曲线表示收益率不超过横轴数值的累计概率。</p></figcaption>
      <div class="chart-wrap" id="cdf-wrap"><svg class="chart" id="cdf-chart" role="img" aria-label="收益率累计分布图"></svg><div class="tooltip" id="cdf-tooltip" role="tooltip" hidden></div></div>
    </figure>
  </section>

  <section class="section" aria-labelledby="summary-title">
    <div class="section-head"><h2 id="summary-title">12 组合汇总表</h2><span class="context">当前点位口径共 12 组合；沪深300两种口径合计 24 组合。当前组合以底色标识</span></div>
    <div class="table-wrap"><table><thead id="summary-table-head"><tr><th scope="col">期限</th><th scope="col" class="strategy-column">策略</th><th scope="col">样本数</th><th scope="col">盈利样本占比</th><th scope="col">累计收益率均值</th><th scope="col">累计收益率中位数</th><th scope="col">较差情景收益率（P10）</th><th scope="col">较好情景收益率（P90）</th><th scope="col" class="distribution-column">历史收益分布</th></tr></thead><tbody id="summary-table-body"></tbody></table></div>
  </section>

  <section class="section" aria-labelledby="risk-summary-title">
    <div class="section-head"><h2 id="risk-summary-title">历史最大亏损分布</h2><span class="context" id="risk-summary-context">按当前市场、点位口径与起点日期范围统计</span></div>
    <div class="table-wrap"><table><thead id="risk-summary-table-head"><tr><th scope="col">期限</th><th scope="col" class="strategy-column">策略</th><th scope="col">样本数</th><th scope="col">最大亏损平均值</th><th scope="col">最大亏损中位数</th><th scope="col">最大亏损P90</th><th scope="col">P95</th><th scope="col">P100</th><th scope="col" class="distribution-column">最大亏损频率分布</th></tr></thead><tbody id="risk-summary-table-body"></tbody></table></div>
  </section>

  <section class="section" aria-labelledby="method-title">
    <div class="section-head"><h2 id="method-title">口径与限制</h2></div>
    <div class="notes">
      <article class="note"><h3>数据与回测口径</h3><p id="price-basis-note">每个有效交易日作为一个滚动起点；日期范围只筛选买入或开始定投的起点，不限制固定持有期的实际结束日期。目标到期日若非交易日，使用其后首个有效交易日。不同点位口径独立回测，不插值、不混算。</p></article>
      <article class="note"><h3>投入金额 X</h3><p>每日定投金额 X 仅按比例缩放累计本金与期末价值，不影响收益率及其概率分布；报告展示的是收益率，而非绝对盈亏金额。</p></article>
      <article class="note"><h3>最大亏损口径与限制</h3><p>一次性买入为窗口内相对起点的最大跌幅；每日定投为每天收盘投入 X 后按同点位估值，相对当时累计本金的最大亏损。均含首尾及实际顺延终点，未亏损记 0、以正数显示。历史分布不代表未来表现。</p></article>
    </div>
    <p class="meta" id="report-metadata"></p>
  </section>
</main>
<script id="report-data" type="application/json">{data}</script>
<script>{runtime}</script>
</body>
</html>
"""


def write_report(payload: Mapping[str, Any], output_path: str | Path) -> Path:
    """Write a UTF-8 report and return its resolved output path."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(build_report_html(payload), encoding="utf-8")
    return destination.resolve()


# Explicit alias for callers that prefer a verb matching the output type.
write_report_html = write_report

__all__ = ["build_report_html", "write_report", "write_report_html"]

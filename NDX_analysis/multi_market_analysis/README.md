# NASDAQ-100 与沪深300历史收益回测

本任务以每个有效交易日作为滚动投资起点，比较 NASDAQ-100 与沪深300在不同持有期限下的历史收益和最大亏损。

## 分析内容

- 市场与口径：
  - NASDAQ-100：收盘点位。
  - 沪深300：普通收盘点位。
  - 沪深300：全收益收盘点位（含现金分红再投资）。
- 持有期限：1、3、6 个月，以及 1、3、5 年。
- 投资方式：一次性买入、逐交易日等额定投。
- 输出指标：历史收益概率、收益分布、分位数、最大亏损分布。

## 运行

在 `NDX_analysis` 根目录运行：

```python
python -m multi_market_analysis.run_analysis
```

默认读取任务内 `data/` 目录的两份 CSV，因此从 GitHub 下载后可直接运行。如果要使用其他数据，指定输入路径：

```python
python -m multi_market_analysis.run_analysis \
  --ndx-input "C:\path\NASDAQ100.csv" \
  --csi300-input "C:\path\CSI300.csv"
```

## 输出

- [index_return_backtest.html](output/index_return_backtest.html)：完全离线的交互式回测报告，默认展示 NASDAQ-100，可切换到沪深300两种口径。
- [index_return_samples.csv](output/index_return_samples.csv)：样本级审计明细，覆盖三个数据集。

可通过 `--output`、`--audit-output` 改写默认输出路径。

## 回测口径

- 一次性买入收益率：$P_e / P_s - 1$。
- 定投：从起点到实际终点（均包含）每个有效交易日投入相同金额。
- 最大亏损：一次买入按窗口内点位相对起点的最大跌幅计算；定投按每日累计本金与每日市值的最大亏损计算。
- 若目标日不是有效交易日，实际终点使用其后的首个有效交易日。
- 缺失点位不插值；尾部无法满足完整持有期限的样本不纳入统计。
- 滚动窗口之间会重叠，历史统计不代表未来表现。

## 目录说明

- `run_analysis.py`：任务入口、参数与数据集编排。
- `core/`：数据读取、回测、统计和离线报告生成逻辑。
- `tests/`：Python 与浏览器运行时测试。
- `output/`：本任务生成的报告与审计数据。

## 测试

在 `NDX_analysis` 根目录运行：

```python
python -m unittest discover -s multi_market_analysis/tests -v
node --test multi_market_analysis/tests/test_report_runtime.js
```

> 仅供研究，不构成投资建议。

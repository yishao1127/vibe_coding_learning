# 纳指 QDII ETF 溢价率研究

本任务研究两只场内纳指 QDII ETF：

- `513390`：纳指100ETF博时
- `513100`：纳指 ETF

## 目标

获取历史收盘价和历史单位净值，按集思录 QDII 页面使用的口径计算每日溢价率，并展示过去三年的价格、净值和溢价率。

## 目录

```text
etf_premium_analysis/
├── data/
│   ├── raw/       # 东方财富导出的日线与历史净值
│   └── derived/   # 按集思录口径计算的溢价率及过程核对文件
├── scripts/       # 图表生成脚本
├── output/        # 可复现图表
└── archive/       # 无生成脚本的历史静态报告
```

## 数据来源

| 数据 | 来源 | 接口 |
|---|---|---|
| ETF 日线收盘价 | 东方财富行情 | `https://push2his.eastmoney.com/api/qt/stock/kline/get`；沪市 ETF 使用 `secid=1.<代码>`、`klt=101`、`fqt=0` |
| 历史单位净值 | 天天基金 / 东方财富 | `https://fund.eastmoney.com/pingzhongdata/<代码>.js` 中的 `Data_netWorthTrend` |
| 集思录口径核对 | 集思录 QDII 明细 | `https://www.jisilu.cn/data/qdii/detail/<代码>`；历史明细接口为 `/data/qdii/detail_hists/` |

## 计算口径

QDII ETF 的单位净值通常晚于价格日披露。对每一个价格日，使用**严格早于该价格日**的最近已披露单位净值：

$$
\text{溢价率}_t=\left(\frac{\text{收盘价}_t}{\text{最近已披露单位净值}}-1\right)\times100\%
$$

例如 2026-08-27 的 513390：收盘价 2.4390，使用 2026-08-26 净值 2.2179，结果为 9.97%，与集思录一致。

## 生成图表

从 `NDX_analysis` 根目录运行：

```python
python etf_premium_analysis/scripts/build_combined_etf_chart.py
```

输出：[513390与513100_过去三年溢价率图.html](output/513390与513100_过去三年溢价率图.html)。图表上半部分为 513390，下半部分为 513100；左轴显示收盘价和单位净值，右轴显示溢价率。

## 历史归档

[NDX_ETF_溢价率对比.html](archive/NDX_ETF_溢价率对比.html) 是旧的六只纳指 ETF 静态报告，数据内嵌、没有可复现的生成脚本，仅供历史参考。

> 数据为公开数据源的历史快照，仅供研究，不构成投资建议。

# 纳指分析任务

本目录下每个子目录都是一个独立、可运行的纳指相关分析任务。

| 任务 | 用途 | 运行入口 | 输出 |
|---|---|---|---|
| [multi_market_analysis](multi_market_analysis/) | NASDAQ-100 与沪深300的滚动收益、定投和最大亏损回测 | `python -m multi_market_analysis.run_analysis` | `multi_market_analysis/output/` |
| [etf_premium_analysis](etf_premium_analysis/) | 纳指 QDII ETF 收盘价、净值和集思录口径溢价率分析 | `python etf_premium_analysis/scripts/build_combined_etf_chart.py` | `etf_premium_analysis/output/` |

请进入各任务目录阅读其 README，了解数据来源、计算口径和完整说明。

> 仅供研究，不构成投资建议。

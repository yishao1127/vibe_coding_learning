"use strict";

(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root && root.document) api.start(root.document);
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const NS = "http://www.w3.org/2000/svg";

  function finiteNumbers(values) { return Array.isArray(values) ? values.map(Number).filter(Number.isFinite) : []; }
  function quantile(sortedValues, probability) {
    if (!sortedValues.length) return null;
    if (sortedValues.length === 1) return sortedValues[0];
    const position = (sortedValues.length - 1) * probability;
    const lower = Math.floor(position); const upper = Math.ceil(position); const fraction = position - lower;
    return sortedValues[lower] * (1 - fraction) + sortedValues[upper] * fraction;
  }
  function histogramEdges(values, binWidth) {
    const data = finiteNumbers(values); const width = Number(binWidth);
    if (!data.length || !Number.isFinite(width) || width <= 0) return [];
    let lowerStep = Math.floor(Math.min.apply(null, data) / width);
    let upperStep = Math.ceil(Math.max.apply(null, data) / width);
    if (Math.abs(Math.max.apply(null, data) - upperStep * width) <= 1e-12) upperStep += 1;
    if (lowerStep === upperStep) upperStep += 1;
    const edges = []; for (let step = lowerStep; step <= upperStep; step += 1) edges.push(step * width);
    return edges;
  }
  function summarizeReturns(values, config) {
    const data = finiteNumbers(values); if (!data.length) return null;
    const sorted = data.slice().sort(function (a, b) { return a - b; });
    const edges = histogramEdges(data, Number(config.bin_width || 0.05));
    const counts = new Array(Math.max(0, edges.length - 1)).fill(0);
    data.forEach(function (value) { let index = edges.length - 2; for (let candidate = 0; candidate < edges.length - 1; candidate += 1) { if (value < edges[candidate + 1]) { index = candidate; break; } } counts[index] += 1; });
    const probabilities = counts.map(function (count) { return count / data.length; });
    let cumulative = 0; const cdf = probabilities.map(function (probability) { cumulative += probability; return cumulative; });
    const quantiles = finiteNumbers(config.quantile_probabilities || [0.1, 0.5, 0.9]).map(function (probability) { return { probability: probability, value: quantile(sorted, probability) }; });
    return { count: data.length, mean: data.reduce(function (sum, value) { return sum + value; }, 0) / data.length, median: quantile(sorted, 0.5), minimum: sorted[0], maximum: sorted[sorted.length - 1], profitProbability: data.filter(function (value) { return value > 0; }).length / data.length, quantiles: quantiles, edges: edges, counts: counts, probabilities: probabilities, cdf: cdf };
  }
  function filterReturns(startDates, returns, startDate, endDate) {
    const dates = Array.isArray(startDates) ? startDates : []; const values = Array.isArray(returns) ? returns : []; const count = Math.min(dates.length, values.length); const filtered = [];
    for (let index = 0; index < count; index += 1) { const value = Number(values[index]); const itemDate = String(dates[index]); if ((!startDate || itemDate >= startDate) && (!endDate || itemDate <= endDate) && Number.isFinite(value)) filtered.push(value); }
    return filtered;
  }
  function summarizeMaximumLosses(values) {
    const data = finiteNumbers(values); if (!data.length) return null;
    const sorted = data.slice().sort(function (a, b) { return a - b; });
    const binWidth = 0.02; const maximum = sorted[sorted.length - 1];
    let upperStep = Math.ceil(maximum / binWidth);
    if (Math.abs(maximum - upperStep * binWidth) <= 1e-12) upperStep += 1;
    upperStep = Math.max(1, upperStep);
    const edges = []; for (let step = 0; step <= upperStep; step += 1) edges.push(step * binWidth);
    const counts = new Array(edges.length - 1).fill(0);
    data.forEach(function (value) { let index = edges.length - 2; for (let candidate = 0; candidate < edges.length - 1; candidate += 1) { if (value < edges[candidate + 1]) { index = candidate; break; } } counts[index] += 1; });
    const probabilities = counts.map(function (count) { return count / data.length; });
    return { count: data.length, mean: data.reduce(function (sum, value) { return sum + value; }, 0) / data.length, median: quantile(sorted, 0.5), p90: quantile(sorted, 0.9), p95: quantile(sorted, 0.95), p100: maximum, edges: edges, counts: counts, probabilities: probabilities };
  }
  function computeAllStatistics(horizonSamples, strategies, startDate, endDate, config) {
    const result = {};
    (horizonSamples || []).forEach(function (horizon) { (strategies || []).forEach(function (strategy) { const key = strategy + "|" + Number(horizon.horizon_months); result[key] = summarizeReturns(filterReturns(horizon.start_dates, (horizon.returns || {})[strategy], startDate, endDate), config || {}); }); });
    return result;
  }
  function computeAllMaximumLossStatistics(horizonSamples, strategies, startDate, endDate) {
    const result = {};
    (horizonSamples || []).forEach(function (horizon) { (strategies || []).forEach(function (strategy) { const key = strategy + "|" + Number(horizon.horizon_months); result[key] = summarizeMaximumLosses(filterReturns(horizon.start_dates, (horizon.maximum_losses || {})[strategy], startDate, endDate)); }); });
    return result;
  }
  function validateDateRange(startDate, endDate, minimumDate, maximumDate) {
    if (startDate && endDate && startDate > endDate) return { valid: false, message: "开始日期不能晚于结束日期。" };
    if ((startDate && minimumDate && startDate < minimumDate) || (endDate && maximumDate && endDate > maximumDate)) return { valid: false, message: "日期必须位于当前点位口径的可用回测起点范围内。" };
    return { valid: true, message: "" };
  }
  function subtractCalendarYears(dateString, years) {
    const parts = String(dateString || "").split("-").map(Number); const count = Number(years);
    if (parts.length !== 3 || parts.some(function (value) { return !Number.isInteger(value); }) || !Number.isInteger(count) || count < 0) return "";
    const year = parts[0] - count; const month = parts[1]; const day = parts[2];
    const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate();
    return String(year).padStart(4, "0") + "-" + String(month).padStart(2, "0") + "-" + String(Math.min(day, lastDay)).padStart(2, "0");
  }
  function presetDateRange(years, minimumDate, maximumDate) {
    const endDate = String(maximumDate || ""); const candidate = subtractCalendarYears(endDate, years);
    if (!candidate || !endDate) return { startDate: "", endDate: endDate };
    return { startDate: minimumDate && candidate < minimumDate ? String(minimumDate) : candidate, endDate: endDate };
  }
  function normalizeDatasets(payload) {
    if (Array.isArray(payload.datasets) && payload.datasets.length) return payload.datasets;
    return [{ id: "legacy", market_id: "ndx", market_label: "NASDAQ-100", price_label: "收盘点位", title: payload.title, subtitle: payload.subtitle, price_note: "指数收盘点位口径。", analysis_config: payload.analysis_config || {}, horizon_samples: payload.horizon_samples || [], metadata: payload.metadata || {} }];
  }
  function alignHistogramStatistics(items) {
    const available = (items || []).filter(function (item) { return item && Array.isArray(item.edges) && item.edges.length > 1 && Array.isArray(item.probabilities); });
    if (!available.length) return { edges: [], rows: (items || []).map(function () { return null; }) };
    const edgeByKey = {};
    available.forEach(function (item) { item.edges.forEach(function (edge) { const value = Number(edge); if (Number.isFinite(value)) edgeByKey[value.toFixed(12)] = value; }); });
    const edges = Object.keys(edgeByKey).map(function (key) { return edgeByKey[key]; }).sort(function (a, b) { return a - b; });
    const indexByLeftEdge = {}; edges.slice(0, -1).forEach(function (edge, index) { indexByLeftEdge[Number(edge).toFixed(12)] = index; });
    const rows = (items || []).map(function (item) {
      if (!item || !Array.isArray(item.edges) || !Array.isArray(item.probabilities)) return null;
      const probabilities = new Array(Math.max(0, edges.length - 1)).fill(0);
      item.probabilities.forEach(function (probability, index) { const target = indexByLeftEdge[Number(item.edges[index]).toFixed(12)]; if (target !== undefined) probabilities[target] = Number(probability) || 0; });
      return probabilities;
    });
    return { edges: edges, rows: rows };
  }

  function start(document) {
    const rawPayload = JSON.parse(document.getElementById("report-data").textContent);
    const datasets = normalizeDatasets(rawPayload); const datasetById = {}; datasets.forEach(function (item) { datasetById[item.id] = item; });
    const marketOrder = []; const marketLabels = {}; datasets.forEach(function (item) { if (!marketLabels[item.market_id]) marketOrder.push(item.market_id); marketLabels[item.market_id] = item.market_label; });
    const strategyLabels = Object.assign({ single_purchase: "一次性买入", daily_investment: "每日定投" }, rawPayload.strategy_labels || {});
    const horizonLabels = Object.assign({}, rawPayload.horizon_labels || {});
    const els = {
      market: document.getElementById("market-filter"), priceBasis: document.getElementById("price-basis-filter"), marketControl: document.getElementById("market-control"), priceBasisControl: document.getElementById("price-basis-control"),
      strategy: document.getElementById("strategy-filter"), horizon: document.getElementById("horizon-filter"), startDate: document.getElementById("start-date-filter"), endDate: document.getElementById("end-date-filter"), datePresets: document.getElementById("date-presets"), dateMessage: document.getElementById("date-filter-message"), theme: document.getElementById("theme-toggle"), reset: document.getElementById("reset-button"),
      eyebrow: document.getElementById("report-eyebrow"), title: document.getElementById("report-title"), subtitle: document.getElementById("report-subtitle"), context: document.getElementById("selection-context"), kpis: document.getElementById("kpi-grid"), histogram: document.getElementById("histogram-chart"), histogramTooltip: document.getElementById("histogram-tooltip"), cdf: document.getElementById("cdf-chart"), cdfTooltip: document.getElementById("cdf-tooltip"), summary: document.getElementById("summary-table-body"), summaryHead: document.getElementById("summary-table-head"), summaryTitle: document.getElementById("summary-title"), riskSummary: document.getElementById("risk-summary-table-body"), riskSummaryHead: document.getElementById("risk-summary-table-head"), riskContext: document.getElementById("risk-summary-context"), metadata: document.getElementById("report-metadata"), priceNote: document.getElementById("price-basis-note")
    };
    const defaultDatasetId = String(rawPayload.default_dataset_id || datasets[0].id); const defaultDataset = datasetById[defaultDatasetId] || datasets[0];
    const defaults = { datasetId: defaultDataset.id, market: defaultDataset.market_id, strategy: String(rawPayload.default_strategy || "single_purchase"), horizon: Number(rawPayload.default_horizon_months || 12), theme: "light" };
    let state = {}; let statisticsCache = null; let marketStatisticsCache = {}; let marketRiskCache = {}; let cacheDateKey = "";

    fillSelect(els.market, marketOrder, function (value) { return marketLabels[value] || value; }); els.market.value = defaults.market;
    refreshPriceBasis(defaults.datasetId, false); refreshDataset(true);
    els.market.addEventListener("change", function () { refreshPriceBasis("", false); refreshDataset(false); });
    els.priceBasis.addEventListener("change", function () { refreshDataset(false); });
    els.strategy.addEventListener("change", renderSelected); els.horizon.addEventListener("change", renderSelected);
    els.startDate.addEventListener("change", renderForDateChange); els.endDate.addEventListener("change", renderForDateChange);
    els.datePresets.addEventListener("click", function (event) { const button = event.target.closest("button[data-years]"); if (!button) return; const range = presetDateRange(Number(button.dataset.years), state.minimumDate, state.maximumDate); els.startDate.value = range.startDate; els.endDate.value = range.endDate; renderForDateChange(); });
    els.theme.addEventListener("click", function () { setTheme(document.body.dataset.theme === "dark" ? "light" : "dark"); });
    els.reset.addEventListener("click", function () { els.market.value = defaults.market; refreshPriceBasis(defaults.datasetId, false); refreshDataset(true); setTheme(defaults.theme); });
    setTheme(defaults.theme);

    function datasetsForMarket(market) { return datasets.filter(function (item) { return item.market_id === market; }); }
    function refreshPriceBasis(preferredId, trigger) {
      const choices = datasetsForMarket(els.market.value); fillSelect(els.priceBasis, choices.map(function (item) { return item.id; }), function (id) { return datasetById[id].price_label; });
      els.priceBasis.value = choices.some(function (item) { return item.id === preferredId; }) ? preferredId : (choices[0] || {}).id || "";
      els.marketControl.hidden = marketOrder.length <= 1; els.priceBasisControl.hidden = choices.length <= 1;
      if (trigger) refreshDataset(false);
    }
    function refreshDataset(useDefaults) {
      state.dataset = datasetById[els.priceBasis.value] || datasetsForMarket(els.market.value)[0] || datasets[0];
      state.samples = Array.isArray(state.dataset.horizon_samples) ? state.dataset.horizon_samples : [];
      state.config = Object.assign({ bin_width: 0.05, quantile_probabilities: [0.1, 0.5, 0.9] }, state.dataset.analysis_config || {});
      state.strategies = Object.keys(strategyLabels).filter(function (strategy) { return state.samples.some(function (horizon) { return Array.isArray((horizon.returns || {})[strategy]); }); });
      state.horizons = state.samples.map(function (item) { return Number(item.horizon_months); }).filter(Number.isFinite).sort(function (a, b) { return a - b; });
      const allDates = state.samples.reduce(function (dates, item) { return dates.concat(item.start_dates || []); }, []).sort();
      state.minimumDate = String(state.config.minimum_date || allDates[0] || ""); state.maximumDate = String(state.config.maximum_date || allDates[allDates.length - 1] || "");
      fillSelect(els.strategy, state.strategies, labelStrategy); fillSelect(els.horizon, state.horizons, labelHorizon);
      els.strategy.value = state.strategies.includes(defaults.strategy) ? defaults.strategy : state.strategies[0] || "";
      els.horizon.value = state.horizons.includes(defaults.horizon) ? String(defaults.horizon) : String(state.horizons[0] || "");
      [els.startDate, els.endDate].forEach(function (input) { input.min = state.minimumDate; input.max = state.maximumDate; });
      els.startDate.value = String(state.config.default_start_date || state.minimumDate); els.endDate.value = String(state.config.default_end_date || state.maximumDate);
      els.eyebrow.textContent = state.dataset.market_label + " · 离线分析"; els.title.textContent = String(state.dataset.title || rawPayload.title || "指数历史收益分布报告"); els.subtitle.textContent = String(state.dataset.subtitle || rawPayload.subtitle || "");
      els.priceNote.textContent = String(state.dataset.price_note || "不同点位口径独立回测，不插值、不混算。") + " 每个有效交易日作为滚动起点；日期仅筛选起点，目标到期日非交易日时顺延到其后首个有效交易日。";
      els.summaryTitle.textContent = (state.dataset.market_id === "csi300" ? "沪深300 24 组合汇总（当前口径 12 组合）" : "NASDAQ-100 12 组合汇总");
      statisticsCache = null; marketStatisticsCache = {}; marketRiskCache = {}; cacheDateKey = ""; renderMetadata(); renderForDateChange();
    }
    function labelStrategy(value) { return String(strategyLabels[value] || value || "未命名策略"); }
    function labelHorizon(value) { const label = horizonLabels[value] || horizonLabels[String(value)]; if (label) return String(label); const months = Number(value); return months % 12 === 0 ? (months / 12) + " 年" : months + " 个月"; }
    function fillSelect(select, values, formatter) { select.replaceChildren(); values.forEach(function (value) { const option = document.createElement("option"); option.value = String(value); option.textContent = formatter(value); select.appendChild(option); }); }
    function currentValidation() { return validateDateRange(els.startDate.value, els.endDate.value, state.minimumDate, state.maximumDate); }
    function renderForDateChange() {
      const validation = currentValidation(); els.dateMessage.textContent = validation.message; els.startDate.setAttribute("aria-invalid", String(!validation.valid)); els.endDate.setAttribute("aria-invalid", String(!validation.valid));
      if (!validation.valid) { statisticsCache = {}; marketStatisticsCache = {}; marketRiskCache = {}; renderSummary(); renderRiskSummary(); renderSelected(); return; }
      const key = state.dataset.id + "|" + els.startDate.value + "|" + els.endDate.value;
      if (key !== cacheDateKey || !statisticsCache) {
        statisticsCache = computeAllStatistics(state.samples, state.strategies, els.startDate.value, els.endDate.value, state.config);
        marketStatisticsCache = {}; marketRiskCache = {};
        datasetsForMarket(state.dataset.market_id).forEach(function (dataset) {
          const datasetConfig = Object.assign({ bin_width: 0.05, quantile_probabilities: [0.1, 0.5, 0.9] }, dataset.analysis_config || {});
          marketStatisticsCache[dataset.id] = computeAllStatistics(dataset.horizon_samples || [], state.strategies, els.startDate.value, els.endDate.value, datasetConfig);
          marketRiskCache[dataset.id] = computeAllMaximumLossStatistics(dataset.horizon_samples || [], state.strategies, els.startDate.value, els.endDate.value);
        });
        cacheDateKey = key;
      }
      renderSummary(); renderRiskSummary(); renderSelected();
    }
    function selectedStatistics() { return statisticsCache && statisticsCache[els.strategy.value + "|" + Number(els.horizon.value)] || null; }
    function renderSelected() { const item = selectedStatistics(); els.context.textContent = state.dataset.market_label + " · " + state.dataset.price_label + " · " + labelStrategy(els.strategy.value) + " · " + labelHorizon(Number(els.horizon.value)) + " · 起点 " + els.startDate.value + " 至 " + els.endDate.value + (item ? " · " + item.count + " 个样本" : " · 无样本"); renderKpis(item); renderHistogram(item); renderCdf(item); highlightSummary(); }
    function renderKpis(item) { els.kpis.replaceChildren(); const metrics = item ? [["样本数", formatInteger(item.count)], ["平均收益率", formatPercent(item.mean)], ["中位数", formatPercent(item.median)], ["盈利样本占比", formatPercent(item.profitProbability)], ["较差情景收益率（P10）", formatPercent(quantileValue(item.quantiles, 0.1))], ["较好情景收益率（P90）", formatPercent(quantileValue(item.quantiles, 0.9))]] : [["暂无数据", "—"]]; metrics.forEach(function (metric) { const card = element("article", "kpi"); card.append(element("div", "kpi-label", metric[0]), element("div", "kpi-value", metric[1])); els.kpis.appendChild(card); }); }
    function renderHistogram(item) { clearSvg(els.histogram); hideTooltip(els.histogramTooltip); if (!item) return drawEmpty(els.histogram); const layout = chartLayout(); setSvgFrame(els.histogram, layout); const maxY = niceMax(Math.max.apply(null, item.probabilities)); drawAxes(els.histogram, layout, item.edges[0], item.edges[item.edges.length - 1], maxY); const plotWidth = layout.width - layout.left - layout.right; const plotHeight = layout.height - layout.top - layout.bottom; const slot = plotWidth / item.probabilities.length; item.probabilities.forEach(function (probability, index) { const height = maxY ? probability / maxY * plotHeight : 0; const mark = svg("rect", { x: layout.left + index * slot + 1, y: layout.top + plotHeight - height, width: Math.max(1, slot - 2), height: height, class: item.edges[index + 1] <= 0 ? "bar negative" : "bar", tabindex: "0", role: "img", "aria-label": intervalText(item, index) }); bindTooltip(mark, els.histogramTooltip, function () { return intervalText(item, index); }); els.histogram.appendChild(mark); }); drawZeroLine(els.histogram, layout, item.edges[0], item.edges[item.edges.length - 1]); }
    function renderCdf(item) { clearSvg(els.cdf); hideTooltip(els.cdfTooltip); if (!item) return drawEmpty(els.cdf); const layout = chartLayout(); setSvgFrame(els.cdf, layout); const xMin = item.edges[0]; const xMax = item.edges[item.edges.length - 1]; drawAxes(els.cdf, layout, xMin, xMax, 1); const xValues = item.cdf.map(function (_, index) { return item.edges[index + 1]; }); const points = xValues.map(function (value, index) { return [scaleX(value, xMin, xMax, layout), scaleY(item.cdf[index], 1, layout)]; }); const path = points.map(function (point, index) { return (index ? "L" : "M") + point[0].toFixed(2) + " " + point[1].toFixed(2); }).join(" "); els.cdf.appendChild(svg("path", { d: path, class: "cdf-line" })); points.forEach(function (point, index) { const description = "收益率不超过 " + formatPercent(xValues[index]) + "\n累计概率 " + formatPercent(item.cdf[index]); const hit = svg("circle", { cx: point[0], cy: point[1], r: 7, class: "cdf-point", tabindex: "0", role: "img", "aria-label": description }); bindTooltip(hit, els.cdfTooltip, function () { return description; }); els.cdf.appendChild(hit); }); drawZeroLine(els.cdf, layout, xMin, xMax); }
    function renderDatasetHeader(targetBody, label, labels) { const groupRow = document.createElement("tr"); const groupHeader = element("th", "horizon-group", label); groupHeader.colSpan = labels.length; groupHeader.setAttribute("scope", "colgroup"); groupRow.appendChild(groupHeader); targetBody.appendChild(groupRow); const columnRow = document.createElement("tr"); columnRow.className = "group-column-header"; labels.forEach(function (value, index) { const headerClass = index === 1 ? "strategy-column" : value === "历史收益分布" || value === "最大亏损频率分布" ? "distribution-column" : ""; const header = element("th", headerClass, value); header.setAttribute("scope", "col"); columnRow.appendChild(header); }); targetBody.appendChild(columnRow); }
    function strategyCell(strategy) { const node = cell(""); node.className = "strategy-column"; node.appendChild(element("span", "strategy-badge", labelStrategy(strategy))); return node; }
    function renderSummary() {
      els.summary.replaceChildren();
      const marketDatasets = datasetsForMarket(state.dataset.market_id);
      els.summaryHead.hidden = marketDatasets.length > 1;
      const labels = ["期限", "策略", "样本数", "盈利样本占比", "累计收益率均值", "累计收益率中位数", "较差情景收益率（P10）", "较好情景收益率（P90）", "历史收益分布"];
      marketDatasets.forEach(function (dataset) {
        const samples = dataset.horizon_samples || [];
        const cache = marketStatisticsCache[dataset.id] || {};
        if (marketDatasets.length > 1) renderDatasetHeader(els.summary, dataset.price_label, labels);
        samples.forEach(function (horizon) {
          const horizonItems = state.strategies.map(function (strategy) { return cache[strategy + "|" + Number(horizon.horizon_months)] || null; });
          const alignedHistograms = alignHistogramStatistics(horizonItems);
          state.strategies.forEach(function (strategy, strategyIndex) {
            const item = horizonItems[strategyIndex];
            const row = document.createElement("tr");
            row.dataset.dataset = dataset.id;
            row.dataset.strategy = strategy;
            row.dataset.horizon = String(horizon.horizon_months);
            row.className = "summary-row " + (strategy === "daily_investment" ? "daily-investment" : "single-purchase");
            if (strategyIndex === 0) { const horizonCell = cell(labelHorizon(horizon.horizon_months)); horizonCell.rowSpan = state.strategies.length; horizonCell.className = "horizon-group"; row.appendChild(horizonCell); }
            row.appendChild(strategyCell(strategy));
            row.appendChild(cell(item ? formatInteger(item.count) : "—"));
            row.appendChild(cell(item ? formatPercent(item.profitProbability) : "—"));
            [item && item.mean, item && item.median].forEach(function (value) { row.appendChild(returnCell(value)); });
            row.appendChild(returnCell(item ? quantileValue(item.quantiles, 0.1) : null));
            row.appendChild(returnCell(item ? quantileValue(item.quantiles, 0.9) : null));
            row.appendChild(sparkHistogramCell(item, alignedHistograms.edges, alignedHistograms.rows[strategyIndex], labelStrategy(strategy), labelHorizon(horizon.horizon_months)));
            els.summary.appendChild(row);
          });
        });
      });
    }
    function renderRiskSummary() {
      els.riskSummary.replaceChildren();
      const marketDatasets = datasetsForMarket(state.dataset.market_id);
      els.riskSummaryHead.hidden = marketDatasets.length > 1;
      els.riskContext.textContent = state.dataset.market_label + " · " + (marketDatasets.length > 1 ? "两种点位口径共 24 行" : "当前点位口径共 12 行") + " · 起点 " + els.startDate.value + " 至 " + els.endDate.value;
      const labels = ["期限", "策略", "样本数", "最大亏损平均值", "最大亏损中位数", "最大亏损P90", "P95", "P100", "最大亏损频率分布"];
      marketDatasets.forEach(function (dataset) {
        const samples = dataset.horizon_samples || []; const cache = marketRiskCache[dataset.id] || {};
        if (marketDatasets.length > 1) renderDatasetHeader(els.riskSummary, dataset.price_label, labels);
        samples.forEach(function (horizon) {
          const horizonItems = state.strategies.map(function (strategy) { return cache[strategy + "|" + Number(horizon.horizon_months)] || null; });
          const alignedHistograms = alignHistogramStatistics(horizonItems);
          state.strategies.forEach(function (strategy, strategyIndex) {
            const item = horizonItems[strategyIndex]; const row = document.createElement("tr");
            row.className = "summary-row " + (strategy === "daily_investment" ? "daily-investment" : "single-purchase");
            if (strategyIndex === 0) { const horizonCell = cell(labelHorizon(horizon.horizon_months)); horizonCell.rowSpan = state.strategies.length; horizonCell.className = "horizon-group"; row.appendChild(horizonCell); }
            row.appendChild(strategyCell(strategy));
            row.appendChild(cell(item ? formatInteger(item.count) : "—"));
            [item && item.mean, item && item.median, item && item.p90, item && item.p95, item && item.p100].forEach(function (value) { row.appendChild(riskCell(value)); });
            row.appendChild(sparkMaximumLossCell(item, alignedHistograms.edges, alignedHistograms.rows[strategyIndex], labelStrategy(strategy), labelHorizon(horizon.horizon_months)));
            els.riskSummary.appendChild(row);
          });
        });
      });
    }
    function highlightSummary() { Array.from(els.summary.rows).forEach(function (row) { if (row.dataset.dataset === state.dataset.id && row.dataset.strategy === els.strategy.value && Number(row.dataset.horizon) === Number(els.horizon.value)) row.setAttribute("aria-current", "true"); else row.removeAttribute("aria-current"); }); }
    function renderMetadata() { const metadata = state.dataset.metadata; if (!metadata) return; if (typeof metadata === "string") { els.metadata.textContent = metadata; return; } els.metadata.textContent = Object.keys(metadata).map(function (key) { return key + "：" + String(metadata[key]); }).join(" · "); }
    function setTheme(theme) { document.body.dataset.theme = theme; const dark = theme === "dark"; els.theme.setAttribute("aria-pressed", String(dark)); els.theme.textContent = dark ? "切换明亮主题" : "切换深色主题"; }
  }

  function sparkHistogramCell(item, edges, probabilities, strategyLabel, horizonLabel) {
    const node = cell(""); node.className = "spark-cell";
    if (!item || !Array.isArray(probabilities) || !probabilities.length || !Array.isArray(edges) || edges.length < 2) { node.appendChild(element("span", "spark-empty", "—")); return node; }
    const wrap = element("span", "spark-histogram-wrap");
    const chart = svg("svg", { viewBox: "0 0 96 28", width: "96", height: "28", class: "spark-histogram", tabindex: "0", role: "img" });
    const xMin = edges[0]; const xMax = edges[edges.length - 1]; const maxY = Math.max.apply(null, probabilities); const slot = 96 / probabilities.length;
    probabilities.forEach(function (probability, index) { const height = maxY > 0 ? Number(probability) / maxY * 25 : 0; chart.appendChild(svg("rect", { x: (index * slot + 0.5).toFixed(2), y: (27 - height).toFixed(2), width: Math.max(0.5, slot - 1).toFixed(2), height: height.toFixed(2), class: edges[index + 1] <= 0 ? "spark-bar negative" : "spark-bar" })); });
    if (xMin <= 0 && xMax >= 0) { const zeroX = (0 - xMin) / (xMax - xMin || 1) * 96; chart.appendChild(svg("line", { x1: zeroX.toFixed(2), y1: 1, x2: zeroX.toFixed(2), y2: 28, class: "spark-zero-line" })); }
    const description = horizonLabel + " · " + strategyLabel + "历史收益分布，共 " + formatInteger(item.count) + " 个样本，范围 " + formatPercent(item.minimum) + " 至 " + formatPercent(item.maximum) + "，最高区间占比 " + formatPercent(maxY);
    chart.setAttribute("aria-label", description);
    const tooltip = element("span", "tooltip spark-tooltip"); tooltip.setAttribute("role", "tooltip"); tooltip.hidden = true;
    bindTooltip(chart, tooltip, function () { return description; });
    wrap.append(chart, tooltip); node.appendChild(wrap); return node;
  }

  function sparkMaximumLossCell(item, edges, probabilities, strategyLabel, horizonLabel) {
    const node = cell(""); node.className = "spark-cell";
    if (!item || !Array.isArray(probabilities) || !probabilities.length || !Array.isArray(edges) || edges.length < 2) { node.appendChild(element("span", "spark-empty", "—")); return node; }
    const wrap = element("span", "spark-histogram-wrap");
    const chart = svg("svg", { viewBox: "0 0 96 28", width: "96", height: "28", class: "spark-histogram risk-spark-histogram", tabindex: "0", role: "img" });
    const maxY = Math.max.apply(null, probabilities); const slot = 96 / probabilities.length;
    chart.appendChild(svg("line", { x1: 0, y1: 27, x2: 96, y2: 27, class: "spark-loss-baseline" }));
    probabilities.forEach(function (probability, index) { const height = maxY > 0 ? Number(probability) / maxY * 25 : 0; chart.appendChild(svg("rect", { x: (index * slot + 0.5).toFixed(2), y: (27 - height).toFixed(2), width: Math.max(0.5, slot - 1).toFixed(2), height: height.toFixed(2), class: "spark-loss-bar" })); });
    const bins = probabilities.map(function (probability, index) { const count = Math.round(Number(probability) * item.count); return formatInterval(edges[index], edges[index + 1], index === probabilities.length - 1) + "：" + formatInteger(count) + " 个（" + formatPercent(probability) + "）"; });
    const description = horizonLabel + " · " + strategyLabel + "最大亏损频率分布，共 " + formatInteger(item.count) + " 个样本，2% 区间从 0% 起，P100 " + formatPercent(item.p100) + "，各区间：\n" + bins.join("\n");
    chart.setAttribute("aria-label", description);
    const tooltip = element("span", "tooltip spark-tooltip"); tooltip.setAttribute("role", "tooltip"); tooltip.hidden = true;
    bindTooltip(chart, tooltip, function () { return description; });
    wrap.append(chart, tooltip); node.appendChild(wrap); return node;
  }

  function chartLayout() { return { width: 640, height: 330, left: 64, right: 18, top: 18, bottom: 54 }; }
  function setSvgFrame(target, layout) { target.setAttribute("viewBox", "0 0 " + layout.width + " " + layout.height); target.setAttribute("preserveAspectRatio", "xMidYMid meet"); }
  function drawAxes(target, layout, xMin, xMax, yMax) { const bottom = layout.height - layout.bottom; const right = layout.width - layout.right; for (let index = 0; index <= 4; index += 1) { const ratio = index / 4; const y = bottom - ratio * (bottom - layout.top); target.appendChild(svg("line", { x1: layout.left, y1: y, x2: right, y2: y, class: "grid-line" })); target.appendChild(svgText(layout.left - 9, y + 4, formatPercent(ratio * yMax, 0), "tick-label", "end")); } target.appendChild(svg("line", { x1: layout.left, y1: layout.top, x2: layout.left, y2: bottom, class: "axis" })); target.appendChild(svg("line", { x1: layout.left, y1: bottom, x2: right, y2: bottom, class: "axis" })); const span = xMax - xMin; const width = 0.05; let tickIndex = 0; for (let value = xMin; value <= xMax + 1e-12; value += width) { const rounded = Math.round(value / width) * width; if (tickIndex % Math.max(1, Math.ceil((span / width) / 10)) === 0 || Math.abs(rounded) < 1e-12 || rounded >= xMax - 1e-12) { const x = scaleX(rounded, xMin, xMax, layout); target.appendChild(svgText(x, bottom + 22, formatPercent(rounded, 0), "tick-label", rounded === xMin ? "start" : rounded >= xMax - 1e-12 ? "end" : "middle")); } tickIndex += 1; } target.appendChild(svgText((layout.left + right) / 2, layout.height - 10, "收益率", "axis-label", "middle")); const yLabel = svgText(15, (layout.top + bottom) / 2, "概率", "axis-label", "middle"); yLabel.setAttribute("transform", "rotate(-90 15 " + ((layout.top + bottom) / 2) + ")"); target.appendChild(yLabel); }
  function drawZeroLine(target, layout, xMin, xMax) { if (xMin <= 0 && xMax >= 0) { const x = scaleX(0, xMin, xMax, layout); target.appendChild(svg("line", { x1: x, y1: layout.top, x2: x, y2: layout.height - layout.bottom, class: "zero-line" })); } }
  function niceMax(value) { if (!Number.isFinite(value) || value <= 0) return 1; const step = value <= 0.25 ? 0.05 : value <= 0.5 ? 0.1 : 0.25; return Math.ceil(value / step) * step; }
  function scaleX(value, min, max, layout) { return layout.left + (value - min) / (max - min || 1) * (layout.width - layout.left - layout.right); }
  function scaleY(value, max, layout) { const bottom = layout.height - layout.bottom; return bottom - value / (max || 1) * (bottom - layout.top); }
  function quantileValue(quantiles, probability) { const match = (quantiles || []).find(function (entry) { return Math.abs(entry.probability - probability) <= 0.011; }); return match ? match.value : null; }
  function intervalText(item, index) { return formatInterval(item.edges[index], item.edges[index + 1], index === item.probabilities.length - 1) + "\n样本数 " + formatInteger(item.counts[index]) + "\n样本占比 " + formatPercent(item.probabilities[index]) + "\n累计占比 " + formatPercent(item.cdf[index]); }
  function formatInterval(left, right, isLast) { return "[" + formatPercent(left) + ", " + formatPercent(right) + (isLast ? "]" : ")"); }
  function formatPercent(value, digits) { if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—"; return new Intl.NumberFormat("zh-CN", { style: "percent", minimumFractionDigits: digits == null ? 1 : digits, maximumFractionDigits: digits == null ? 1 : digits }).format(Number(value)); }
  function formatInteger(value) { return Number.isFinite(Number(value)) ? new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(Number(value)) : "—"; }
  function element(tag, className, text) { const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = text; return node; }
  function cell(text) { return element("td", "", text); }
  function returnCell(value) { const node = cell(formatPercent(value)); if (Number.isFinite(Number(value))) node.className = Number(value) < 0 ? "return-negative" : Number(value) > 0 ? "return-positive" : ""; return node; }
  function riskCell(value) { const node = cell(formatPercent(value)); if (Number.isFinite(Number(value))) node.className = "risk-value"; return node; }
  function svg(tag, attributes) { const node = document.createElementNS(NS, tag); Object.keys(attributes).forEach(function (key) { node.setAttribute(key, String(attributes[key])); }); return node; }
  function svgText(x, y, text, className, anchor) { const node = svg("text", { x: x, y: y, class: className, "text-anchor": anchor }); node.textContent = text; return node; }
  function clearSvg(target) { target.replaceChildren(); }
  function drawEmpty(target) { target.setAttribute("viewBox", "0 0 640 180"); target.appendChild(svgText(320, 90, "当前日期范围暂无样本", "tick-label", "middle")); }
  function bindTooltip(mark, tooltip, textProvider) { function show(event) { tooltip.textContent = textProvider(); tooltip.hidden = false; positionTooltip(event, mark, tooltip); } mark.addEventListener("mouseenter", show); mark.addEventListener("mousemove", show); mark.addEventListener("mouseleave", function () { hideTooltip(tooltip); }); mark.addEventListener("focus", show); mark.addEventListener("blur", function () { hideTooltip(tooltip); }); }
  function positionTooltip(event, mark, tooltip) { const wrap = tooltip.parentElement.getBoundingClientRect(); if (event && typeof event.clientX === "number" && event.clientX) { tooltip.style.left = (event.clientX - wrap.left) + "px"; tooltip.style.top = (event.clientY - wrap.top) + "px"; return; } const rect = mark.getBoundingClientRect(); tooltip.style.left = (rect.left + rect.width / 2 - wrap.left) + "px"; tooltip.style.top = (rect.top - wrap.top) + "px"; }
  function hideTooltip(tooltip) { tooltip.hidden = true; }

  return { start: start, filterReturns: filterReturns, histogramEdges: histogramEdges, summarizeReturns: summarizeReturns, summarizeMaximumLosses: summarizeMaximumLosses, computeAllStatistics: computeAllStatistics, computeAllMaximumLossStatistics: computeAllMaximumLossStatistics, validateDateRange: validateDateRange, subtractCalendarYears: subtractCalendarYears, presetDateRange: presetDateRange, quantile: quantile, normalizeDatasets: normalizeDatasets, alignHistogramStatistics: alignHistogramStatistics };
}));

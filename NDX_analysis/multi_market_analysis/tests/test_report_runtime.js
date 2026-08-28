"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const runtime = require("../core/report_runtime.js");

const config = { bin_width: 0.05, quantile_probabilities: [0.1, 0.5, 0.9] };

test("closed start-date filtering does not inspect holding end dates", () => {
  const values = runtime.filterReturns(
    ["2020-01-02", "2020-01-03", "2020-01-06"],
    [-0.1, 0.2, 0.4],
    "2020-01-03",
    "2020-01-06"
  );
  assert.deepEqual(values, [0.2, 0.4]);
});

test("statistics use zero-aligned 5 percent bins covering extrema", () => {
  const stats = runtime.summarizeReturns([-0.1, -0.02, 0, 0.11], config);
  assert.equal(stats.count, 4);
  assert.equal(stats.edges[0], -0.1);
  assert.ok(Math.abs(stats.edges.at(-1) - 0.15) < 1e-12);
  assert.ok(stats.edges.some((value) => Math.abs(value) < 1e-12));
  assert.equal(stats.counts.reduce((sum, value) => sum + value, 0), 4);
  assert.equal(stats.cdf.at(-1), 1);
});

test("an exact positive upper edge gets an additional bin", () => {
  assert.deepEqual(runtime.histogramEdges([0, 0.1], 0.05), [0, 0.05, 0.1, 0.15000000000000002]);
});

test("each selected distribution gets its own compact axis range", () => {
  const shortTerm = runtime.summarizeReturns([-0.08, 0.03, 0.12], config);
  const longTerm = runtime.summarizeReturns([0.2, 1.1, 2.4], config);
  assert.ok(shortTerm.edges.at(-1) <= 0.15 + 1e-12);
  assert.ok(longTerm.edges.at(-1) >= 2.4);
  assert.notDeepEqual(shortTerm.edges, longTerm.edges);
});

test("spark histograms align two strategies to a zero-filled union axis", () => {
  const single = runtime.summarizeReturns([-0.12, -0.07, 0.03], config);
  const daily = runtime.summarizeReturns([-0.02, 0.08, 0.12], config);
  const aligned = runtime.alignHistogramStatistics([single, daily]);
  assert.deepEqual(aligned.edges, [-0.15000000000000002, -0.1, -0.05, 0, 0.05, 0.1, 0.15000000000000002]);
  assert.equal(aligned.rows[0].length, aligned.edges.length - 1);
  assert.equal(aligned.rows[1].length, aligned.edges.length - 1);
  assert.deepEqual(aligned.rows[0].slice(-2), [0, 0]);
  assert.deepEqual(aligned.rows[1].slice(0, 2), [0, 0]);
  assert.ok(Math.abs(aligned.rows[0].reduce((sum, value) => sum + value, 0) - 1) < 1e-12);
  assert.ok(Math.abs(aligned.rows[1].reduce((sum, value) => sum + value, 0) - 1) < 1e-12);
});

test("spark histogram alignment preserves empty placeholders", () => {
  const item = runtime.summarizeReturns([0.01, 0.02], config);
  const aligned = runtime.alignHistogramStatistics([item, null]);
  assert.equal(aligned.rows[0].length, aligned.edges.length - 1);
  assert.equal(aligned.rows[1], null);
  assert.deepEqual(runtime.alignHistogramStatistics([null, null]), { edges: [], rows: [null, null] });
});

test("all strategy and horizon combinations recompute for a date change", () => {
  const samples = [
    { horizon_months: 1, start_dates: ["2020-01-01", "2020-01-02"], returns: { a: [0.1, 0.2], b: [-0.1, 0.3] } },
    { horizon_months: 3, start_dates: ["2020-01-01", "2020-01-03"], returns: { a: [0.4, 0.5], b: [0.2, 0.6] } }
  ];
  const result = runtime.computeAllStatistics(samples, ["a", "b"], "2020-01-02", "2020-01-03", config);
  assert.equal(Object.keys(result).length, 4);
  assert.equal(result["a|1"].count, 1);
  assert.equal(result["b|3"].count, 1);
});

test("calendar-year presets use maximum date, clamp minimum date, and handle leap day", () => {
  assert.equal(runtime.subtractCalendarYears("2024-02-29", 2), "2022-02-28");
  assert.equal(runtime.subtractCalendarYears("2020-02-29", 20), "2000-02-29");
  assert.deepEqual(runtime.presetDateRange(5, "2000-01-01", "2026-08-03"), {
    startDate: "2021-08-03", endDate: "2026-08-03"
  });
  assert.deepEqual(runtime.presetDateRange(20, "2010-01-01", "2026-08-03"), {
    startDate: "2010-01-01", endDate: "2026-08-03"
  });
});

test("reversed, out-of-range, and empty selections are handled", () => {
  assert.equal(runtime.validateDateRange("2020-02-01", "2020-01-01", "2020-01-01", "2020-12-31").valid, false);
  assert.equal(runtime.validateDateRange("2019-12-31", "2020-02-01", "2020-01-01", "2020-12-31").valid, false);
  assert.equal(runtime.validateDateRange("2020-01-01", "2020-02-01", "2020-01-01", "2020-12-31").valid, true);
  assert.equal(runtime.summarizeReturns([], config), null);
});

test("maximum-loss statistics use two-percent bins from zero and expose P100", () => {
  const stats = runtime.summarizeMaximumLosses([0, 0.01, 0.02, 0.039, 0.04]);
  assert.equal(stats.count, 5);
  assert.ok(Math.abs(stats.mean - 0.0218) < 1e-12);
  assert.equal(stats.median, 0.02);
  assert.ok(Math.abs(stats.p90 - 0.0396) < 1e-12);
  assert.ok(Math.abs(stats.p95 - 0.0398) < 1e-12);
  assert.equal(stats.p100, 0.04);
  assert.deepEqual(stats.edges, [0, 0.02, 0.04, 0.06]);
  assert.deepEqual(stats.counts, [2, 2, 1]);
  assert.deepEqual(stats.probabilities, [0.4, 0.4, 0.2]);
  assert.equal(stats.counts.reduce((sum, value) => sum + value, 0), stats.count);
  assert.equal("worst" in stats, false);
  assert.equal("atLeast10" in stats, false);
  assert.equal("atLeast20" in stats, false);
  assert.equal("atLeast30" in stats, false);
});

test("maximum-loss strategy sparks align on one horizon axis", () => {
  const single = runtime.summarizeMaximumLosses([0, 0.01, 0.07]);
  const daily = runtime.summarizeMaximumLosses([0.02, 0.03]);
  const aligned = runtime.alignHistogramStatistics([single, daily]);
  assert.deepEqual(aligned.edges, [0, 0.02, 0.04, 0.06, 0.08]);
  assert.deepEqual(aligned.rows[0], [2 / 3, 0, 0, 1 / 3]);
  assert.deepEqual(aligned.rows[1], [0, 1, 0, 0]);
});

test("maximum-loss combinations recompute using the same closed date filter", () => {
  const samples = [{ horizon_months: 1, start_dates: ["2020-01-01", "2020-01-02"], maximum_losses: { a: [0.1, 0.4], b: [0, 0.2] } }];
  const result = runtime.computeAllMaximumLossStatistics(samples, ["a", "b"], "2020-01-02", "2020-01-02");
  assert.equal(result["a|1"].p100, 0.4);
  assert.equal(result["b|1"].mean, 0.2);
});

test("legacy payload becomes one selectable dataset", () => {
  const datasets = runtime.normalizeDatasets({
    title: "NDX", analysis_config: { minimum_date: "2020-01-01" },
    horizon_samples: [{ horizon_months: 1, start_dates: [], returns: {} }]
  });
  assert.equal(datasets.length, 1);
  assert.equal(datasets[0].id, "legacy");
  assert.equal(datasets[0].market_label, "NASDAQ-100");
});

test("separate point-basis datasets are never mixed", () => {
  const close = runtime.computeAllStatistics([
    { horizon_months: 1, start_dates: ["2020-01-01"], returns: { a: [0.1] } }
  ], ["a"], "2020-01-01", "2020-12-31", config);
  const total = runtime.computeAllStatistics([
    { horizon_months: 1, start_dates: ["2021-01-01"], returns: { a: [0.9] } }
  ], ["a"], "2021-01-01", "2021-12-31", config);
  assert.equal(close["a|1"].mean, 0.1);
  assert.equal(total["a|1"].mean, 0.9);
});

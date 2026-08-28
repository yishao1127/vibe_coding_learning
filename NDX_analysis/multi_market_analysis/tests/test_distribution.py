import unittest

from multi_market_analysis.core.distribution import (
    analyze_distributions,
    shared_histogram_edges,
    summarize_distribution,
)


class DistributionTests(unittest.TestCase):
    def test_shared_edges_are_five_points_and_zero_aligned(self):
        edges = shared_histogram_edges([[-0.12, 0.03], [0.10]], 0.05)
        self.assertEqual(edges, (-0.15000000000000002, -0.1, -0.05, 0.0, 0.05, 0.1, 0.15000000000000002))
        self.assertIn(0.0, edges)
        for left, right in zip(edges, edges[1:]):
            self.assertAlmostEqual(right - left, 0.05)

    def test_statistics_histogram_probabilities_and_cdf(self):
        values = [-0.1, 0.0, 0.1, 0.2]
        edges = (-0.1, 0.0, 0.1, 0.2, 0.3)
        stats = summarize_distribution(values, edges, (0.0, 0.5, 1.0))
        self.assertEqual(stats.count, 4)
        self.assertAlmostEqual(stats.mean, 0.05)
        self.assertAlmostEqual(stats.population_stddev, (0.0125) ** 0.5)
        self.assertEqual(stats.quantiles, {0.0: -0.1, 0.5: 0.05, 1.0: 0.2})
        self.assertEqual(stats.loss_probability, 0.25)
        self.assertEqual(stats.break_even_probability, 0.25)
        self.assertEqual(stats.profit_probability, 0.5)
        self.assertEqual(stats.bin_counts, (1, 1, 1, 1))
        self.assertEqual(stats.bin_probabilities, (0.25, 0.25, 0.25, 0.25))
        self.assertEqual(stats.cdf, (0.25, 0.5, 0.75, 1.0))

    def test_named_datasets_use_identical_edges(self):
        edges, results = analyze_distributions({"one": [-0.01], "two": [0.11]})
        self.assertEqual(results["one"].bin_edges, edges)
        self.assertEqual(results["two"].bin_edges, edges)

    def test_rejects_empty_input(self):
        with self.assertRaises(ValueError):
            shared_histogram_edges([])
        with self.assertRaises(ValueError):
            summarize_distribution([], (0, 0.05))


if __name__ == "__main__":
    unittest.main()

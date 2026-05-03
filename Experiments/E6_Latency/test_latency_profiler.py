import unittest

from Experiments.E6_Latency.latency_profiler import summarize_latency


class LatencyProfilerTests(unittest.TestCase):
    def test_summarize_latency_computes_total_uncached(self) -> None:
        rows = [
            {
                "audio_preprocess_ms": 1.0,
                "wav2vec_forward_ms": 10.0,
                "trr_encoding_ms": 2.0,
                "search_ms": 0.5,
                "validation_ms": 0.5,
            }
        ]

        summary = summarize_latency(rows)

        self.assertEqual(summary["median_total_uncached_ms"], 14.0)

    def test_summarize_latency_reports_p95(self) -> None:
        rows = [
            {
                "audio_preprocess_ms": 0.0,
                "wav2vec_forward_ms": float(i),
                "trr_encoding_ms": 0.0,
                "search_ms": 0.0,
                "validation_ms": 0.0,
            }
            for i in range(1, 101)
        ]

        summary = summarize_latency(rows)

        self.assertEqual(summary["p95_total_uncached_ms"], 95.0)

    def test_summarize_latency_rejects_empty_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "latency rows must not be empty"):
            summarize_latency([])


if __name__ == "__main__":
    unittest.main()

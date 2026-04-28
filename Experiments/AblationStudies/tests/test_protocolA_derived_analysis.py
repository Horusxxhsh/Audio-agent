import tempfile
import unittest
from pathlib import Path

from Experiments.AblationStudies.protocolA_derived_analysis import (
    analyze_protocol_a,
    classify_delta,
    format_markdown,
    signed_delta,
)


CSV_TEXT = """query_idx,query_name,method,retrieved_name,l2,acc@0.1,recall,cosine,module,missing
1,Q1,TRR,TRR-A,0.10,0.90,0.80,0.95,1.00,0
2,Q2,TRR,TRR-B,0.50,0.40,0.30,0.60,0.70,0
3,Q3,TRR,TRR-C,0.25,0.60,0.50,0.70,0.80,0
1,Q1,Text-RAG,TXT-A,0.20,0.85,0.75,0.90,0.90,0
2,Q2,Text-RAG,TXT-B,0.40,0.35,0.20,0.55,0.75,0
3,Q3,Text-RAG,TXT-C,0.25,0.65,0.55,0.68,0.80,0
1,Q1,Wav2Vec-RAG,W2V-A,0.12,0.88,0.70,0.91,0.95,0
2,Q2,Wav2Vec-RAG,W2V-B,0.80,0.20,0.10,0.40,0.50,0
3,Q3,Wav2Vec-RAG,W2V-C,0.20,0.65,0.45,0.69,0.78,0
"""


class ProtocolADerivedAnalysisTests(unittest.TestCase):
    def test_signed_delta_uses_metric_direction(self) -> None:
        self.assertAlmostEqual(signed_delta(0.3, 0.5, "l2"), 0.2)
        self.assertAlmostEqual(signed_delta(0.7, 0.5, "cosine"), 0.2)

    def test_classify_delta_handles_wins_losses_and_ties(self) -> None:
        self.assertEqual(classify_delta(0.1), "win")
        self.assertEqual(classify_delta(-0.1), "loss")
        self.assertEqual(classify_delta(0.0), "tie")

    def test_analyze_protocol_a_summarizes_pairwise_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "protocolA.csv"
            csv_path.write_text(CSV_TEXT, encoding="utf-8")

            report = analyze_protocol_a(csv_path, top_k=2)

        self.assertEqual(report["query_count"], 3)
        self.assertEqual(report["unique_query_names"], 3)
        baselines = {entry["baseline"]: entry for entry in report["baselines"]}

        text_summary = baselines["Text-RAG"]["metric_summaries"]["l2"]
        self.assertEqual(text_summary["wins"], 1)
        self.assertEqual(text_summary["losses"], 1)
        self.assertEqual(text_summary["ties"], 1)

        wav_summary = baselines["Wav2Vec-RAG"]["metric_summaries"]["acc@0.1"]
        self.assertEqual(wav_summary["wins"], 2)
        self.assertEqual(wav_summary["losses"], 1)

        top_gain = baselines["Wav2Vec-RAG"]["top_gains_l2"][0]
        self.assertEqual(top_gain["query_idx"], 2)
        self.assertAlmostEqual(top_gain["delta_l2"], 0.3)

    def test_format_markdown_includes_bookkeeping_note_and_case_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "protocolA.csv"
            csv_path.write_text(CSV_TEXT, encoding="utf-8")
            report = analyze_protocol_a(csv_path, top_k=1)

        markdown = format_markdown(report)
        self.assertIn("Pairing is performed by `query_idx`", markdown)
        self.assertIn("Largest TRR Gains by L2", markdown)
        self.assertIn("Largest TRR Failures by L2", markdown)


if __name__ == "__main__":
    unittest.main()

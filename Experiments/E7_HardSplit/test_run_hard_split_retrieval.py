import tempfile
import unittest
from pathlib import Path

from Experiments.E7_HardSplit.run_hard_split_retrieval import load_requested_query_indices, write_outputs


class HardSplitRunnerTests(unittest.TestCase):
    def test_write_outputs_creates_json_csv_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            results = [
                {"method": "TRR", "n": 2, "norm_l2": 0.2, "acc_at_0_1": 0.6, "coverage": 1.0},
                {"method": "Wav2Vec", "n": 2, "norm_l2": 0.3, "acc_at_0_1": 0.5, "coverage": 1.0},
            ]
            audit = {"threshold": 0.02, "test_count": 2, "kb_count": 3}

            write_outputs(output_dir, results, audit)

            self.assertTrue((output_dir / "hard_split_results.json").exists())
            self.assertTrue((output_dir / "hard_split_results.csv").exists())
            self.assertTrue((output_dir / "hard_split_audit.json").exists())

    def test_csv_contains_method_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            write_outputs(output_dir, [{"method": "TRR", "n": 1, "norm_l2": 0.2}], {"threshold": 0.02})

            csv_text = (output_dir / "hard_split_results.csv").read_text(encoding="utf-8")

        self.assertTrue(csv_text.startswith("method,n,norm_l2"))

    def test_json_is_pretty_printed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            write_outputs(output_dir, [{"method": "TRR", "n": 1}], {"threshold": 0.02})

            json_text = (output_dir / "hard_split_results.json").read_text(encoding="utf-8")

        self.assertIn("\n  {", json_text)

    def test_query_split_consumes_one_index_per_name_line(self) -> None:
        dataset = [
            {"SongName": "Hard Rock Crunch"},
            {"SongName": "Hard Rock Crunch"},
            {"SongName": "Neo-Soul Clean"},
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            split_file = Path(tmp_dir) / "test.txt"
            split_file.write_text("Hard Rock Crunch\nNeo-Soul Clean\n", encoding="utf-8")

            indices = load_requested_query_indices(dataset, split_file)

        self.assertEqual(indices, [0, 2])


if __name__ == "__main__":
    unittest.main()

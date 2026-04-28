import tempfile
import unittest
from pathlib import Path

from Experiments.common.query_splits import select_query_indices


class QuerySplitsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = [
            {"SongName": "Dry Funk"},
            {"SongName": "Dry Funk - Alt Take"},
            {"SongName": "Neo-Soul Clean"},
            {"SongName": "Unlisted Song"},
        ]

    def test_file_selector_uses_explicit_names_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            selector_path = Path(tmp_dir) / "test.txt"
            selector_path.write_text("Neo-Soul Clean\nDry Funk - Alt Take\n", encoding="utf-8")

            selection = select_query_indices(self.dataset, f"file:{selector_path}")

        self.assertEqual(Path(selection.split.removeprefix("file:")), selector_path.resolve())
        self.assertEqual(selection.requested_names, ["Neo-Soul Clean", "Dry Funk - Alt Take"])
        self.assertEqual(selection.found_names, ["Neo-Soul Clean", "Dry Funk - Alt Take"])
        self.assertEqual(selection.missing_names, [])
        self.assertEqual(selection.test_indices, [2, 1])
        self.assertFalse(selection.used_random_fallback)

    def test_plain_path_selector_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            selector_path = Path(tmp_dir) / "test.txt"
            selector_path.write_text("Dry Funk\n", encoding="utf-8")

            selection = select_query_indices(self.dataset, str(selector_path))

        self.assertEqual(Path(selection.split.removeprefix("file:")), selector_path.resolve())
        self.assertEqual(selection.test_indices, [0])
        self.assertFalse(selection.used_random_fallback)

    def test_explicit_file_selector_does_not_random_fallback_when_names_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            selector_path = Path(tmp_dir) / "test.txt"
            selector_path.write_text("Missing Song\n", encoding="utf-8")

            selection = select_query_indices(self.dataset, f"file:{selector_path}")

        self.assertEqual(selection.requested_names, ["Missing Song"])
        self.assertEqual(selection.found_names, [])
        self.assertEqual(selection.missing_names, ["Missing Song"])
        self.assertEqual(selection.test_indices, [])
        self.assertFalse(selection.used_random_fallback)


if __name__ == "__main__":
    unittest.main()

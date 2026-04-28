import unittest

from Experiments.AblationStudies.direct_retrieval_comparison import (
    base_name_for_song,
    filter_ranked_results_for_query,
    select_same_base_hard_subset_queries,
)


class DirectRetrievalHardSubsetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = [
            {"SongName": "Dry Funk"},
            {"SongName": "Dry Funk - Alt Take"},
            {"SongName": "Dry Funk - Studio Mix"},
            {"SongName": "Neo-Soul Clean"},
            {"SongName": "Neo-Soul Clean - Pocket Groove Cut"},
            {"SongName": "One Off"},
        ]

    def test_base_name_for_song_collapses_variant_suffix(self) -> None:
        self.assertEqual(base_name_for_song("Dry Funk - Alt Take"), "Dry Funk")
        self.assertEqual(base_name_for_song("Dry Funk"), "Dry Funk")

    def test_select_same_base_hard_subset_queries_requires_min_family_size(self) -> None:
        selected = select_same_base_hard_subset_queries(self.dataset, min_family_size=3)
        selected_names = [item["SongName"] for item in selected]

        self.assertEqual(
            selected_names,
            ["Dry Funk", "Dry Funk - Alt Take", "Dry Funk - Studio Mix"],
        )

    def test_filter_ranked_results_keeps_same_base_and_excludes_self(self) -> None:
        query_item = {"SongName": "Dry Funk"}
        ranked_results = [
            {"SongName": "Dry Funk"},
            {"SongName": "Neo-Soul Clean"},
            {"SongName": "Dry Funk - Studio Mix"},
            {"SongName": "Dry Funk - Alt Take"},
        ]

        filtered = filter_ranked_results_for_query(
            query_item,
            ranked_results,
            hard_subset_mode="same_base_exclude_self",
        )

        self.assertEqual(
            [item["SongName"] for item in filtered],
            ["Dry Funk - Studio Mix", "Dry Funk - Alt Take"],
        )

    def test_filter_ranked_results_returns_empty_when_no_same_base_candidates(self) -> None:
        query_item = {"SongName": "One Off"}
        ranked_results = [
            {"SongName": "One Off"},
            {"SongName": "Dry Funk"},
            {"SongName": "Neo-Soul Clean"},
        ]

        filtered = filter_ranked_results_for_query(
            query_item,
            ranked_results,
            hard_subset_mode="same_base_exclude_self",
        )

        self.assertEqual(filtered, [])


if __name__ == "__main__":
    unittest.main()

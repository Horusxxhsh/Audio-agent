import unittest

from Experiments.common.hard_split import build_parameter_cluster_split


def item(name: str, drive: float, mix: float) -> dict:
    return {
        "SongName": name,
        "Parameters": {
            "Drive": {"On": 1.0, "Amount": drive},
            "Delay": {"On": 1.0, "Mix": mix},
        },
    }


class HardSplitTests(unittest.TestCase):
    def test_keeps_near_duplicate_cluster_on_one_side(self) -> None:
        dataset = [
            item("query-a", 0.10, 0.20),
            item("near-a", 0.11, 0.20),
            item("kb-b", 0.80, 0.90),
        ]

        split = build_parameter_cluster_split(dataset, requested_query_indices=[0], threshold=0.02)

        self.assertEqual(split["test_indices"], [0])
        self.assertNotIn(1, split["kb_indices"])
        self.assertIn(2, split["kb_indices"])
        self.assertEqual(split["removed_query_count"], 0)

    def test_drops_requested_query_when_cluster_already_taken(self) -> None:
        dataset = [
            item("query-a", 0.10, 0.20),
            item("query-a-duplicate", 0.11, 0.20),
            item("kb-b", 0.80, 0.90),
        ]

        split = build_parameter_cluster_split(dataset, requested_query_indices=[0, 1], threshold=0.02)

        self.assertEqual(split["test_indices"], [0])
        self.assertEqual(split["removed_query_count"], 1)
        self.assertNotIn(1, split["kb_indices"])

    def test_threshold_zero_only_groups_exact_matches(self) -> None:
        dataset = [
            item("query-a", 0.10, 0.20),
            item("different", 0.11, 0.20),
            item("exact", 0.10, 0.20),
        ]

        split = build_parameter_cluster_split(dataset, requested_query_indices=[0], threshold=0.0)

        self.assertNotIn(2, split["kb_indices"])
        self.assertIn(1, split["kb_indices"])

    def test_cluster_summary_contains_members(self) -> None:
        dataset = [item("a", 0.10, 0.20), item("b", 0.10, 0.20)]

        split = build_parameter_cluster_split(dataset, requested_query_indices=[0], threshold=0.0)

        self.assertEqual(split["clusters"][0]["members"], [0, 1])
        self.assertEqual(split["clusters"][0]["names"], ["a", "b"])

    def test_rejects_empty_query_indices(self) -> None:
        with self.assertRaisesRegex(ValueError, "requested_query_indices must not be empty"):
            build_parameter_cluster_split([item("a", 0.1, 0.2)], requested_query_indices=[], threshold=0.02)


if __name__ == "__main__":
    unittest.main()

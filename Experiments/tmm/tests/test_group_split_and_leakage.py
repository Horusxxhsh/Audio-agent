import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from Experiments.tmm import dataset_audit, leakage_scan, make_splits


class GroupAwareSplitTests(unittest.TestCase):
    def test_group_key_collapses_suffix_variants(self):
        self.assertEqual(
            make_splits.group_key_for_name("Dry Funk - Chic Rhythm Pass"),
            "Dry Funk",
        )
        self.assertEqual(
            make_splits.group_key_for_name("Dry Funk"),
            "Dry Funk",
        )

    def test_grouped_split_keeps_same_base_family_together(self):
        dataset = [
            {"SongName": "Dry Funk"},
            {"SongName": "Dry Funk - Chic Rhythm Pass"},
            {"SongName": "Dreamy Shoegaze"},
            {"SongName": "Dreamy Shoegaze - Wide Bloom Take"},
        ]

        split = make_splits.build_grouped_split(
            dataset,
            seed=0,
            train_ratio=0.5,
            val_ratio=0.0,
            test_ratio=0.5,
        )

        memberships = {}
        for split_name in ("train", "val", "test"):
            for name in split[split_name]:
                memberships[name] = split_name

        self.assertEqual(memberships["Dry Funk"], memberships["Dry Funk - Chic Rhythm Pass"])
        self.assertEqual(
            memberships["Dreamy Shoegaze"],
            memberships["Dreamy Shoegaze - Wide Bloom Take"],
        )

    def test_resolved_audio_grouping_keeps_shared_audio_together(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_dir = root / "Data" / "Audio_Synthetic"
            audio_dir.mkdir(parents=True)

            sr = 16000
            t = np.linspace(0, 0.25, sr // 4, endpoint=False)
            wave = (0.5 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
            shared_audio = audio_dir / "Dry Funk.wav"
            wavfile.write(shared_audio, sr, wave)

            dataset = [
                {"SongName": "Dry Funk", "AudioPath": str(shared_audio)},
                {"SongName": "Dry Funk Rhythm", "AudioPath": str(shared_audio)},
                {"SongName": "Dreamy Shoegaze"},
                {"SongName": "Math Rock Crystal"},
            ]

            split = make_splits.build_grouped_split(
                dataset,
                seed=0,
                train_ratio=0.5,
                val_ratio=0.0,
                test_ratio=0.5,
                group_mode="resolved_audio",
            )

            memberships = {}
            for split_name in ("train", "val", "test"):
                for name in split[split_name]:
                    memberships[name] = split_name

            self.assertEqual(memberships["Dry Funk"], memberships["Dry Funk Rhythm"])


class SplitLeakageScanTests(unittest.TestCase):
    def test_scan_split_leakage_reports_cross_split_exact_and_near_duplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_dir = root / "audio"
            split_root = root / "splits" / "seed0"
            audio_dir.mkdir(parents=True)
            split_root.mkdir(parents=True)

            sr = 16000
            t = np.linspace(0, 1.0, sr, endpoint=False)
            base = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
            near = (0.48 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

            exact_a = audio_dir / "dry_funk.wav"
            exact_b = audio_dir / "dry_funk_copy.wav"
            near_b = audio_dir / "dreamy_shoegaze.wav"
            wavfile.write(exact_a, sr, base)
            wavfile.write(exact_b, sr, base)
            wavfile.write(near_b, sr, near)

            dataset = [
                {"SongName": "Dry Funk", "AudioPath": str(exact_a)},
                {"SongName": "Dry Funk - Chic Rhythm Pass", "AudioPath": str(exact_b)},
                {"SongName": "Dreamy Shoegaze", "AudioPath": str(near_b)},
            ]
            dataset_json = root / "dataset.json"
            dataset_json.write_text(json.dumps(dataset), encoding="utf-8")

            (split_root / "train.txt").write_text("Dry Funk\n", encoding="utf-8")
            (split_root / "val.txt").write_text("", encoding="utf-8")
            (split_root / "test.txt").write_text(
                "Dry Funk - Chic Rhythm Pass\nDreamy Shoegaze\n",
                encoding="utf-8",
            )

            report = leakage_scan.scan_split_leakage(
                dataset_json=dataset_json,
                split_root=split_root.parent,
                near_dup_threshold=0.99,
                max_pairs=20,
            )

            exact_pairs = report["split_reports"]["seed0"]["exact_cross_split_pairs"]
            near_pairs = report["split_reports"]["seed0"]["near_cross_split_pairs"]

            self.assertTrue(
                any(
                    {pair["a"], pair["b"]} == {"Dry Funk", "Dry Funk - Chic Rhythm Pass"}
                    for pair in exact_pairs
                )
            )
            self.assertTrue(
                any(
                    "Dreamy Shoegaze" in {pair["a"], pair["b"]}
                    and "Dry Funk" in {pair["a"], pair["b"]}
                    for pair in near_pairs
                )
            )


class DatasetAuditResolutionTests(unittest.TestCase):
    def test_resolve_audio_path_maps_windows_style_path_by_basename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_dir = root / "Data" / "Audio_Synthetic"
            audio_dir.mkdir(parents=True)

            sr = 16000
            t = np.linspace(0, 0.25, sr // 4, endpoint=False)
            wave = (0.5 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
            local_wav = audio_dir / "Studio Clean.wav"
            wavfile.write(local_wav, sr, wave)

            resolved = dataset_audit.resolve_audio_path_for_item(
                root,
                {
                    "SongName": "Studio Clean",
                    "AudioPath": r"C:\Users\someone\Audio-agent\Data\Audio_Synthetic\Studio Clean.wav",
                },
            )

            self.assertEqual(resolved, local_wav.resolve())


if __name__ == "__main__":
    unittest.main()

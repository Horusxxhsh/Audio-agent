# Protocol-A Split Audit

- Dataset JSON: `/Users/xyh/Code/Audio-agent/Data/External_1267_211/dataset/dataset_full_vectors_1267.json`
- Manifest CSV: `/Users/xyh/Code/Audio-agent/Experiments/tmm/protocolA_split_manifest.csv`
- Selection rule: Protocol-A test set is defined exactly as rows whose SongName appears in direct_retrieval_comparison.TEST_SAMPLE_SET; KB is the complement.

## Summary

- n_total=1267
- n_test=211
- n_kb=1056
- n_duplicate_song_names_total=3
- n_duplicate_song_names_test=1
- n_unique_base_names_test=30
- n_unique_base_names_kb=1054
- n_shared_base_names_test_kb=0
- n_shared_resolved_audio_paths_cross_split=16
- n_near_duplicate_pairs_cross_split=48

## Coverage

| Split | audio_exists | TRR | Wav2Vec | FeatureNN | CLAP(JSON) | CLAP(cache) |
| --- | --- | --- | --- | --- | --- | --- |
| test | 211 | 211 | 211 | 211 | 0 | 211 |
| kb | 1038 | 1056 | 1051 | 1051 | 1002 | 1038 |

## Notes

- Text provenance: The dataset JSON exposes SongName/Style/Feature/Parameters/Vectors but does not include a separate auditable text-source field; Style/Feature are therefore the only explicit text-side provenance fields available in-repo.
- Parameter provenance: Ground-truth parameters are taken from the dataset JSON Parameters field as stored in the external 1267 benchmark drop-in.
- Example shared resolved audio path across split: `/Users/xyh/Code/Audio-agent/Data/Audio_Synthetic/80s Hair Metal.wav` with test=['80s Hair Metal', '80s Hair Metal - Heavy Riff Pass', '80s Hair Metal - High Gain Forge'] and kb=['80s Hair Metal Arena']
- Example near-duplicate cross-split pair: test=['Acoustic Sim', 'Acoustic Sim - Bright Air Version'] vs kb=['Atmospheric Grime'] (cos=0.9973)

# E7 Hard Split Retrieval

This experiment evaluates cached retrieval embeddings under a parameter-cluster hard split.

The split starts from the existing 204-query audio-grouped Protocol-A list in
`Experiments/tmm/splits/tmm_external1267_audio_grouped/seed0/test.txt`. It then
clusters all records by normalized parameter RMSE and removes every knowledge-base
candidate that belongs to a selected query cluster. This makes the result a
near-duplicate sensitivity check, not a replacement for the main P0 leaderboard.

Run:

```bash
python Experiments/E7_HardSplit/run_hard_split_retrieval.py \
  --dataset Data/External_1267_211/dataset/dataset_full_vectors_1267.json \
  --threshold 0.02 \
  --output-dir Experiments/E7_HardSplit
```

Outputs:

- `hard_split_results.json`
- `hard_split_results.csv`
- `hard_split_audit.json`

Rows with `n=0` and `coverage=0.0` indicate that the current dataset does not
contain usable cached vectors for that method under this local execution path.

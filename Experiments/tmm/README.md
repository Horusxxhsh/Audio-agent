# TMM Synthetic Expansion (E0/E1)

This folder contains the minimum tooling to expand the dataset synthetically and to generate:
- a unified dataset JSON for experiments (`Experiments/dataset_full_vectors.json`)
- a file manifest with checksums
- train/val/test split files (fixed seeds)

## Prerequisites (for rendering)
The renderer uses the plugin's existing Auto-Import offline pipeline:
- The plugin must be running and **Auto Import** enabled in the UI.
- The plugin watches `~/Documents/Supertonal/Audio-agent/` for:
  - `import_params.json` (parameter values)
  - `generated_input.wav` (input audio)
- It writes `final_output.wav` (rendered output) back to the same directory.

On macOS, the default documents path is `~/Documents`. Override with `DOCUMENTS_DIR` if needed.

## Typical workflow
1) Synthesize and render a dataset (Tier M target, e.g., 220 presets):
`python3 Experiments/tmm/synth_dataset.py --n 220 --seed 0 --out Data/TMM_Synth_v1 --dataset_json Experiments/dataset_full_vectors.json`

2) Make fixed splits for reproducible experiments:
`python3 Experiments/tmm/make_splits.py --dataset_json Experiments/dataset_full_vectors.json --name tmm_synth_v1 --seeds 0 1 2`

3) Audit dataset integrity + split disjointness:
`python3 Experiments/tmm/dataset_audit.py --dataset_json Experiments/dataset_full_vectors.json --split_root Experiments/tmm/splits/tmm_synth_v1 --out Experiments/tmm/dataset_audit_report.json`

4) Run existing experiment scripts (they will prefer the JSON dataset if present):
- any script calling `Experiments/common/dataset_loader.py`

## Notes
- This initial synth pipeline is designed to be a *reproducible scaling step* (E0/E1).
- If your paper claims require modules not covered by offline rendering, you should extend the renderer and re-generate.

## Optional: SOTA Retrieval Baselines (CLAP / PaSST / PANNs)
Some TMM ablation scripts can optionally evaluate stronger audio representation baselines.

Install the optional dependencies:
`python -m pip install -r Experiments/requirements_sota.txt`

Embedding extraction is done offline and cached to avoid repeated computation.

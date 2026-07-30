import pandas as pd
import json
from scipy.stats import wilcoxon
import numpy as np

# Load per-query rows
rows_path = "/home/xyh/code/Audio-agent/Experiments/E9_TMMMajorRevision/outputs/unified_protocol/unified_topk_rows.csv"
df = pd.read_csv(rows_path)

# Filter ok status
df = df[df["status"] == "ok"]

methods = ["TRR", "Wav2Vec", "FeatureNN", "PaSST"]
metrics = ["top1_norm_l2", "top1_acc_at_0_1", "top1_recall", "top1_cosine", "top1_switch_f1"]

# Pivot to paired format
results = {}
for metric in metrics:
    # Build paired dataframe: index=query_idx, columns=method
    sub = df[["query_idx", "method", metric]].copy()
    pivoted = sub.pivot(index="query_idx", columns="method", values=metric)
    pivoted = pivoted.dropna(subset=methods)
    n = len(pivoted)
    if n == 0:
        continue
    results[metric] = {}
    trr_vals = pivoted["TRR"].values
    for baseline in ["Wav2Vec", "FeatureNN", "PaSST"]:
        base_vals = pivoted[baseline].values
        # For norm_l2, lower is better. We test if baseline - TRR > 0
        if metric == "top1_norm_l2":
            diff = base_vals - trr_vals
            alt = "greater"
        else:
            # For others, higher is better. We test if TRR - baseline > 0
            diff = trr_vals - base_vals
            alt = "greater"
        # Wilcoxon requires non-zero diffs; remove zeros to be safe for exact test
        mask = diff != 0
        diff_nonzero = diff[mask]
        n_eff = len(diff_nonzero)
        if n_eff < 10:
            results[metric][baseline] = {"n_pairs": int(n), "n_nonzero": n_eff, "p": None, "z": None, "r": None, "mean_diff": float(np.mean(diff)), "median_diff": float(np.median(diff))}
            continue
        try:
            stat, p = wilcoxon(diff_nonzero, alternative=alt, method="exact" if n_eff <= 50 else "auto")
            # Approximate Z from statistic for large n; for exact, we can still approximate r
            # Using normal approximation for r: r = Z / sqrt(N), where Z = (stat - mu) / sigma
            # scipy 1.11+ exposes .zstatistic if normal approx used; for exact we approximate manually
            if hasattr(stat, 'zstatistic'):
                z = stat.zstatistic
            else:
                # manual normal approx for signed-rank
                n_r = n_eff
                mu = n_r * (n_r + 1) / 4
                sigma = np.sqrt(n_r * (n_r + 1) * (2 * n_r + 1) / 24)
                z = (stat - mu) / sigma if sigma > 0 else 0.0
            r = z / np.sqrt(n_eff) if n_eff > 0 else 0.0
            results[metric][baseline] = {
                "n_pairs": int(n),
                "n_nonzero": int(n_eff),
                "statistic": int(stat),
                "p": float(p),
                "z": float(z),
                "r": float(r),
                "mean_diff": float(np.mean(diff)),
                "median_diff": float(np.median(diff)),
                "alt": alt
            }
        except Exception as e:
            results[metric][baseline] = {"error": str(e)}

# Pretty print
print("=== Wilcoxon Signed-Rank Test: TRR vs Baselines (per-query paired) ===\n")
for metric, baselines in results.items():
    print(f"Metric: {metric}")
    for baseline, res in baselines.items():
        if "error" in res:
            print(f"  {baseline}: ERROR {res['error']}")
        elif res["p"] is None:
            print(f"  {baseline}: n={res['n_pairs']} (nonzero={res['n_nonzero']}), too few pairs")
        else:
            sig = "***" if res["p"] < 0.001 else "**" if res["p"] < 0.01 else "*" if res["p"] < 0.05 else "ns"
            direction = "TRR lower" if res["alt"] == "greater" and metric=="top1_norm_l2" else "TRR higher"
            print(f"  {baseline}: n={res['n_pairs']} (nz={res['n_nonzero']}), p={res['p']:.2e} {sig}, r={res['r']:.3f}, mean_diff={res['mean_diff']:.4f}, median_diff={res['median_diff']:.4f} [{direction}]")
    print()

# Save JSON
out_path = "/home/xyh/code/Audio-agent/Experiments/E9_TMMMajorRevision/outputs/unified_protocol/significance_results.json"
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"Saved to {out_path}")

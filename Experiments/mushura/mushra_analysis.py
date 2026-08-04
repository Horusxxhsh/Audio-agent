from __future__ import annotations

"""
Listening-Test Analysis (TMM Route A)
====================================

This script analyzes `mushra.csv` and produces a paper-auditable report without
requiring heavy scientific dependencies.

Terminology (important for TMM):
- This dataset corresponds to a "Multiple-Stimulus Listening Test with Hidden Reference".
- There is NO explicit low-quality anchor, so it should NOT be called a standard
  ITU-R BS.1534 MUSHRA test in the paper.

Outputs:
- `results_report.md`: descriptive stats + repeated-measures tests (Friedman + post-hoc
  Wilcoxon signed-rank with Holm correction) for groups that contain `HCAP`.
- (Optional) `system_boxplot_*.png` if matplotlib is available.
"""

import argparse
import csv
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


@dataclass(frozen=True)
class Row:
    email: str
    trial_id: str
    stimulus: str
    score: float


def _load_rows(csv_path: Path) -> List[Row]:
    rows: List[Row] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            email = (r.get("email") or "").strip()
            if email.lower() == "email" or not email:
                continue
            trial_id = (r.get("trial_id") or "").strip()
            stimulus = (r.get("rating_stimulus") or "").strip()
            try:
                score = float(r.get("rating_score") or "")
            except Exception:
                continue
            rows.append(Row(email=email, trial_id=trial_id, stimulus=stimulus, score=score))
    return rows


def _mean(xs: Sequence[float]) -> float:
    return float(sum(xs) / len(xs)) if xs else float("nan")


def _std_sample(xs: Sequence[float]) -> float:
    if len(xs) <= 1:
        return 0.0
    return float(statistics.stdev(xs))


def _rank_with_ties(values: Sequence[float]) -> List[float]:
    """
    1..k ranks with average ranks for ties.
    """
    k = len(values)
    order = sorted(range(k), key=lambda i: values[i])
    ranks = [0.0] * k
    i = 0
    while i < k:
        j = i
        while j + 1 < k and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for t in range(i, j + 1):
            ranks[order[t]] = avg_rank
        i = j + 1
    return ranks


def _friedman_statistic(matrix: List[List[float]]) -> float:
    """
    Friedman chi-square statistic (no p-value; use permutation for p).
    matrix: shape (n_subjects, k_conditions)
    """
    n = len(matrix)
    k = len(matrix[0]) if n else 0
    if n == 0 or k <= 1:
        return 0.0

    # Rank within each subject.
    ranks = [_rank_with_ties(row) for row in matrix]
    r_sum = [0.0] * k
    for row in ranks:
        for j, r in enumerate(row):
            r_sum[j] += float(r)

    q = (12.0 / (n * k * (k + 1.0))) * sum(r * r for r in r_sum) - 3.0 * n * (k + 1.0)
    return float(q)


def _friedman_permutation_pvalue(matrix: List[List[float]], *, n_perm: int, seed: int) -> Tuple[float, float]:
    """
    Permutation p-value for Friedman statistic by permuting condition labels within subject.
    One-sided (Q >= 0): p = P(Q_perm >= Q_obs).
    """
    rng = np.random.default_rng(int(seed))
    obs = _friedman_statistic(matrix)
    n = len(matrix)
    k = len(matrix[0]) if n else 0
    if n == 0 or k <= 1:
        return obs, 1.0

    ge = 0
    for _ in range(int(n_perm)):
        permuted = []
        for row in matrix:
            idx = rng.permutation(k)
            permuted.append([row[int(i)] for i in idx])
        q = _friedman_statistic(permuted)
        if q >= obs - 1e-12:
            ge += 1
    p = (ge + 1.0) / (float(n_perm) + 1.0)
    return float(obs), float(p)


def _wilcoxon_signed_rank_permutation(
    x: Sequence[float], y: Sequence[float], *, n_perm: int, seed: int
) -> Dict[str, float]:
    """
    Paired Wilcoxon signed-rank test via sign-flip permutation on ranked abs diffs.

    Returns:
    - n (non-zero diffs)
    - mean_diff
    - median_diff
    - rbc (rank-biserial correlation)
    - p_perm_two_sided
    """
    if len(x) != len(y):
        raise ValueError("x and y must have the same length (paired data).")

    diffs = [float(a - b) for a, b in zip(x, y)]
    diffs_nz = [d for d in diffs if abs(d) > 1e-12]
    if not diffs_nz:
        return {
            "n": 0.0,
            "mean_diff": float(_mean(diffs)),
            "median_diff": float(statistics.median(diffs)) if diffs else float("nan"),
            "rbc": 0.0,
            "p_perm_two_sided": 1.0,
        }

    abs_d = [abs(d) for d in diffs_nz]
    ranks = _rank_with_ties(abs_d)
    signs = [1.0 if d > 0 else -1.0 for d in diffs_nz]
    s_obs = float(sum(s * r for s, r in zip(signs, ranks)))
    w_total = float(sum(ranks))  # equals n*(n+1)/2 even with averaged ties
    rbc = float(s_obs / (w_total + 1e-12))

    rng = np.random.default_rng(int(seed))
    ge = 0
    for _ in range(int(n_perm)):
        perm_signs = rng.choice(np.array([-1.0, 1.0], dtype=float), size=len(ranks), replace=True)
        s_perm = float(np.sum(perm_signs * np.asarray(ranks, dtype=np.float64)))
        if abs(s_perm) >= abs(s_obs) - 1e-12:
            ge += 1
    p = (ge + 1.0) / (float(n_perm) + 1.0)

    return {
        "n": float(len(diffs_nz)),
        "mean_diff": float(_mean(diffs_nz)),
        "median_diff": float(statistics.median(diffs_nz)),
        "rbc": float(rbc),
        "p_perm_two_sided": float(p),
    }


def _holm_bonferroni(pvals: List[float]) -> List[float]:
    """
    Holm-Bonferroni adjusted p-values (step-down), preserving original order.
    """
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    prev = 0.0
    for rank, i in enumerate(order):
        p_adj = (m - rank) * pvals[i]
        p_adj = min(1.0, max(p_adj, prev))
        adj[i] = p_adj
        prev = p_adj
    return adj


def _group_subject_system_means(rows: List[Row], trial_ids: set) -> Tuple[Dict[str, Dict[str, float]], List[str]]:
    """
    (email, stimulus, trial_id) -> mean -> then (email, stimulus) -> mean across trials.
    Returns:
    - subject_system_mean[email][stimulus] = mean score
    - sorted list of stimuli
    """
    by_triplet: Dict[Tuple[str, str, str], List[float]] = defaultdict(list)
    for r in rows:
        if r.trial_id not in trial_ids:
            continue
        by_triplet[(r.email, r.stimulus, r.trial_id)].append(float(r.score))

    by_subsys: Dict[Tuple[str, str], List[float]] = defaultdict(list)
    for (email, stimulus, _trial), scores in by_triplet.items():
        by_subsys[(email, stimulus)].append(_mean(scores))

    subject_system_mean: Dict[str, Dict[str, float]] = defaultdict(dict)
    stimuli = set()
    for (email, stimulus), trial_means in by_subsys.items():
        subject_system_mean[email][stimulus] = _mean(trial_means)
        stimuli.add(stimulus)

    stimuli_sorted = sorted(stimuli)
    return subject_system_mean, stimuli_sorted


def _complete_cases(subject_system_mean: Dict[str, Dict[str, float]], stimuli: List[str]) -> Tuple[List[str], List[List[float]]]:
    emails = []
    matrix = []
    for email, stim_map in subject_system_mean.items():
        if all(s in stim_map for s in stimuli):
            emails.append(email)
            matrix.append([float(stim_map[s]) for s in stimuli])
    return emails, matrix


def _maybe_plot_boxplot(
    *,
    out_path: Path,
    stimuli: List[str],
    per_subject_scores: Dict[str, List[float]],
    title: str,
) -> Optional[str]:
    """
    Optional plot helper. Returns a note string if plotting was skipped.
    """
    try:
        import matplotlib.pyplot as plt  # noqa: F401
    except Exception:
        return "Plot skipped (matplotlib not installed)."

    display = {"HCAP": "TRR-based system"}
    labels = [display.get(s, s) for s in stimuli]
    data = [per_subject_scores[s] for s in stimuli]
    try:
        import matplotlib.pyplot as plt

        import matplotlib

        matplotlib.rcParams["pdf.fonttype"] = 42
        matplotlib.rcParams["ps.fonttype"] = 42
        matplotlib.rcParams["font.size"] = 9
        matplotlib.rcParams["axes.titlesize"] = 10
        matplotlib.rcParams["axes.labelsize"] = 9
        matplotlib.rcParams["xtick.labelsize"] = 8
        matplotlib.rcParams["ytick.labelsize"] = 8
        rng = np.random.default_rng(42)

        plt.figure(figsize=(6.3, 2.8))
        plt.boxplot(data, tick_labels=labels, showfliers=True)
        for i, s in enumerate(stimuli, 1):
            y = per_subject_scores[s]
            x = rng.normal(loc=i, scale=0.04, size=len(y))
            plt.scatter(x, y, s=8, alpha=0.4, color="black")
        plt.xticks(rotation=25, ha="right")
        plt.ylim(0, 100)
        plt.ylabel("Listener score (0-100)")
        plt.title(title)
        plt.tight_layout()
        plt.savefig(out_path, dpi=300)
        if out_path.suffix.lower() != ".pdf":
            plt.savefig(out_path.with_suffix(".pdf"))
        plt.close()
        return None
    except Exception as exc:
        return f"Plot failed: {exc}"


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="Analyze listening test ratings and generate a stats report.")
    ap.add_argument("--csv", type=str, default=str(base_dir / "mushra.csv"), help="Input ratings CSV path.")
    ap.add_argument("--out_md", type=str, default=str(base_dir / "results_report.md"), help="Output Markdown report.")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed for permutation tests.")
    ap.add_argument("--friedman_perm", type=int, default=20000, help="Permutations for Friedman test.")
    ap.add_argument("--wilcoxon_perm", type=int, default=20000, help="Permutations for pairwise Wilcoxon tests.")
    ap.add_argument("--plots", action="store_true", help="Generate system-level boxplots (requires matplotlib).")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    out_md = Path(args.out_md)

    rows = _load_rows(csv_path)
    if not rows:
        raise SystemExit(f"No valid rows loaded from: {csv_path}")

    groups = {
        "Trial 1": {"trial1"},
        "Trial 2-5": {"trial2", "trial3", "trial4", "trial5"},
        "Trial 6-10": {"trial6", "trial7", "trial8", "trial9", "trial10"},
    }

    lines: List[str] = []
    lines.append("# Multiple-Stimulus Listening Test with Hidden Reference (No Explicit Anchor)")
    lines.append("")
    lines.append("This report summarizes descriptive statistics and repeated-measures tests.")
    lines.append("Important: the study includes a hidden reference (`reference`) but no explicit low-quality anchor.")
    lines.append("")
    lines.append(f"- Input CSV: `{csv_path}`")
    lines.append(f"- Participants (unique emails): {len(set(r.email for r in rows))}")
    lines.append(f"- Total ratings: {len(rows)}")
    lines.append("")

    for group_name, trial_ids in groups.items():
        rows_g = [r for r in rows if r.trial_id in trial_ids]
        stimuli_g = sorted(set(r.stimulus for r in rows_g))
        participants_g = sorted(set(r.email for r in rows_g))

        # Within-subject means.
        subj_sys_mean, _stimuli_sorted = _group_subject_system_means(rows, trial_ids)
        # Use the stimuli order based on median for readability.
        per_subject_scores: Dict[str, List[float]] = {s: [] for s in stimuli_g}
        for email, stim_map in subj_sys_mean.items():
            for s in stimuli_g:
                if s in stim_map:
                    per_subject_scores[s].append(float(stim_map[s]))

        stim_order = sorted(
            stimuli_g,
            key=lambda s: statistics.median(per_subject_scores[s]) if per_subject_scores[s] else -1e9,
            reverse=True,
        )

        # Raw-score descriptive stats.
        raw_scores = [float(r.score) for r in rows_g]

        lines.append(f"## {group_name}")
        lines.append("")
        lines.append("### Data Overview")
        lines.append(f"- Trials: {sorted(trial_ids)}")
        lines.append(f"- Ratings (rows): {len(rows_g)}")
        lines.append(f"- Participants: {len(participants_g)}")
        lines.append(f"- Stimuli: {len(stimuli_g)} ({', '.join(stimuli_g)})")
        lines.append("")

        lines.append("### Descriptive Stats (Raw Ratings)")
        lines.append(f"- mean={_mean(raw_scores):.2f}")
        lines.append(f"- median={statistics.median(raw_scores):.2f}")
        lines.append(f"- std={_std_sample(raw_scores):.2f}")
        lines.append(f"- min={min(raw_scores):.2f}")
        lines.append(f"- max={max(raw_scores):.2f}")
        lines.append("")

        # System-level descriptive stats from within-subject means.
        lines.append("### System-Level Stats (Within-Subject Means)")
        lines.append("")
        header = ["Stimulus", "n_subj", "mean", "median", "std"]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for s in stim_order:
            xs = per_subject_scores[s]
            if not xs:
                continue
            lines.append(
                "| "
                + " | ".join(
                    [
                        s,
                        str(len(xs)),
                        f"{_mean(xs):.2f}",
                        f"{statistics.median(xs):.2f}",
                        f"{_std_sample(xs):.2f}",
                    ]
                )
                + " |"
            )
        lines.append("")

        if args.plots:
            plot_path = base_dir / f"system_boxplot_{group_name.replace(' ', '_').replace('-', '_')}.png"
            note = _maybe_plot_boxplot(
                out_path=plot_path,
                stimuli=stim_order,
                per_subject_scores=per_subject_scores,
                title=f"System-Level Boxplot ({group_name})",
            )
            lines.append("### Plot")
            if note:
                lines.append(note)
            else:
                lines.append(f"![]({plot_path.name})")
            lines.append("")

        # Repeated-measures tests: only for groups containing HCAP comparisons.
        if "HCAP" not in stimuli_g:
            continue

        complete_emails, complete_matrix = _complete_cases(subj_sys_mean, stim_order)
        if len(complete_matrix) < 2:
            lines.append("### Repeated-Measures Tests")
            lines.append("Not enough complete cases to run repeated-measures tests.")
            lines.append("")
            continue

        lines.append("### Repeated-Measures Tests (Complete Cases)")
        lines.append(f"- n_complete={len(complete_emails)}")
        lines.append(f"- k_stimuli={len(stim_order)}")
        lines.append("")

        # Friedman omnibus test (permutation).
        q_obs, p_friedman = _friedman_permutation_pvalue(
            complete_matrix, n_perm=int(args.friedman_perm), seed=int(args.seed)
        )
        lines.append(f"- Friedman Q={q_obs:.4f}, p_perm={p_friedman:.4g} (one-sided)")
        lines.append("")

        # Post-hoc pairwise Wilcoxon signed-rank tests (permutation) with Holm correction.
        pair_results = []
        pvals = []
        for i in range(len(stim_order)):
            for j in range(i + 1, len(stim_order)):
                a = stim_order[i]
                b = stim_order[j]
                xa = [row[i] for row in complete_matrix]
                xb = [row[j] for row in complete_matrix]
                res = _wilcoxon_signed_rank_permutation(
                    xa, xb, n_perm=int(args.wilcoxon_perm), seed=int(args.seed) + i * 97 + j * 131
                )
                pair_results.append((a, b, res))
                pvals.append(float(res["p_perm_two_sided"]))

        p_holm = _holm_bonferroni(pvals) if pvals else []
        lines.append("#### Pairwise Wilcoxon Signed-Rank (Permutation) + Holm Correction")
        lines.append("")
        header = ["A", "B", "n", "mean(A-B)", "median(A-B)", "rbc", "p", "p(Holm)"]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for (a, b, res), p_adj in zip(pair_results, p_holm):
            lines.append(
                "| "
                + " | ".join(
                    [
                        a,
                        b,
                        str(int(res["n"])),
                        f"{float(res['mean_diff']):.2f}",
                        f"{float(res['median_diff']):.2f}",
                        f"{float(res['rbc']):.3f}",
                        f"{float(res['p_perm_two_sided']):.4g}",
                        f"{float(p_adj):.4g}",
                    ]
                )
                + " |"
            )
        lines.append("")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote report: {out_md}")


if __name__ == "__main__":
    main()

import math
from typing import Dict, Iterable, List, Sequence, Tuple


def mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def std(values: Sequence[float], ddof: int = 1) -> float:
    n = len(values)
    if n <= ddof:
        return 0.0
    mu = mean(values)
    var = sum((x - mu) ** 2 for x in values) / (n - ddof)
    return math.sqrt(var)


def cohens_d_paired(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    diffs = [x - y for x, y in zip(a, b)]
    s = std(diffs, ddof=1)
    if s == 0:
        return 0.0
    return mean(diffs) / s


def holm_bonferroni(pvalues: Dict[str, float], alpha: float = 0.05) -> Dict[str, Dict[str, float]]:
    """
    Return Holm-Bonferroni adjusted decisions.
    """
    m = len(pvalues)
    ordered = sorted(pvalues.items(), key=lambda kv: kv[1])
    out: Dict[str, Dict[str, float]] = {}
    any_failed = False
    for i, (name, p) in enumerate(ordered):
        threshold = alpha / (m - i) if m - i > 0 else alpha
        reject = (not any_failed) and (p <= threshold)
        if not reject:
            any_failed = True
        out[name] = {
            "p_value": p,
            "holm_threshold": threshold,
            "reject_h0": 1.0 if reject else 0.0,
        }
    return out


def win_tie_loss(reference: Sequence[float], baseline: Sequence[float], lower_better: bool = True, tie_eps: float = 1e-12) -> Tuple[int, int, int]:
    """
    Compare baseline against reference: (win, tie, loss) for baseline.
    """
    wins = ties = losses = 0
    for r, b in zip(reference, baseline):
        d = b - r
        if abs(d) <= tie_eps:
            ties += 1
            continue
        if lower_better:
            if b < r:
                wins += 1
            else:
                losses += 1
        else:
            if b > r:
                wins += 1
            else:
                losses += 1
    return wins, ties, losses


def _sign_test_pvalue(a: Sequence[float], b: Sequence[float], lower_better_for_a: bool = True) -> float:
    """
    Two-sided sign test p-value (exact binomial).
    """
    pos = 0
    neg = 0
    for x, y in zip(a, b):
        if x == y:
            continue
        better = x < y if lower_better_for_a else x > y
        if better:
            pos += 1
        else:
            neg += 1
    n = pos + neg
    if n == 0:
        return 1.0
    k = min(pos, neg)
    tail = 0.0
    for i in range(0, k + 1):
        tail += math.comb(n, i) * (0.5 ** n)
    p = min(1.0, 2.0 * tail)
    return p


def paired_test(a: Sequence[float], b: Sequence[float], lower_better_for_a: bool = True) -> Dict[str, float]:
    """
    Try Wilcoxon if scipy is available, otherwise use sign test.
    """
    if len(a) != len(b) or not a:
        return {"p_value": 1.0, "test": "invalid"}

    try:
        from scipy.stats import wilcoxon  # type: ignore

        # for lower_better_for_a, alternative='less' means a < b
        if lower_better_for_a:
            stat, p = wilcoxon(a, b, alternative="less", zero_method="wilcox")
        else:
            stat, p = wilcoxon(a, b, alternative="greater", zero_method="wilcox")
        return {"p_value": float(p), "statistic": float(stat), "test": "wilcoxon"}
    except Exception:
        p = _sign_test_pvalue(a, b, lower_better_for_a=lower_better_for_a)
        return {"p_value": float(p), "test": "sign_test"}


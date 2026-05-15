from __future__ import annotations

from scipy.stats import fisher_exact, hypergeom


def hypergeom_enrichment_p_value(k: int, n: int, K: int, N: int) -> float:
    if min(k, n, K, N) < 0 or n == 0 or K == 0 or N == 0:
        return 1.0
    if k > n or k > K or n > N or K > N:
        return 1.0
    return float(hypergeom.sf(k - 1, N, K, n))


def fold_enrichment(k: int, n: int, K: int, N: int) -> float:
    if n == 0 or K == 0 or N == 0:
        return 0.0
    background = K / N
    if background == 0:
        return 0.0
    return (k / n) / background


def fisher_greater_p_value(a: int, b: int, c: int, d: int) -> float:
    if min(a, b, c, d) < 0:
        return 1.0
    if a + b == 0 or c + d == 0:
        return 1.0
    result = fisher_exact([[a, b], [c, d]], alternative="greater")
    return float(result.pvalue if hasattr(result, "pvalue") else result[1])


def odds_ratio(a: int, b: int, c: int, d: int) -> float:
    if min(a, b, c, d) < 0:
        return 0.0
    numerator = a * d
    denominator = b * c
    if denominator == 0:
        return float("inf") if numerator > 0 else 0.0
    return numerator / denominator


def frequency_ratio(k_in: int, n_in: int, k_out: int, n_out: int) -> float:
    if n_in == 0:
        return 0.0
    inside = k_in / n_in
    outside = k_out / n_out if n_out else 0.0
    if outside == 0:
        return float("inf") if inside > 0 else 0.0
    return inside / outside

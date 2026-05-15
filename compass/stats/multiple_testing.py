from __future__ import annotations


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    if not p_values:
        return []
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    q_values = [1.0] * len(p_values)
    running_min = 1.0
    total = len(p_values)
    for rank, (index, p_value) in reversed(list(enumerate(indexed, start=1))):
        adjusted = min(running_min, p_value * total / rank)
        running_min = adjusted
        q_values[index] = min(adjusted, 1.0)
    return q_values

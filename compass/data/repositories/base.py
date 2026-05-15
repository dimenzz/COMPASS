from __future__ import annotations

from collections.abc import Iterable


def batched(values: list[str], size: int = 900) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]

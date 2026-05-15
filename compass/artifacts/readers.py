from __future__ import annotations

import csv
import json
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_headerless_tsv(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.reader(handle, delimiter="\t") if row]


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

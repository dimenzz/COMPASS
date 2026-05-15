from __future__ import annotations

import csv
from pathlib import Path


class ManifestRepository:
    def __init__(self, manifest_path: Path | None):
        self.manifest_path = manifest_path
        self._paths: dict[str, Path] | None = None

    def get_path(self, genome_id: str) -> Path | None:
        if not genome_id or self.manifest_path is None:
            return None
        paths = self._load()
        return paths.get(genome_id)

    def _load(self) -> dict[str, Path]:
        if self._paths is not None:
            return self._paths
        paths: dict[str, Path] = {}
        if self.manifest_path is None or not self.manifest_path.exists():
            self._paths = paths
            return paths
        with self.manifest_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.reader(handle):
                if len(row) >= 2 and row[0] and row[1]:
                    paths[row[0]] = Path(row[1])
        self._paths = paths
        return paths

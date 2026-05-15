from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

from compass.artifacts.state import utc_now


BACKGROUND_SCHEMA_VERSION = "1"
BACKGROUND_FIELDS = ["family30_id", "num_90_representatives"]


def default_background_meta_path(background_path: Path) -> Path:
    return background_path.with_suffix(".meta.json")


def build_family30_background(clusters_db: Path, output_path: Path, meta_path: Path | None = None) -> dict[str, Any]:
    if not clusters_db.exists():
        raise FileNotFoundError(f"Cluster database does not exist: {clusters_db}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_meta_path = meta_path or default_background_meta_path(output_path)
    resolved_meta_path.parent.mkdir(parents=True, exist_ok=True)

    num_families = 0
    total_90_representatives = 0
    with sqlite3.connect(f"file:{clusters_db}?mode=ro", uri=True) as conn:
        rows = conn.execute(
            """
            SELECT representative_id, COUNT(*) AS count
            FROM clusters
            WHERE cluster_level = '30'
            GROUP BY representative_id
            ORDER BY representative_id
            """
        )
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=BACKGROUND_FIELDS, delimiter="\t")
            writer.writeheader()
            for family30_id, count in rows:
                count = int(count)
                writer.writerow({"family30_id": family30_id, "num_90_representatives": count})
                num_families += 1
                total_90_representatives += count

    metadata = {
        "source_clusters_db": str(clusters_db),
        "cluster_level": "30",
        "count_unit": "90_percent_representatives",
        "num_families": num_families,
        "num_total_90_representatives": total_90_representatives,
        "created_at": utc_now(),
        "schema_version": BACKGROUND_SCHEMA_VERSION,
    }
    resolved_meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def load_family30_background(background_path: Path) -> tuple[dict[str, int], int]:
    if not background_path.exists():
        raise FileNotFoundError(
            "Family30 background cache does not exist: "
            f"{background_path}. Build it with `compass build-background --clusters-db <clusters.db> --output {background_path}`."
        )

    counts: dict[str, int] = {}
    with background_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = [field for field in BACKGROUND_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Family30 background cache missing required columns {missing}: {background_path}")
        for row in reader:
            family_id = row.get("family30_id", "")
            if not family_id:
                continue
            try:
                count = int(row.get("num_90_representatives", "0"))
            except ValueError as exc:
                raise ValueError(f"Invalid num_90_representatives for family {family_id}: {background_path}") from exc
            if count < 0:
                raise ValueError(f"Negative num_90_representatives for family {family_id}: {background_path}")
            counts[family_id] = count

    total = sum(counts.values())
    if total <= 0:
        raise ValueError(f"Family30 background cache is empty: {background_path}")
    return counts, total

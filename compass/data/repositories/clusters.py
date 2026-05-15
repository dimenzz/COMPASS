from __future__ import annotations

import sqlite3
from pathlib import Path

from compass.data.repositories.base import batched


class ClusterRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def __enter__(self) -> "ClusterRepository":
        self.conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.conn.close()

    def get_parent_30_families(self, representative90_ids: list[str]) -> dict[str, str]:
        return self.get_representatives(representative90_ids, cluster_level="30")

    def get_representatives(self, member_ids: list[str], cluster_level: str) -> dict[str, str]:
        if not member_ids:
            return {}
        result: dict[str, str] = {}
        for chunk in batched(member_ids):
            placeholders = ",".join("?" for _ in chunk)
            rows = self.conn.execute(
                f"""
                SELECT member_id, representative_id
                FROM clusters
                WHERE cluster_level = ? AND member_id IN ({placeholders})
                """,
                [cluster_level, *chunk],
            )
            result.update({member_id: representative_id for member_id, representative_id in rows})
        return result

    def expand_30_families_to_90_reps(self, family30_ids: list[str]) -> dict[str, list[str]]:
        expanded: dict[str, list[str]] = {family_id: [] for family_id in family30_ids}
        if not family30_ids:
            return expanded
        for chunk in batched(family30_ids):
            placeholders = ",".join("?" for _ in chunk)
            rows = self.conn.execute(
                f"""
                SELECT representative_id, member_id
                FROM clusters
                WHERE cluster_level = '30' AND representative_id IN ({placeholders})
                ORDER BY representative_id, member_id
                """,
                chunk,
            )
            for family30_id, representative90_id in rows:
                expanded.setdefault(family30_id, []).append(representative90_id)
        return expanded

    def count_90_reps_by_30_family(self, family30_ids: list[str] | None = None) -> dict[str, int]:
        if family30_ids == []:
            return {}
        counts: dict[str, int] = {}
        if family30_ids is None:
            rows = self.conn.execute(
                """
                SELECT representative_id, COUNT(*) AS count
                FROM clusters
                WHERE cluster_level = '30'
                GROUP BY representative_id
                """
            )
            return {family_id: int(count) for family_id, count in rows}
        for chunk in batched(sorted(set(family30_ids))):
            placeholders = ",".join("?" for _ in chunk)
            rows = self.conn.execute(
                f"""
                SELECT representative_id, COUNT(*) AS count
                FROM clusters
                WHERE cluster_level = '30' AND representative_id IN ({placeholders})
                GROUP BY representative_id
                """,
                chunk,
            )
            counts.update({family_id: int(count) for family_id, count in rows})
        return counts

    def count_total_90_reps_in_30_families(self) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM clusters WHERE cluster_level = '30'"
        ).fetchone()
        return int(row[0] or 0)

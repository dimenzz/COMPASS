from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path

from compass.data.models import ContextWindowItem, ProteinRecord
from compass.data.repositories.base import batched


class ProteinRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def __enter__(self) -> "ProteinRepository":
        self.conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.conn.close()

    def get_proteins(self, protein_ids: list[str]) -> dict[str, ProteinRecord]:
        if not protein_ids:
            return {}
        records: dict[str, ProteinRecord] = {}
        for chunk in batched(protein_ids):
            placeholders = ",".join("?" for _ in chunk)
            rows = self.conn.execute(
                f"""
                SELECT p.*, c.taxonomy, c.environment
                FROM proteins p
                LEFT JOIN contigs c ON c.contig_id = p.contig_id
                WHERE p.protein_id IN ({placeholders})
                """,
                chunk,
            )
            for row in rows:
                record = _to_record(row)
                records[record.protein_id] = record
        return records

    def get_context_windows(
        self,
        seed_protein_ids: list[str],
        upstream_genes: int,
        downstream_genes: int,
        max_distance_bp: int,
    ) -> dict[str, list[ContextWindowItem]]:
        seed_records = self.get_proteins(seed_protein_ids)
        seeds_by_contig: dict[str, list[ProteinRecord]] = defaultdict(list)
        for seed_id in seed_protein_ids:
            seed = seed_records.get(seed_id)
            if seed is None or seed.start is None or seed.end is None or not seed.contig_id:
                continue
            seeds_by_contig[seed.contig_id].append(seed)

        windows: dict[str, list[ContextWindowItem]] = {seed_id: [] for seed_id in seed_protein_ids}
        for contig_id, seeds in seeds_by_contig.items():
            min_start = min(seed.start or 0 for seed in seeds) - max_distance_bp
            max_end = max(seed.end or 0 for seed in seeds) + max_distance_bp
            contig_records = self._get_contig_records(contig_id, min_start, max_end)
            index_by_protein_id = {record.protein_id: index for index, record in enumerate(contig_records)}
            for seed in seeds:
                seed_index = index_by_protein_id.get(seed.protein_id)
                if seed_index is None:
                    continue
                window_start = max(0, seed_index - upstream_genes)
                window_end = min(len(contig_records), seed_index + downstream_genes + 1)
                for neighbor_index in range(window_start, window_end):
                    if neighbor_index == seed_index:
                        continue
                    neighbor = contig_records[neighbor_index]
                    distance_bp = _distance_bp(seed, neighbor)
                    if distance_bp <= max_distance_bp:
                        windows[seed.protein_id].append(
                            ContextWindowItem(
                                seed_protein_id=seed.protein_id,
                                neighbor=neighbor,
                                relative_gene_index=neighbor_index - seed_index,
                                distance_bp=distance_bp,
                            )
                        )
        return windows

    def _get_contig_records(self, contig_id: str, min_start: int, max_end: int) -> list[ProteinRecord]:
        rows = self.conn.execute(
            """
            SELECT p.*, c.taxonomy, c.environment
            FROM proteins p
            LEFT JOIN contigs c ON c.contig_id = p.contig_id
            WHERE p.contig_id = ? AND p.end >= ? AND p.start <= ?
            ORDER BY p.start, p.end, p.protein_id
            """,
            (contig_id, min_start, max_end),
        )
        return [_to_record(row) for row in rows]


def _to_record(row: sqlite3.Row) -> ProteinRecord:
    return ProteinRecord(
        protein_id=row["protein_id"],
        contig_id=row["contig_id"] or "",
        mag_id=row["mag_id"] or "",
        start=int(row["start"]) if row["start"] is not None else None,
        end=int(row["end"]) if row["end"] is not None else None,
        strand=row["strand"] or "",
        length=int(row["length"]) if row["length"] is not None else None,
        product=row["product"] or "",
        gene_name=row["gene_name"] or "",
        locus_tag=row["locus_tag"] or "",
        pfam=row["pfam"] or "",
        interpro=row["interpro"] or "",
        kegg=row["kegg"] or "",
        cog_category=row["cog_category"] or "",
        cog_id=row["cog_id"] or "",
        ec_number=row["ec_number"] or "",
        eggnog=row["eggnog"] or "",
        taxonomy=row["taxonomy"] or "",
        environment=row["environment"] or "",
    )


def _distance_bp(seed: ProteinRecord, neighbor: ProteinRecord) -> int:
    if seed.start is None or seed.end is None or neighbor.start is None or neighbor.end is None:
        return 0
    if neighbor.end < seed.start:
        return seed.start - neighbor.end
    if neighbor.start > seed.end:
        return neighbor.start - seed.end
    return 0

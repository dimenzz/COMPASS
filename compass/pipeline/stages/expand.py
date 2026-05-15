from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from compass.artifacts.layout import RunLayout
from compass.artifacts.state import utc_now, write_stage_state
from compass.artifacts.writers import write_tsv
from compass.config.loader import read_run_metadata
from compass.data.models import ProteinRecord, SearchHit
from compass.data.repositories.clusters import ClusterRepository
from compass.data.repositories.proteins import ProteinRepository
from compass.pipeline.stages.base import (
    StageError,
    require_run,
    validate_stage_outputs,
    write_stage_log,
)
from compass.pipeline.stages.specs import STAGE_SPECS
from compass.tools.bio_tools.mmseqs import parse_hits, search_score_bin


MATCHED_30_FIELDS = [
    "cluster30_id",
    "direct_90_rep_count",
    "expanded_90_rep_count",
    "best_query",
    "best_direct_90_rep",
    "best_evalue",
    "best_bits",
    "direct_90_reps",
]

HOMOLOG_90_FIELDS = [
    "homolog_id",
    "seed_id",
    "protein_id",
    "cluster90_id",
    "cluster30_id",
    "source",
    "source_direct_90_rep",
    "best_evalue",
    "best_bits",
    "sequence_search_score_bin",
    "contig_id",
    "mag_id",
    "start",
    "end",
    "strand",
    "length",
    "taxonomy",
    "environment",
    "product",
    "gene_name",
    "pfam",
    "interpro",
    "kegg",
    "cog_id",
    "eggnog",
]


def run_expand_stage(run_dir: Path, direct_hits: Path | None = None, force: bool = False) -> None:
    layout = RunLayout(run_dir)
    require_run(layout)
    spec = STAGE_SPECS["expand"]
    validate_stage_outputs(layout, spec, force=force)

    metadata = read_run_metadata(layout.run_yaml)
    direct_hits_path = direct_hits or (layout.run_dir / STAGE_SPECS["search"].outputs["direct_90_hits"])
    if not direct_hits_path.exists():
        raise FileNotFoundError(f"Direct 90% hit table does not exist: {direct_hits_path}")

    started_at = utc_now()
    hits = parse_hits(direct_hits_path)
    direct_targets = sorted({hit.target for hit in hits if hit.target})
    if not direct_targets:
        raise StageError(f"No direct 90% hits found in {direct_hits_path}")

    best_hit_by_target = _best_hit_by_target(hits)
    with ClusterRepository(metadata.config.database.clusters_db) as clusters:
        parent_by_target = clusters.get_parent_30_families(direct_targets)
        family_ids = sorted(set(parent_by_target.values()))
        expanded_by_family = clusters.expand_30_families_to_90_reps(family_ids)

    expanded_reps = sorted({rep for reps in expanded_by_family.values() for rep in reps})
    with ProteinRepository(metadata.config.database.proteins_db) as proteins:
        protein_records = proteins.get_proteins(expanded_reps)

    family_hits = _family_hits(hits, parent_by_target)
    matched_rows = [
        _matched_family_row(family_id, family_hits[family_id], expanded_by_family.get(family_id, []))
        for family_id in family_ids
    ]
    homolog_rows = _homolog_rows(
        family_ids=family_ids,
        expanded_by_family=expanded_by_family,
        family_hits=family_hits,
        best_hit_by_target=best_hit_by_target,
        protein_records=protein_records,
    )

    write_tsv(layout.run_dir / spec.outputs["matched_30_families"], matched_rows, MATCHED_30_FIELDS)
    write_tsv(layout.run_dir / spec.outputs["homolog_90_reps"], homolog_rows, HOMOLOG_90_FIELDS)

    missing_parent_count = len(set(direct_targets) - set(parent_by_target))
    missing_metadata_count = len(set(expanded_reps) - set(protein_records))
    write_stage_log(
        layout,
        "expand",
        "\n".join(
            [
                "expand stage completed",
                f"direct_hits: {direct_hits_path}",
                f"num_direct_hits: {len(hits)}",
                f"num_unique_direct_90_reps: {len(direct_targets)}",
                f"num_matched_30_families: {len(family_ids)}",
                f"num_homolog_90_reps: {len(expanded_reps)}",
                f"missing_parent_30_assignments: {missing_parent_count}",
                f"missing_protein_metadata: {missing_metadata_count}",
                "",
            ]
        ),
    )
    write_stage_state(
        layout=layout,
        stage="expand",
        started_at=started_at,
        inputs={"direct_90_hits": str(direct_hits_path)},
        outputs=spec.outputs,
        parameters={
            "direct_hits_override": str(direct_hits) if direct_hits is not None else None,
            "clusters_db": str(metadata.config.database.clusters_db),
            "proteins_db": str(metadata.config.database.proteins_db),
        },
    )


def _best_hit_by_target(hits: list[SearchHit]) -> dict[str, SearchHit]:
    best: dict[str, SearchHit] = {}
    for hit in hits:
        current = best.get(hit.target)
        if current is None or _hit_sort_key(hit) < _hit_sort_key(current):
            best[hit.target] = hit
    return best


def _family_hits(hits: list[SearchHit], parent_by_target: dict[str, str]) -> dict[str, list[SearchHit]]:
    grouped: dict[str, list[SearchHit]] = defaultdict(list)
    for hit in hits:
        family_id = parent_by_target.get(hit.target)
        if family_id is not None:
            grouped[family_id].append(hit)
    return grouped


def _matched_family_row(family_id: str, hits: list[SearchHit], expanded_reps: list[str]) -> dict[str, object]:
    best_hit = min(hits, key=_hit_sort_key)
    direct_reps = sorted({hit.target for hit in hits})
    return {
        "cluster30_id": family_id,
        "direct_90_rep_count": len(direct_reps),
        "expanded_90_rep_count": len(set(expanded_reps)),
        "best_query": best_hit.query,
        "best_direct_90_rep": best_hit.target,
        "best_evalue": best_hit.evalue,
        "best_bits": best_hit.bits,
        "direct_90_reps": ";".join(direct_reps),
    }


def _homolog_rows(
    family_ids: list[str],
    expanded_by_family: dict[str, list[str]],
    family_hits: dict[str, list[SearchHit]],
    best_hit_by_target: dict[str, SearchHit],
    protein_records: dict[str, ProteinRecord],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    homolog_index = 1
    for family_id in family_ids:
        best_family_hit = min(family_hits[family_id], key=_hit_sort_key)
        for protein_id in sorted(set(expanded_by_family.get(family_id, []))):
            direct_hit = best_hit_by_target.get(protein_id)
            source_hit = direct_hit or best_family_hit
            record = protein_records.get(protein_id, ProteinRecord(protein_id=protein_id))
            rows.append(
                {
                    "homolog_id": f"homolog_{homolog_index:07d}",
                    "seed_id": source_hit.query,
                    "protein_id": protein_id,
                    "cluster90_id": protein_id,
                    "cluster30_id": family_id,
                    "source": "direct_90_hit" if direct_hit is not None else "cluster30_expansion",
                    "source_direct_90_rep": source_hit.target,
                    "best_evalue": source_hit.evalue,
                    "best_bits": source_hit.bits,
                    "sequence_search_score_bin": search_score_bin(direct_hit),
                    **_protein_fields(record),
                }
            )
            homolog_index += 1
    return rows


def _protein_fields(record: ProteinRecord) -> dict[str, object]:
    return {
        "contig_id": record.contig_id,
        "mag_id": record.mag_id,
        "start": record.start,
        "end": record.end,
        "strand": record.strand,
        "length": record.length,
        "taxonomy": record.taxonomy,
        "environment": record.environment,
        "product": record.product,
        "gene_name": record.gene_name,
        "pfam": record.pfam,
        "interpro": record.interpro,
        "kegg": record.kegg,
        "cog_id": record.cog_id,
        "eggnog": record.eggnog,
    }


def _hit_sort_key(hit: SearchHit) -> tuple[float, float, str, str]:
    return (hit.evalue, -hit.bits, hit.query, hit.target)

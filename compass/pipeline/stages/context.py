from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from compass.artifacts.layout import RunLayout
from compass.artifacts.readers import read_tsv
from compass.artifacts.state import utc_now, write_stage_state
from compass.artifacts.writers import write_tsv
from compass.config.loader import read_run_metadata
from compass.data.models import ContextWindowItem, ProteinRecord
from compass.data.repositories.clusters import ClusterRepository
from compass.data.repositories.proteins import ProteinRepository
from compass.pipeline.stages.base import (
    StageError,
    require_run,
    validate_stage_outputs,
    write_stage_log,
)
from compass.pipeline.stages.specs import STAGE_SPECS


LOCI_FIELDS = [
    "locus_id",
    "homolog_id",
    "seed_protein_id",
    "cluster90_id",
    "cluster30_id",
    "contig_id",
    "mag_id",
    "start",
    "end",
    "strand",
    "taxonomy",
    "environment",
    "upstream_neighbor_count",
    "downstream_neighbor_count",
    "neighbor_count",
]

NEIGHBOR_FIELDS = [
    "locus_id",
    "homolog_id",
    "seed_protein_id",
    "seed_30_family",
    "neighbor_instance_id",
    "neighbor_protein_id",
    "neighbor_90_rep",
    "neighbor_30_family",
    "relative_gene_index",
    "distance_bp",
    "same_strand",
    "orientation_pattern",
    "contig_id",
    "start",
    "end",
    "strand",
    "product",
    "pfam",
    "interpro",
    "kegg",
    "cog_id",
    "eggnog",
]

SIGNATURE_FIELDS = [
    "locus_id",
    "homolog_id",
    "seed_protein_id",
    "seed_30_family",
    "neighbor_family_signature",
    "neighbor_30_family_count",
    "neighbor_count",
]


def run_context_stage(run_dir: Path, homologs: Path | None = None, force: bool = False) -> None:
    layout = RunLayout(run_dir)
    require_run(layout)
    spec = STAGE_SPECS["context"]
    validate_stage_outputs(layout, spec, force=force)

    metadata = read_run_metadata(layout.run_yaml)
    homologs_path = homologs or (layout.run_dir / STAGE_SPECS["expand"].outputs["homolog_90_reps"])
    if not homologs_path.exists():
        raise FileNotFoundError(f"Homolog 90% representative table does not exist: {homologs_path}")

    started_at = utc_now()
    homolog_rows = read_tsv(homologs_path)
    if not homolog_rows:
        raise StageError(f"No homolog rows found in {homologs_path}")

    homolog_by_protein_id = {row["protein_id"]: row for row in homolog_rows if row.get("protein_id")}
    seed_protein_ids = list(homolog_by_protein_id)
    with ProteinRepository(metadata.config.database.proteins_db) as proteins:
        seed_records = proteins.get_proteins(seed_protein_ids)
        windows = proteins.get_context_windows(
            seed_protein_ids=seed_protein_ids,
            upstream_genes=metadata.config.context.upstream_genes,
            downstream_genes=metadata.config.context.downstream_genes,
            max_distance_bp=metadata.config.context.max_distance_bp,
        )

    neighbor_ids = sorted({item.neighbor.protein_id for items in windows.values() for item in items})
    with ClusterRepository(metadata.config.database.clusters_db) as clusters:
        neighbor_90_by_protein = clusters.get_representatives(neighbor_ids, cluster_level="90")
        neighbor_90_reps = sorted({neighbor_90_by_protein.get(protein_id, protein_id) for protein_id in neighbor_ids})
        neighbor_30_by_rep = clusters.get_parent_30_families(neighbor_90_reps)

    loci_rows: list[dict[str, object]] = []
    neighbor_rows: list[dict[str, object]] = []
    signature_rows: list[dict[str, object]] = []
    neighbor_index = 1
    for locus_index, (seed_protein_id, homolog_row) in enumerate(homolog_by_protein_id.items(), start=1):
        locus_id = f"locus_{locus_index:07d}"
        seed_record = seed_records.get(seed_protein_id, ProteinRecord(protein_id=seed_protein_id))
        items = windows.get(seed_protein_id, [])
        upstream_count = sum(1 for item in items if item.relative_gene_index < 0)
        downstream_count = sum(1 for item in items if item.relative_gene_index > 0)
        seed_30_family = homolog_row.get("cluster30_id", "")
        loci_rows.append(
            {
                "locus_id": locus_id,
                "homolog_id": homolog_row.get("homolog_id", ""),
                "seed_protein_id": seed_protein_id,
                "cluster90_id": homolog_row.get("cluster90_id", seed_protein_id),
                "cluster30_id": seed_30_family,
                **_locus_record_fields(seed_record),
                "upstream_neighbor_count": upstream_count,
                "downstream_neighbor_count": downstream_count,
                "neighbor_count": len(items),
            }
        )
        family_signature_parts: list[str] = []
        observed_families: set[str] = set()
        for item in sorted(items, key=lambda value: value.relative_gene_index):
            neighbor_90 = neighbor_90_by_protein.get(item.neighbor.protein_id, item.neighbor.protein_id)
            neighbor_30 = neighbor_30_by_rep.get(neighbor_90, "")
            if neighbor_30:
                observed_families.add(neighbor_30)
                family_signature_parts.append(f"{item.relative_gene_index}:{neighbor_30}")
            neighbor_rows.append(
                _neighbor_row(
                    locus_id=locus_id,
                    homolog_id=homolog_row.get("homolog_id", ""),
                    seed_protein_id=seed_protein_id,
                    seed_30_family=seed_30_family,
                    neighbor_instance_id=f"neighbor_{neighbor_index:07d}",
                    item=item,
                    neighbor_90=neighbor_90,
                    neighbor_30=neighbor_30,
                    seed_record=seed_record,
                )
            )
            neighbor_index += 1
        signature_rows.append(
            {
                "locus_id": locus_id,
                "homolog_id": homolog_row.get("homolog_id", ""),
                "seed_protein_id": seed_protein_id,
                "seed_30_family": seed_30_family,
                "neighbor_family_signature": ";".join(family_signature_parts),
                "neighbor_30_family_count": len(observed_families),
                "neighbor_count": len(items),
            }
        )

    write_tsv(layout.run_dir / spec.outputs["loci"], loci_rows, LOCI_FIELDS)
    write_tsv(layout.run_dir / spec.outputs["context_neighbors"], neighbor_rows, NEIGHBOR_FIELDS)
    write_tsv(layout.run_dir / spec.outputs["context_signatures"], signature_rows, SIGNATURE_FIELDS)
    write_stage_log(
        layout,
        "context",
        "\n".join(
            [
                "context stage completed",
                f"homologs: {homologs_path}",
                f"num_homolog_rows: {len(homolog_rows)}",
                f"num_loci: {len(loci_rows)}",
                f"num_neighbor_rows: {len(neighbor_rows)}",
                f"num_neighbor_90_reps: {len(set(neighbor_90_by_protein.values()))}",
                "",
            ]
        ),
    )
    write_stage_state(
        layout=layout,
        stage="context",
        started_at=started_at,
        inputs={"homolog_90_reps": str(homologs_path)},
        outputs=spec.outputs,
        parameters={
            "homologs_override": str(homologs) if homologs is not None else None,
            "context": metadata.config.context.model_dump(mode="json"),
            "clusters_db": str(metadata.config.database.clusters_db),
            "proteins_db": str(metadata.config.database.proteins_db),
        },
    )


def _locus_record_fields(record: ProteinRecord) -> dict[str, object]:
    return {
        "contig_id": record.contig_id,
        "mag_id": record.mag_id,
        "start": record.start,
        "end": record.end,
        "strand": record.strand,
        "taxonomy": record.taxonomy,
        "environment": record.environment,
    }


def _neighbor_row(
    locus_id: str,
    homolog_id: str,
    seed_protein_id: str,
    seed_30_family: str,
    neighbor_instance_id: str,
    item: ContextWindowItem,
    neighbor_90: str,
    neighbor_30: str,
    seed_record: ProteinRecord,
) -> dict[str, object]:
    neighbor = item.neighbor
    same_strand = bool(seed_record.strand and neighbor.strand and seed_record.strand == neighbor.strand)
    return {
        "locus_id": locus_id,
        "homolog_id": homolog_id,
        "seed_protein_id": seed_protein_id,
        "seed_30_family": seed_30_family,
        "neighbor_instance_id": neighbor_instance_id,
        "neighbor_protein_id": neighbor.protein_id,
        "neighbor_90_rep": neighbor_90,
        "neighbor_30_family": neighbor_30,
        "relative_gene_index": item.relative_gene_index,
        "distance_bp": item.distance_bp,
        "same_strand": same_strand,
        "orientation_pattern": _orientation_pattern(item.relative_gene_index, same_strand),
        "contig_id": neighbor.contig_id,
        "start": neighbor.start,
        "end": neighbor.end,
        "strand": neighbor.strand,
        "product": neighbor.product,
        "pfam": neighbor.pfam,
        "interpro": neighbor.interpro,
        "kegg": neighbor.kegg,
        "cog_id": neighbor.cog_id,
        "eggnog": neighbor.eggnog,
    }


def _orientation_pattern(relative_gene_index: int, same_strand: bool) -> str:
    side = "upstream" if relative_gene_index < 0 else "downstream"
    orientation = "same" if same_strand else "opposite"
    return f"{side}_{orientation}"

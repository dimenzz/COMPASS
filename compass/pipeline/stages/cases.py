from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from compass.artifacts.layout import RunLayout
from compass.artifacts.readers import read_tsv
from compass.artifacts.state import utc_now, write_stage_state
from compass.artifacts.writers import write_jsonl
from compass.config.loader import read_run_metadata
from compass.pipeline.stages.base import require_run, validate_stage_outputs, write_stage_log
from compass.pipeline.stages.specs import STAGE_SPECS


def run_select_cases_stage(
    run_dir: Path,
    neighbor_enrichment: Path | None = None,
    context_neighbors: Path | None = None,
    force: bool = False,
) -> None:
    layout = RunLayout(run_dir)
    require_run(layout)
    spec = STAGE_SPECS["select-cases"]
    validate_stage_outputs(layout, spec, force=force)

    metadata = read_run_metadata(layout.run_yaml)
    enrichment_path = neighbor_enrichment or (layout.run_dir / STAGE_SPECS["enrich"].outputs["neighbor_enrichment"])
    neighbors_path = context_neighbors or (layout.run_dir / STAGE_SPECS["context"].outputs["context_neighbors"])
    if not enrichment_path.exists():
        raise FileNotFoundError(f"Neighbor enrichment table does not exist: {enrichment_path}")
    if not neighbors_path.exists():
        raise FileNotFoundError(f"Context neighbor table does not exist: {neighbors_path}")

    started_at = utc_now()
    enrichment_rows = read_tsv(enrichment_path)
    neighbor_rows = read_tsv(neighbors_path)
    selected_families = _selected_families(enrichment_rows, metadata.config)
    neighbors_by_family = _neighbors_by_family(neighbor_rows)

    enriched_family_records = []
    case_records = []
    diagram_records = []
    case_index = 1
    for family in selected_families:
        family_id = family["neighbor_30_family"]
        candidate_neighbors = sorted(
            neighbors_by_family.get(family_id, []),
            key=lambda row: (_to_int(row.get("distance_bp")), abs(_to_int(row.get("relative_gene_index"))), row.get("locus_id", "")),
        )
        selected_neighbors = candidate_neighbors[: metadata.config.agent.cases_per_family]
        enriched_family_records.append(
            {
                "family_id": family_id,
                "rank": len(enriched_family_records) + 1,
                "metrics": family,
                "selected_case_count": len(selected_neighbors),
            }
        )
        for neighbor in selected_neighbors:
            case_id = f"cmp:{metadata.run_name}:case:{case_index:07d}"
            case_records.append(_case_record(case_id, family_id, neighbor))
            diagram_records.append(_diagram_record(case_id, neighbor))
            case_index += 1

    write_jsonl(layout.run_dir / spec.outputs["enriched_families"], enriched_family_records)
    write_jsonl(layout.run_dir / spec.outputs["cases"], case_records)
    write_jsonl(layout.run_dir / spec.outputs["locus_diagrams"], diagram_records)
    write_stage_log(
        layout,
        "select-cases",
        "\n".join(
            [
                "select-cases stage completed",
                f"neighbor_enrichment: {enrichment_path}",
                f"context_neighbors: {neighbors_path}",
                f"num_selected_families: {len(enriched_family_records)}",
                f"num_cases: {len(case_records)}",
                "",
            ]
        ),
    )
    write_stage_state(
        layout=layout,
        stage="select-cases",
        started_at=started_at,
        inputs={"neighbor_enrichment": str(enrichment_path), "context_neighbors": str(neighbors_path)},
        outputs=spec.outputs,
        parameters={
            "thresholds": metadata.config.enrichment.model_dump(mode="json"),
            "cases_per_family": metadata.config.agent.cases_per_family,
            "max_families_for_llm": metadata.config.agent.max_families_for_llm,
            "neighbor_enrichment_override": str(neighbor_enrichment) if neighbor_enrichment is not None else None,
            "context_neighbors_override": str(context_neighbors) if context_neighbors is not None else None,
        },
    )


def _selected_families(enrichment_rows: list[dict[str, str]], config) -> list[dict[str, str]]:
    filtered = [
        row
        for row in enrichment_rows
        if _to_float(row.get("q_value")) <= config.enrichment.q_value
        and _to_float(row.get("fold_enrichment")) >= config.enrichment.fold_enrichment
        and _to_int(row.get("support_contexts")) >= config.enrichment.support_contexts
        and _to_float(row.get("observed_frequency")) >= config.enrichment.observed_frequency
    ]
    filtered.sort(key=lambda row: (_to_float(row.get("q_value")), -_to_float(row.get("fold_enrichment")), row.get("neighbor_30_family", "")))
    return filtered[: config.agent.max_families_for_llm]


def _neighbors_by_family(neighbor_rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in neighbor_rows:
        family_id = row.get("neighbor_30_family", "")
        if family_id:
            grouped[family_id].append(row)
    return grouped


def _case_record(case_id: str, family_id: str, neighbor: dict[str, str]) -> dict:
    return {
        "case_id": case_id,
        "locus_id": neighbor.get("locus_id", ""),
        "homolog_id": neighbor.get("homolog_id", ""),
        "neighbor_instance_id": neighbor.get("neighbor_instance_id", ""),
        "neighbor_30_family": family_id,
        "seed_protein_id": neighbor.get("seed_protein_id", ""),
        "neighbor_protein_id": neighbor.get("neighbor_protein_id", ""),
        "contig_id": neighbor.get("contig_id", ""),
        "coordinates": {
            "neighbor_start": _to_int(neighbor.get("start")),
            "neighbor_end": _to_int(neighbor.get("end")),
            "neighbor_strand": neighbor.get("strand", ""),
        },
        "relative_gene_index": _to_int(neighbor.get("relative_gene_index")),
        "distance_bp": _to_int(neighbor.get("distance_bp")),
        "annotation_payload": {
            "product": neighbor.get("product", ""),
            "pfam": neighbor.get("pfam", ""),
            "interpro": neighbor.get("interpro", ""),
            "kegg": neighbor.get("kegg", ""),
            "cog_id": neighbor.get("cog_id", ""),
            "eggnog": neighbor.get("eggnog", ""),
        },
    }


def _diagram_record(case_id: str, neighbor: dict[str, str]) -> dict:
    return {
        "case_id": case_id,
        "locus_id": neighbor.get("locus_id", ""),
        "seed_protein_id": neighbor.get("seed_protein_id", ""),
        "neighbor_protein_id": neighbor.get("neighbor_protein_id", ""),
        "relative_gene_index": _to_int(neighbor.get("relative_gene_index")),
        "distance_bp": _to_int(neighbor.get("distance_bp")),
        "text_diagram": f"{neighbor.get('seed_protein_id', 'seed')} --({neighbor.get('relative_gene_index', '')}; {neighbor.get('distance_bp', '')} bp)-- {neighbor.get('neighbor_protein_id', 'neighbor')}",
    }


def _to_float(value: str | None) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _to_int(value: str | None) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))

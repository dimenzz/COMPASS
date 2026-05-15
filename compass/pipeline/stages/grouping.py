from __future__ import annotations

import hashlib
from pathlib import Path
from statistics import median

from compass.artifacts.layout import RunLayout
from compass.artifacts.readers import read_tsv
from compass.artifacts.state import utc_now, write_stage_state
from compass.artifacts.writers import write_tsv
from compass.pipeline.stages.base import StageError, require_run, validate_stage_outputs, write_stage_log
from compass.pipeline.stages.specs import STAGE_SPECS


HOMOLOG_GROUP_FIELDS = [
    "homolog_id",
    "protein_id",
    "cluster90_id",
    "cluster30_id",
    "protein_subgroup_id",
    "primary_subgroup_method",
    "sequence_community_id",
    "domain_community_id",
    "sequence_search_score_bin",
    "length",
    "length_ratio_to_seed",
    "length_bin",
    "domain_architecture",
    "context_signature_cluster",
]

CONTEXT_CLUSTER_FIELDS = [
    "context_signature_cluster",
    "neighbor_family_signature",
    "locus_count",
]


def run_group_stage(
    run_dir: Path,
    homologs: Path | None = None,
    context_signatures: Path | None = None,
    protein_subgroups: Path | None = None,
    force: bool = False,
) -> None:
    layout = RunLayout(run_dir)
    require_run(layout)
    spec = STAGE_SPECS["group"]
    validate_stage_outputs(layout, spec, force=force)

    homologs_path = homologs or (layout.run_dir / STAGE_SPECS["expand"].outputs["homolog_90_reps"])
    signatures_path = context_signatures or (layout.run_dir / STAGE_SPECS["context"].outputs["context_signatures"])
    if not homologs_path.exists():
        raise FileNotFoundError(f"Homolog table does not exist: {homologs_path}")
    if not signatures_path.exists():
        raise FileNotFoundError(f"Context signatures table does not exist: {signatures_path}")
    if protein_subgroups is not None and not protein_subgroups.exists():
        raise FileNotFoundError(f"Protein subgroup table does not exist: {protein_subgroups}")

    started_at = utc_now()
    homolog_rows = read_tsv(homologs_path)
    signature_rows = read_tsv(signatures_path)
    subgroup_by_homolog = _read_protein_subgroups(protein_subgroups)
    if not homolog_rows:
        raise StageError(f"No homolog rows found in {homologs_path}")

    signature_by_homolog = {row.get("homolog_id", ""): row.get("neighbor_family_signature", "") for row in signature_rows}
    signature_cluster_by_signature = _cluster_context_signatures(signature_by_homolog.values())
    lengths = [_to_int(row.get("length")) for row in homolog_rows if _to_int(row.get("length")) > 0]
    median_length = median(lengths) if lengths else 0

    group_rows = []
    for row in homolog_rows:
        signature = signature_by_homolog.get(row.get("homolog_id", ""), "")
        length = _to_int(row.get("length"))
        subgroup = _subgroup_fields(row, subgroup_by_homolog)
        group_rows.append(
            {
                "homolog_id": row.get("homolog_id", ""),
                "protein_id": row.get("protein_id", ""),
                "cluster90_id": row.get("cluster90_id", row.get("protein_id", "")),
                "cluster30_id": row.get("cluster30_id", ""),
                **subgroup,
                "sequence_search_score_bin": row.get("sequence_search_score_bin", ""),
                "length": row.get("length", ""),
                "length_ratio_to_seed": "",
                "length_bin": _length_bin(length, median_length),
                "domain_architecture": _domain_architecture(row),
                "context_signature_cluster": signature_cluster_by_signature.get(signature, ""),
            }
        )

    cluster_rows = _context_cluster_rows(signature_cluster_by_signature, signature_by_homolog.values())
    protein_subgroup_count = len({row["protein_subgroup_id"] for row in group_rows if row.get("protein_subgroup_id")})
    primary_methods = sorted({row["primary_subgroup_method"] for row in group_rows if row.get("primary_subgroup_method")})
    write_tsv(layout.run_dir / spec.outputs["homolog_groups"], group_rows, HOMOLOG_GROUP_FIELDS)
    write_tsv(layout.run_dir / spec.outputs["context_signature_clusters"], cluster_rows, CONTEXT_CLUSTER_FIELDS)
    write_stage_log(
        layout,
        "group",
        "\n".join(
            [
                "group stage completed",
                f"homologs: {homologs_path}",
                f"context_signatures: {signatures_path}",
                f"protein_subgroups: {protein_subgroups or 'cluster30_id fallback'}",
                f"num_homolog_groups: {len(group_rows)}",
                f"num_protein_subgroups: {protein_subgroup_count}",
                f"primary_subgroup_methods: {','.join(primary_methods)}",
                f"num_context_signature_clusters: {len(cluster_rows)}",
                "",
            ]
        ),
    )
    write_stage_state(
        layout=layout,
        stage="group",
        started_at=started_at,
        inputs={
            "homolog_90_reps": str(homologs_path),
            "context_signatures": str(signatures_path),
            "protein_subgroups": str(protein_subgroups) if protein_subgroups is not None else "",
        },
        outputs=spec.outputs,
        parameters={
            "homologs_override": str(homologs) if homologs is not None else None,
            "context_signatures_override": str(context_signatures) if context_signatures is not None else None,
            "protein_subgroups_override": str(protein_subgroups) if protein_subgroups is not None else None,
        },
    )


def _read_protein_subgroups(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    rows = read_tsv(path)
    subgroup_by_homolog: dict[str, dict[str, str]] = {}
    for row in rows:
        homolog_id = row.get("homolog_id", "")
        if not homolog_id:
            continue
        subgroup_by_homolog[homolog_id] = row
    return subgroup_by_homolog


def _subgroup_fields(homolog_row: dict[str, str], subgroup_by_homolog: dict[str, dict[str, str]]) -> dict[str, str]:
    homolog_id = homolog_row.get("homolog_id", "")
    subgroup_row = subgroup_by_homolog.get(homolog_id, {})
    sequence_community_id = subgroup_row.get("sequence_community_id", "")
    domain_community_id = subgroup_row.get("domain_community_id", "")
    protein_subgroup_id = subgroup_row.get("protein_subgroup_id", "")
    primary_method = subgroup_row.get("primary_subgroup_method", "")

    if not protein_subgroup_id and sequence_community_id:
        protein_subgroup_id = sequence_community_id
        primary_method = primary_method or "sequence_community_id"
    if not protein_subgroup_id and domain_community_id:
        protein_subgroup_id = domain_community_id
        primary_method = primary_method or "domain_community_id"
    if not protein_subgroup_id:
        protein_subgroup_id = homolog_row.get("cluster30_id", "") or homolog_row.get("cluster90_id", "") or homolog_id
        primary_method = primary_method or "cluster30_id"
    return {
        "protein_subgroup_id": protein_subgroup_id,
        "primary_subgroup_method": primary_method or "protein_subgroup_id",
        "sequence_community_id": sequence_community_id,
        "domain_community_id": domain_community_id,
    }


def _cluster_context_signatures(signatures: object) -> dict[str, str]:
    unique_signatures = sorted(set(str(signature) for signature in signatures))
    return {signature: f"ctxsig_{_short_hash(signature)}" for signature in unique_signatures}


def _context_cluster_rows(cluster_by_signature: dict[str, str], signatures: object) -> list[dict[str, object]]:
    counts = {signature: 0 for signature in cluster_by_signature}
    for signature in signatures:
        counts[str(signature)] = counts.get(str(signature), 0) + 1
    return [
        {
            "context_signature_cluster": cluster_id,
            "neighbor_family_signature": signature,
            "locus_count": counts.get(signature, 0),
        }
        for signature, cluster_id in sorted(cluster_by_signature.items(), key=lambda item: item[1])
    ]


def _length_bin(length: int, median_length: float) -> str:
    if length <= 0 or median_length <= 0:
        return "unknown"
    if length < 0.8 * median_length:
        return "short"
    if length > 1.2 * median_length:
        return "long"
    return "typical"


def _domain_architecture(row: dict[str, str]) -> str:
    for key in ("pfam", "interpro", "kegg", "cog_id"):
        value = row.get(key, "")
        if value:
            return value
    return "unannotated"


def _short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def _to_int(value: str | None) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))

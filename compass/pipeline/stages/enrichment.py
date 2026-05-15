from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from compass.artifacts.layout import RunLayout
from compass.artifacts.readers import read_tsv
from compass.artifacts.state import utc_now, write_stage_state
from compass.artifacts.writers import write_jsonl, write_tsv
from compass.config.loader import read_run_metadata
from compass.data.background import load_family30_background
from compass.pipeline.stages.base import StageError, require_run, validate_stage_outputs, write_stage_log
from compass.pipeline.stages.specs import STAGE_SPECS
from compass.stats.enrichment import (
    fisher_greater_p_value,
    fold_enrichment,
    frequency_ratio,
    hypergeom_enrichment_p_value,
    odds_ratio,
)
from compass.stats.multiple_testing import benjamini_hochberg


FAMILY_BACKGROUND_FIELDS = [
    "family30_id",
    "family30_representative_id",
    "num_90_representatives",
    "annotation_summary",
]

NEIGHBOR_ENRICHMENT_FIELDS = [
    "neighbor_30_family",
    "k_contexts_with_family",
    "n_total_contexts",
    "K_family_90_rep_count",
    "N_total_90_rep_count",
    "observed_frequency",
    "background_frequency",
    "fold_enrichment",
    "p_value",
    "q_value",
    "support_contexts",
    "support_loci_examples",
    "annotation_summary",
]

SUBGROUP_ENRICHMENT_FIELDS = [
    "protein_subgroup_id",
    "primary_subgroup_method",
    "subgroup_size",
    "neighbor_30_family",
    "k_in_subgroup",
    "n_subgroup",
    "k_outside_subgroup",
    "n_outside",
    "within_subgroup_observed_frequency",
    "outside_subgroup_observed_frequency",
    "within_subgroup_fold_enrichment",
    "subgroup_specificity_odds_ratio",
    "p_value",
    "q_value",
    "rank_within_subgroup",
    "support_contexts",
    "support_loci_examples",
    "annotation_summary",
]


def run_enrich_stage(
    run_dir: Path,
    context_neighbors: Path | None = None,
    homolog_groups: Path | None = None,
    force: bool = False,
) -> None:
    layout = RunLayout(run_dir)
    require_run(layout)
    spec = STAGE_SPECS["enrich"]
    validate_stage_outputs(layout, spec, force=force)

    metadata = read_run_metadata(layout.run_yaml)
    neighbors_path = context_neighbors or (layout.run_dir / STAGE_SPECS["context"].outputs["context_neighbors"])
    groups_path = homolog_groups or (layout.run_dir / STAGE_SPECS["group"].outputs["homolog_groups"])
    if not neighbors_path.exists():
        raise FileNotFoundError(f"Context neighbor table does not exist: {neighbors_path}")
    if not groups_path.exists():
        raise FileNotFoundError(f"Homolog group table does not exist: {groups_path}")
    if metadata.config.database.family30_background is None:
        raise StageError("database.family30_background is required for enrich. Run `compass build-background` first.")

    started_at = utc_now()
    neighbor_rows = read_tsv(neighbors_path)
    group_rows = read_tsv(groups_path)
    if not group_rows:
        raise StageError(f"No homolog group rows found in {groups_path}")

    family_counts, total_90_count = load_family30_background(metadata.config.database.family30_background)
    index = _build_context_index(neighbor_rows, group_rows)
    observed_families = sorted(index.family_homologs)

    background_rows = _background_rows(observed_families, family_counts, neighbor_rows)
    enrichment_rows = _enrichment_rows(index, family_counts, total_90_count)
    subgroup_rows = _subgroup_rows(index, metadata.config.enrichment)
    top_subgroup_hits = _top_subgroup_hits(subgroup_rows, metadata.config.enrichment.max_subgroup_neighbors_for_report)

    write_tsv(layout.run_dir / spec.outputs["family_background"], background_rows, FAMILY_BACKGROUND_FIELDS)
    write_tsv(layout.run_dir / spec.outputs["neighbor_enrichment"], enrichment_rows, NEIGHBOR_ENRICHMENT_FIELDS)
    write_tsv(layout.run_dir / spec.outputs["subgroup_neighbor_enrichment"], subgroup_rows, SUBGROUP_ENRICHMENT_FIELDS)
    write_tsv(layout.run_dir / spec.outputs["subfamily_neighbor_enrichment"], subgroup_rows, SUBGROUP_ENRICHMENT_FIELDS)
    write_jsonl(layout.run_dir / spec.outputs["top_subgroup_neighbor_hits"], top_subgroup_hits)
    write_stage_log(
        layout,
        "enrich",
        "\n".join(
            [
                "enrich stage completed",
                f"context_neighbors: {neighbors_path}",
                f"homolog_groups: {groups_path}",
                f"family30_background: {metadata.config.database.family30_background}",
                f"num_homolog_contexts: {len(index.all_homologs)}",
                f"num_neighbor_rows: {len(neighbor_rows)}",
                f"num_observed_neighbor_families: {len(observed_families)}",
                f"num_neighbor_enrichment_rows: {len(enrichment_rows)}",
                f"num_subgroup_neighbor_enrichment_rows: {len(subgroup_rows)}",
                "",
            ]
        ),
    )
    write_stage_state(
        layout=layout,
        stage="enrich",
        started_at=started_at,
        inputs={"context_neighbors": str(neighbors_path), "homolog_groups": str(groups_path)},
        outputs=spec.outputs,
        parameters={
            "context_neighbors_override": str(context_neighbors) if context_neighbors is not None else None,
            "homolog_groups_override": str(homolog_groups) if homolog_groups is not None else None,
            "family30_background": str(metadata.config.database.family30_background),
            "family30_background_meta": str(metadata.config.database.family30_background_meta)
            if metadata.config.database.family30_background_meta is not None
            else None,
            "enrichment": metadata.config.enrichment.model_dump(mode="json"),
        },
    )


class ContextIndex:
    def __init__(
        self,
        all_homologs: set[str],
        homolog_neighbors: dict[str, set[str]],
        family_homologs: dict[str, set[str]],
        family_loci: dict[str, set[str]],
        loci_by_family_homolog: dict[str, dict[str, set[str]]],
        subgroup_homologs: dict[str, set[str]],
        subgroup_method: str,
        annotations: dict[str, str],
    ):
        self.all_homologs = all_homologs
        self.homolog_neighbors = homolog_neighbors
        self.family_homologs = family_homologs
        self.family_loci = family_loci
        self.loci_by_family_homolog = loci_by_family_homolog
        self.subgroup_homologs = subgroup_homologs
        self.subgroup_method = subgroup_method
        self.annotations = annotations


def _build_context_index(neighbor_rows: list[dict[str, str]], group_rows: list[dict[str, str]]) -> ContextIndex:
    all_homologs = {row.get("homolog_id", "") for row in group_rows if row.get("homolog_id")}
    homolog_neighbors: dict[str, set[str]] = {homolog_id: set() for homolog_id in all_homologs}
    family_homologs: dict[str, set[str]] = defaultdict(set)
    family_loci: dict[str, set[str]] = defaultdict(set)
    loci_by_family_homolog: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for row in neighbor_rows:
        homolog_id = row.get("homolog_id", "")
        family_id = row.get("neighbor_30_family", "")
        locus_id = row.get("locus_id", "")
        if not homolog_id or not family_id:
            continue
        if homolog_id not in all_homologs:
            continue
        homolog_neighbors.setdefault(homolog_id, set()).add(family_id)
        family_homologs[family_id].add(homolog_id)
        if locus_id:
            family_loci[family_id].add(locus_id)
            loci_by_family_homolog[family_id][homolog_id].add(locus_id)

    subgroup_method, subgroup_homologs = _subgroup_homologs(group_rows)
    return ContextIndex(
        all_homologs=all_homologs,
        homolog_neighbors=homolog_neighbors,
        family_homologs=dict(family_homologs),
        family_loci=dict(family_loci),
        loci_by_family_homolog={family_id: dict(by_homolog) for family_id, by_homolog in loci_by_family_homolog.items()},
        subgroup_homologs=subgroup_homologs,
        subgroup_method=subgroup_method,
        annotations=_annotation_summary_by_family(neighbor_rows),
    )


def _subgroup_homologs(group_rows: list[dict[str, str]]) -> tuple[str, dict[str, set[str]]]:
    if any(row.get("protein_subgroup_id") for row in group_rows):
        method = _most_common_value(group_rows, "primary_subgroup_method") or "protein_subgroup_id"
        return _homologs_by_feature(group_rows, feature="protein_subgroup_id", method=method)
    if any(row.get("sequence_community_id") for row in group_rows):
        return _homologs_by_feature(group_rows, feature="sequence_community_id", method="sequence_community_id")
    if any(row.get("domain_community_id") for row in group_rows):
        return _homologs_by_feature(group_rows, feature="domain_community_id", method="domain_community_id")
    return _homologs_by_feature(group_rows, feature="cluster30_id", method="cluster30_id")


def _most_common_value(rows: list[dict[str, str]], key: str) -> str:
    values = [row.get(key, "") for row in rows if row.get(key)]
    if not values:
        return ""
    return Counter(values).most_common(1)[0][0]


def _homologs_by_feature(group_rows: list[dict[str, str]], feature: str, method: str) -> tuple[str, dict[str, set[str]]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for row in group_rows:
        homolog_id = row.get("homolog_id", "")
        group_id = row.get(feature, "")
        if homolog_id and group_id:
            grouped[group_id].add(homolog_id)
    return method, dict(grouped)


def _background_rows(
    family_ids: list[str],
    family_counts: dict[str, int],
    neighbor_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    annotations = _annotation_summary_by_family(neighbor_rows)
    return [
        {
            "family30_id": family_id,
            "family30_representative_id": family_id,
            "num_90_representatives": family_counts.get(family_id, 0),
            "annotation_summary": annotations.get(family_id, ""),
        }
        for family_id in family_ids
    ]


def _enrichment_rows(index: ContextIndex, family_counts: dict[str, int], total_90_count: int) -> list[dict[str, object]]:
    n_total = len(index.all_homologs)
    rows = []
    p_values = []
    for family_id, homolog_ids in sorted(index.family_homologs.items()):
        k = len(homolog_ids)
        K = family_counts.get(family_id, 0)
        p_value = hypergeom_enrichment_p_value(k=k, n=n_total, K=K, N=total_90_count)
        p_values.append(p_value)
        observed = k / n_total if n_total else 0.0
        background = K / total_90_count if total_90_count else 0.0
        rows.append(
            {
                "neighbor_30_family": family_id,
                "k_contexts_with_family": k,
                "n_total_contexts": n_total,
                "K_family_90_rep_count": K,
                "N_total_90_rep_count": total_90_count,
                "observed_frequency": observed,
                "background_frequency": background,
                "fold_enrichment": fold_enrichment(k=k, n=n_total, K=K, N=total_90_count),
                "p_value": p_value,
                "q_value": 1.0,
                "support_contexts": k,
                "support_loci_examples": ";".join(sorted(index.family_loci.get(family_id, set()))[:5]),
                "annotation_summary": index.annotations.get(family_id, ""),
            }
        )
    q_values = benjamini_hochberg(p_values)
    for row, q_value in zip(rows, q_values, strict=True):
        row["q_value"] = q_value
    return sorted(rows, key=lambda row: (float(row["q_value"]), -float(row["fold_enrichment"]), row["neighbor_30_family"]))


def _subgroup_rows(index: ContextIndex, config: Any) -> list[dict[str, object]]:
    candidate_rows: list[dict[str, object]] = []
    p_values = []
    all_homologs = index.all_homologs
    for subgroup_id, subgroup_homologs in sorted(index.subgroup_homologs.items()):
        n_subgroup = len(subgroup_homologs)
        if n_subgroup < config.min_subgroup_size:
            continue
        outside_homologs = all_homologs - subgroup_homologs
        n_outside = len(outside_homologs)
        candidate_families = sorted({
            family_id
            for homolog_id in subgroup_homologs
            for family_id in index.homolog_neighbors.get(homolog_id, set())
        })
        for family_id in candidate_families:
            family_homologs = index.family_homologs.get(family_id, set())
            k_in = len(subgroup_homologs & family_homologs)
            if k_in < config.min_subgroup_support_contexts:
                continue
            k_out = len(outside_homologs & family_homologs)
            b = n_subgroup - k_in
            d = n_outside - k_out
            p_value = fisher_greater_p_value(a=k_in, b=b, c=k_out, d=d)
            p_values.append(p_value)
            odds = odds_ratio(a=k_in, b=b, c=k_out, d=d)
            candidate_rows.append(
                {
                    "protein_subgroup_id": subgroup_id,
                    "primary_subgroup_method": index.subgroup_method,
                    "subgroup_size": n_subgroup,
                    "neighbor_30_family": family_id,
                    "k_in_subgroup": k_in,
                    "n_subgroup": n_subgroup,
                    "k_outside_subgroup": k_out,
                    "n_outside": n_outside,
                    "within_subgroup_observed_frequency": k_in / n_subgroup if n_subgroup else 0.0,
                    "outside_subgroup_observed_frequency": k_out / n_outside if n_outside else 0.0,
                    "within_subgroup_fold_enrichment": frequency_ratio(k_in, n_subgroup, k_out, n_outside),
                    "subgroup_specificity_odds_ratio": odds,
                    "p_value": p_value,
                    "q_value": 1.0,
                    "rank_within_subgroup": 0,
                    "support_contexts": k_in,
                    "support_loci_examples": _subgroup_loci_examples(index, family_id, subgroup_homologs),
                    "annotation_summary": index.annotations.get(family_id, ""),
                }
            )

    q_values = benjamini_hochberg(p_values)
    for row, q_value in zip(candidate_rows, q_values, strict=True):
        row["q_value"] = q_value

    filtered_rows = [
        row
        for row in candidate_rows
        if float(row["q_value"]) <= config.subgroup_specificity_q_value
        and float(row["subgroup_specificity_odds_ratio"]) >= config.subgroup_specificity_odds_ratio
    ]
    filtered_rows.sort(
        key=lambda row: (
            row["protein_subgroup_id"],
            float(row["q_value"]),
            -float(row["subgroup_specificity_odds_ratio"]),
            -float(row["within_subgroup_fold_enrichment"]),
            row["neighbor_30_family"],
        )
    )
    _rank_within_subgroup(filtered_rows)
    return filtered_rows


def _subgroup_loci_examples(index: ContextIndex, family_id: str, subgroup_homologs: set[str]) -> str:
    loci = []
    by_homolog = index.loci_by_family_homolog.get(family_id, {})
    for homolog_id in sorted(subgroup_homologs):
        loci.extend(sorted(by_homolog.get(homolog_id, set())))
        if len(loci) >= 5:
            break
    return ";".join(loci[:5])


def _rank_within_subgroup(rows: list[dict[str, object]]) -> None:
    current_subgroup = None
    rank = 0
    for row in rows:
        subgroup_id = row["protein_subgroup_id"]
        if subgroup_id != current_subgroup:
            current_subgroup = subgroup_id
            rank = 1
        else:
            rank += 1
        row["rank_within_subgroup"] = rank


def _top_subgroup_hits(rows: list[dict[str, object]], max_neighbors: int) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["protein_subgroup_id"])].append(row)
    records = []
    for subgroup_id, subgroup_rows in sorted(grouped.items()):
        subgroup_rows = sorted(subgroup_rows, key=lambda row: int(row["rank_within_subgroup"]))[:max_neighbors]
        records.append(
            {
                "protein_subgroup_id": subgroup_id,
                "primary_subgroup_method": subgroup_rows[0]["primary_subgroup_method"] if subgroup_rows else "",
                "subgroup_size": subgroup_rows[0]["subgroup_size"] if subgroup_rows else 0,
                "top_neighbors": [_compact_subgroup_hit(row) for row in subgroup_rows],
            }
        )
    return records


def _compact_subgroup_hit(row: dict[str, object]) -> dict[str, object]:
    keys = [
        "neighbor_30_family",
        "rank_within_subgroup",
        "k_in_subgroup",
        "n_subgroup",
        "k_outside_subgroup",
        "n_outside",
        "within_subgroup_observed_frequency",
        "outside_subgroup_observed_frequency",
        "subgroup_specificity_odds_ratio",
        "q_value",
        "support_loci_examples",
        "annotation_summary",
    ]
    return {key: row.get(key, "") for key in keys}


def _annotation_summary_by_family(neighbor_rows: list[dict[str, str]]) -> dict[str, str]:
    products_by_family: dict[str, Counter[str]] = defaultdict(Counter)
    for row in neighbor_rows:
        family_id = row.get("neighbor_30_family", "")
        product = row.get("product", "")
        if family_id and product:
            products_by_family[family_id][product] += 1
    return {
        family_id: "; ".join(product for product, _count in counter.most_common(3))
        for family_id, counter in products_by_family.items()
    }

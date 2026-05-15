from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StageSpec:
    name: str
    inputs: dict[str, str]
    outputs: dict[str, str]


STAGE_SPECS: dict[str, StageSpec] = {
    "search": StageSpec(
        name="search",
        inputs={"seed": "inputs/seed.faa"},
        outputs={
            "mmseqs_hits": "search/mmseqs_hits.tsv",
            "direct_90_hits": "search/direct_90_hits.tsv",
        },
    ),
    "expand": StageSpec(
        name="expand",
        inputs={"direct_90_hits": "search/direct_90_hits.tsv"},
        outputs={
            "matched_30_families": "search/matched_30_families.tsv",
            "homolog_90_reps": "search/homolog_90_reps.tsv",
        },
    ),
    "context": StageSpec(
        name="context",
        inputs={"homolog_90_reps": "search/homolog_90_reps.tsv"},
        outputs={
            "loci": "context/loci.tsv",
            "context_neighbors": "context/context_neighbors.tsv",
            "context_signatures": "context/context_signatures.tsv",
        },
    ),
    "group": StageSpec(
        name="group",
        inputs={
            "homolog_90_reps": "search/homolog_90_reps.tsv",
            "context_signatures": "context/context_signatures.tsv",
        },
        outputs={
            "homolog_groups": "search/homolog_groups.tsv",
            "context_signature_clusters": "context/context_signature_clusters.tsv",
        },
    ),
    "enrich": StageSpec(
        name="enrich",
        inputs={
            "context_neighbors": "context/context_neighbors.tsv",
            "homolog_groups": "search/homolog_groups.tsv",
        },
        outputs={
            "family_background": "stats/family_background.tsv",
            "neighbor_enrichment": "stats/neighbor_enrichment.tsv",
            "subgroup_neighbor_enrichment": "stats/subgroup_neighbor_enrichment.tsv",
            "subfamily_neighbor_enrichment": "stats/subfamily_neighbor_enrichment.tsv",
            "top_subgroup_neighbor_hits": "stats/top_subgroup_neighbor_hits.jsonl",
        },
    ),
    "select-cases": StageSpec(
        name="select-cases",
        inputs={
            "neighbor_enrichment": "stats/neighbor_enrichment.tsv",
            "context_neighbors": "context/context_neighbors.tsv",
        },
        outputs={
            "enriched_families": "cases/enriched_families.jsonl",
            "cases": "cases/cases.jsonl",
            "locus_diagrams": "cases/locus_diagrams.jsonl",
        },
    ),
    "inspect-cases": StageSpec(
        name="inspect-cases",
        inputs={"cases": "cases/cases.jsonl"},
        outputs={
            "features": "cases/features.jsonl",
            "tool_evidence": "evidence/tool_evidence.jsonl",
        },
    ),
    "report": StageSpec(
        name="report",
        inputs={
            "neighbor_enrichment": "stats/neighbor_enrichment.tsv",
            "cases": "cases/cases.jsonl",
            "features": "cases/features.jsonl",
            "tool_evidence": "evidence/tool_evidence.jsonl",
        },
        outputs={
            "claims": "evidence/claims.jsonl",
            "report_md": "report/report.md",
            "report_html": "report/report.html",
        },
    ),
}


LINEAR_STAGES = [
    "search",
    "expand",
    "context",
    "group",
    "enrich",
    "select-cases",
    "inspect-cases",
    "report",
]

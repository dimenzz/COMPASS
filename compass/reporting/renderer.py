from __future__ import annotations

from html import escape
from pathlib import Path

from compass.artifacts.readers import read_jsonl, read_tsv
from compass.config.schema import RunMetadata


def render_markdown_report(
    metadata: RunMetadata,
    enrichment_path: Path,
    cases_path: Path,
    claims_path: Path,
    features_path: Path,
    tool_evidence_path: Path,
) -> str:
    enrichment_rows = read_tsv(enrichment_path) if enrichment_path.exists() else []
    cases = read_jsonl(cases_path) if cases_path.exists() else []
    claims = read_jsonl(claims_path) if claims_path.exists() else []
    features = read_jsonl(features_path) if features_path.exists() else []
    tool_evidence = read_jsonl(tool_evidence_path) if tool_evidence_path.exists() else []
    top_rows = enrichment_rows[:20]
    features_by_case = _features_by_case(features)

    lines = [
        "# COMPASS Discovery Report",
        "",
        "## Run Summary",
        "",
        f"- Run name: `{metadata.run_name}`",
        f"- Seed FASTA: `{metadata.seed_fasta}`",
        f"- LLM enabled: `{metadata.config.llm.enabled}`",
        "",
        "## Homolog Universe",
        "",
        "Homolog candidates were obtained from cluster_90 sequence hits, expanded through their parent 30% families to all contained 90% representatives.",
        "",
        "## Top Co-localized Neighbor Families",
        "",
    ]
    if top_rows:
        lines.extend(
            [
                "| Rank | Neighbor 30% family | Support | Observed freq. | Background freq. | Fold | q-value | Annotation |",
                "|---:|---|---:|---:|---:|---:|---:|---|",
            ]
        )
        for index, row in enumerate(top_rows, start=1):
            lines.append(
                "| {rank} | `{family}` | {support} | {obs:.4g} | {bg:.4g} | {fold:.4g} | {q:.4g} | {annotation} |".format(
                    rank=index,
                    family=row.get("neighbor_30_family", ""),
                    support=row.get("support_contexts", ""),
                    obs=_to_float(row.get("observed_frequency")),
                    bg=_to_float(row.get("background_frequency")),
                    fold=_to_float(row.get("fold_enrichment")),
                    q=_to_float(row.get("q_value")),
                    annotation=row.get("annotation_summary", ""),
                )
            )
    else:
        lines.append("No neighbor-family enrichment rows were produced.")
    lines.extend(["", "## Candidate System Summaries", ""])
    if cases:
        by_family = {}
        for case in cases:
            by_family.setdefault(case.get("neighbor_30_family", ""), []).append(case)
        for family_id, family_cases in by_family.items():
            family_features = [feature for case in family_cases for feature in features_by_case.get(case.get("case_id", ""), [])]
            lines.extend([f"### `{family_id}`", ""])
            lines.append(f"- Selected cases: {len(family_cases)}")
            examples = ", ".join(f"`{case['case_id']}`" for case in family_cases[:5])
            lines.append(f"- Example case IDs: {examples}")
            if family_features:
                feature_summary = _feature_summary(family_features)
                feature_examples = ", ".join(f"`{feature.get('feature_id', '')}`" for feature in family_features[:5])
                lines.append(f"- Sequence features detected: {feature_summary}")
                lines.append(f"- Example feature IDs: {feature_examples}")
            else:
                lines.append("- Sequence features detected: none in selected scanned windows")
            lines.append("")
    else:
        lines.append("No families passed the current LLM/case-selection thresholds.")
    lines.extend(
        [
            "",
            "## Cross-family Patterns",
            "",
            "Cross-family pattern synthesis is reserved for the LLM-assisted report pass.",
            "",
            "## Evidence and Claims",
            "",
        ]
    )
    warning_rows = _tool_warnings(tool_evidence)
    if warning_rows:
        lines.extend(["### Tool Warnings", ""])
        for row in warning_rows[:20]:
            warnings = "; ".join(row.get("payload", {}).get("warnings", []))
            lines.append(f"- `{row.get('case_id', '')}` via `{row.get('tool_id', '')}`: {warnings}")
        lines.append("")
    lines.extend(["### Claims", ""])
    if claims:
        for claim in claims:
            lines.append(f"- `{claim.get('claim_id', '')}`: {claim.get('statement', '')}")
    else:
        lines.append("No claims were generated.")
    lines.extend(
        [
            "",
            "## Methods",
            "",
            "- Search: MMseqs sequence search against cluster_90 representatives.",
            "- Expansion: direct 90% representative hits mapped to 30% families, then expanded to all 90% representatives in those families.",
            "- Context: protein-coding windows on the same contig with configured upstream/downstream gene counts and max distance.",
            "- Enrichment: presence/absence of neighbor 30% families per seed context, tested against global 30% family abundance over 90% representatives.",
            "- Subgroup specificity: neighbor families tested within protein subgroups against the remaining homolog contexts.",
            "",
            "## Artifacts",
            "",
            "- `search/homolog_90_reps.tsv`",
            "- `context/context_neighbors.tsv`",
            "- `stats/neighbor_enrichment.tsv`",
            "- `stats/subgroup_neighbor_enrichment.tsv`",
            "- `cases/cases.jsonl`",
            "- `cases/features.jsonl`",
            "- `evidence/tool_evidence.jsonl`",
            "- `evidence/claims.jsonl`",
            "",
        ]
    )
    return "\n".join(lines)


def render_html_report(markdown: str) -> str:
    body = "\n".join(f"<pre>{escape(line)}</pre>" for line in markdown.splitlines())
    return f"<!doctype html><html><body>{body}</body></html>\n"


def _to_float(value: str | None) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _features_by_case(features: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for feature in features:
        grouped.setdefault(feature.get("case_id", ""), []).append(feature)
    return grouped


def _feature_summary(features: list[dict]) -> str:
    counts: dict[str, int] = {}
    for feature in features:
        feature_type = feature.get("feature_type", "unknown")
        counts[feature_type] = counts.get(feature_type, 0) + 1
    return ", ".join(f"{feature_type}={count}" for feature_type, count in sorted(counts.items()))


def _tool_warnings(tool_evidence: list[dict]) -> list[dict]:
    return [
        row
        for row in tool_evidence
        if row.get("payload", {}).get("warnings")
    ]

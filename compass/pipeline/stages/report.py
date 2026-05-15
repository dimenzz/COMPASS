from __future__ import annotations

from pathlib import Path

from compass.artifacts.layout import RunLayout
from compass.artifacts.readers import read_jsonl, read_tsv
from compass.artifacts.state import utc_now, write_stage_state
from compass.artifacts.writers import write_jsonl
from compass.agents.hypothesis import generate_llm_claims, generate_llm_unavailable_claim
from compass.agents.llm_client import LlmUnavailableError
from compass.config.loader import read_run_metadata
from compass.pipeline.stages.base import require_run, validate_stage_outputs, write_stage_log
from compass.pipeline.stages.specs import STAGE_SPECS
from compass.reporting.renderer import render_html_report, render_markdown_report


def run_report_stage(
    run_dir: Path,
    neighbor_enrichment: Path | None = None,
    cases: Path | None = None,
    features: Path | None = None,
    tool_evidence: Path | None = None,
    force: bool = False,
) -> None:
    layout = RunLayout(run_dir)
    require_run(layout)
    spec = STAGE_SPECS["report"]
    validate_stage_outputs(layout, spec, force=force)

    metadata = read_run_metadata(layout.run_yaml)
    enrichment_path = neighbor_enrichment or (layout.run_dir / STAGE_SPECS["enrich"].outputs["neighbor_enrichment"])
    cases_path = cases or (layout.run_dir / STAGE_SPECS["select-cases"].outputs["cases"])
    features_path = features or (layout.run_dir / STAGE_SPECS["inspect-cases"].outputs["features"])
    tool_evidence_path = tool_evidence or (layout.run_dir / STAGE_SPECS["inspect-cases"].outputs["tool_evidence"])
    if not enrichment_path.exists():
        raise FileNotFoundError(f"Neighbor enrichment table does not exist: {enrichment_path}")
    if not cases_path.exists():
        raise FileNotFoundError(f"Cases JSONL does not exist: {cases_path}")
    if not features_path.exists():
        raise FileNotFoundError(f"Features JSONL does not exist: {features_path}")
    if not tool_evidence_path.exists():
        raise FileNotFoundError(f"Tool evidence JSONL does not exist: {tool_evidence_path}")

    started_at = utc_now()
    claims_path = layout.run_dir / spec.outputs["claims"]
    claims = _deterministic_claims(enrichment_path, cases_path, features_path)
    llm_warning = ""
    try:
        llm_claims, _warnings = generate_llm_claims(
            metadata=metadata,
            enrichment_path=enrichment_path,
            cases_path=cases_path,
            features_path=features_path,
            tool_evidence_path=tool_evidence_path,
            starting_claim_index=len(claims) + 1,
        )
        claims.extend(llm_claims)
    except LlmUnavailableError as exc:
        llm_warning = str(exc)
        claims.append(generate_llm_unavailable_claim(exc, len(claims) + 1))
    write_jsonl(claims_path, claims)
    markdown = render_markdown_report(
        metadata,
        enrichment_path,
        cases_path,
        claims_path,
        features_path,
        tool_evidence_path,
    )
    html = render_html_report(markdown)
    (layout.run_dir / spec.outputs["report_md"]).parent.mkdir(parents=True, exist_ok=True)
    (layout.run_dir / spec.outputs["report_md"]).write_text(markdown, encoding="utf-8")
    (layout.run_dir / spec.outputs["report_html"]).write_text(html, encoding="utf-8")
    write_stage_log(
        layout,
        "report",
        "\n".join(
            [
                "report stage completed",
                f"neighbor_enrichment: {enrichment_path}",
                f"cases: {cases_path}",
                f"features: {features_path}",
                f"tool_evidence: {tool_evidence_path}",
                f"num_claims: {len(claims)}",
                f"llm_warning: {llm_warning}",
                "",
            ]
        ),
    )
    write_stage_state(
        layout=layout,
        stage="report",
        started_at=started_at,
        inputs={
            "neighbor_enrichment": str(enrichment_path),
            "cases": str(cases_path),
            "features": str(features_path),
            "tool_evidence": str(tool_evidence_path),
        },
        outputs=spec.outputs,
        parameters={
            "neighbor_enrichment_override": str(neighbor_enrichment) if neighbor_enrichment is not None else None,
            "cases_override": str(cases) if cases is not None else None,
            "features_override": str(features) if features is not None else None,
            "tool_evidence_override": str(tool_evidence) if tool_evidence is not None else None,
            "llm_enabled": metadata.config.llm.enabled,
        },
    )


def _deterministic_claims(enrichment_path: Path, cases_path: Path, features_path: Path) -> list[dict]:
    enrichment_rows = read_tsv(enrichment_path)
    cases = read_jsonl(cases_path)
    features = read_jsonl(features_path)
    cases_by_family = {}
    for case in cases:
        cases_by_family.setdefault(case.get("neighbor_30_family", ""), []).append(case.get("case_id", ""))
    features_by_case = {}
    for feature in features:
        features_by_case.setdefault(feature.get("case_id", ""), []).append(feature)
    claims = []
    for index, row in enumerate(enrichment_rows[:20], start=1):
        family_id = row.get("neighbor_30_family", "")
        case_ids = cases_by_family.get(family_id, [])
        claims.append(
            {
                "claim_id": f"claim_{index:07d}",
                "claim_type": "statistical_observation",
                "neighbor_30_family": family_id,
                "statement": (
                    f"Neighbor family {family_id} is observed in {row.get('support_contexts', '0')} "
                    f"seed contexts with fold enrichment {row.get('fold_enrichment', '')} "
                    f"and q-value {row.get('q_value', '')}."
                ),
                "evidence": {
                    "enrichment_table": "stats/neighbor_enrichment.tsv",
                    "case_ids": case_ids[:10],
                },
                "confidence": "statistical_only",
            }
        )
    claim_index = len(claims) + 1
    for family_id, case_ids in sorted(cases_by_family.items()):
        family_features = [feature for case_id in case_ids for feature in features_by_case.get(case_id, [])]
        if not family_features:
            continue
        feature_counts: dict[str, int] = {}
        for feature in family_features:
            feature_type = feature.get("feature_type", "unknown")
            feature_counts[feature_type] = feature_counts.get(feature_type, 0) + 1
        summary = ", ".join(f"{feature_type}={count}" for feature_type, count in sorted(feature_counts.items()))
        claims.append(
            {
                "claim_id": f"claim_{claim_index:07d}",
                "claim_type": "case_sequence_feature_observation",
                "neighbor_30_family": family_id,
                "statement": f"Selected cases for neighbor family {family_id} contain local sequence features: {summary}.",
                "evidence": {
                    "features_table": "cases/features.jsonl",
                    "case_ids": case_ids[:10],
                    "feature_ids": [feature.get("feature_id", "") for feature in family_features[:20]],
                },
                "confidence": "sequence_feature_detected_not_mechanistic",
            }
        )
        claim_index += 1
    return claims

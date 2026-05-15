from __future__ import annotations

from pathlib import Path

from compass.artifacts.ids import make_evidence_id
from compass.artifacts.layout import RunLayout
from compass.artifacts.state import utc_now, write_stage_state
from compass.artifacts.writers import write_jsonl
from compass.config.loader import read_run_metadata
from compass.pipeline.stages.base import require_run, validate_stage_outputs, write_stage_log
from compass.pipeline.stages.specs import STAGE_SPECS
from compass.tools.case_tools.get_case import CaseArtifactStore
from compass.tools.case_tools.scan_case_features import FeatureScanRequest, scan_case_features


def run_inspect_cases_stage(run_dir: Path, cases: Path | None = None, force: bool = False) -> None:
    layout = RunLayout(run_dir)
    require_run(layout)
    spec = STAGE_SPECS["inspect-cases"]
    validate_stage_outputs(layout, spec, force=force)

    metadata = read_run_metadata(layout.run_yaml)
    started_at = utc_now()
    store = CaseArtifactStore.from_run_dir(layout.run_dir, cases_path=cases)
    all_features: list[dict] = []
    evidence_rows: list[dict] = []
    evidence_index = 1
    for case_id in store.list_case_ids():
        case_card = store.get_case_card(case_id)
        evidence_rows.append(
            {
                "evidence_id": make_evidence_id(metadata.run_name, evidence_index),
                "tool_id": "get_case",
                "case_id": case_id,
                "status": "ok",
                "summary": f"Validated case card for {case_id}",
                "payload": {
                    "locus_id": case_card["locus"]["locus_id"],
                    "neighbor_family_id": case_card["neighbor"]["neighbor_family_id"],
                },
            }
        )
        evidence_index += 1
        scan_result = scan_case_features(
            FeatureScanRequest(
                run_dir=layout.run_dir,
                case_id=case_id,
                feature_types=("direct_repeat", "inverted_repeat", "tandem_repeat", "low_complexity"),
                flank_bp=max(50, metadata.config.agent.scan_case_features_per_family * 200),
            )
        )
        all_features.extend(scan_result["features"])
        evidence_rows.append(
            {
                "evidence_id": make_evidence_id(metadata.run_name, evidence_index),
                "tool_id": "scan_case_features",
                "case_id": case_id,
                "status": "ok" if not scan_result["warnings"] else "warning",
                "summary": f"Scanned {case_id}; detected {len(scan_result['features'])} sequence features",
                "payload": {
                    "scan_id": scan_result["scan_id"],
                    "feature_ids": [feature["feature_id"] for feature in scan_result["features"]],
                    "warnings": scan_result["warnings"],
                    "scanned_region": scan_result["scanned_region"],
                },
            }
        )
        evidence_index += 1

    write_jsonl(layout.run_dir / spec.outputs["features"], all_features)
    write_jsonl(layout.run_dir / spec.outputs["tool_evidence"], evidence_rows)
    write_stage_log(
        layout,
        "inspect-cases",
        "\n".join(
            [
                "inspect-cases stage completed",
                f"cases: {cases or (layout.run_dir / STAGE_SPECS['select-cases'].outputs['cases'])}",
                f"num_cases: {len(store.list_case_ids())}",
                f"num_features: {len(all_features)}",
                f"num_tool_evidence: {len(evidence_rows)}",
                "",
            ]
        ),
    )
    write_stage_state(
        layout=layout,
        stage="inspect-cases",
        started_at=started_at,
        inputs={"cases": str(cases or (layout.run_dir / STAGE_SPECS["select-cases"].outputs["cases"]))},
        outputs=spec.outputs,
        parameters={
            "cases_override": str(cases) if cases is not None else None,
            "feature_types": ["direct_repeat", "inverted_repeat", "tandem_repeat", "low_complexity"],
        },
    )

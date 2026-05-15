from __future__ import annotations

from pathlib import Path

from compass.artifacts.layout import RunLayout
from compass.artifacts.state import utc_now, write_stage_state
from compass.pipeline.stages.specs import STAGE_SPECS, StageSpec


class StageError(RuntimeError):
    """Raised when a pipeline stage cannot run."""


def run_scaffold_stage(run_dir: Path, stage_name: str, force: bool = False) -> None:
    spec = STAGE_SPECS[stage_name]
    layout = RunLayout(run_dir)
    require_run(layout)
    validate_stage_inputs(layout, spec)
    validate_stage_outputs(layout, spec, force=force)

    started_at = utc_now()
    write_stage_log(layout, stage_name, "scaffold stage executed; biological implementation pending\n")
    _write_placeholder_outputs(layout, spec)
    write_stage_state(
        layout=layout,
        stage=stage_name,
        started_at=started_at,
        inputs=spec.inputs,
        outputs=spec.outputs,
        parameters={"stage": stage_name, "force": force, "implementation": "scaffold"},
        status="scaffold",
    )


def require_run(layout: RunLayout) -> None:
    if not layout.run_yaml.exists():
        raise StageError(f"Missing run metadata: {layout.run_yaml}. Run compass init-run first.")


def validate_stage_inputs(layout: RunLayout, spec: StageSpec) -> None:
    missing = [path for path in spec.inputs.values() if not (layout.run_dir / path).exists()]
    if missing:
        joined = ", ".join(missing)
        raise StageError(f"Stage {spec.name} missing required inputs: {joined}")


def validate_stage_outputs(layout: RunLayout, spec: StageSpec, force: bool) -> None:
    existing = [path for path in spec.outputs.values() if (layout.run_dir / path).exists()]
    if existing and not force:
        joined = ", ".join(existing)
        raise StageError(f"Stage {spec.name} outputs already exist: {joined}. Use --force to overwrite.")


def write_stage_log(layout: RunLayout, stage_name: str, message: str) -> None:
    layout.logs.mkdir(parents=True, exist_ok=True)
    (layout.logs / f"{stage_name}.log").write_text(message, encoding="utf-8")


def _write_placeholder_outputs(layout: RunLayout, spec: StageSpec) -> None:
    for output_name, relative_path in spec.outputs.items():
        path = layout.run_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".jsonl":
            path.write_text("", encoding="utf-8")
        elif path.suffix == ".html":
            path.write_text("<html><body><p>COMPASS scaffold output.</p></body></html>\n", encoding="utf-8")
        elif path.suffix == ".md":
            path.write_text("# COMPASS scaffold report\n\nBiological implementation pending.\n", encoding="utf-8")
        else:
            path.write_text(f"# scaffold output: {output_name}\n", encoding="utf-8")

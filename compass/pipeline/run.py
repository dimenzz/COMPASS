from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from compass.artifacts.layout import RunLayout
from compass.config.loader import load_config, write_run_metadata
from compass.config.schema import RunMetadata
from compass.pipeline.stages.base import run_scaffold_stage
from compass.pipeline.stages.cases import run_select_cases_stage
from compass.pipeline.stages.context import run_context_stage
from compass.pipeline.stages.enrichment import run_enrich_stage
from compass.pipeline.stages.expand import run_expand_stage
from compass.pipeline.stages.grouping import run_group_stage
from compass.pipeline.stages.inspection import run_inspect_cases_stage
from compass.pipeline.stages.report import run_report_stage
from compass.pipeline.stages.search import run_search_stage
from compass.pipeline.stages.specs import LINEAR_STAGES


T = TypeVar("T")
StageRunner = Callable[[str, Path, Callable[[], T]], T]


def init_run(
    seed: Path,
    name: str,
    config_path: Path | None,
    cli_overrides: dict,
    force: bool = False,
) -> RunLayout:
    config, loaded_files = load_config(config_path=config_path, cli_overrides=cli_overrides)
    layout = RunLayout(config.artifacts.output_root / name)
    if layout.run_yaml.exists() and not force:
        raise FileExistsError(f"Run already exists: {layout.run_dir}. Use --force to overwrite metadata.")
    layout.ensure()
    seed_destination = layout.inputs / "seed.faa"
    shutil.copyfile(seed, seed_destination)
    metadata = RunMetadata(
        run_name=name,
        seed_fasta=seed_destination,
        config_files=loaded_files,
        config=config,
    )
    write_run_metadata(layout.run_yaml, metadata)
    return layout


def run_all(
    seed: Path,
    name: str,
    config_path: Path | None,
    cli_overrides: dict,
    mmseqs_hits: Path | None = None,
    force: bool = False,
    stage_runner: StageRunner | None = None,
) -> RunLayout:
    layout = init_run(seed=seed, name=name, config_path=config_path, cli_overrides=cli_overrides, force=force)
    for stage in LINEAR_STAGES:
        if stage == "search":
            _run_stage(stage, layout.run_dir, stage_runner, lambda: run_search_stage(layout.run_dir, mmseqs_hits=mmseqs_hits, force=force))
        elif stage == "expand":
            _run_stage(stage, layout.run_dir, stage_runner, lambda: run_expand_stage(layout.run_dir, force=force))
        elif stage == "context":
            _run_stage(stage, layout.run_dir, stage_runner, lambda: run_context_stage(layout.run_dir, force=force))
        elif stage == "group":
            _run_stage(stage, layout.run_dir, stage_runner, lambda: run_group_stage(layout.run_dir, force=force))
        elif stage == "enrich":
            _run_stage(stage, layout.run_dir, stage_runner, lambda: run_enrich_stage(layout.run_dir, force=force))
        elif stage == "select-cases":
            _run_stage(stage, layout.run_dir, stage_runner, lambda: run_select_cases_stage(layout.run_dir, force=force))
        elif stage == "inspect-cases":
            _run_stage(stage, layout.run_dir, stage_runner, lambda: run_inspect_cases_stage(layout.run_dir, force=force))
        elif stage == "report":
            _run_stage(stage, layout.run_dir, stage_runner, lambda: run_report_stage(layout.run_dir, force=force))
        else:
            _run_stage(stage, layout.run_dir, stage_runner, lambda: run_scaffold_stage(layout.run_dir, stage, force=force))
    return layout


def _run_stage(stage_name: str, run_dir: Path, stage_runner: StageRunner | None, action: Callable[[], T]) -> T:
    if stage_runner is None:
        return action()
    return stage_runner(stage_name, run_dir, action)

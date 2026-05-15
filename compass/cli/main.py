from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from compass.cli.options import ConfigOption, ForceOption, RunOption, common_overrides
from compass.cli.progress import CliProgress
from compass.data.background import build_family30_background
from compass.pipeline.run import init_run, run_all
from compass.pipeline.stages.base import StageError, run_scaffold_stage
from compass.pipeline.stages.cases import run_select_cases_stage
from compass.pipeline.stages.context import run_context_stage
from compass.pipeline.stages.enrichment import run_enrich_stage
from compass.pipeline.stages.expand import run_expand_stage
from compass.pipeline.stages.grouping import run_group_stage
from compass.pipeline.stages.inspection import run_inspect_cases_stage
from compass.pipeline.stages.report import run_report_stage
from compass.pipeline.stages.search import run_search_stage

app = typer.Typer(help="COMPASS sequence-context discovery CLI.")
console = Console()
progress = CliProgress(console)


@app.command("build-background")
def build_background_command(
    clusters_db: Annotated[Path, typer.Option("--clusters-db", exists=True, readable=True, help="Cluster metadata SQLite database.")],
    output: Annotated[Path, typer.Option("--output", help="Output family30 background TSV.")],
    meta_output: Annotated[Path | None, typer.Option("--meta-output", help="Optional metadata JSON path.")] = None,
) -> None:
    try:
        metadata = progress.run_step(
            label=f"build family30 background clusters_db={clusters_db}",
            action=lambda: build_family30_background(clusters_db=clusters_db, output_path=output, meta_path=meta_output),
            log_path=meta_output or output.with_suffix(".meta.json"),
        )
    except (FileNotFoundError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(
        "Built family30 background: "
        f"{output} ({metadata['num_families']} families, "
        f"{metadata['num_total_90_representatives']} 90% representatives)"
    )


@app.command("init-run")
def init_run_command(
    seed: Annotated[Path, typer.Option("--seed", exists=True, readable=True, help="Seed protein FASTA.")],
    name: Annotated[str, typer.Option("--name", help="Run name.")],
    config: ConfigOption = None,
    output_root: Annotated[Path | None, typer.Option("--artifacts.output-root", "--output-root")] = None,
    family30_background: Annotated[Path | None, typer.Option("--database.family30-background", "--family30-background")] = None,
    llm_enabled: Annotated[bool | None, typer.Option("--llm.enabled", "--llm-enabled")] = None,
    llm_model: Annotated[str | None, typer.Option("--llm.model", "--llm-model")] = None,
    force: ForceOption = False,
) -> None:
    layout = init_run(
        seed=seed,
        name=name,
        config_path=config,
        cli_overrides=common_overrides(
            output_root=output_root,
            family30_background=family30_background,
            llm_enabled=llm_enabled,
            llm_model=llm_model,
        ),
        force=force,
    )
    console.print(f"Initialized run: {layout.run_dir}")


@app.command("run")
def run_command(
    seed: Annotated[Path, typer.Option("--seed", exists=True, readable=True, help="Seed protein FASTA.")],
    name: Annotated[str, typer.Option("--name", help="Run name.")],
    config: ConfigOption = None,
    mmseqs_hits: Annotated[Path | None, typer.Option("--mmseqs-hits", exists=True, readable=True)] = None,
    output_root: Annotated[Path | None, typer.Option("--artifacts.output-root", "--output-root")] = None,
    family30_background: Annotated[Path | None, typer.Option("--database.family30-background", "--family30-background")] = None,
    llm_enabled: Annotated[bool | None, typer.Option("--llm.enabled", "--llm-enabled")] = None,
    llm_model: Annotated[str | None, typer.Option("--llm.model", "--llm-model")] = None,
    force: ForceOption = False,
) -> None:
    layout = run_all(
        seed=seed,
        name=name,
        config_path=config,
        cli_overrides=common_overrides(
            output_root=output_root,
            family30_background=family30_background,
            llm_enabled=llm_enabled,
            llm_model=llm_model,
        ),
        mmseqs_hits=mmseqs_hits,
        force=force,
        stage_runner=progress.run_stage,
    )
    console.print(f"Completed run: {layout.run_dir}")


@app.command("search")
def search_command(
    run: RunOption,
    mmseqs_hits: Annotated[Path | None, typer.Option("--mmseqs-hits", exists=True, readable=True)] = None,
    force: ForceOption = False,
) -> None:
    try:
        progress.run_stage("search", run, lambda: run_search_stage(run, mmseqs_hits=mmseqs_hits, force=force))
    except (FileNotFoundError, StageError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("expand")
def expand_command(
    run: RunOption,
    direct_hits: Annotated[Path | None, typer.Option("--direct-hits", exists=True, readable=True)] = None,
    force: ForceOption = False,
) -> None:
    try:
        progress.run_stage("expand", run, lambda: run_expand_stage(run, direct_hits=direct_hits, force=force))
    except (FileNotFoundError, StageError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("context")
def context_command(
    run: RunOption,
    homologs: Annotated[Path | None, typer.Option("--homologs", exists=True, readable=True)] = None,
    force: ForceOption = False,
) -> None:
    try:
        progress.run_stage("context", run, lambda: run_context_stage(run, homologs=homologs, force=force))
    except (FileNotFoundError, StageError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("group")
def group_command(
    run: RunOption,
    homologs: Annotated[Path | None, typer.Option("--homologs", exists=True, readable=True)] = None,
    context_signatures: Annotated[Path | None, typer.Option("--context-signatures", exists=True, readable=True)] = None,
    protein_subgroups: Annotated[Path | None, typer.Option("--protein-subgroups", exists=True, readable=True)] = None,
    force: ForceOption = False,
) -> None:
    try:
        progress.run_stage(
            "group",
            run,
            lambda: run_group_stage(
                run,
                homologs=homologs,
                context_signatures=context_signatures,
                protein_subgroups=protein_subgroups,
                force=force,
            ),
        )
    except (FileNotFoundError, StageError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("enrich")
def enrich_command(
    run: RunOption,
    context_neighbors: Annotated[Path | None, typer.Option("--context-neighbors", exists=True, readable=True)] = None,
    homolog_groups: Annotated[Path | None, typer.Option("--homolog-groups", exists=True, readable=True)] = None,
    force: ForceOption = False,
) -> None:
    try:
        progress.run_stage(
            "enrich",
            run,
            lambda: run_enrich_stage(run, context_neighbors=context_neighbors, homolog_groups=homolog_groups, force=force),
        )
    except (FileNotFoundError, StageError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("select-cases")
def select_cases_command(
    run: RunOption,
    neighbor_enrichment: Annotated[Path | None, typer.Option("--neighbor-enrichment", exists=True, readable=True)] = None,
    context_neighbors: Annotated[Path | None, typer.Option("--context-neighbors", exists=True, readable=True)] = None,
    force: ForceOption = False,
) -> None:
    try:
        progress.run_stage(
            "select-cases",
            run,
            lambda: run_select_cases_stage(
                run,
                neighbor_enrichment=neighbor_enrichment,
                context_neighbors=context_neighbors,
                force=force,
            ),
        )
    except (FileNotFoundError, StageError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("report")
def report_command(
    run: RunOption,
    neighbor_enrichment: Annotated[Path | None, typer.Option("--neighbor-enrichment", exists=True, readable=True)] = None,
    cases: Annotated[Path | None, typer.Option("--cases", exists=True, readable=True)] = None,
    features: Annotated[Path | None, typer.Option("--features", exists=True, readable=True)] = None,
    tool_evidence: Annotated[Path | None, typer.Option("--tool-evidence", exists=True, readable=True)] = None,
    force: ForceOption = False,
) -> None:
    try:
        progress.run_stage(
            "report",
            run,
            lambda: run_report_stage(
                run,
                neighbor_enrichment=neighbor_enrichment,
                cases=cases,
                features=features,
                tool_evidence=tool_evidence,
                force=force,
            ),
        )
    except (FileNotFoundError, StageError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("inspect-cases")
def inspect_cases_command(
    run: RunOption,
    cases: Annotated[Path | None, typer.Option("--cases", exists=True, readable=True)] = None,
    force: ForceOption = False,
) -> None:
    try:
        progress.run_stage("inspect-cases", run, lambda: run_inspect_cases_stage(run, cases=cases, force=force))
    except (FileNotFoundError, StageError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc


def _stage_command(stage_name: str):
    def command(run: RunOption, force: ForceOption = False) -> None:
        try:
            run_scaffold_stage(run, stage_name, force=force)
        except StageError as exc:
            raise typer.BadParameter(str(exc)) from exc
        console.print(f"Completed scaffold stage {stage_name}: {run}")

    return command


def main() -> None:
    app()


if __name__ == "__main__":
    main()

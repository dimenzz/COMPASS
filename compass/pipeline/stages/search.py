from __future__ import annotations

from pathlib import Path

from compass.artifacts.layout import RunLayout
from compass.artifacts.state import utc_now, write_stage_state
from compass.artifacts.writers import write_tsv
from compass.config.loader import read_run_metadata
from compass.data.models import SearchHit
from compass.pipeline.stages.base import (
    require_run,
    validate_stage_outputs,
    write_stage_log,
)
from compass.pipeline.stages.specs import STAGE_SPECS
from compass.tools.bio_tools.mmseqs import copy_existing_hits, parse_hits, run_easy_search


DIRECT_HIT_FIELDS = ["query", "target", "pident", "alnlen", "evalue", "bits", "qcov", "tcov"]


def run_search_stage(run_dir: Path, mmseqs_hits: Path | None = None, force: bool = False) -> None:
    layout = RunLayout(run_dir)
    require_run(layout)
    spec = STAGE_SPECS["search"]
    validate_stage_outputs(layout, spec, force=force)

    metadata = read_run_metadata(layout.run_yaml)
    seed_fasta = layout.inputs / "seed.faa"
    if not seed_fasta.exists():
        raise FileNotFoundError(f"Missing seed FASTA: {seed_fasta}")

    started_at = utc_now()
    mmseqs_output = layout.run_dir / spec.outputs["mmseqs_hits"]
    direct_hits_output = layout.run_dir / spec.outputs["direct_90_hits"]

    if mmseqs_hits is None:
        run_easy_search(
            seed_fasta=seed_fasta,
            output_path=mmseqs_output,
            tmp_dir=layout.tmp / "mmseqs-search",
            config=metadata.config,
            tool_log_path=layout.logs / "search.mmseqs.log",
        )
        source = "mmseqs easy-search"
    else:
        if not mmseqs_hits.exists():
            raise FileNotFoundError(f"MMseqs hit override does not exist: {mmseqs_hits}")
        if mmseqs_hits.resolve() != mmseqs_output.resolve():
            copy_existing_hits(mmseqs_hits, mmseqs_output)
        source = str(mmseqs_hits)

    hits = parse_hits(mmseqs_output)
    write_tsv(direct_hits_output, [_hit_row(hit) for hit in hits], DIRECT_HIT_FIELDS)
    write_stage_log(
        layout,
        "search",
        "\n".join(
            [
                "search stage completed",
                f"source: {source}",
                f"seed_fasta: {seed_fasta}",
                f"mmseqs_hits: {mmseqs_output}",
                f"direct_90_hits: {direct_hits_output}",
                f"num_hits: {len(hits)}",
                "",
            ]
        ),
    )
    write_stage_state(
        layout=layout,
        stage="search",
        started_at=started_at,
        inputs={
            "seed": "inputs/seed.faa",
            "mmseqs_hits_override": str(mmseqs_hits) if mmseqs_hits is not None else "",
        },
        outputs=spec.outputs,
        parameters={
            "mmseqs_hits_override": str(mmseqs_hits) if mmseqs_hits is not None else None,
            "search": metadata.config.search.model_dump(mode="json"),
            "database": {"mmseqs_db": str(metadata.config.database.mmseqs_db)},
        },
    )


def _hit_row(hit: SearchHit) -> dict[str, object]:
    return {
        "query": hit.query,
        "target": hit.target,
        "pident": hit.pident,
        "alnlen": hit.alnlen,
        "evalue": hit.evalue,
        "bits": hit.bits,
        "qcov": hit.qcov,
        "tcov": hit.tcov,
    }

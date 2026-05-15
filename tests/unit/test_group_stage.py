from __future__ import annotations

from pathlib import Path

from compass.artifacts.readers import read_tsv
from compass.pipeline.stages.grouping import run_group_stage


def test_group_stage_writes_cluster30_subgroup_fallback(tmp_path: Path) -> None:
    run_dir = _prepare_group_run(tmp_path)

    run_group_stage(run_dir)

    rows = read_tsv(run_dir / "search" / "homolog_groups.tsv")
    assert rows[0]["protein_subgroup_id"] == "famA"
    assert rows[0]["primary_subgroup_method"] == "cluster30_id"
    assert rows[0]["sequence_community_id"] == ""
    assert rows[0]["domain_community_id"] == ""


def test_group_stage_accepts_external_protein_subgroups(tmp_path: Path) -> None:
    run_dir = _prepare_group_run(tmp_path)
    subgroups = tmp_path / "protein_subgroups.tsv"
    subgroups.write_text(
        "homolog_id\tprotein_subgroup_id\tprimary_subgroup_method\tsequence_community_id\tdomain_community_id\n"
        "h1\tseqcomm_1\tsequence_community_id\tseqcomm_1\t\n"
        "h2\tseqcomm_2\tsequence_community_id\tseqcomm_2\t\n",
        encoding="utf-8",
    )

    run_group_stage(run_dir, protein_subgroups=subgroups)

    rows = read_tsv(run_dir / "search" / "homolog_groups.tsv")
    assert [row["protein_subgroup_id"] for row in rows] == ["seqcomm_1", "seqcomm_2"]
    assert {row["primary_subgroup_method"] for row in rows} == {"sequence_community_id"}


def _prepare_group_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "runs" / "demo"
    (run_dir / "search").mkdir(parents=True)
    (run_dir / "context").mkdir()
    (run_dir / "run.yaml").write_text("run_name: demo\n", encoding="utf-8")
    (run_dir / "search" / "homolog_90_reps.tsv").write_text(
        "homolog_id\tprotein_id\tcluster90_id\tcluster30_id\tsequence_search_score_bin\tlength\tpfam\n"
        "h1\trepA\trepA\tfamA\tclose\t100\tPF1\n"
        "h2\trepB\trepB\tfamB\tremote\t120\tPF2\n",
        encoding="utf-8",
    )
    (run_dir / "context" / "context_signatures.tsv").write_text(
        "locus_id\thomolog_id\tneighbor_family_signature\n"
        "locus_1\th1\t1:famN\n"
        "locus_2\th2\t1:famM\n",
        encoding="utf-8",
    )
    return run_dir

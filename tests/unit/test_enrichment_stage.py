from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from compass.artifacts.readers import read_jsonl, read_tsv
from compass.cli.main import app
from compass.pipeline.stages.enrichment import run_enrich_stage


def test_build_background_command_writes_tsv_and_metadata(tmp_path: Path) -> None:
    clusters_db = tmp_path / "clusters.db"
    output = tmp_path / "family30_background.tsv"
    _write_clusters_db(clusters_db)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["build-background", "--clusters-db", str(clusters_db), "--output", str(output)],
    )

    assert result.exit_code == 0, result.output
    rows = read_tsv(output)
    assert rows == [
        {"family30_id": "famA", "num_90_representatives": "2"},
        {"family30_id": "famB", "num_90_representatives": "1"},
    ]
    metadata = json.loads((tmp_path / "family30_background.meta.json").read_text(encoding="utf-8"))
    assert metadata["cluster_level"] == "30"
    assert metadata["count_unit"] == "90_percent_representatives"
    assert metadata["num_families"] == 2
    assert metadata["num_total_90_representatives"] == 3


def test_enrich_stage_uses_background_cache_and_writes_subgroup_specificity(tmp_path: Path) -> None:
    run_dir = _prepare_enrich_run(tmp_path)

    run_enrich_stage(run_dir)

    global_rows = read_tsv(run_dir / "stats" / "neighbor_enrichment.tsv")
    subgroup_rows = read_tsv(run_dir / "stats" / "subgroup_neighbor_enrichment.tsv")
    alias_rows = read_tsv(run_dir / "stats" / "subfamily_neighbor_enrichment.tsv")
    top_hits = read_jsonl(run_dir / "stats" / "top_subgroup_neighbor_hits.jsonl")

    assert global_rows[0]["neighbor_30_family"] == "famN"
    fam_n_rows = [row for row in subgroup_rows if row["protein_subgroup_id"] == "seedFamA" and row["neighbor_30_family"] == "famN"]
    assert len(fam_n_rows) == 1
    assert fam_n_rows[0]["primary_subgroup_method"] == "cluster30_id"
    assert fam_n_rows[0]["k_in_subgroup"] == "2"
    assert fam_n_rows[0]["k_outside_subgroup"] == "0"
    assert fam_n_rows[0]["support_loci_examples"] == "locus_1;locus_2"
    assert alias_rows == subgroup_rows
    assert top_hits[0]["protein_subgroup_id"] == "seedFamA"
    assert top_hits[0]["top_neighbors"][0]["neighbor_30_family"] == "famN"


def test_enrich_stage_fails_fast_when_background_cache_is_missing(tmp_path: Path) -> None:
    run_dir = _prepare_enrich_run(tmp_path)
    (tmp_path / "family30_background.tsv").unlink()

    with pytest.raises(FileNotFoundError, match="Family30 background cache does not exist"):
        run_enrich_stage(run_dir)


def _prepare_enrich_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "runs" / "demo"
    (run_dir / "context").mkdir(parents=True)
    (run_dir / "search").mkdir()
    background = tmp_path / "family30_background.tsv"
    background.write_text(
        "family30_id\tnum_90_representatives\n"
        "famN\t2\n"
        "famM\t2\n"
        "famOther\t6\n",
        encoding="utf-8",
    )
    (run_dir / "run.yaml").write_text(
        f"""
run_name: demo
seed_fasta: {run_dir / "inputs" / "seed.faa"}
config_files: []
config:
  database:
    proteins_db: {tmp_path / "proteins.db"}
    clusters_db: {tmp_path / "clusters.db"}
    mmseqs_db: {tmp_path / "mmseqs_db"}
    family30_background: {background}
  context:
    upstream_genes: 10
    downstream_genes: 10
    max_distance_bp: 20000
  search:
    sensitivity: 5.7
    evalue: 0.001
    max_seqs: 300
  enrichment:
    q_value: 1.0
    fold_enrichment: 1.0
    support_contexts: 1
    observed_frequency: 0.01
    min_subgroup_size: 2
    min_subgroup_support_contexts: 1
    subgroup_specificity_q_value: 1.0
    subgroup_specificity_odds_ratio: 1.0
    max_subgroup_neighbors_for_report: 3
    enable_context_signature_enrichment: false
  agent:
    max_families_for_llm: 20
    cases_per_family: 10
    scan_case_features_per_family: 3
    max_revision_rounds: 1
  llm:
    enabled: false
    provider: openai
    model: gpt-4.1
    api_key_env: OPENAI_API_KEY
    temperature: 0.2
    max_output_tokens: 4096
    structured_outputs: true
  artifacts:
    output_root: {tmp_path / "runs"}
""",
        encoding="utf-8",
    )
    (run_dir / "search" / "homolog_groups.tsv").write_text(
        "homolog_id\tcluster30_id\n"
        "h1\tseedFamA\n"
        "h2\tseedFamA\n"
        "h3\tseedFamB\n"
        "h4\tseedFamB\n",
        encoding="utf-8",
    )
    (run_dir / "context" / "context_neighbors.tsv").write_text(
        "locus_id\thomolog_id\tneighbor_30_family\tproduct\n"
        "locus_1\th1\tfamN\tNAG-like protein\n"
        "locus_2\th2\tfamN\tNAG-like protein\n"
        "locus_3\th3\tfamM\tmobile element protein\n",
        encoding="utf-8",
    )
    return run_dir


def _write_clusters_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE clusters (representative_id TEXT, member_id TEXT, cluster_level TEXT, "
        "PRIMARY KEY(member_id, cluster_level))"
    )
    conn.executemany(
        "INSERT INTO clusters VALUES (?, ?, ?)",
        [
            ("famA", "repA", "30"),
            ("famA", "repB", "30"),
            ("famB", "repC", "30"),
            ("repA", "repA", "90"),
        ],
    )
    conn.commit()
    conn.close()

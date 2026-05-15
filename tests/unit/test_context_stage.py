from __future__ import annotations

import sqlite3
from pathlib import Path

from compass.pipeline.stages.context import run_context_stage


def test_context_stage_writes_loci_neighbors_and_signatures(tmp_path: Path) -> None:
    run_dir, homologs = _prepare_run(tmp_path)

    run_context_stage(run_dir, homologs=homologs)

    loci = (run_dir / "context" / "loci.tsv").read_text(encoding="utf-8")
    neighbors = (run_dir / "context" / "context_neighbors.tsv").read_text(encoding="utf-8")
    signatures = (run_dir / "context" / "context_signatures.tsv").read_text(encoding="utf-8")
    assert "locus_0000001\thomolog_0000001\trepA\trepA\tfamSeed" in loci
    assert "neighbor_0000001\tn1\trepN1\tfamNeighbor" in neighbors
    assert "1:famNeighbor" in signatures
    assert (run_dir / "state" / "context.done.json").exists()


def _prepare_run(tmp_path: Path) -> tuple[Path, Path]:
    clusters_db = tmp_path / "clusters.db"
    proteins_db = tmp_path / "proteins.db"
    _write_clusters_db(clusters_db)
    _write_proteins_db(proteins_db)
    run_dir = tmp_path / "runs" / "demo"
    (run_dir / "inputs").mkdir(parents=True)
    (run_dir / "context").mkdir()
    (run_dir / "search").mkdir()
    (run_dir / "run.yaml").write_text(
        f"""
run_name: demo
seed_fasta: {run_dir / "inputs" / "seed.faa"}
config_files: []
config:
  database:
    proteins_db: {proteins_db}
    clusters_db: {clusters_db}
    mmseqs_db: {tmp_path / "mmseqs_db"}
  context:
    upstream_genes: 1
    downstream_genes: 1
    max_distance_bp: 500
  search:
    sensitivity: 5.7
    evalue: 0.001
    max_seqs: 300
  enrichment:
    q_value: 0.05
    fold_enrichment: 5.0
    support_contexts: 5
    observed_frequency: 0.05
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
    homologs = tmp_path / "homologs.tsv"
    homologs.write_text(
        "homolog_id\tseed_id\tprotein_id\tcluster90_id\tcluster30_id\n"
        "homolog_0000001\tseedA\trepA\trepA\tfamSeed\n",
        encoding="utf-8",
    )
    return run_dir, homologs


def _write_clusters_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE clusters (representative_id TEXT, member_id TEXT, cluster_level TEXT, "
        "PRIMARY KEY(member_id, cluster_level))"
    )
    conn.executemany(
        "INSERT INTO clusters VALUES (?, ?, ?)",
        [
            ("repA", "repA", "90"),
            ("repN1", "n1", "90"),
            ("repN1", "repN1", "90"),
            ("famSeed", "repA", "30"),
            ("famNeighbor", "repN1", "30"),
        ],
    )
    conn.commit()
    conn.close()


def _write_proteins_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE proteins (
          protein_id TEXT PRIMARY KEY, contig_id TEXT, mag_id TEXT, start INTEGER, end INTEGER,
          strand TEXT, length INTEGER, product TEXT, gene_name TEXT, locus_tag TEXT, pfam TEXT,
          interpro TEXT, kegg TEXT, cog_category TEXT, cog_id TEXT, ec_number TEXT, eggnog TEXT
        )
        """
    )
    conn.execute("CREATE TABLE contigs (contig_id TEXT PRIMARY KEY, mag_id TEXT, length INTEGER, taxonomy TEXT, environment TEXT)")
    conn.executemany(
        "INSERT INTO proteins VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("repA", "contig1", "mag1", 100, 200, "+", 33, "seed protein", "", "", "PFseed", "", "", "", "", "", ""),
            ("n1", "contig1", "mag1", 250, 340, "+", 30, "neighbor protein", "", "", "PFn", "", "", "", "", "", ""),
            ("far", "contig1", "mag1", 5000, 5100, "+", 33, "far protein", "", "", "", "", "", "", "", "", ""),
        ],
    )
    conn.execute("INSERT INTO contigs VALUES (?, ?, ?, ?, ?)", ("contig1", "mag1", 6000, "Bacteria;Test", "soil"))
    conn.commit()
    conn.close()

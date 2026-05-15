from __future__ import annotations

import sqlite3
from pathlib import Path

from compass.data.repositories.clusters import ClusterRepository
from compass.pipeline.stages.expand import run_expand_stage


def test_cluster_repository_expands_30_family_to_90_reps(tmp_path: Path) -> None:
    clusters_db = tmp_path / "clusters.db"
    _write_clusters_db(clusters_db)

    with ClusterRepository(clusters_db) as repo:
        parents = repo.get_parent_30_families(["repA", "repC"])
        expanded = repo.expand_30_families_to_90_reps(["fam1"])

    assert parents == {"repA": "fam1", "repC": "fam2"}
    assert expanded == {"fam1": ["repA", "repB"]}


def test_expand_stage_writes_matched_families_and_homologs(tmp_path: Path) -> None:
    run_dir, direct_hits = _prepare_run(tmp_path)

    run_expand_stage(run_dir, direct_hits=direct_hits)

    matched = (run_dir / "search" / "matched_30_families.tsv").read_text(encoding="utf-8")
    homologs = (run_dir / "search" / "homolog_90_reps.tsv").read_text(encoding="utf-8")
    assert "fam1\t1\t2\tseedA\trepA" in matched
    assert "homolog_0000001\tseedA\trepA\trepA\tfam1\tdirect_90_hit" in homologs
    assert "homolog_0000002\tseedA\trepB\trepB\tfam1\tcluster30_expansion" in homologs
    assert (run_dir / "state" / "expand.done.json").exists()


def _prepare_run(tmp_path: Path) -> tuple[Path, Path]:
    clusters_db = tmp_path / "clusters.db"
    proteins_db = tmp_path / "proteins.db"
    _write_clusters_db(clusters_db)
    _write_proteins_db(proteins_db)

    run_dir = tmp_path / "runs" / "demo"
    (run_dir / "inputs").mkdir(parents=True)
    (run_dir / "search").mkdir()
    run_yaml = run_dir / "run.yaml"
    run_yaml.write_text(
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
    upstream_genes: 10
    downstream_genes: 10
    max_distance_bp: 20000
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
    direct_hits = tmp_path / "direct.tsv"
    direct_hits.write_text(
        "query\ttarget\tpident\talnlen\tevalue\tbits\tqcov\ttcov\n"
        "seedA\trepA\t42\t100\t1e-20\t90\t0.8\t0.9\n",
        encoding="utf-8",
    )
    return run_dir, direct_hits


def _write_clusters_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE clusters (representative_id TEXT, member_id TEXT, cluster_level TEXT, "
        "PRIMARY KEY(member_id, cluster_level))"
    )
    conn.executemany(
        "INSERT INTO clusters VALUES (?, ?, ?)",
        [("fam1", "repA", "30"), ("fam1", "repB", "30"), ("fam2", "repC", "30")],
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
            ("repA", "contig1", "mag1", 10, 300, "+", 96, "protein A", "", "", "PF1", "", "", "", "", "", ""),
            ("repB", "contig1", "mag1", 500, 900, "-", 133, "protein B", "", "", "PF2", "", "", "", "", "", ""),
        ],
    )
    conn.execute("INSERT INTO contigs VALUES (?, ?, ?, ?, ?)", ("contig1", "mag1", 1000, "Bacteria;Test", "soil"))
    conn.commit()
    conn.close()

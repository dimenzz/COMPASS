from __future__ import annotations

import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from compass.artifacts.readers import read_jsonl
from compass.cli.main import app


def test_v1_cli_run_generates_case_features_and_report_claims(tmp_path: Path) -> None:
    seed, hits, config, output_root = _write_smoke_inputs(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "run",
            "--seed",
            str(seed),
            "--name",
            "smoke",
            "--config",
            str(config),
            "--mmseqs-hits",
            str(hits),
        ],
    )

    assert result.exit_code == 0, result.output
    run_dir = output_root / "smoke"
    cases = read_jsonl(run_dir / "cases" / "cases.jsonl")
    features = read_jsonl(run_dir / "cases" / "features.jsonl")
    claims = read_jsonl(run_dir / "evidence" / "claims.jsonl")
    report = (run_dir / "report" / "report.md").read_text(encoding="utf-8")
    assert len(cases) == 1
    assert features
    assert any(feature["feature_type"] == "tandem_repeat" for feature in features)
    assert any(claim["claim_type"] == "case_sequence_feature_observation" for claim in claims)
    assert "Sequence features detected" in report


def _write_smoke_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    clusters_db = tmp_path / "clusters.db"
    proteins_db = tmp_path / "proteins.db"
    background = tmp_path / "family30_background.tsv"
    genome = tmp_path / "mag1.fna"
    genome_manifest = tmp_path / "genome_manifest.csv"
    seed = tmp_path / "seed.faa"
    hits = tmp_path / "hits.tsv"
    config = tmp_path / "config.yaml"
    output_root = tmp_path / "runs"

    _write_clusters_db(clusters_db)
    _write_proteins_db(proteins_db)
    background.write_text(
        "family30_id\tnum_90_representatives\nfamSeed\t1\nfamNeighbor\t1\n",
        encoding="utf-8",
    )
    sequence = "N" * 40 + "ATGATGATG" + "A" * 12 + "CGTACGTAGG" + "N" * 200
    genome.write_text(f">contig1\n{sequence}\n", encoding="utf-8")
    genome_manifest.write_text(f"mag1,{genome}\n", encoding="utf-8")
    seed.write_text(">seed\nMKK\n", encoding="utf-8")
    hits.write_text("seed\trepA\t45\t90\t1e-30\t100\t0.9\t0.9\n", encoding="utf-8")
    config.write_text(
        f"""
database:
  proteins_db: {proteins_db}
  clusters_db: {clusters_db}
  mmseqs_db: {tmp_path / "mmseqs_db"}
  family30_background: {background}
  genome_manifest: {genome_manifest}
  protein_manifest: {tmp_path / "protein_manifest.csv"}
enrichment:
  q_value: 1.0
  fold_enrichment: 1.0
  support_contexts: 1
  observed_frequency: 0.01
agent:
  scan_case_features_per_family: 1
artifacts:
  output_root: {output_root}
""",
        encoding="utf-8",
    )
    return seed, hits, config, output_root


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
            ("repN", "n1", "90"),
            ("repN", "repN", "90"),
            ("famSeed", "repA", "30"),
            ("famNeighbor", "repN", "30"),
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
            ("repA", "contig1", "mag1", 50, 70, "+", 7, "seed protein", "", "", "PFseed", "", "", "", "", "", ""),
            ("n1", "contig1", "mag1", 80, 90, "+", 4, "neighbor protein", "", "", "PFn", "", "", "", "", "", ""),
        ],
    )
    conn.execute("INSERT INTO contigs VALUES (?, ?, ?, ?, ?)", ("contig1", "mag1", 400, "Bacteria;Test", "soil"))
    conn.commit()
    conn.close()

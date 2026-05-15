from __future__ import annotations

from pathlib import Path
import sqlite3

from typer.testing import CliRunner

from compass.cli.main import app


def test_init_run_writes_run_yaml(tmp_path: Path) -> None:
    seed = tmp_path / "seed.faa"
    seed.write_text(">seed\nMKK\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "init-run",
            "--seed",
            str(seed),
            "--name",
            "demo",
            "--output-root",
            str(tmp_path / "runs"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "runs" / "demo" / "run.yaml").exists()
    assert (tmp_path / "runs" / "demo" / "inputs" / "seed.faa").exists()


def test_run_uses_real_search_and_expand_then_scaffold_remaining_stages(tmp_path: Path) -> None:
    seed = tmp_path / "seed.faa"
    seed.write_text(">seed\nMKK\n", encoding="utf-8")
    config = _write_cli_test_config(tmp_path)
    hits = tmp_path / "hits.tsv"
    hits.write_text("seed\trepA\t45\t90\t1e-30\t100\t0.9\t0.9\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "run",
            "--seed",
            str(seed),
            "--name",
            "demo",
            "--config",
            str(config),
            "--mmseqs-hits",
            str(hits),
            "--output-root",
            str(tmp_path / "runs"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "runs" / "demo" / "state" / "search.done.json").exists()
    assert (tmp_path / "runs" / "demo" / "state" / "expand.done.json").exists()
    assert (tmp_path / "runs" / "demo" / "state" / "context.done.json").exists()
    assert (tmp_path / "runs" / "demo" / "state" / "group.done.json").exists()
    assert (tmp_path / "runs" / "demo" / "state" / "enrich.done.json").exists()
    assert (tmp_path / "runs" / "demo" / "state" / "select-cases.done.json").exists()
    assert (tmp_path / "runs" / "demo" / "state" / "report.done.json").exists()
    assert (tmp_path / "runs" / "demo" / "search" / "direct_90_hits.tsv").exists()
    assert (tmp_path / "runs" / "demo" / "search" / "homolog_90_reps.tsv").exists()
    assert (tmp_path / "runs" / "demo" / "stats" / "neighbor_enrichment.tsv").exists()
    report = tmp_path / "runs" / "demo" / "report" / "report.md"
    assert "# COMPASS Discovery Report" in report.read_text(encoding="utf-8")


def test_search_command_accepts_existing_mmseqs_hits(tmp_path: Path) -> None:
    seed = tmp_path / "seed.faa"
    seed.write_text(">seed\nMKK\n", encoding="utf-8")
    hits = tmp_path / "hits.tsv"
    hits.write_text("seed\trepA\t45\t90\t1e-30\t100\t0.9\t0.9\n", encoding="utf-8")
    runner = CliRunner()
    init_result = runner.invoke(
        app,
        [
            "init-run",
            "--seed",
            str(seed),
            "--name",
            "demo",
            "--output-root",
            str(tmp_path / "runs"),
        ],
    )
    assert init_result.exit_code == 0, init_result.output

    result = runner.invoke(
        app,
        ["search", "--run", str(tmp_path / "runs" / "demo"), "--mmseqs-hits", str(hits)],
    )

    assert result.exit_code == 0, result.output
    assert "START stage search" in result.output
    assert "DONE stage search" in result.output
    direct_hits = tmp_path / "runs" / "demo" / "search" / "direct_90_hits.tsv"
    assert direct_hits.read_text(encoding="utf-8").splitlines()[0] == "query\ttarget\tpident\talnlen\tevalue\tbits\tqcov\ttcov"


def _write_cli_test_config(tmp_path: Path) -> Path:
    clusters_db = tmp_path / "clusters.db"
    proteins_db = tmp_path / "proteins.db"
    background = tmp_path / "family30_background.tsv"
    _write_clusters_db(clusters_db)
    _write_proteins_db(proteins_db)
    background.write_text("family30_id\tnum_90_representatives\nfam1\t2\n", encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.write_text(
        f"""
database:
  clusters_db: {clusters_db}
  proteins_db: {proteins_db}
  mmseqs_db: {tmp_path / "mmseqs_db"}
  family30_background: {background}
""",
        encoding="utf-8",
    )
    return config


def _write_clusters_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE clusters (representative_id TEXT, member_id TEXT, cluster_level TEXT, "
        "PRIMARY KEY(member_id, cluster_level))"
    )
    conn.executemany("INSERT INTO clusters VALUES (?, ?, ?)", [("fam1", "repA", "30"), ("fam1", "repB", "30")])
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

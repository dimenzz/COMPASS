from __future__ import annotations

from pathlib import Path

import pytest

from compass.artifacts.ids import parse_case_id
from compass.pipeline.stages.inspection import run_inspect_cases_stage
from compass.tools.case_tools.get_case import CaseToolError, GetCaseRequest, get_case
from compass.tools.case_tools.scan_case_features import FeatureScanRequest, scan_case_features


def test_parse_case_id_rejects_wrong_type() -> None:
    with pytest.raises(ValueError, match="Expected case_id"):
        parse_case_id("cmp:demo:family30:abc")


def test_get_case_validates_run_id_and_returns_case_card(tmp_path: Path) -> None:
    run_dir = _write_case_run(tmp_path)

    card = get_case(GetCaseRequest(run_dir=run_dir, case_id="cmp:demo:case:0000001"))

    assert card["case_id"] == "cmp:demo:case:0000001"
    assert card["seed_homolog"]["protein_id"] == "seedA"
    assert card["neighbor"]["neighbor_family_id"] == "famN"
    assert card["locus"]["mag_id"] == "mag1"

    with pytest.raises(CaseToolError, match="belongs to run other"):
        get_case(GetCaseRequest(run_dir=run_dir, case_id="cmp:other:case:0000001"))


def test_scan_case_features_reads_genome_manifest_and_detects_features(tmp_path: Path) -> None:
    run_dir = _write_case_run(tmp_path, with_genome=True)

    result = scan_case_features(
        FeatureScanRequest(
            run_dir=run_dir,
            case_id="cmp:demo:case:0000001",
            feature_types=("tandem_repeat", "low_complexity"),
            flank_bp=50,
        )
    )

    assert result["warnings"] == []
    feature_types = {feature["feature_type"] for feature in result["features"]}
    assert "tandem_repeat" in feature_types
    assert "low_complexity" in feature_types
    assert all(feature["feature_id"].startswith("cmp:demo:feature:") for feature in result["features"])


def test_inspect_cases_stage_writes_features_and_tool_evidence(tmp_path: Path) -> None:
    run_dir = _write_case_run(tmp_path, with_genome=True)

    run_inspect_cases_stage(run_dir)

    features = (run_dir / "cases" / "features.jsonl").read_text(encoding="utf-8")
    evidence = (run_dir / "evidence" / "tool_evidence.jsonl").read_text(encoding="utf-8")
    assert "tandem_repeat" in features
    assert "scan_case_features" in evidence
    assert (run_dir / "state" / "inspect-cases.done.json").exists()


def _write_case_run(tmp_path: Path, with_genome: bool = False) -> Path:
    run_dir = tmp_path / "runs" / "demo"
    for relative in ("cases", "context", "evidence", "inputs", "logs", "state"):
        (run_dir / relative).mkdir(parents=True, exist_ok=True)
    manifest_path = tmp_path / "genome_manifest.csv"
    if with_genome:
        genome_path = tmp_path / "mag1.fna"
        sequence = "N" * 40 + "ATGATGATG" + "A" * 10 + "CGTACGTAGG" + "N" * 200
        genome_path.write_text(f">contig1\n{sequence}\n", encoding="utf-8")
        manifest_path.write_text(f"mag1,{genome_path}\n", encoding="utf-8")
    else:
        manifest_path.write_text("", encoding="utf-8")
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
    genome_manifest: {manifest_path}
    protein_manifest: {tmp_path / "protein_manifest.csv"}
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
    scan_case_features_per_family: 1
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
    (run_dir / "cases" / "cases.jsonl").write_text(
        """
{"annotation_payload":{"product":"neighbor protein","pfam":"PFN"},"case_id":"cmp:demo:case:0000001","contig_id":"contig1","coordinates":{"neighbor_end":90,"neighbor_start":80,"neighbor_strand":"+"},"distance_bp":10,"homolog_id":"homolog_0000001","locus_id":"locus_0000001","neighbor_30_family":"famN","neighbor_instance_id":"neighbor_0000001","neighbor_protein_id":"neighborA","relative_gene_index":1,"seed_protein_id":"seedA"}
""".lstrip(),
        encoding="utf-8",
    )
    (run_dir / "cases" / "locus_diagrams.jsonl").write_text(
        """
{"case_id":"cmp:demo:case:0000001","locus_id":"locus_0000001","text_diagram":"seedA -- neighborA"}
""".lstrip(),
        encoding="utf-8",
    )
    (run_dir / "context" / "loci.tsv").write_text(
        "locus_id\thomolog_id\tseed_protein_id\tcluster90_id\tcluster30_id\tcontig_id\tmag_id\tstart\tend\tstrand\ttaxonomy\tenvironment\tupstream_neighbor_count\tdownstream_neighbor_count\tneighbor_count\n"
        "locus_0000001\thomolog_0000001\tseedA\tseedA\tfamSeed\tcontig1\tmag1\t50\t70\t+\tBacteria\tsoil\t0\t1\t1\n",
        encoding="utf-8",
    )
    (run_dir / "context" / "context_neighbors.tsv").write_text(
        "locus_id\thomolog_id\tseed_protein_id\tseed_30_family\tneighbor_instance_id\tneighbor_protein_id\tneighbor_90_rep\tneighbor_30_family\trelative_gene_index\tdistance_bp\tsame_strand\torientation_pattern\tcontig_id\tstart\tend\tstrand\tproduct\tpfam\tinterpro\tkegg\tcog_id\teggnog\n"
        "locus_0000001\thomolog_0000001\tseedA\tfamSeed\tneighbor_0000001\tneighborA\tneighborA\tfamN\t1\t10\tTrue\tdownstream_same\tcontig1\t80\t90\t+\tneighbor protein\tPFN\t\t\t\t\n",
        encoding="utf-8",
    )
    return run_dir

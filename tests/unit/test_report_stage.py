from __future__ import annotations

from pathlib import Path

from compass.artifacts.readers import read_jsonl
from compass.pipeline.stages.report import run_report_stage


def test_report_stage_includes_case_features_and_tool_warnings(tmp_path: Path) -> None:
    run_dir = _write_report_run(tmp_path)

    run_report_stage(run_dir)

    report = (run_dir / "report" / "report.md").read_text(encoding="utf-8")
    claims = read_jsonl(run_dir / "evidence" / "claims.jsonl")
    assert "Sequence features detected: tandem_repeat=1" in report
    assert "Tool Warnings" in report
    assert any(claim["claim_type"] == "case_sequence_feature_observation" for claim in claims)
    feature_claim = [claim for claim in claims if claim["claim_type"] == "case_sequence_feature_observation"][0]
    assert feature_claim["evidence"]["feature_ids"] == ["cmp:demo:feature:0000001"]


def test_report_stage_records_llm_unavailable_when_enabled_without_key(tmp_path: Path, monkeypatch) -> None:
    run_dir = _write_report_run(tmp_path, llm_enabled=True)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    run_report_stage(run_dir)

    claims = read_jsonl(run_dir / "evidence" / "claims.jsonl")
    assert any(claim["claim_type"] == "llm_unavailable" for claim in claims)


def _write_report_run(tmp_path: Path, llm_enabled: bool = False) -> Path:
    run_dir = tmp_path / "runs" / "demo"
    for relative in ("cases", "evidence", "inputs", "logs", "report", "state", "stats"):
        (run_dir / relative).mkdir(parents=True, exist_ok=True)
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
    genome_manifest: {tmp_path / "genome_manifest.csv"}
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
    enabled: {str(llm_enabled).lower()}
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
    (run_dir / "stats" / "neighbor_enrichment.tsv").write_text(
        "neighbor_30_family\tk_contexts_with_family\tn_total_contexts\tK_family_90_rep_count\tN_total_90_rep_count\tobserved_frequency\tbackground_frequency\tfold_enrichment\tp_value\tq_value\tsupport_contexts\tsupport_loci_examples\tannotation_summary\n"
        "famN\t5\t10\t2\t1000\t0.5\t0.002\t250\t1e-10\t1e-8\t5\tlocus_0000001\tneighbor protein\n",
        encoding="utf-8",
    )
    (run_dir / "cases" / "cases.jsonl").write_text(
        """
{"annotation_payload":{"product":"neighbor protein"},"case_id":"cmp:demo:case:0000001","contig_id":"contig1","coordinates":{"neighbor_end":90,"neighbor_start":80,"neighbor_strand":"+"},"distance_bp":10,"homolog_id":"homolog_0000001","locus_id":"locus_0000001","neighbor_30_family":"famN","neighbor_instance_id":"neighbor_0000001","neighbor_protein_id":"neighborA","relative_gene_index":1,"seed_protein_id":"seedA"}
""".lstrip(),
        encoding="utf-8",
    )
    (run_dir / "cases" / "features.jsonl").write_text(
        """
{"case_id":"cmp:demo:case:0000001","caller":"scan_case_features","contig_id":"contig1","end":70,"feature_id":"cmp:demo:feature:0000001","feature_type":"tandem_repeat","parameters":{},"score":3,"sequence":"ATGATGATG","start":62,"strand":".","summary":"Tandem repeat unit ATG with 3 copies"}
""".lstrip(),
        encoding="utf-8",
    )
    (run_dir / "evidence" / "tool_evidence.jsonl").write_text(
        """
{"case_id":"cmp:demo:case:0000001","evidence_id":"cmp:demo:evidence:0000001","payload":{"warnings":["example warning"],"feature_ids":["cmp:demo:feature:0000001"]},"status":"warning","summary":"Scanned case","tool_id":"scan_case_features"}
""".lstrip(),
        encoding="utf-8",
    )
    return run_dir

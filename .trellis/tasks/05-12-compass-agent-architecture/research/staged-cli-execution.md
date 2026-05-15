# Staged CLI Execution

## Decision

COMPASS should support both full workflow execution and individual stage execution. Every stage reads durable artifacts from previous stages and writes its own artifacts, state, and logs.

## CLI Commands

```bash
compass init-run --seed seed.faa --name demo --config configs/default.yaml

compass search --run runs/demo
compass expand --run runs/demo
compass context --run runs/demo
compass group --run runs/demo
compass enrich --run runs/demo
compass select-cases --run runs/demo
compass inspect-cases --run runs/demo
compass report --run runs/demo

compass run --seed seed.faa --name demo --config configs/default.yaml
```

`compass run` is a convenience command equivalent to:

```text
init-run -> search -> expand -> context -> group -> enrich -> select-cases -> inspect-cases -> report
```

## Stage Contract

Each stage must:

1. Read `runs/{run_name}/run.yaml`.
2. Validate required input artifacts.
3. Refuse to overwrite existing outputs unless `--force` is passed.
4. Write output artifacts atomically where practical.
5. Write a log file under `logs/`.
6. Write a state file under `state/`.

## State Files

Each completed stage writes:

```text
runs/{run_name}/state/{stage}.done.json
```

Example:

```json
{
  "stage": "context",
  "started_at": "2026-05-13T00:00:00Z",
  "finished_at": "2026-05-13T00:12:00Z",
  "inputs": {
    "homolog_90_reps": "search/homolog_90_reps.tsv"
  },
  "outputs": {
    "loci": "context/loci.tsv",
    "neighbors": "context/context_neighbors.tsv"
  },
  "parameters_hash": "sha256:...",
  "software": {
    "compass": "0.1.0"
  }
}
```

## Stage Inputs and Outputs

```text
init-run
  input: seed.faa, config
  output: run.yaml, inputs/seed.faa

search
  input: inputs/seed.faa, run.yaml
  output: search/mmseqs_hits.tsv, search/direct_90_hits.tsv

expand
  input: search/direct_90_hits.tsv
  output: search/matched_30_families.tsv, search/homolog_90_reps.tsv

context
  input: search/homolog_90_reps.tsv
  output: context/loci.tsv, context/context_neighbors.tsv, context/context_signatures.tsv

group
  input: search/homolog_90_reps.tsv, context/context_signatures.tsv
  output: search/homolog_groups.tsv, context/context_signature_clusters.tsv

enrich
  input: context/context_neighbors.tsv, search/homolog_groups.tsv
  output: stats/family_background.tsv, stats/neighbor_enrichment.tsv, stats/subfamily_neighbor_enrichment.tsv

select-cases
  input: stats/neighbor_enrichment.tsv, context/context_neighbors.tsv
  output: cases/enriched_families.jsonl, cases/cases.jsonl, cases/locus_diagrams.jsonl

inspect-cases
  input: cases/cases.jsonl
  output: cases/features.jsonl, evidence/tool_evidence.jsonl

report
  input: all previous artifacts
  output: evidence/claims.jsonl, report/report.md, report/report.html
```

## Override Inputs

Stages should support explicit input override flags for debugging and reuse:

```bash
compass search --run runs/demo --mmseqs-hits existing_hits.tsv
compass expand --run runs/demo --direct-hits custom_direct_90_hits.tsv
compass context --run runs/demo --homologs custom_homolog_90_reps.tsv
```

## Future Dynamic Agent Use

The staged design lets a future dynamic agent resume from any checkpoint, inspect which artifacts exist, and choose the next evidence-gathering action without rerunning the whole pipeline.

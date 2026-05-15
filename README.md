# COMPASS

COMPASS is a sequence-context discovery workflow for mining candidate microbial gene function systems from large genome collections. It starts from seed protein FASTA sequences, searches dereplicated protein representatives, expands hits through broad protein families, extracts genomic neighborhoods, scores co-localized neighbor families, inspects representative cases, and writes an auditable report.

V1 is intentionally conservative:

- sequence search is required; structure search is reserved for future Foldseek/DALI adapters;
- direct hits are searched against 90% cluster representatives;
- matched 30% families are expanded to all contained 90% representatives;
- enrichment combines all homolog contexts and uses 30% family abundance over 90% representatives as background;
- LLM inference is optional and never required for deterministic pipeline stages.

## Installation

Create and activate the conda environment:

```bash
conda env create -f environment.yml
conda activate compass
```

The environment installs the package in editable mode and provides the `compass` console command.

Verify the install:

```bash
compass --help
pytest -q
```

## Required Data

The default configuration expects these local resources:

- protein metadata SQLite: `/mnt/nfs/share/MGnify/all_data/proteins.db`
- cluster metadata SQLite: `/mnt/nfs/share/MGnify/all_data/clusters.db`
- precomputed 30% family background TSV: `/mnt/nfs/share/MGnify/all_data/family30_background.tsv`
- MMseqs 90% representative database: `/mnt/nfs/share/MGnify/all_data/mmseqs_db/cluster_90/all_proteins_90`
- genome FASTA manifest: `data/data_manifests/genome_manifest.csv`
- protein FASTA manifest: `data/data_manifests/protein_manifest.csv`

Protein IDs are expected to follow the project convention:

```text
{genome_id}_{contig_order}_{start}_{end}_{strand}
```

Build the background cache once per cluster database:

```bash
compass build-background \
  --clusters-db /mnt/nfs/share/MGnify/all_data/clusters.db \
  --output /mnt/nfs/share/MGnify/all_data/family30_background.tsv
```

This writes `family30_id` and `num_90_representatives` plus a sidecar metadata JSON. The `enrich` stage reads this cache and fails fast if it is missing.

## Configuration

Configuration precedence is:

```text
code defaults < configs/default.yaml < --config user.yaml < explicit CLI flags
```

The default config is [configs/default.yaml](configs/default.yaml). A minimal override file usually only needs database paths, thresholds, or output root:

```yaml
database:
  proteins_db: /path/to/proteins.db
  clusters_db: /path/to/clusters.db
  mmseqs_db: /path/to/mmseqs/cluster_90/all_proteins_90
  family30_background: /path/to/family30_background.tsv
  genome_manifest: data/data_manifests/genome_manifest.csv

artifacts:
  output_root: runs
```

## Full Workflow

Run the full v1 workflow:

```bash
compass run \
  --seed seed.faa \
  --name demo \
  --config configs/default.yaml \
  --family30-background /mnt/nfs/share/MGnify/all_data/family30_background.tsv
```

For testing or resuming from an existing MMseqs hit table:

```bash
compass run \
  --seed seed.faa \
  --name demo \
  --config configs/default.yaml \
  --mmseqs-hits existing_hits.tsv
```

The MMseqs hit table should contain these columns, either with or without a header:

```text
query target pident alnlen evalue bits qcov tcov
```

## Staged Execution

Every stage reads durable artifacts from the previous stage and writes its own outputs, log, and state file. Existing outputs are not overwritten unless `--force` is passed.
CLI commands print `START`, `DONE`, `FAILED`, elapsed time, and the stage log path. External tool output, including MMseqs stdout/stderr, is redirected into run-local log files instead of being streamed to the terminal.

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
```

Useful override inputs:

```bash
compass search --run runs/demo --mmseqs-hits existing_hits.tsv
compass expand --run runs/demo --direct-hits custom_direct_90_hits.tsv
compass context --run runs/demo --homologs custom_homolog_90_reps.tsv
compass group --run runs/demo --protein-subgroups custom_protein_subgroups.tsv
compass report --run runs/demo --features cases/features.jsonl --tool-evidence evidence/tool_evidence.jsonl
```

## Run Artifacts

A run writes:

```text
runs/{run_name}/
  run.yaml
  inputs/seed.faa
  logs/{stage}.log
  state/{stage}.done.json
  search/mmseqs_hits.tsv
  search/direct_90_hits.tsv
  search/matched_30_families.tsv
  search/homolog_90_reps.tsv
  search/homolog_groups.tsv
  context/loci.tsv
  context/context_neighbors.tsv
  context/context_signatures.tsv
  context/context_signature_clusters.tsv
  stats/family_background.tsv
  stats/neighbor_enrichment.tsv
  stats/subgroup_neighbor_enrichment.tsv
  stats/subfamily_neighbor_enrichment.tsv
  stats/top_subgroup_neighbor_hits.jsonl
  cases/enriched_families.jsonl
  cases/cases.jsonl
  cases/locus_diagrams.jsonl
  cases/features.jsonl
  evidence/tool_evidence.jsonl
  evidence/claims.jsonl
  report/report.md
  report/report.html
```

`subgroup_neighbor_enrichment.tsv` reports neighbor families specifically enriched within protein subgroups using Fisher exact tests. Until sequence-community subgrouping is implemented, v1.1 falls back to `cluster30_id` as the protein subgroup. `subfamily_neighbor_enrichment.tsv` is currently written as a compatibility alias of the subgroup table.

An optional protein subgroup table can be supplied to `compass group` with columns:

```text
homolog_id protein_subgroup_id primary_subgroup_method sequence_community_id domain_community_id
```

If `protein_subgroup_id` is absent for a homolog, `group` falls back to `cluster30_id`. This keeps context-derived signatures available as a descriptive artifact while preventing context pattern from defining the default protein subgroup used by enrichment.

## LLM Mode

Deterministic stages run without API credentials. To enable optional LLM hypothesis generation in the report stage:

```yaml
llm:
  enabled: true
  provider: openai
  model: gpt-4.1
  api_key_env: OPENAI_API_KEY
```

Then set the configured environment variable before running `compass report` or `compass run`:

```bash
export OPENAI_API_KEY=...
```

If `llm.enabled: true` but the API key or optional LLM dependencies are unavailable, COMPASS records an `llm_unavailable` claim instead of silently inventing a hypothesis.

## Case Tools

V1 exposes typed case-level tools for agent use:

- `get_case`: validates a run-scoped `case_id` and returns seed, neighbor, locus, annotations, and locus diagram payloads.
- `scan_case_features`: validates `case_id`, extracts the configured genome FASTA window, and scans simple direct repeats, inverted repeats, tandem repeats, and low-complexity regions.

Agents should pass typed IDs such as:

```text
cmp:demo:case:0000001
```

They should not pass raw protein IDs, contig IDs, coordinates, or 30% family IDs to case-level tools.

## Development Checks

Use the conda environment for validation:

```bash
conda run -n compass pytest -q
conda run -n compass python -m compileall -q compass
conda run -n compass compass --help
```

The integration smoke test builds a temporary SQLite/MMseqs-hit/genome-manifest fixture and verifies the complete v1 path through report generation.

## V1 Limitations

- Structure search is not implemented yet.
- Repeat and motif scanning is intentionally simple and should be treated as preliminary evidence.
- LLM output is hypothesis text over existing evidence, not an independent source of truth.
- Literature retrieval and dynamic autonomous planning are reserved for later versions.

# Run Artifact Schema

## Decision

Each COMPASS v1 run should write a checkpointed artifact directory. LLM tools should read these artifacts through a typed gateway instead of querying raw databases directly.

## Directory Layout

```text
runs/{run_name}/
  run.yaml
  inputs/
    seed.faa
  search/
    mmseqs_hits.tsv
    direct_90_hits.tsv
    matched_30_families.tsv
    homolog_90_reps.tsv
    homolog_groups.tsv
  context/
    loci.tsv
    context_neighbors.tsv
    context_signatures.tsv
    context_signature_clusters.tsv
  stats/
    family_background.tsv
    neighbor_enrichment.tsv
    subfamily_neighbor_enrichment.tsv
  cases/
    enriched_families.jsonl
    cases.jsonl
    locus_diagrams.jsonl
    features.jsonl
  evidence/
    literature_evidence.jsonl
    tool_evidence.jsonl
    claims.jsonl
  report/
    report.md
    report.html
```

## Core Artifacts

### `run.yaml`

Run parameters, database paths, command versions, timestamps, and checksums.

### `search/homolog_90_reps.tsv`

All final seed homolog candidates after mapping direct 90% hits to 30% clusters and expanding to all 90% representatives in those clusters.

Suggested columns:

```text
homolog_id
seed_id
protein_id
cluster90_id
cluster30_id
source_direct_hit_id
contig_id
mag_id
start
end
strand
taxonomy
environment
```

### `context/context_neighbors.tsv`

One row per neighbor protein in a homolog context window.

Suggested columns:

```text
locus_id
homolog_id
seed_protein_id
neighbor_instance_id
neighbor_protein_id
neighbor_90_rep
neighbor_30_family
relative_gene_index
distance_bp
same_strand
orientation_pattern
product
pfam
interpro
kegg
cog_id
eggnog
```

### `search/homolog_groups.tsv`

Lightweight homolog grouping table.

Suggested columns:

```text
homolog_id
protein_id
cluster90_id
cluster30_id
sequence_search_score_bin
length
length_ratio_to_seed
length_bin
domain_architecture
context_signature_cluster
```

### `stats/family_background.tsv`

Global 30% family abundance over 90% representatives.

Suggested columns:

```text
family30_id
family30_representative_id
num_90_representatives
annotation_summary
```

### `stats/subfamily_neighbor_enrichment.tsv`

Exploratory enrichment table for subgroup-specific neighbor patterns.

Suggested columns:

```text
grouping_feature
group_id
neighbor_30_family
k_contexts_with_family
n_group_contexts
K_family_90_rep_count
N_total_90_rep_count
fold_enrichment
p_value
q_value
support_contexts
```

### `stats/neighbor_enrichment.tsv`

Main enrichment result table.

Suggested columns:

```text
neighbor_30_family
k_contexts_with_family
n_total_contexts
K_family_90_rep_count
N_total_90_rep_count
observed_frequency
background_frequency
fold_enrichment
p_value
q_value
support_contexts
support_loci_examples
annotation_summary
```

### `cases/cases.jsonl`

LLM case-access object table. Each row binds one enriched neighbor instance to one seed homolog locus.

Must include:

```text
case_id
locus_id
homolog_id
neighbor_instance_id
neighbor_30_family
seed_protein_id
neighbor_protein_id
contig_id
coordinates
relative_gene_index
distance_bp
annotation_payload
```

### `cases/features.jsonl`

Structured output from tools such as `scan_case_features`.

Must include:

```text
feature_id
case_id
feature_type
contig_id
start
end
strand
score
sequence
summary
caller
parameters
```

## Tool Access Rule

LLM tools should access run artifacts through typed object IDs and a gateway. They should not directly query `/mnt/nfs/share/MGnify/all_data/proteins.db` or parse raw identifiers to infer coordinates.

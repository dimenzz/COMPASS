# Homolog Grouping Strategy

## Decision

V1 should include lightweight homolog grouping. Heavy embedding-, structure-, and phylogeny-based clustering should be deferred to later versions, but schemas should leave room for them.

## Why This Belongs in V1

Novel system discovery often depends on subfamily-specific context:

* a neighbor family may be enriched only around long seed homologs;
* a repeat/array feature may appear only in one domain-architecture subgroup;
* a remote homolog subgroup may have a unique genomic context that is diluted in global statistics.

This is central to Pro-CRISPR/NAG-Cas9-like and TIGR-Tas-like discovery.

## V1 Grouping Features

### `cluster30_id`

Broad family grouping from the existing 30% clustering.

### `sequence_search_score_bin`

Derived from direct MMseqs hit statistics where available:

* `close`
* `medium`
* `remote`
* `expanded_only`

For representatives collected only through 30% expansion, use `expanded_only` unless additional search/profile evidence is available.

### `length_bin`

Based on seed length ratio or absolute length:

* `short`
* `normal`
* `long`

Suggested seed-ratio thresholds:

* `<0.7x`: short
* `0.7-1.3x`: normal
* `>1.3x`: long

### `domain_architecture`

Simplified Pfam/InterPro signature:

```text
PFxxxxx+PFyyyyy
IPRxxxxx+IPRyyyyy
no_domain
hypothetical
```

### `context_signature_cluster`

A lightweight grouping based on neighbor 30% family presence/absence and optionally ordered gene-neighborhood patterns.

V1 can start with exact/similarity grouping over `ordered_neighbor_30_families`.

## V1 Artifacts

Add:

```text
search/homolog_groups.tsv
context/context_signature_clusters.tsv
stats/subfamily_neighbor_enrichment.tsv
```

`homolog_groups.tsv` suggested columns:

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

`subfamily_neighbor_enrichment.tsv` suggested columns:

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

## Ranking Policy

V1 primary ranking remains global combined neighbor enrichment.

Subfamily enrichment is exploratory and should be used to highlight patterns like:

* "Neighbor family X is weak globally but strongly enriched in long seed homologs."
* "Neighbor family Y is specific to one domain-architecture subgroup."
* "A repeat/array signal appears only in context-signature cluster 3."

## Deferred

Later versions should add:

* ESM embedding and Leiden/HDBSCAN clustering;
* structure-based clustering;
* profile/HMM evidence bins;
* phylogenetic tree construction;
* domain-interval seed handling.

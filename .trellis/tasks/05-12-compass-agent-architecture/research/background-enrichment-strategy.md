# Background Enrichment Strategy

## Decision

V1 should use the existing two-level clustering hierarchy as the primary enrichment background:

* Treat each 30% cluster as a broad protein family.
* Treat 90% representatives as de-redundant observations within each family.
* Use the number of 90% representatives in a 30% cluster as that family's global background abundance.

## Interpretation

For a candidate neighbor family:

* Observed signal: how often that neighbor's 30% family appears in genomic contexts around the collected seed homolog 90% representatives.
* Background abundance: how many 90% representatives belong to that neighbor's 30% family across the database.

This asks whether a neighbor protein family is over-represented near seed homologs compared with how common that family is in the de-redundant protein universe.

## Recommended Statistic

Use 30% family-level counts for enrichment:

* `N`: total number of 90% representatives in the searchable/de-redundant protein universe.
* `K`: number of 90% representatives in the neighbor's 30% family.
* `n`: total number of seed homolog contexts.
* `k`: number of seed homolog contexts where the neighbor's 30% family is present at least once.

Then score enrichment with Fisher exact test / hypergeometric test, plus effect sizes:

* `observed_frequency = k / n`
* `background_frequency = K / N`
* `fold_enrichment = observed_frequency / background_frequency`
* `q_value` after multiple-testing correction across neighbor families.

Use presence/absence per seed context as the primary count. If the same neighbor family appears multiple times in one context window, count it once for enrichment and preserve copy number as an auxiliary metric.

## Default LLM Analysis Threshold

Neighbor families enter LLM case-level analysis by default when they satisfy:

* `q_value <= 0.05`
* `fold_enrichment >= 5`
* `support_contexts >= 5`
* `observed_frequency >= 0.05`

Limit the default number of families passed to LLM analysis:

* `max_families_for_llm = 20`

## Why This Is Reasonable

* It matches the existing data model.
* It avoids using raw non-dereplicated protein counts.
* It treats broad 30% clusters as functional families, which is appropriate for remote-homology discovery.
* It is simple enough for v1 and can scale using precomputed 30% family sizes.

## Caveat

This global family-abundance background does not fully correct lineage or environment bias. A protein family can be globally rare but common within the specific taxa/environments where the seed homolog family occurs.

V1 can still use this as the primary score, but reports should expose taxonomy/environment breadth and allow later matched-background extensions if needed.

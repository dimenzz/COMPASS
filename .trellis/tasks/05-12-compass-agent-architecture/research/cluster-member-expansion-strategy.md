# Cluster Member Expansion Strategy

## Question

When v1 searches `cluster_90` representatives, should COMPASS expand hits to all 90% cluster members and extract every member's genomic context?

## Updated decision

The chosen v1 strategy is:

1. Search seed proteins against the `cluster_90` representative database.
2. Do not expand direct 90% representative hits to 90% cluster members.
3. Map each direct 90% representative hit to its parent 30% cluster.
4. Expand each matched 30% cluster to all of its 90% representatives, with no default cap.
5. Treat all collected 90% representatives as seed homolog candidates.
6. Extract genomic context for all collected 90% representatives.
7. Combine all contexts into one enrichment analysis rather than reporting tier-stratified statistics.
8. De-duplicate repeated 30% clusters and repeated 90% representatives internally before context extraction/statistics.

## Observations

Limited inspection confirms that 90% clusters can contain many near-duplicate members from the same lineage and environment. One sampled 90% cluster had 20 members, all annotated as `Acetatifactor` from `Mouse Gut`.

This means full member expansion can inflate support for a context pattern that is really lineage-specific or dataset-sampling-specific.

## Options

### Option A: Representative-only context

Use only the `cluster_90` representative's genomic context.

Pros:

* Fast and simple.
* Avoids near-duplicate context inflation.
* Good for quick exploratory runs.

Cons:

* The representative's context may not represent the full cluster.
* Misses context variation across members.
* Underestimates support and taxonomic breadth.

### Option B: Full 90% member expansion

Extract context for every member of every hit cluster.

Pros:

* Captures real support count and context diversity.
* Required for strong evidence when the same association appears across independent genomes.
* Enables lineage/environment breadth analysis.

Cons:

* Can over-weight oversampled species, MAG sets, or environments.
* Expensive for large hit sets.
* Can make LLM-facing summaries noisy.

### Option C: Stratified capped 90% member expansion

Expand members, but cap and stratify extraction by taxonomic/environmental diversity and context uniqueness.

Previously recommended behavior:

1. Always keep the representative context.
2. Expand members only for scoring and evidence support, not as independent raw observations.
3. Cap sampled member contexts per 90% cluster by default, e.g. `max_members_per_cluster = 20`.
4. Stratify member sampling by taxonomy and environment when available.
5. Collapse near-identical contexts into `context_signature` groups before enrichment.
6. Compute both raw support and de-redundant support:
   * `raw_loci_count`
   * `unique_mag_count`
   * `unique_species_count`
   * `unique_genus_count`
   * `unique_context_signature_count`
7. Use de-redundant support for ranking; report raw support separately.
8. Allow `--expand-members full` for deliberate exhaustive runs.

### Option D: 30% cluster homolog expansion

After a 90% representative is hit, find its parent 30% cluster and inspect additional 90% representatives inside that broader family.

Observed scale:

* A sampled 90% representative belonged to a 30% cluster containing 3,118 90% representatives.

Pros:

* Can recover additional genomic-context patterns around remote homologs that the direct sequence search missed.
* Helps identify subfamilies where the same broad protein family has different functional partners.
* More aligned with discovery cases such as TIGR-Tas, where family-level embedding/community analysis revealed subgroups with distinct context.

Cons:

* 30% identity clusters can mix related but functionally diverged proteins.
* Treating every 30% cluster member as a true homolog would inflate noise and false associations.
* Direct joins from broad 30% clusters back into the 257 GB protein database can be slow; this needs cached/batched tooling.

Chosen v1 behavior:

1. Include 30%-expanded representatives in the homolog universe as remote homolog candidates.
2. Do not expand to 90% cluster members.
3. Expand to all 90% representatives within matched 30% clusters, with no default cap.
4. Combine contexts from all collected representatives into one enrichment analysis.
5. Do not report tier-stratified statistics in v1.
6. Preserve minimal provenance internally for reproducibility/debugging, but do not expose it as a separate statistical tier.
7. Prevent broad-family over-counting by de-duplicating repeated 30% clusters and repeated 90% representatives before context extraction.

## Recommendation

Use `cluster_90` representatives as the search and context unit. Do not use 90% member expansion in v1. Use 30% clusters to broaden direct hits into a remote-homolog representative universe, then run combined context statistics over that representative universe.

The run configuration should expose:

* `--family30-expansion all|none`
* `--dedupe-30-clusters true|false`
* `--dedupe-90-representatives true|false`
* `--dedupe-context-signatures true|false`

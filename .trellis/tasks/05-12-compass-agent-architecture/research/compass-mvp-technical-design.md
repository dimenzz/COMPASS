# COMPASS MVP Technical Design

## MVP stance

Build COMPASS as a backend-first, checkpointed sequence-context CLI workflow with an agent layer on top. The deterministic bioinformatics pipeline should own sequence search, context extraction, clustering, and statistics. LLM agents should own planning, evidence retrieval, interpretation, critique, and report writing.

Structure search is not mandatory for v1. Foldseek/DALI should be modeled as an optional future evidence provider behind a stable interface.

## End-to-end run

1. `seed_ingest`
   * Input: FASTA plus optional domain interval, seed name, biological background, and search budget.
   * Output: normalized seed records and run manifest.

2. `homolog_search`
   * Fast pass: MMseqs against 90% representatives.
   * Do not expand direct hits to 90% cluster members in v1.
   * Remote-homolog expansion: map direct hit representatives to parent 30% clusters, then collect all 90% representatives in those 30% clusters with no default cap.
   * De-duplicate repeated 30% clusters and repeated 90% representatives before context extraction.
   * Remote pass: profile/HMM iterative search if needed.
   * Future optional pass: Foldseek/DALI against predicted/available structures through a separate structure-search adapter.
   * Output: merged homolog representative table with evidence per direct hit, cluster IDs, expansion provenance, and context extraction status.

3. `seed_subfamily_clustering`
   * V1 features: 30% cluster, sequence-search score bin, length bin, domain architecture, and context-signature cluster.
   * V1 methods: lightweight grouping/binning and exact/similarity grouping over context signatures.
   * Deferred methods: ESM embeddings, HDBSCAN/Leiden, structure clustering, and phylogenetic trees.
   * Output: `homolog_groups.tsv`, `context_signature_clusters.tsv`, and exploratory `subfamily_neighbor_enrichment.tsv`.

4. `context_extraction`
   * Protein context: default upstream 10 and downstream 10 protein-coding genes on the same contig, with maximum seed-neighbor distance 20 kb.
   * Noncoding context: CRISPR arrays, repeat arrays, inverted repeats, terminators, Rfam/Infernal ncRNAs, transposon/mobile element signatures.
   * Output: context rows normalized by seed hit and genomic position.

5. `co_localization_statistics`
   * Combined enrichment: neighbor cluster enrichment around all collected homolog representative contexts.
   * Exploratory subfamily enrichment: neighbor clusters and genetic elements that distinguish lightweight homolog groups.
   * V1 background: treat each 30% cluster as a broad protein family and use its number of 90% representatives as global family abundance.
   * Controls: 90% representative de-redundancy, repeated 30% cluster de-duplication, repeated context de-duplication, and multiple-testing correction.
   * Future controls: taxonomic/environment stratification, contig length, local gene density, and randomized matched neighborhoods.
   * Output: ranked context signatures with effect sizes, p-values/q-values, support counts, and examples.

6. `evidence_retrieval`
   * Literature: seed domains, neighbor domains, genetic elements, analogous systems.
   * Databases: Pfam, InterPro, KEGG, COG, eggNOG, UniProt where relevant.
   * Structure: AlphaFold/Foldseek/DALI/HHpred/co-folding evidence where relevant.
   * Output: normalized evidence items linked to candidate claims.

7. `case_access`
   * Build typed, run-scoped IDs for seed records, homolog representatives, loci, neighbor instances, neighbor families, cases, sequence features, and evidence items.
   * Provide LLM-safe tools such as `list_cases`, `get_case`, `get_locus_diagram`, `get_sequence_window`, and future `scan_case_features`.
   * Validate object type and run scope on every tool call to prevent ID confusion and object misuse.
   * Register LLM-callable tools with manifest-style metadata and agent-facing descriptions so the agent knows when and how to use them.
   * Output: case registry and feature/evidence records.

8. `hypothesis_synthesis`
   * Generate hypotheses per seed subfamily and context signature.
   * Explicitly separate observations, inferences, analogies, caveats, and proposed validation experiments.
   * Output: report plus machine-readable claim/evidence graph.

## Co-localization score

Use several scores instead of one:

* `support`: number of independent genomes/contigs/loci supporting the association.
* `specificity`: enrichment near the seed versus global 30% family abundance among 90% representatives.
* `subfamily_specificity`: enrichment in one seed subfamily versus other seed subfamilies.
* `proximity`: distance/order and orientation consistency.
* `architecture_consistency`: whether the association preserves operon order and strand.
* `taxonomic_breadth`: whether the pattern spans taxa or is a lineage artifact.
* `annotation_novelty`: whether the neighbor is unannotated or weakly annotated.
* `mechanistic_plausibility`: domain/structure/literature support for interaction or shared pathway.

## Critical implementation constraints

* Do not let the LLM issue arbitrary SQL over the 257 GB protein database.
* Precompute or cache ordered contig protein lists for frequent neighborhood extraction.
* Use 90% cluster representatives as the context and counting unit in v1; do not expand to 90% cluster members.
* Every long-running task should write a parameter file, log, output table, and checksum.
* Reports should cite artifact paths and source records so that every claim is traceable.
* LLM-facing tools must pass typed object IDs through a registry; do not let the agent infer object type from raw protein IDs or coordinates.
* LLM-facing tools should read checkpointed run artifacts through a gateway rather than directly querying raw databases.

## First implementation slice

1. CLI command: `compass run --seed seed.faa --name <run_name> --mode sequence-context`.
2. MMseqs search against `cluster_90` database.
3. Map direct hit representatives to 30% clusters and expand to all 90% representatives in those 30% clusters.
4. Protein-only genomic context extraction from `proteins.db`.
5. Combined neighbor 30% family enrichment against global 90%-representative family abundance.
6. Build typed case registry for enriched seed-neighbor loci.
7. Markdown/HTML report with top neighbor clusters and LLM-assisted biological interpretation.

Defer for later slices:

* Foldseek/DALI integration.
* ESM embedding and Leiden clustering.
* CRISPR/ncRNA/repeat feature detection.
* Structure co-folding and docking evidence.
* Multi-agent autonomous planning over multiple seed families.

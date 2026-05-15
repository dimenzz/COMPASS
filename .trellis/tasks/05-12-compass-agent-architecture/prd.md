# brainstorm: COMPASS LLM agents architecture

## Goal

Design COMPASS, an LLM-agent-assisted discovery system for mining novel microbial gene function systems from large-scale microbial genomes. The system should start from user-provided seed protein FASTA sequences, recover remote homologs, analyze genomic contexts, identify strongly co-localized neighbor proteins or genetic elements, and synthesize multi-source evidence into biological hypotheses with an auditable evidence chain.

## What I already know

* The user has about 480,000 microbial genomes with predicted protein sequences and functional annotations.
* Genome and protein file manifests are under `data/data_manifests/`.
* Protein identifiers follow `{genome_id}_{contig_order}_{start}_{end}_{strand}`.
* Protein metadata and taxonomic information are stored in `/mnt/nfs/share/MGnify/all_data/proteins.db`.
* Cluster metadata are stored in `/mnt/nfs/share/MGnify/all_data/clusters.db`.
* Protein clustering has two levels: MMseqs 90% identity dereplication, then 30% identity clustering over 90% representatives.
* MMseqs databases are under `/mnt/nfs/share/MGnify/all_data/mmseqs_db`.
* Desired fixed pipeline: seed FASTA -> structure and sequence search -> remote homolog retrieval -> genomic context extraction -> co-localization enrichment -> LLM biological function reasoning.
* Desired reasoning evidence sources include literature, seed and neighbor protein functions/mechanisms, nearby genetic elements such as ncRNA, inverted repeats, and CRISPR arrays, and cross-system comparison.
* Inspiration cases:
  * Nuclease-associated genes (NAGs) near oversized Cas9 proteins, followed by structural clustering and discovery of NAG-Cas9 interaction/function.
  * TIGR-Tas discovery from an IS110 RNA-binding domain seed, ESM embedding clustering, CRISPR-array-like DNA array context, and experimental validation.
* Reference bio-agent projects to inspect: `zaixizhang/STELLA` and `zou-group/CellVoyager`.

## Assumptions (temporary)

* COMPASS should be implemented as a reproducible backend-first research system before any rich frontend.
* The first MVP should support semi-autonomous analysis for one seed family at a time rather than fully open-ended autonomous discovery over all families.
* LLM agents should not directly run expensive global jobs without a planner/budget layer and checkpointed intermediate artifacts.
* Biological claims should be separated into evidence-backed observations, model inferences, and experimentally testable hypotheses.

## Decisions

* V1 is locked to a sequence-context CLI workflow.
* Structure search is not mandatory for v1. Foldseek/DALI should be represented as an optional future interface so the architecture can add structure evidence without rewriting the core run model.
* Search uses `cluster_90` representatives as the primary search database.
* V1 does not expand direct 90% representative hits to their 90% cluster members.
* Each direct 90% representative hit is mapped to its parent 30% cluster, then COMPASS expands to all 90% representatives in those 30% clusters with no default cap.
* All collected 90% representatives are treated as seed homolog candidates.
* V1 combines all homolog genomic contexts into a single enrichment analysis. It does not report tier-stratified context statistics.
* Internal de-duplication is still required so the same 30% cluster or 90% representative is not counted repeatedly when reached through multiple direct hits.
* V1 uses 30% clusters as broad protein families and uses the number of 90% representatives in each 30% cluster as the global family-abundance background for neighbor enrichment.
* V1 primary enrichment uses neighbor-family presence/absence per seed context. Copy number within a context is retained as an auxiliary metric, not the primary count.
* V1 default genomic context window is upstream 10 protein-coding genes and downstream 10 protein-coding genes, restricted to the same contig and filtered by a maximum seed-neighbor distance of 20 kb.
* LLM agents need typed per-case access to co-localized seed-neighbor loci, including future sequence-feature tools for arrays, motifs, inverted repeats, repeats, and ncRNA candidates.
* Agent tools must use run-scoped typed object IDs, not raw untyped strings, to prevent seed/neighbor/family/locus confusion.
* V1 default thresholds for neighbor families entering LLM analysis: `q_value <= 0.05`, `fold_enrichment >= 5`, `support_contexts >= 5`, `observed_frequency >= 0.05`, and at most 20 families per run.
* For each enriched neighbor family, v1 defaults to 10 representative cases selected by a mixed strategy: shortest-distance/high-confidence, taxonomy/environment diversity, context-signature diversity, and annotation-interesting examples.
* V1 uses a fixed bounded agent loop with one critic-driven revision round: RunPlanner -> SearchExecutor -> HomologExpander -> ContextExtractor -> StatisticsAgent -> CaseSelector -> CaseInspector -> HypothesisGenerator -> CriticAgent -> ReportWriter.
* Future agent architecture should use evidence-driven dynamic planning over typed tools and a lightweight evidence graph, not rigid workflow templates.
* V1 produces both human-readable Markdown/HTML reports and lightweight JSONL evidence graph artifacts.
* V1 report structure is fixed: Run Summary, Homolog Universe, Top Co-localized Neighbor Families, Candidate System Summaries, Cross-family Patterns, Evidence and Claims, Methods, and Artifacts.
* V1 includes lightweight homolog grouping by 30% family, sequence-search score bin, length bin, domain architecture, and context-signature cluster. Heavy ESM/structure/phylogeny clustering is deferred.
* V1 primary ranking remains global combined neighbor enrichment. Subfamily neighbor enrichment is emitted as exploratory evidence for discovering subgroup-specific systems.
* Code organization should use a responsibility-based package layout with clear boundaries among CLI, config, deterministic pipeline stages, data repositories, artifacts, tools, agents, stats, and reporting.
* COMPASS should run in a conda environment defined by `environment.yml`, while `pyproject.toml` defines package metadata and console scripts.
* Configuration precedence is `code defaults < configs/default.yaml < user YAML (--config) < explicit CLI args`.
* V1 supports both full workflow execution (`compass run`) and individual stage execution (`compass search`, `compass expand`, `compass context`, etc.) with checkpointed artifacts and stage state files.
* LLM inference is optional but first-class in v1. Deterministic stages run without API credentials; when `llm.enabled` is true, `inspect-cases` and `report` use LLM-backed evidence synthesis, hypothesis generation, and critique.

## Open Questions

* None blocking for v1 planning.

## Requirements (evolving)

* Accept user-provided seed protein FASTA input.
* Search the local protein universe for sequence and remote homolog candidates.
* Retrieve local genomic neighborhoods for each homolog.
* Quantify neighbor co-localization strength with cluster-aware statistics.
* Cluster homologs by sequence, structure, domain architecture, and potentially embedding features.
* Compare genomic contexts between homolog subfamilies.
* Detect or ingest nearby non-protein genetic elements relevant to defense/mobile systems.
* Retrieve external evidence from literature and curated databases.
* Produce a report containing candidates, statistics, subfamily context signatures, evidence chains, caveats, and testable hypotheses.

## Research References

* [`research/local-data-inventory.md`](research/local-data-inventory.md) — local data scale, SQLite schemas, MMseqs assets, and derived-table recommendations.
* [`research/discovery-case-studies.md`](research/discovery-case-studies.md) — implementation lessons from the NAG/Cas9 and TIGR-Tas discovery patterns.
* [`research/reference-agent-architectures.md`](research/reference-agent-architectures.md) — transferable patterns from STELLA and CellVoyager.
* [`research/compass-mvp-technical-design.md`](research/compass-mvp-technical-design.md) — proposed backend-first MVP pipeline and agent roles.
* [`research/cluster-member-expansion-strategy.md`](research/cluster-member-expansion-strategy.md) — trade-offs for expanding `cluster_90` hits to member genomic contexts.
* [`research/background-enrichment-strategy.md`](research/background-enrichment-strategy.md) — v1 enrichment background using 30% protein-family abundance over 90% representatives.
* [`research/agent-case-access-and-id-safety.md`](research/agent-case-access-and-id-safety.md) — typed case/locus/feature access for LLM agents and safeguards against object misuse.
* [`research/llm-tool-interface-design.md`](research/llm-tool-interface-design.md) — STELLA/CellVoyager-inspired LLM tool manifest and prompt contract for `scan_case_features`.
* [`research/run-artifact-schema.md`](research/run-artifact-schema.md) — checkpointed run directory and core TSV/JSONL artifacts for CLI, tools, and reports.
* [`research/case-selection-strategy.md`](research/case-selection-strategy.md) — default 10-case mixed selection strategy per enriched neighbor family.
* [`research/agent-loop-design.md`](research/agent-loop-design.md) — STELLA/CellVoyager-inspired fixed v1 loop and future Pro-CRISPR/TIGR-Tas discovery loops.
* [`research/evidence-graph-vs-markdown.md`](research/evidence-graph-vs-markdown.md) — rationale for lightweight JSONL evidence graph artifacts plus human-readable reports.
* [`research/report-structure.md`](research/report-structure.md) — stable v1 Markdown/HTML report sections and candidate hypothesis format.
* [`research/homolog-grouping-strategy.md`](research/homolog-grouping-strategy.md) — lightweight v1 homolog grouping and exploratory subfamily enrichment.
* [`research/project-structure-and-config.md`](research/project-structure-and-config.md) — proposed package layout, conda environment, and config precedence.
* [`research/staged-cli-execution.md`](research/staged-cli-execution.md) — full and per-stage CLI commands, stage contracts, and checkpoint state files.

## Proposed MVP Convergence

Build the first implementation as a backend-first, checkpointed CLI workflow. This is now the locked v1 direction:

```text
seed FASTA
  -> MMseqs search over cluster_90 representatives
  -> map direct hits to parent 30% clusters
  -> expand to all 90% representatives inside those 30% clusters
  -> protein-only genomic context extraction from proteins.db
  -> combined neighbor 30% family enrichment against global 90%-representative family abundance
  -> typed case registry for enriched seed-neighbor loci
  -> LLM-assisted evidence synthesis and report generation
```

The LLM layer should not own raw database-scale computation in v1. It should:

* validate and refine the run plan;
* call typed tools with explicit budgets;
* inspect concrete cases through LLM-callable tools such as `get_case`, `get_locus_diagram`, and `scan_case_features`;
* retrieve and normalize literature/database evidence;
* critique statistical and biological claims;
* generate an auditable report.

## Agent Loop

V1 uses a fixed, reproducible loop:

```text
RunPlanner
  -> SearchExecutor
  -> HomologExpander
  -> ContextExtractor
  -> StatisticsAgent
  -> CaseSelector
  -> CaseInspector
  -> HypothesisGenerator
  -> CriticAgent
  -> ReportWriter
```

The loop borrows STELLA's manager/executor/critic/tool-registry pattern and CellVoyager's hypothesis/execution/critique/revision pattern. V1 keeps tool calls bounded and allows one critic-driven revision round. Future versions should use evidence-driven dynamic planning over typed tools and a lightweight evidence graph rather than rigid workflow templates.

## Evidence Outputs

V1 should produce both:

* Markdown/HTML report for humans.
* Lightweight JSONL evidence graph artifacts for agent/critic validation: `cases.jsonl`, `features.jsonl`, `literature_evidence.jsonl`, `tool_evidence.jsonl`, and `claims.jsonl`.

Every mechanistic claim should cite concrete `case_id`, `feature_id`, and/or `evidence_id` records.

## Report Structure

V1 reports use fixed sections:

1. Run Summary.
2. Homolog Universe.
3. Top Co-localized Neighbor Families.
4. Candidate System Summaries.
5. Cross-family Patterns.
6. Evidence and Claims.
7. Methods.
8. Artifacts.

Each candidate hypothesis should include statistical, genomic-context, sequence-feature, and annotation/literature evidence; caveats; proposed validation experiments; confidence; and linked IDs.

## Run Artifact Schema

Each v1 run writes a checkpointed directory:

```text
runs/{run_name}/
  run.yaml
  inputs/seed.faa
  logs/{stage}.log
  state/{stage}.done.json
  search/{mmseqs_hits.tsv,direct_90_hits.tsv,matched_30_families.tsv,homolog_90_reps.tsv}
  search/{homolog_groups.tsv}
  context/{loci.tsv,context_neighbors.tsv,context_signatures.tsv,context_signature_clusters.tsv}
  stats/{family_background.tsv,neighbor_enrichment.tsv,subfamily_neighbor_enrichment.tsv}
  cases/{enriched_families.jsonl,cases.jsonl,locus_diagrams.jsonl,features.jsonl}
  evidence/{literature_evidence.jsonl,tool_evidence.jsonl,claims.jsonl}
  report/{report.md,report.html}
```

LLM tools read these artifacts through typed object IDs and a gateway. They should not query raw databases directly.

Later slices should add Foldseek/DALI, profile/HMM iteration, ESM embeddings with Leiden clustering, ncRNA/CRISPR/repeat feature detection, structure co-folding, and multi-run autonomous discovery.

## Acceptance Criteria (evolving)

* [x] A concrete MVP architecture is agreed with scoped modules and data contracts.
* [x] A first-pass technical design exists for search, context extraction, co-localization scoring, subfamily clustering, evidence retrieval, and report generation.
* [x] Research notes exist for the two inspiration papers and comparable LLM bio-agent architectures.
* [x] The PRD captures the main implementation decisions before code starts.

## Definition of Done (team quality bar)

* Tests added/updated where implementation changes behavior.
* Lint / typecheck / CI green where applicable.
* Docs/notes updated if behavior changes.
* Rollout/rollback considered if risky.

## Out of Scope (explicit)

* Full autonomous genome-wide discovery across all possible seed families in the first MVP.
* Experimental validation automation.
* A polished web UI before the backend workflow and evidence model are stable.

## Technical Notes

* Current repo is mostly scaffolding: `README.md`, Trellis metadata, sample GFF, and data manifests.
* Backend/frontend spec files exist but are mostly placeholders.
* Research findings should be persisted under `research/` in this task directory.

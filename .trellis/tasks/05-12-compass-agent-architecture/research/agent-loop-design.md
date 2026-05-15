# Agent Loop Design

## Goal

Design a COMPASS agent loop that can support v1 sequence-context discovery and later evolve toward novel-system discovery workflows similar to Pro-CRISPR/NAG-Cas9 and TIGR-Tas.

## Reference Patterns

### STELLA pattern

STELLA uses:

* manager agent for task decomposition and orchestration;
* dev/execution agent for tool use and analysis;
* critic agent for quality review and gap detection;
* governed tool registry with tool manifests;
* reusable workflow templates learned from successful runs.

COMPASS should reuse this as a high-level orchestration pattern.

### CellVoyager pattern

CellVoyager separates:

* hypothesis generation;
* execution in a durable notebook/artifact workspace;
* interpretation of outputs;
* self-critique and revision;
* interactive user checkpoints.

COMPASS should reuse this as an evidence-to-hypothesis loop pattern.

## Design Principle

The LLM agent should not invent evidence. It should:

1. choose which typed tools to call;
2. inspect structured outputs;
3. synthesize biological hypotheses;
4. ask a critic whether the evidence supports the hypothesis;
5. iterate only within an explicit budget.

The deterministic pipeline owns expensive and reproducible computation. The agent owns planning, inspection, critique, and reporting.

## V1 Fixed Loop

V1 should use a fixed, reproducible loop:

```text
User seed FASTA
  -> RunPlanner creates run config and artifact directory
  -> SearchExecutor runs MMseqs over cluster_90 reps
  -> HomologExpander maps direct hits to 30% clusters and all 90% reps
  -> ContextExtractor extracts upstream/downstream context
  -> StatisticsAgent computes enrichment
  -> CaseSelector creates typed cases for enriched neighbor families
  -> CaseInspector calls get_case/get_locus_diagram/scan_case_features
  -> HypothesisGenerator proposes biological hypotheses
  -> CriticAgent checks evidence sufficiency and claim strength
  -> ReportWriter emits report.md, claims.jsonl, evidence tables
```

Default budget:

* `max_families_for_llm = 20`
* `cases_per_family = 10`
* `scan_case_features_per_family = 3`
* `max_revision_rounds = 1`

## Agent Roles

### RunPlanner

Inputs:

* seed FASTA;
* user notes;
* run mode and budget.

Responsibilities:

* validate inputs;
* choose v1 workflow template;
* write `run.yaml`;
* decide whether optional tools are enabled.

### SearchExecutor

Responsibilities:

* run MMseqs search against `cluster_90`;
* produce `mmseqs_hits.tsv` and `direct_90_hits.tsv`;
* never make biological claims.

### HomologExpander

Responsibilities:

* map direct 90% hits to parent 30% clusters;
* expand to all 90% representatives in those 30% clusters;
* de-duplicate 30% clusters and 90% representatives;
* produce `homolog_90_reps.tsv`.

### ContextExtractor

Responsibilities:

* extract default upstream/downstream protein contexts;
* produce `loci.tsv`, `context_neighbors.tsv`, and `context_signatures.tsv`;
* later: add noncoding context tracks.

### StatisticsAgent

Responsibilities:

* compute 30% family-level background over 90% representatives;
* compute neighbor enrichment using presence/absence per context;
* produce `neighbor_enrichment.tsv`;
* choose families passing LLM-analysis threshold.

### CaseSelector

Responsibilities:

* create `case_id` objects for enriched neighbor families;
* select default 10 cases per family by mixed strategy;
* write `cases.jsonl` and `locus_diagrams.jsonl`.

### CaseInspector

Responsibilities:

* call LLM-safe tools on typed cases:
  * `get_case`;
  * `get_locus_diagram`;
  * `get_sequence_window`;
  * `scan_case_features`;
  * later `compare_cases`.
* convert tool outputs into structured evidence records.

### HypothesisGenerator

Responsibilities:

* generate one or more hypotheses per enriched neighbor family;
* separate observations, analogies, mechanistic inferences, caveats, and proposed experiments;
* cite `case_id`, `feature_id`, and `evidence_id`.

This is the CellVoyager-like component.

### CriticAgent

Responsibilities:

* reject unsupported claims;
* detect overreach from co-localization to mechanism;
* ask whether evidence comes from enough cases;
* flag taxonomy/environment narrowness;
* recommend one bounded revision action if needed.

This is the STELLA-like critic component.

### ReportWriter

Responsibilities:

* write `report.md` and `claims.jsonl`;
* preserve links to artifacts and evidence IDs.

## Loop for Pro-CRISPR/NAG-Cas9-like Discovery

This pattern looks for an accessory neighbor that modifies or extends a known seed system.

```text
1. Start from known seed family.
2. Find broad homolog universe.
3. Stratify seed homologs by size, domain architecture, and context signature.
4. Identify enriched neighbor families.
5. Inspect cases where neighbor is tightly linked to seed.
6. Ask whether the neighbor explains a seed subfamily property:
   * oversized seed protein;
   * missing/extra domain;
   * conserved orientation;
   * fixed distance;
   * co-occurring regulatory or repeat elements.
7. Generate mechanism hypothesis:
   neighbor modulates seed activity, guide processing, target recognition, immunity, mobility, or regulation.
8. Critic checks whether the claim is supported by statistics, context conservation, annotations, and case-level sequence features.
```

Required future tools:

* domain architecture comparison;
* seed length/subfamily clustering;
* structure/cofolding evidence adapter.

## Loop for TIGR-Tas-like Discovery

This pattern discovers a novel system from a remote homolog/domain seed and a noncoding context pattern.

```text
1. Start from seed protein or seed domain.
2. Build broad homolog universe through sequence-context v1 and later profile/structure expansion.
3. Cluster homolog representatives by sequence/domain/embedding features.
4. Compare context signatures between subfamilies.
5. Identify subfamilies with unusual noncoding or repeat context.
6. Use scan_case_features and later ncRNA/array tools to detect arrays, repeats, motifs, and conserved intergenic signals.
7. Generate hypothesis:
   protein family + array/motif/ncRNA form a guide-like, regulatory, mobile, or defense system.
8. Critic checks:
   * repeat/array consistency across cases;
   * protein domain plausibility;
   * context conservation;
   * whether alternative explanations exist.
```

Required future tools:

* domain interval seed handling;
* embedding/Leiden clustering;
* CRISPR-like/repeat-array detector;
* Infernal/Rfam ncRNA scan;
* case comparison across selected loci.

## V1 Versus Future Autonomy

V1:

* fixed loop;
* bounded tool calls;
* one critic revision round;
* no autonomous creation of new pipeline steps.

V2:

* planner dynamically chooses the next evidence-gathering action from the current evidence graph;
* critic can trigger additional bounded analyses;
* successful reasoning patterns can inform prompts and heuristics, but not as rigid workflow templates;
* user checkpoints after search, enrichment, and hypothesis synthesis.

Future COMPASS should use evidence-driven dynamic planning rather than rigid workflow templates. The stable parts should be typed tools, evidence objects, claim/evidence schemas, critic rules, and budgets. The exploration path should remain flexible.

## Prompt Contract

The manager prompt should tell the agent:

```text
You are not allowed to infer a novel biological system from enrichment alone.
For each prioritized neighbor family, inspect representative case_id records.
Use typed tools only. Cite case_id, feature_id, and evidence_id in every
mechanistic claim. If evidence is insufficient, state a weaker hypothesis and
recommend the next computational or experimental validation.
```

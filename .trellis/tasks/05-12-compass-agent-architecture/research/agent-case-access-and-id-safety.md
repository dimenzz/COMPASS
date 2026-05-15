# Agent Case Access and ID Safety

## Problem

COMPASS cannot stop at neighbor-family enrichment statistics. For each enriched neighbor family, the LLM agent must inspect concrete co-localized cases and ask follow-up questions about local genomic sequence features:

* upstream/downstream arrays;
* inverted repeats;
* direct repeats;
* CRISPR-like repeats;
* ncRNA candidates;
* motifs near seed or neighbor genes;
* transposon/mobile-element boundary signatures;
* conserved intergenic regions.

The risk is that an LLM may confuse object types:

* using a 30% family ID where a protein ID is required;
* using a neighbor protein as the seed protein;
* mixing contexts from two loci;
* requesting sequence from the wrong contig interval;
* citing evidence from one case as if it came from another.

## Design Decision

Use typed, opaque, run-scoped object IDs and a tool gateway. The LLM should not build raw SQL, infer coordinates by string parsing, or pass untyped identifiers between tools.

## Object Model

Every run creates stable objects:

* `run_id`: one COMPASS analysis run.
* `seed_id`: input seed sequence record.
* `homolog_id`: collected 90% representative treated as a seed homolog.
* `locus_id`: one genomic context window around one homolog.
* `neighbor_instance_id`: one neighbor protein instance inside one locus.
* `neighbor_family_id`: one enriched 30% neighbor protein family.
* `case_id`: a curated pair of `locus_id + neighbor_instance_id + neighbor_family_id`.
* `feature_id`: one detected local sequence feature.
* `evidence_id`: one normalized evidence item used in a report claim.

Recommended opaque ID format:

```text
cmp:{run_id}:seed:{n}
cmp:{run_id}:homolog:{n}
cmp:{run_id}:locus:{n}
cmp:{run_id}:neighbor:{n}
cmp:{run_id}:family30:{representative_hash}
cmp:{run_id}:case:{n}
cmp:{run_id}:feature:{n}
cmp:{run_id}:evidence:{n}
```

The original protein IDs, cluster IDs, contig IDs, and coordinates are payload fields, not the main handles passed by the agent.

## Tool Gateway

Expose typed tools such as:

* `list_enriched_neighbor_families(run_id)` -> ranked `neighbor_family_id` records.
* `list_cases(run_id, neighbor_family_id, filters)` -> `case_id` list.
* `get_case(case_id)` -> seed homolog, neighbor instance, locus coordinates, annotations, and context signature.
* `get_locus_diagram(case_id)` -> ordered gene diagram and compact annotation table.
* `get_sequence_window(case_id, target, flank_bp)` -> validated nucleotide sequence window.
* `scan_case_features(case_id, feature_types)` -> arrays, repeats, IRs, motifs, ncRNA candidates.
* `compare_cases(case_ids)` -> conserved gene order and conserved sequence-feature patterns.
* `promote_feature_to_evidence(feature_id, claim)` -> normalized evidence item.

Each tool validates object type and `run_id` before doing work. For example, a `neighbor_family_id` must not be accepted where a `case_id` is required.

## Case Cards

For LLM consumption, each `case_id` should return a compact case card:

```yaml
case_id: cmp:RUN123:case:42
seed_homolog:
  homolog_id: cmp:RUN123:homolog:17
  protein_id: MGYG...
  family30_id: cmp:RUN123:family30:...
neighbor:
  neighbor_instance_id: cmp:RUN123:neighbor:88
  protein_id: MGYG...
  neighbor_family_id: cmp:RUN123:family30:...
locus:
  locus_id: cmp:RUN123:locus:17
  contig_id: MGYG..._12
  seed_coordinates: [12345, 14567]
  neighbor_coordinates: [15001, 15600]
  relative_gene_index: 2
  distance_bp: 434
  same_strand: true
annotations:
  seed: {...}
  neighbor: {...}
available_sequence_tools:
  - scan_case_features
  - get_sequence_window
```

## Provenance Rules

* Every report claim must cite `case_id` and `feature_id` / `evidence_id`.
* Batch summaries must retain links to the individual cases they summarize.
* The agent may request more cases, but should not silently generalize from one case to the whole family.
* Feature detectors should write results to structured tables and return IDs, not only prose.

## Practical V1 Scope

V1 should implement the object registry and typed access API even if only protein-coding context is available at first. Sequence-feature scanners can be added behind the same interface.

Minimum v1:

* `list_enriched_neighbor_families`
* `list_cases`
* `get_case`
* `get_locus_diagram`
* `get_sequence_window`

Next v1.1:

* `scan_case_features` with simple repeat/IR/motif detectors.
* `compare_cases` across selected cases.

Agent-facing tool documentation and prompt contract are specified in `llm-tool-interface-design.md`.

# LLM Tool Interface Design

## Goal

COMPASS should expose selected analysis capabilities as LLM-callable tools. The design should borrow two patterns:

* STELLA-style governed tool registry: each tool has a manifest, description, parameters, dependencies, validation status, and intended use.
* CellVoyager-style execution gateway: the agent calls constrained tools that operate on durable analysis objects and return structured results that can be written into a report/notebook.

`scan_case_features` is the first important example because the LLM agent needs to inspect case-level sequence evidence after family-level co-localization statistics identify candidate neighbor families.

## Tool Manifest

```yaml
tool_id: scan_case_features
name: scan_case_features
category: genomic_context
status: planned
description: >
  Scan a specific seed-neighbor co-localization case for local nucleotide
  sequence features such as direct repeats, inverted repeats, tandem arrays,
  conserved motifs, low-complexity sequence, and future ncRNA/CRISPR-like
  features. Use this after selecting a concrete case_id from an enriched
  neighbor family.
inputs:
  case_id:
    type: string
    required: true
    description: Run-scoped typed case ID, e.g. cmp:RUN123:case:42.
  feature_types:
    type: array[string]
    required: false
    default: ["direct_repeat", "inverted_repeat", "tandem_repeat", "motif"]
    allowed:
      - direct_repeat
      - inverted_repeat
      - tandem_repeat
      - motif
      - low_complexity
      - crispr_like_array
      - ncrna_candidate
      - terminator
  target_region:
    type: string
    required: false
    default: locus
    allowed:
      - locus
      - seed_upstream
      - seed_downstream
      - neighbor_upstream
      - neighbor_downstream
      - intergenic_seed_neighbor
  flank_bp:
    type: integer
    required: false
    default: 500
    min: 50
    max: 5000
  min_score:
    type: number
    required: false
    default: 0.0
outputs:
  scan_id: string
  case_id: string
  scanned_region:
    contig_id: string
    start: integer
    end: integer
    strand: string
  features:
    type: array
    items:
      feature_id: string
      feature_type: string
      start: integer
      end: integer
      strand: string
      score: number
      sequence: string
      summary: string
      evidence_strength: string
  warnings:
    type: array[string]
```

## Agent-Facing Description

The agent should see a concise description like:

```text
scan_case_features(case_id, feature_types=None, target_region="locus", flank_bp=500)

Use this tool to inspect one concrete co-localized seed-neighbor case for
local nucleotide sequence features. Call it after list_cases/get_case when
you need evidence such as repeats, inverted repeats, arrays, motifs, or
possible guide-like/noncoding elements near the seed and neighbor genes.

The input must be a case_id from the current COMPASS run. Do not pass raw
protein IDs, 30% family IDs, contig IDs, or coordinates. The tool validates
the case, extracts the correct sequence window, runs feature scanners, and
returns feature_id records that can be cited in evidence chains.
```

## Usage Pattern

The intended LLM workflow:

```text
1. list_enriched_neighbor_families(run_id)
2. list_cases(run_id, neighbor_family_id)
3. get_case(case_id)
4. get_locus_diagram(case_id)
5. scan_case_features(case_id, feature_types=["direct_repeat", "inverted_repeat", "tandem_repeat", "motif"])
6. compare_cases(case_ids) if a pattern appears in several cases
7. promote_feature_to_evidence(feature_id, claim)
```

## Guardrails

The tool must reject:

* IDs that are not `case_id` objects.
* Case IDs from a different `run_id`.
* Raw protein IDs, contig IDs, or 30% family IDs.
* Requests for sequence outside the current contig.
* Excessive flank sizes unless explicitly allowed by run configuration.

The returned features must be structured records. The LLM can summarize them, but the report should cite `feature_id` and `case_id`, not only prose.

## V1 Feature Scanners

Minimum v1 scanners:

* `direct_repeat`: exact or near-exact repeats within the selected region.
* `inverted_repeat`: palindromic/inverted repeat pairs with spacer constraints.
* `tandem_repeat`: repeated units suggestive of guide arrays or simple arrays.
* `motif`: short conserved k-mers across selected cases or user-provided motifs.
* `low_complexity`: low-complexity or homopolymer-rich regions.

Deferred scanners:

* `crispr_like_array`: CRISPR-style repeat-spacer structures.
* `ncrna_candidate`: Rfam/Infernal or RNA secondary-structure-based candidates.
* `terminator`: rho-independent terminator prediction.

## Prompt Contract

The agent system prompt should include:

```text
When statistical enrichment identifies a neighbor family, do not infer the
mechanism from enrichment alone. Select representative case_id records and
use get_case, get_locus_diagram, and scan_case_features to inspect concrete
loci. Cite case_id and feature_id in every mechanistic claim. Never pass raw
protein IDs or coordinates to case-level tools.
```

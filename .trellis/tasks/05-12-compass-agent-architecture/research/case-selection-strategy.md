# Case Selection Strategy

## Decision

For each enriched neighbor family that passes the LLM-analysis threshold, v1 should select 10 representative cases by default.

Default parameter:

```text
--cases-per-family 10
```

## Mixed Selection Strategy

Select cases by a mixed strategy rather than only by p-value, distance, or random sampling:

* 3 highest-confidence / shortest-distance cases.
* 3 taxonomy- or environment-diverse cases.
* 2 context-signature-diverse cases.
* 2 annotation-interesting cases, such as hypothetical proteins, unusual domains, or unexpected gene architectures.

## Tool Interface

`list_cases` should support strategy parameters:

```text
list_cases(neighbor_family_id, limit=10, strategy="mixed")
list_cases(neighbor_family_id, limit=10, strategy="taxonomy_diverse")
list_cases(neighbor_family_id, limit=10, strategy="shortest_distance")
list_cases(neighbor_family_id, limit=10, strategy="same_gene_order")
list_cases(neighbor_family_id, limit=10, strategy="unusual_annotation")
```

## Rationale

The LLM agent needs concrete cases, but showing only one repeated pattern can hide diversity or create false confidence. The mixed strategy gives the agent a compact but diverse evidence set for case-level inspection and feature scanning.

# Report Structure

## Decision

V1 should generate a stable Markdown/HTML report structure. The LLM should fill fixed sections rather than freely inventing report organization.

## Report Sections

```text
# COMPASS Report: {run_name}

## 1. Run Summary
Seed information, database versions, search parameters, context window, and statistical thresholds.

## 2. Homolog Universe
Direct 90% hit counts, matched 30% family counts, final homolog 90% representative counts, and expansion notes.

## 3. Top Co-localized Neighbor Families
Ranked table with neighbor 30% family, annotation summary, support, fold enrichment, q value, and observed frequency.

## 4. Candidate System Summaries
One section per enriched neighbor family:
* statistical evidence;
* representative cases;
* locus diagrams;
* sequence features from `scan_case_features`;
* annotation/literature evidence;
* biological hypothesis;
* caveats;
* proposed validation experiments.

## 5. Cross-family Patterns
Shared domain, array, repeat, orientation, taxonomy/environment, or context-signature patterns across candidates.

## 6. Evidence and Claims
Human-readable summary of `claims.jsonl`, with links to `case_id`, `feature_id`, and `evidence_id`.

## 7. Methods
MMseqs parameters, cluster expansion, context extraction, enrichment test, LLM tool budget, and feature scanning methods.

## 8. Artifacts
Paths to run artifacts.
```

## Candidate Hypothesis Format

Each candidate hypothesis should use:

```text
Hypothesis:
Evidence:
  - Statistical:
  - Genomic context:
  - Sequence features:
  - Annotation/literature:
Caveats:
Next experiments:
Confidence: low / medium / high
Linked IDs:
  cases:
  features:
  claims:
```

## Rationale

A fixed report shape keeps outputs comparable between runs and makes it easier for the critic to verify that every claim is tied to evidence.

# Evidence Graph and Markdown Report

## Decision

COMPASS should use both:

* human-readable Markdown/HTML reports;
* lightweight machine-readable evidence graph artifacts in JSONL.

V1 should not require a graph database. JSONL files are enough:

```text
cases.jsonl
features.jsonl
literature_evidence.jsonl
tool_evidence.jsonl
claims.jsonl
```

## Why Not Markdown Only

Markdown is good for human reading and biological narrative, but it is weak for agent reliability:

* hard to automatically check whether each claim is supported;
* easy for LLMs to mix evidence from different cases;
* hard to track negative evidence;
* hard to update incrementally when new features/cases are scanned;
* hard to query for missing evidence types.

## Why Evidence Graph

The evidence graph makes claims and evidence machine-checkable:

```json
{
  "claim_id": "claim_12",
  "claim_type": "mechanistic_hypothesis",
  "claim": "This seed-neighbor system may use a guide-like RNA element.",
  "supporting_case_ids": ["case_8", "case_19"],
  "supporting_feature_ids": ["feature_31", "feature_44"],
  "supporting_literature_ids": ["paper_5"],
  "contradicting_case_ids": ["case_27"],
  "confidence": "medium",
  "status": "hypothesis"
}
```

This lets the critic check:

* whether a mechanistic claim cites concrete cases;
* whether sequence-feature claims cite `feature_id`;
* whether confidence exceeds evidence strength;
* whether negative/contradictory cases exist.

## Trade-Off

Evidence graph cost:

* requires schema design;
* requires validators;
* less pleasant for humans to read;
* can be overkill for very early exploration.

Markdown cost:

* poor machine validation;
* poor traceability;
* prone to hallucinated or mixed evidence.

## V1 Recommendation

Use lightweight JSONL evidence graph artifacts plus a report generated from or linked to those artifacts. Every report claim should cite IDs:

* `case_id`
* `feature_id`
* `evidence_id`
* `claim_id`

The Markdown report remains the primary human-facing output.

from __future__ import annotations

from pathlib import Path
from typing import Any

from compass.agents.llm_client import LlmClient, LlmUnavailableError, llm_is_enabled
from compass.artifacts.readers import read_jsonl, read_tsv
from compass.config.schema import RunMetadata


SYSTEM_PROMPT = """You are COMPASS, a cautious microbial genomics hypothesis generator.
Use only the supplied evidence. Do not invent protein functions, papers, assays, or mechanisms.
Every mechanistic hypothesis must cite supplied case_id, feature_id, and/or evidence_id records.
Return JSON with keys hypotheses and critique. hypotheses is an array of objects with fields:
neighbor_30_family, hypothesis, evidence_ids, case_ids, feature_ids, confidence, caveats,
validation_experiments. critique is an array of short strings describing limitations."""


def generate_llm_claims(
    metadata: RunMetadata,
    enrichment_path: Path,
    cases_path: Path,
    features_path: Path,
    tool_evidence_path: Path,
    starting_claim_index: int,
) -> tuple[list[dict], list[str]]:
    if not llm_is_enabled(metadata.config.llm):
        return [], []
    payload = _build_payload(enrichment_path, cases_path, features_path, tool_evidence_path)
    client = LlmClient(metadata.config.llm)
    response = client.complete_json(SYSTEM_PROMPT, payload)
    return _claims_from_response(response, starting_claim_index), []


def generate_llm_unavailable_claim(error: LlmUnavailableError, claim_index: int) -> dict:
    return {
        "claim_id": f"claim_{claim_index:07d}",
        "claim_type": "llm_unavailable",
        "neighbor_30_family": "",
        "statement": str(error),
        "evidence": {},
        "confidence": "not_run",
    }


def _build_payload(enrichment_path: Path, cases_path: Path, features_path: Path, tool_evidence_path: Path) -> dict[str, Any]:
    top_subgroup_hits_path = enrichment_path.parent / "top_subgroup_neighbor_hits.jsonl"
    payload = {
        "top_neighbor_families": read_tsv(enrichment_path)[:20],
        "top_subgroup_neighbor_hits": read_jsonl(top_subgroup_hits_path)[:100] if top_subgroup_hits_path.exists() else [],
        "cases": read_jsonl(cases_path)[:200],
        "features": read_jsonl(features_path)[:500],
        "tool_evidence": read_jsonl(tool_evidence_path)[:500],
        "instruction": (
            "Generate cautious biological hypotheses for enriched neighbor families. "
            "Distinguish statistical co-localization from mechanistic inference."
        ),
    }
    return payload


def _claims_from_response(response: dict[str, Any], starting_claim_index: int) -> list[dict]:
    claims: list[dict] = []
    claim_index = starting_claim_index
    for item in response.get("hypotheses", []):
        claims.append(
            {
                "claim_id": f"claim_{claim_index:07d}",
                "claim_type": "llm_hypothesis",
                "neighbor_30_family": item.get("neighbor_30_family", ""),
                "statement": item.get("hypothesis", ""),
                "evidence": {
                    "evidence_ids": item.get("evidence_ids", []),
                    "case_ids": item.get("case_ids", []),
                    "feature_ids": item.get("feature_ids", []),
                },
                "confidence": item.get("confidence", "llm_generated"),
                "caveats": item.get("caveats", []),
                "validation_experiments": item.get("validation_experiments", []),
            }
        )
        claim_index += 1
    critique = response.get("critique", [])
    if critique:
        claims.append(
            {
                "claim_id": f"claim_{claim_index:07d}",
                "claim_type": "llm_critique",
                "neighbor_30_family": "",
                "statement": " ".join(str(item) for item in critique),
                "evidence": {},
                "confidence": "llm_generated",
            }
        )
    return claims

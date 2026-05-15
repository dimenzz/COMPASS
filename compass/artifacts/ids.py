from __future__ import annotations

import re
from dataclasses import dataclass


CASE_ID_PATTERN = re.compile(r"^cmp:(?P<run_id>[^:]+):case:(?P<index>[0-9]{7})$")
FEATURE_ID_PATTERN = re.compile(r"^cmp:(?P<run_id>[^:]+):feature:(?P<index>[0-9]{7})$")
EVIDENCE_ID_PATTERN = re.compile(r"^cmp:(?P<run_id>[^:]+):evidence:(?P<index>[0-9]{7})$")


@dataclass(frozen=True)
class ParsedObjectId:
    run_id: str
    object_type: str
    index: int


def parse_case_id(case_id: str, expected_run_id: str | None = None) -> ParsedObjectId:
    return _parse_typed_id(case_id, CASE_ID_PATTERN, "case", expected_run_id)


def make_feature_id(run_id: str, index: int) -> str:
    return f"cmp:{run_id}:feature:{index:07d}"


def make_evidence_id(run_id: str, index: int) -> str:
    return f"cmp:{run_id}:evidence:{index:07d}"


def _parse_typed_id(
    object_id: str,
    pattern: re.Pattern[str],
    object_type: str,
    expected_run_id: str | None,
) -> ParsedObjectId:
    match = pattern.match(object_id)
    if match is None:
        raise ValueError(f"Expected {object_type}_id in format cmp:<run_id>:{object_type}:0000001, got: {object_id}")
    run_id = match.group("run_id")
    if expected_run_id is not None and run_id != expected_run_id:
        raise ValueError(f"{object_type}_id belongs to run {run_id}, expected {expected_run_id}")
    return ParsedObjectId(run_id=run_id, object_type=object_type, index=int(match.group("index")))

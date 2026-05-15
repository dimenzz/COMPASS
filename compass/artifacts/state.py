from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from compass import __version__
from compass.artifacts.layout import RunLayout


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def write_stage_state(
    layout: RunLayout,
    stage: str,
    started_at: str,
    inputs: dict[str, str],
    outputs: dict[str, str],
    parameters: dict[str, Any],
    status: str = "done",
) -> Path:
    payload = {
        "stage": stage,
        "status": status,
        "started_at": started_at,
        "finished_at": utc_now(),
        "inputs": inputs,
        "outputs": outputs,
        "parameters_hash": _parameters_hash(parameters),
        "software": {"compass": __version__},
    }
    path = layout.state / f"{stage}.done.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _parameters_hash(parameters: dict[str, Any]) -> str:
    encoded = json.dumps(parameters, sort_keys=True, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()

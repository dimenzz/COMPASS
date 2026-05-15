from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer


ConfigOption = Annotated[Path | None, typer.Option("--config", help="User YAML config file.")]
RunOption = Annotated[Path, typer.Option("--run", help="Run directory, e.g. runs/demo.")]
ForceOption = Annotated[bool, typer.Option("--force", help="Overwrite existing stage outputs.")]


def common_overrides(
    output_root: Path | None = None,
    family30_background: Path | None = None,
    llm_enabled: bool | None = None,
    llm_model: str | None = None,
) -> dict:
    overrides: dict = {}
    if output_root is not None:
        overrides.setdefault("artifacts", {})["output_root"] = output_root
    if family30_background is not None:
        overrides.setdefault("database", {})["family30_background"] = family30_background
    if llm_enabled is not None:
        overrides.setdefault("llm", {})["enabled"] = llm_enabled
    if llm_model is not None:
        overrides.setdefault("llm", {})["model"] = llm_model
    return overrides

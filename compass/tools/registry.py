from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ToolManifest:
    tool_id: str
    name: str
    category: str
    description: str
    status: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]


class ToolRegistry:
    def __init__(self, manifests_dir: Path):
        self.manifests_dir = manifests_dir
        self._tools = self._load_manifests()

    def get(self, tool_id: str) -> ToolManifest | None:
        return self._tools.get(tool_id)

    def list_all(self) -> list[ToolManifest]:
        return list(self._tools.values())

    def _load_manifests(self) -> dict[str, ToolManifest]:
        tools: dict[str, ToolManifest] = {}
        if not self.manifests_dir.exists():
            return tools
        for path in sorted(self.manifests_dir.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            manifest = ToolManifest(
                tool_id=data["tool_id"],
                name=data.get("name", data["tool_id"]),
                category=data.get("category", "general"),
                description=data.get("description", ""),
                status=data.get("status", "planned"),
                inputs=data.get("inputs", {}),
                outputs=data.get("outputs", {}),
            )
            tools[manifest.tool_id] = manifest
        return tools

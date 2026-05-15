from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from compass.config.defaults import CODE_DEFAULTS
from compass.config.schema import CompassConfig, RunMetadata


DEFAULT_CONFIG_PATH = Path("configs/default.yaml")


def load_config(
    config_path: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
    include_default_yaml: bool = True,
) -> tuple[CompassConfig, list[Path]]:
    raw = deepcopy(CODE_DEFAULTS)
    loaded_files: list[Path] = []

    if include_default_yaml and DEFAULT_CONFIG_PATH.exists():
        _deep_merge(raw, _read_yaml(DEFAULT_CONFIG_PATH))
        loaded_files.append(DEFAULT_CONFIG_PATH)

    if config_path is not None:
        _deep_merge(raw, _read_yaml(config_path))
        loaded_files.append(config_path)

    if cli_overrides:
        _deep_merge(raw, _remove_none(cli_overrides))

    return CompassConfig.model_validate(raw), loaded_files


def dotted_overrides(**kwargs: Any) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for dotted_key, value in kwargs.items():
        if value is None:
            continue
        current = overrides
        parts = dotted_key.split(".")
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
    return overrides


def dump_config(path: Path, config: CompassConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(mode="json")
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def write_run_metadata(path: Path, metadata: RunMetadata) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = metadata.model_dump(mode="json")
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def read_run_metadata(path: Path) -> RunMetadata:
    data = _read_yaml(path)
    return RunMetadata.model_validate(data)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")
    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _remove_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _remove_none(item) for key, item in value.items() if item is not None}
    return value

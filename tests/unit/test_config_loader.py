from __future__ import annotations

from pathlib import Path

from compass.config.loader import load_config


def test_config_precedence_cli_over_yaml(tmp_path: Path) -> None:
    user_config = tmp_path / "config.yaml"
    user_config.write_text(
        """
search:
  max_seqs: 111
llm:
  enabled: false
""",
        encoding="utf-8",
    )

    config, loaded = load_config(
        config_path=user_config,
        cli_overrides={"search": {"max_seqs": 222}, "llm": {"enabled": True}},
        include_default_yaml=True,
    )

    assert user_config in loaded
    assert config.search.max_seqs == 222
    assert config.llm.enabled is True


def test_code_defaults_are_available_without_yaml() -> None:
    config, loaded = load_config(include_default_yaml=False)

    assert loaded == []
    assert config.context.upstream_genes == 10
    assert config.agent.cases_per_family == 10

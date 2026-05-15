from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from compass.config.schema import LlmConfig


class LlmUnavailableError(RuntimeError):
    """Raised when LLM inference is requested but optional dependencies are unavailable."""


def require_llm_dependencies() -> None:
    try:
        import instructor  # noqa: F401
        import litellm  # noqa: F401
    except ImportError as exc:
        raise LlmUnavailableError(
            "LLM dependencies are not installed. Create the conda environment from environment.yml."
        ) from exc


def llm_is_enabled(config: LlmConfig) -> bool:
    return bool(config.enabled)


@dataclass(frozen=True)
class LlmResponse:
    content: str
    raw: Any


class LlmClient:
    def __init__(self, config: LlmConfig):
        self.config = config
        require_llm_dependencies()
        if not os.environ.get(config.api_key_env):
            raise LlmUnavailableError(f"LLM is enabled but environment variable {config.api_key_env} is not set.")

    def complete_json(self, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        import litellm

        kwargs: dict[str, Any] = {
            "model": _litellm_model(self.config),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True, sort_keys=True)},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_output_tokens,
        }
        if self.config.structured_outputs:
            kwargs["response_format"] = {"type": "json_object"}
        response = litellm.completion(**kwargs)
        content = response["choices"][0]["message"]["content"]
        return json.loads(content)


def _litellm_model(config: LlmConfig) -> str:
    if config.provider == "openai" or "/" in config.model:
        return config.model
    return f"{config.provider}/{config.model}"

"""Provider-agnostic LLM facade. core/normalizer.py and core/verdict.py import `converse`
from here, not from clients/bedrock.py or clients/gemini.py directly - which provider
actually runs is decided once, here, from Config.ai_provider.

This exists because of a real, live situation (see docs/TRD.md's "AI provider" section):
Bedrock access is blocked by an AWS-side account verification hold, so the working path
today is Gemini. Both client modules are fully intact and this is a one-line flip back
(`AI_PROVIDER=bedrock` in infra/samconfig.toml) the moment Bedrock access clears - nothing
in core/ needs to change either way.

model_id resolution also happens here so callers don't need `if provider == ...` branches:
they call `converse(kind="verdict", ...)` or `converse(kind="fast", ...)` and this picks
the right model ID for whichever provider is active.
"""

from __future__ import annotations

from typing import Any, Literal

from bitecheck.config import Config

ModelKind = Literal["verdict", "fast"]


def _model_id(config: Config, kind: ModelKind) -> str:
    if config.ai_provider == "gemini":
        return config.gemini_verdict_model if kind == "verdict" else config.gemini_fast_model
    return config.verdict_model_id if kind == "verdict" else config.fast_model_id


def converse(
    kind: ModelKind,
    system: str,
    messages: list[dict[str, Any]],
    tool_schema: dict | None = None,
) -> dict[str, Any]:
    """Dispatches to the active provider's converse(), with the right model ID for `kind`
    already resolved. Same return contract as both underlying clients: the parsed
    structured object when tool_schema is given, else {"text": ...}.
    """
    config = Config.from_env()
    model_id = _model_id(config, kind)

    if config.ai_provider == "gemini":
        from bitecheck.clients import gemini

        return gemini.converse(
            model_id=model_id, system=system, messages=messages, tool_schema=tool_schema
        )

    from bitecheck.clients import bedrock

    return bedrock.converse(
        model_id=model_id, system=system, messages=messages, tool_schema=tool_schema
    )

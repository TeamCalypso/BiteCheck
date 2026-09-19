"""Bedrock clients: runtime (Converse) and agent-runtime (Retrieve).

Clients are module-level (cached) so they are reused across warm Lambda invocations.
Timeouts are short and explicit: a slow Bedrock call must fail fast rather than burn the
API Gateway 29-second integration budget - see docs/TRD.md's latency budget.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config as BotoConfig

from bitecheck.config import Config

_READ_TIMEOUT_S = 15
_CONNECT_TIMEOUT_S = 3
_TOOL_NAME = "emit_structured_response"


@lru_cache(maxsize=1)
def _boto_config() -> BotoConfig:
    return BotoConfig(
        connect_timeout=_CONNECT_TIMEOUT_S,
        read_timeout=_READ_TIMEOUT_S,
        retries={"max_attempts": 2, "mode": "standard"},
    )


@lru_cache(maxsize=1)
def _runtime_client():
    return boto3.client("bedrock-runtime", region_name=Config.from_env().region, config=_boto_config())


@lru_cache(maxsize=1)
def _agent_runtime_client():
    return boto3.client("bedrock-agent-runtime", region_name=Config.from_env().region, config=_boto_config())


def converse(
    model_id: str,
    system: str,
    messages: list[dict[str, Any]],
    tool_schema: dict | None = None,
) -> dict[str, Any]:
    """Single Converse call.

    When `tool_schema` is given (a JSON Schema object), the call forces the model to
    respond through a single tool invocation matching that schema, and this returns the
    *parsed tool input* directly - not the raw Converse envelope. That's what lets
    core/normalizer.py and core/verdict.py treat this as "call a function, get JSON back"
    rather than parsing prose. Without `tool_schema`, returns `{"text": <response text>}`.
    """
    kwargs: dict[str, Any] = {
        "modelId": model_id,
        "system": [{"text": system}],
        "messages": messages,
        "inferenceConfig": {"maxTokens": 2048, "temperature": 0.1},
    }

    if tool_schema is not None:
        kwargs["toolConfig"] = {
            "tools": [
                {
                    "toolSpec": {
                        "name": _TOOL_NAME,
                        "description": "Emit the structured response for this request.",
                        "inputSchema": {"json": tool_schema},
                    }
                }
            ],
            "toolChoice": {"tool": {"name": _TOOL_NAME}},
        }

    response = _runtime_client().converse(**kwargs)
    output_message = response["output"]["message"]

    if tool_schema is not None:
        for block in output_message["content"]:
            if "toolUse" in block:
                return block["toolUse"]["input"]
        raise RuntimeError(
            f"Bedrock did not return a tool_use block for model {model_id}; "
            f"got content blocks: {[list(b.keys()) for b in output_message['content']]}"
        )

    text = "".join(block.get("text", "") for block in output_message["content"])
    return {"text": text}


def retrieve(
    knowledge_base_id: str,
    query: str,
    top_k: int,
    metadata_filter: dict | None = None,
) -> dict[str, Any]:
    """Raw bedrock-agent-runtime.retrieve response.

    Callers (core/rag.py) parse the `retrievalResults` list into `RetrievedChunk` objects.
    Kept raw here rather than parsed so this module stays a thin, mockable AWS boundary.
    """
    vector_config: dict[str, Any] = {"numberOfResults": top_k}
    if metadata_filter is not None:
        vector_config["filter"] = metadata_filter

    return _agent_runtime_client().retrieve(
        knowledgeBaseId=knowledge_base_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={"vectorSearchConfiguration": vector_config},
    )


def resolve_model_ids() -> dict[str, list[str]]:
    """Discover callable model/inference-profile IDs for this account.

    Newer Claude models require an inference-profile ID rather than a bare model ID, and
    which are enabled varies per account depending on when/whether Bedrock model access
    was granted - so we never hardcode a single ID anywhere in request-time code.

    Used by scripts/bootstrap_kb.py at deploy/bootstrap time only. Request-time code reads
    the already-resolved IDs from Config.verdict_model_id / Config.fast_model_id (set as
    Lambda environment variables by infra/samconfig.toml's parameter_overrides).
    """
    bedrock_client = boto3.client("bedrock", region_name=Config.from_env().region)
    profiles = bedrock_client.list_inference_profiles().get("inferenceProfileSummaries", [])
    models = bedrock_client.list_foundation_models().get("modelSummaries", [])
    return {
        "inference_profiles": [p["inferenceProfileId"] for p in profiles],
        "foundation_models": [
            m["modelId"] for m in models if m.get("modelLifecycle", {}).get("status") == "ACTIVE"
        ],
    }

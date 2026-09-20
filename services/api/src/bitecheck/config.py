"""Runtime configuration, read once from the environment.

Everything account-specific arrives as a Lambda environment variable set by the SAM
template. Nothing here is hardcoded, in particular the Bedrock model IDs: newer Claude
models must be addressed through inference profiles (``us.anthropic.*``) and which ones an
account can actually call varies. ``scripts/bootstrap_kb.py`` resolves them at deploy time.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(
            f"Missing required environment variable {name!r}. "
            "It is set by infra/template.yaml; check the deployed function configuration."
        )
    return value or ""


@dataclass(frozen=True)
class Config:
    region: str
    knowledge_base_id: str
    cache_table: str
    catalog_table: str
    verdict_model_id: str
    fast_model_id: str
    cache_ttl_seconds: int
    retrieval_top_k: int
    openfoodfacts_timeout_s: float
    corpus_bucket: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            region=_env("AWS_REGION", "us-east-1"),
            knowledge_base_id=_env("KNOWLEDGE_BASE_ID"),
            cache_table=_env("CACHE_TABLE", "bitecheck-cache"),
            catalog_table=_env("CATALOG_TABLE", "bitecheck-catalog"),
            # Used for the verdict: needs to follow a strict JSON schema and reason over
            # regulator prose.
            verdict_model_id=_env("BEDROCK_VERDICT_MODEL"),
            # Used for entity normalization and the food gate: short prompt, high volume,
            # so it runs on something cheap.
            fast_model_id=_env("BEDROCK_FAST_MODEL"),
            cache_ttl_seconds=int(_env("CACHE_TTL_SECONDS", "86400")),
            retrieval_top_k=int(_env("RETRIEVAL_TOP_K", "8")),
            openfoodfacts_timeout_s=float(_env("OFF_TIMEOUT_SECONDS", "2.5")),
            corpus_bucket=_env("CORPUS_BUCKET"),
        )


DISCLAIMER = (
    "Informational only, compiled from public regulator records. Not a laboratory result "
    "for the specific pack you are viewing. Always check the batch code printed on your "
    "package."
)

# Shared with the frontend. Kept here so the API and both UIs agree on severity ordering.
SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFO": 3}

#!/usr/bin/env python3
"""One-time setup: S3 corpus bucket -> S3 vector bucket/index -> Bedrock Knowledge Base ->
S3 data source -> first ingestion job.

Run this once per environment, not on every deploy - that's why it's a standalone script
and not part of infra/template.yaml. Slow (KB creation + ingestion can take minutes) and
account/region specific.

Usage:
    python scripts/bootstrap_kb.py --corpus-bucket bitecheck-corpus-<suffix>

Writes infra/kb-outputs.json (gitignored) with every ID the SAM stack needs:
    { "knowledgeBaseId", "dataSourceId", "vectorBucketName", "vectorIndexName",
      "corpusBucketName", "verdictModelId", "fastModelId" }

Requires: an AWS account with Bedrock model access granted for Titan Text Embeddings V2
and your chosen Claude/Nova models (Bedrock console -> Model access). This is a manual,
per-account approval step and the reason Phase 0 does it first.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import boto3

REGION = "us-east-1"
EMBEDDING_MODEL_ARN = f"arn:aws:bedrock:{REGION}::foundation-model/amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSIONS = 1024  # Titan v2 supports 256/512/1024; 1024 for best recall.
VECTOR_INDEX_NAME = "bitecheck-index"
VECTOR_BUCKET_NAME = "bitecheck-vectors"
KB_NAME = "bitecheck-fssai-corpus"
OUTPUTS_PATH = Path(__file__).resolve().parents[1] / "infra" / "kb-outputs.json"

# Preferred verdict model, in priority order. resolve_model_id() picks the first available
# one for this account rather than hardcoding a single ID, because newer Claude models
# require inference-profile addressing (us.anthropic.*) that varies by account.
VERDICT_MODEL_CANDIDATES = [
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
]
FAST_MODEL_CANDIDATES = [
    "us.amazon.nova-lite-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
]


def resolve_model_id(bedrock, candidates: list[str]) -> str:
    """Return the first candidate this account can actually invoke.

    TODO: call bedrock.list_foundation_models() / list_inference_profiles() and intersect
    with candidates, rather than trusting the first one blindly.
    """
    raise NotImplementedError("Fill in during Phase 1 once Bedrock model access is granted.")


def ensure_corpus_bucket(s3, bucket_name: str) -> None:
    """Create the S3 bucket holding normalized corpus markdown + metadata, if absent."""
    raise NotImplementedError


def ensure_vector_index(s3vectors) -> None:
    """Create the S3 vector bucket and index (cosine distance, EMBEDDING_DIMENSIONS)."""
    raise NotImplementedError


def create_knowledge_base(bedrock_agent, corpus_bucket: str) -> str:
    """Create the KB with storageConfiguration.type = S3_VECTORS, return its ID."""
    raise NotImplementedError


def create_data_source(bedrock_agent, kb_id: str, corpus_bucket: str) -> str:
    """Attach the S3 corpus bucket as the KB's data source, return the data source ID."""
    raise NotImplementedError


def start_ingestion(bedrock_agent, kb_id: str, data_source_id: str) -> None:
    """Kick the first sync and poll until COMPLETE or FAILED."""
    raise NotImplementedError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-bucket", default="bitecheck-corpus-demo")
    parser.add_argument("--region", default=REGION)
    args = parser.parse_args()

    session = boto3.Session(region_name=args.region)
    print(f"[bootstrap_kb] region={args.region} corpus_bucket={args.corpus_bucket}")
    print(
        "[bootstrap_kb] This script is scaffolded but not yet implemented - see the "
        "TODOs in scripts/bootstrap_kb.py. Implement in Phase 1 alongside data/corpus."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

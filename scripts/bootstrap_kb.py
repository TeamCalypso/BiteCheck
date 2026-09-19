#!/usr/bin/env python3
"""One-time setup: S3 corpus bucket -> S3 vector bucket/index -> IAM role ->
Bedrock Knowledge Base -> S3 data source -> first ingestion job.

Run this once per environment, not on every deploy - that's why it's a standalone script
and not part of infra/template.yaml. Slow (KB creation + ingestion can take minutes) and
account/region specific. See docs/TRD.md for why the KB is bootstrapped separately from
the SAM stack that gets redeployed repeatedly.

Usage:
    python scripts/bootstrap_kb.py --corpus-bucket bitecheck-corpus-<suffix>

Writes infra/kb-outputs.json (gitignored) with every ID the SAM stack needs:
    { "knowledgeBaseId", "dataSourceId", "vectorBucketName", "vectorIndexName",
      "vectorBucketArn", "indexArn", "corpusBucketName", "verdictModelId", "fastModelId",
      "kbRoleArn" }

Requires: an AWS account with Bedrock model access granted for Titan Text Embeddings V2
and your chosen Claude/Nova models (Bedrock console -> Model access). This is a manual,
per-account approval step and the reason Phase 0 does it first.

API shapes here were verified against the live AWS API reference (not guessed) on
2026-09-20 - if AWS has changed something since, the error message from boto3 will name
the offending field, which is the fastest way to spot drift.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = "ap-south-1"  # Mumbai - lower latency for our actual (Indian) userbase; both
# S3 Vectors and Claude (via Global/APAC cross-region inference) are available here.
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSIONS = 1024  # Titan v2 supports 256/512/1024; 1024 for best recall.
VECTOR_INDEX_NAME = "bitecheck-index"
VECTOR_BUCKET_NAME_DEFAULT = "bitecheck-vectors"
KB_NAME = "bitecheck-fssai-corpus"
KB_ROLE_NAME = "BiteCheckKnowledgeBaseRole"
DATA_SOURCE_NAME = "bitecheck-corpus-s3"
OUTPUTS_PATH = Path(__file__).resolve().parents[1] / "infra" / "kb-outputs.json"

# Preferred verdict model, in priority order. resolve_model_id() picks the first available
# one for this account rather than hardcoding a single ID, because newer Claude models
# require inference-profile addressing that varies by account, by when Bedrock model
# access was granted, and (from ap-south-1 specifically) by inference-profile prefix:
#   - "global.*"  works from any source region, including ap-south-1 - prefer this
#   - "apac.*"     regional profile, keeps inference traffic within APAC - good fallback
#   - "us.*"       a us-east-1-sourced profile; unlikely to be invokable FROM ap-south-1,
#                  kept as a last-resort candidate only in case the account has unusual
#                  cross-region routing enabled
#   - bare model ID (no prefix) - only the oldest models (e.g. Claude 3 Haiku) support
#                  direct on-demand invocation without any inference profile at all
VERDICT_MODEL_CANDIDATES = [
    "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "apac.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "apac.anthropic.claude-3-7-sonnet-20250219-v1:0",
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
]
FAST_MODEL_CANDIDATES = [
    "apac.amazon.nova-lite-v1:0",
    "us.amazon.nova-lite-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",  # old enough to be directly invokable, no profile needed
]

_TERMINAL_INGESTION_STATUSES = {"COMPLETE", "FAILED"}
_TERMINAL_KB_STATUSES = {"ACTIVE", "FAILED"}


def _account_id(session: boto3.Session) -> str:
    return session.client("sts").get_caller_identity()["Account"]


def resolve_model_id(bedrock, candidates: list[str]) -> str:
    """Return the first candidate this account can actually invoke.

    Checks both plain foundation models and cross-Region inference profiles, since recent
    Claude models on Bedrock require inference-profile addressing (the `us.anthropic.*`
    IDs) rather than the bare model ID.
    """
    available: set[str] = set()
    try:
        for m in bedrock.list_foundation_models().get("modelSummaries", []):
            available.add(m["modelId"])
    except ClientError as e:
        print(f"[bootstrap_kb] warning: list_foundation_models failed: {e}")

    try:
        for p in bedrock.list_inference_profiles().get("inferenceProfileSummaries", []):
            available.add(p["inferenceProfileId"])
    except ClientError as e:
        print(f"[bootstrap_kb] warning: list_inference_profiles failed: {e}")

    for candidate in candidates:
        if candidate in available:
            return candidate

    raise RuntimeError(
        f"None of the candidate models are available to this account: {candidates}. "
        "Request Bedrock model access in the console (Bedrock -> Model access) and retry. "
        f"Models/profiles this account CAN see: {sorted(available)[:20]}..."
    )


def ensure_corpus_bucket(s3, bucket_name: str, region: str) -> str:
    """Create the S3 bucket holding normalized corpus markdown + metadata, if absent.
    Returns its ARN."""
    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"[bootstrap_kb] corpus bucket s3://{bucket_name} already exists")
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("404", "NoSuchBucket"):
            raise
        kwargs = {"Bucket": bucket_name}
        if region != "us-east-1":
            # us-east-1 is the one region where passing a LocationConstraint is an error.
            kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
        s3.create_bucket(**kwargs)
        s3.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True, "IgnorePublicAcls": True,
                "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
            },
        )
        print(f"[bootstrap_kb] created corpus bucket s3://{bucket_name}")
    return f"arn:aws:s3:::{bucket_name}"


def ensure_vector_index(s3vectors, vector_bucket_name: str, index_name: str) -> tuple[str, str]:
    """Create the S3 vector bucket and index (cosine distance, EMBEDDING_DIMENSIONS).
    Returns (vector_bucket_arn, index_arn)."""
    try:
        resp = s3vectors.create_vector_bucket(vectorBucketName=vector_bucket_name)
        vector_bucket_arn = resp["vectorBucketArn"]
        print(f"[bootstrap_kb] created vector bucket {vector_bucket_name}")
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("ConflictException", "BucketAlreadyExists"):
            raise
        vector_bucket_arn = s3vectors.get_vector_bucket(vectorBucketName=vector_bucket_name)[
            "vectorBucket"
        ]["vectorBucketArn"]
        print(f"[bootstrap_kb] vector bucket {vector_bucket_name} already exists")

    try:
        resp = s3vectors.create_index(
            vectorBucketName=vector_bucket_name,
            indexName=index_name,
            dataType="float32",
            dimension=EMBEDDING_DIMENSIONS,  # NB: S3 Vectors calls this "dimension"
            distanceMetric="cosine",
            # Bedrock KB metadata fields (issuer, docType, category, date, orderRef,
            # sourceUrl - see docs/backend-schema.md) all stay filterable by omitting them
            # here. Only the large, unfiltered chunk text/context would go in
            # nonFilterableMetadataKeys, and Bedrock manages that itself.
        )
        index_arn = resp["indexArn"]
        print(f"[bootstrap_kb] created vector index {index_name}")
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("ConflictException",):
            raise
        index_arn = s3vectors.get_index(vectorBucketName=vector_bucket_name, indexName=index_name)[
            "index"
        ]["indexArn"]
        print(f"[bootstrap_kb] vector index {index_name} already exists")

    return vector_bucket_arn, index_arn


def ensure_kb_role(
    iam, account_id: str, region: str, corpus_bucket_arn: str, vector_bucket_arn: str, index_arn: str
) -> str:
    """Create (or reuse) the IAM role Bedrock assumes to run the knowledge base. Returns
    its ARN. See docs.aws.amazon.com/bedrock/latest/userguide/kb-permissions.html - every
    statement here matches that page exactly for the S3 + S3 Vectors combination."""
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {"StringEquals": {"aws:SourceAccount": account_id}},
            }
        ],
    }

    try:
        role = iam.create_role(
            RoleName=KB_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Bedrock Knowledge Base execution role for BiteCheck (S3 Vectors)",
        )
        role_arn = role["Role"]["Arn"]
        print(f"[bootstrap_kb] created IAM role {KB_ROLE_NAME}")
        just_created = True
    except ClientError as e:
        if e.response["Error"]["Code"] != "EntityAlreadyExists":
            raise
        role_arn = iam.get_role(RoleName=KB_ROLE_NAME)["Role"]["Arn"]
        print(f"[bootstrap_kb] IAM role {KB_ROLE_NAME} already exists")
        just_created = False

    embedding_model_arn = f"arn:aws:bedrock:{region}::foundation-model/{EMBEDDING_MODEL_ID}"
    corpus_bucket_name = corpus_bucket_arn.rsplit(":::", 1)[-1]

    policies = {
        "BedrockModelAccess": {
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Action": "bedrock:InvokeModel", "Resource": embedding_model_arn}],
        },
        "S3DataSourceAccess": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "S3ListBucketStatement",
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": corpus_bucket_arn,
                    "Condition": {"StringEquals": {"aws:ResourceAccount": account_id}},
                },
                {
                    "Sid": "S3GetObjectStatement",
                    "Effect": "Allow",
                    "Action": "s3:GetObject",
                    "Resource": f"{corpus_bucket_arn}/*",
                    "Condition": {"StringEquals": {"aws:ResourceAccount": account_id}},
                },
            ],
        },
        "S3VectorsAccess": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "S3VectorBucketReadAndWritePermission",
                    "Effect": "Allow",
                    "Action": [
                        "s3vectors:PutVectors", "s3vectors:GetVectors", "s3vectors:DeleteVectors",
                        "s3vectors:QueryVectors", "s3vectors:GetIndex",
                    ],
                    "Resource": index_arn,
                }
            ],
        },
    }
    for policy_name, policy_document in policies.items():
        iam.put_role_policy(RoleName=KB_ROLE_NAME, PolicyName=policy_name, PolicyDocument=json.dumps(policy_document))

    if just_created:
        # IAM role propagation is eventually consistent - a freshly created role is not
        # immediately usable by another service. This is a well-known AWS gotcha, not a
        # bug in this script; the retry loop in create_knowledge_base() below also guards
        # against it, but a short wait here avoids burning most of those retries.
        print("[bootstrap_kb] waiting 12s for IAM role propagation...")
        time.sleep(12)

    return role_arn


def create_knowledge_base(bedrock_agent, role_arn: str, region: str, vector_bucket_arn: str, index_arn: str) -> str:
    """Create the KB with storageConfiguration.type = S3_VECTORS, return its ID.
    Retries on the IAM-propagation race (AccessDenied / ValidationException) for up to
    ~2 minutes before giving up."""
    embedding_model_arn = f"arn:aws:bedrock:{region}::foundation-model/{EMBEDDING_MODEL_ID}"
    index_name = index_arn.rsplit("/", 1)[-1]

    request = {
        "name": KB_NAME,
        "description": "BiteCheck FSSAI/RASFF/FDA/CFS regulator + lab document corpus",
        "roleArn": role_arn,
        "knowledgeBaseConfiguration": {
            "type": "VECTOR",
            "vectorKnowledgeBaseConfiguration": {
                "embeddingModelArn": embedding_model_arn,
                "embeddingModelConfiguration": {
                    "bedrockEmbeddingModelConfiguration": {"dimensions": EMBEDDING_DIMENSIONS}
                },
            },
        },
        "storageConfiguration": {
            "type": "S3_VECTORS",
            "s3VectorsConfiguration": {
                "vectorBucketArn": vector_bucket_arn,
                "indexArn": index_arn,
                "indexName": index_name,
            },
        },
    }

    last_error = None
    for attempt in range(8):
        try:
            resp = bedrock_agent.create_knowledge_base(**request)
            kb_id = resp["knowledgeBase"]["knowledgeBaseId"]
            print(f"[bootstrap_kb] created knowledge base {kb_id}, waiting for ACTIVE...")
            return _wait_for_kb_active(bedrock_agent, kb_id)
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "ConflictException":
                # Already exists from a prior run - find it and reuse it.
                for kb in bedrock_agent.list_knowledge_bases().get("knowledgeBaseSummaries", []):
                    if kb["name"] == KB_NAME:
                        print(f"[bootstrap_kb] knowledge base {KB_NAME} already exists: {kb['knowledgeBaseId']}")
                        return kb["knowledgeBaseId"]
                raise
            if code in ("AccessDeniedException", "ValidationException") and attempt < 7:
                last_error = e
                wait = 5 * (attempt + 1)
                print(f"[bootstrap_kb] {code} (likely IAM propagation) - retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"create_knowledge_base failed after retries: {last_error}")


def _wait_for_kb_active(bedrock_agent, kb_id: str, timeout_s: int = 180) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = bedrock_agent.get_knowledge_base(knowledgeBaseId=kb_id)["knowledgeBase"]["status"]
        if status in _TERMINAL_KB_STATUSES:
            if status == "FAILED":
                raise RuntimeError(f"Knowledge base {kb_id} entered FAILED status")
            return kb_id
        time.sleep(5)
    raise TimeoutError(f"Knowledge base {kb_id} did not become ACTIVE within {timeout_s}s")


def create_data_source(bedrock_agent, kb_id: str, corpus_bucket_arn: str) -> str:
    """Attach the S3 corpus bucket as the KB's data source, return the data source ID."""
    try:
        resp = bedrock_agent.create_data_source(
            knowledgeBaseId=kb_id,
            name=DATA_SOURCE_NAME,
            description="Normalized FSSAI/RASFF/FDA/CFS documents from data/corpus/",
            dataDeletionPolicy="DELETE",
            dataSourceConfiguration={"type": "S3", "s3Configuration": {"bucketArn": corpus_bucket_arn}},
            vectorIngestionConfiguration={
                "chunkingConfiguration": {
                    "chunkingStrategy": "FIXED_SIZE",
                    "fixedSizeChunkingConfiguration": {"maxTokens": 500, "overlapPercentage": 20},
                }
            },
        )
        data_source_id = resp["dataSource"]["dataSourceId"]
        print(f"[bootstrap_kb] created data source {data_source_id}")
        return data_source_id
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConflictException":
            raise
        for ds in bedrock_agent.list_data_sources(knowledgeBaseId=kb_id).get("dataSourceSummaries", []):
            if ds["name"] == DATA_SOURCE_NAME:
                print(f"[bootstrap_kb] data source {DATA_SOURCE_NAME} already exists: {ds['dataSourceId']}")
                return ds["dataSourceId"]
        raise


def start_ingestion(bedrock_agent, kb_id: str, data_source_id: str, timeout_s: int = 600) -> None:
    """Kick a sync and poll until COMPLETE or FAILED. Safe to call repeatedly - each call
    starts a fresh incremental sync, which is exactly what the (currently disabled)
    scheduled handlers/ingest.py will do once it's built."""
    resp = bedrock_agent.start_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=data_source_id)
    job_id = resp["ingestionJob"]["ingestionJobId"]
    print(f"[bootstrap_kb] started ingestion job {job_id}, polling...")

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        job = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb_id, dataSourceId=data_source_id, ingestionJobId=job_id
        )["ingestionJob"]
        status = job["status"]
        if status in _TERMINAL_INGESTION_STATUSES:
            stats = job.get("statistics", {})
            print(f"[bootstrap_kb] ingestion job {status}: {stats}")
            if status == "FAILED":
                raise RuntimeError(f"Ingestion failed: {job.get('failureReasons')}")
            return
        time.sleep(10)
    raise TimeoutError(f"Ingestion job {job_id} did not finish within {timeout_s}s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-bucket", default="bitecheck-corpus-demo")
    parser.add_argument("--vector-bucket", default=VECTOR_BUCKET_NAME_DEFAULT)
    parser.add_argument("--region", default=REGION)
    parser.add_argument("--skip-ingestion", action="store_true", help="stop after creating the data source")
    args = parser.parse_args()

    session = boto3.Session(region_name=args.region)
    account_id = _account_id(session)
    print(f"[bootstrap_kb] account={account_id} region={args.region} corpus_bucket={args.corpus_bucket}")

    bedrock = session.client("bedrock")
    bedrock_agent = session.client("bedrock-agent")
    s3 = session.client("s3")
    s3vectors = session.client("s3vectors")
    iam = session.client("iam")

    print("[bootstrap_kb] resolving model IDs this account can actually invoke...")
    verdict_model_id = resolve_model_id(bedrock, VERDICT_MODEL_CANDIDATES)
    fast_model_id = resolve_model_id(bedrock, FAST_MODEL_CANDIDATES)
    print(f"[bootstrap_kb] verdict_model_id={verdict_model_id} fast_model_id={fast_model_id}")

    corpus_bucket_arn = ensure_corpus_bucket(s3, args.corpus_bucket, args.region)
    vector_bucket_arn, index_arn = ensure_vector_index(s3vectors, args.vector_bucket, VECTOR_INDEX_NAME)
    role_arn = ensure_kb_role(iam, account_id, args.region, corpus_bucket_arn, vector_bucket_arn, index_arn)
    kb_id = create_knowledge_base(bedrock_agent, role_arn, args.region, vector_bucket_arn, index_arn)
    data_source_id = create_data_source(bedrock_agent, kb_id, corpus_bucket_arn)

    if args.skip_ingestion:
        print("[bootstrap_kb] --skip-ingestion set; not starting a sync (data/corpus/ may still be empty).")
    else:
        start_ingestion(bedrock_agent, kb_id, data_source_id)

    outputs = {
        "knowledgeBaseId": kb_id,
        "dataSourceId": data_source_id,
        "vectorBucketName": args.vector_bucket,
        "vectorIndexName": VECTOR_INDEX_NAME,
        "vectorBucketArn": vector_bucket_arn,
        "indexArn": index_arn,
        "corpusBucketName": args.corpus_bucket,
        "kbRoleArn": role_arn,
        "verdictModelId": verdict_model_id,
        "fastModelId": fast_model_id,
    }
    OUTPUTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUTS_PATH.write_text(json.dumps(outputs, indent=2) + "\n", encoding="utf-8")
    print(f"[bootstrap_kb] wrote {OUTPUTS_PATH}")
    print(
        "[bootstrap_kb] next: fill these into infra/samconfig.toml's parameter_overrides, "
        "then `sam build && sam deploy` from infra/."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

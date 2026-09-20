"""Shared pytest fixtures.

`ddb_tables` spins up a moto-mocked DynamoDB matching infra/template.yaml's schema
(including the TrendingIndex GSI), so core/cache.py and clients/ddb.py can be fully unit
tested without any real AWS account, credentials, or cost.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import boto3
import pytest

# moto needs *some* credentials in the environment to satisfy boto3's client construction,
# even though it never makes a real network call. These are fake and standard practice.
# The region here is deliberately hardcoded rather than read from samconfig.toml - moto
# simulates DynamoDB identically regardless of region, so there is no reason to keep this
# in sync with whatever the production region happens to be (see docs/TRD.md's Region &
# account section for why that's changed more than once).
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("CACHE_TABLE", "bitecheck-cache-test")
os.environ.setdefault("CATALOG_TABLE", "bitecheck-catalog-test")


@pytest.fixture
def ddb_tables():
    """A moto-mocked DynamoDB with the cache and catalog tables already created."""
    from moto import mock_aws

    with mock_aws():
        from bitecheck.clients import ddb as ddb_module

        # Config/resource are lru_cached for warm-Lambda reuse in production; tests need a
        # fresh one inside each mock_aws() context, or they'd hold a resource built before
        # (or after) the mock was active.
        ddb_module._config.cache_clear()
        ddb_module._dynamodb.cache_clear()

        client = boto3.client("dynamodb", region_name="us-east-1")
        client.create_table(
            TableName=os.environ["CACHE_TABLE"],
            AttributeDefinitions=[
                {"AttributeName": "asin", "AttributeType": "S"},
                {"AttributeName": "trendBucket", "AttributeType": "S"},
                {"AttributeName": "hitCount", "AttributeType": "N"},
            ],
            KeySchema=[{"AttributeName": "asin", "KeyType": "HASH"}],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "TrendingIndex",
                    "KeySchema": [
                        {"AttributeName": "trendBucket", "KeyType": "HASH"},
                        {"AttributeName": "hitCount", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        client.create_table(
            TableName=os.environ["CATALOG_TABLE"],
            AttributeDefinitions=[{"AttributeName": "asin", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "asin", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )

        yield

        ddb_module._config.cache_clear()
        ddb_module._dynamodb.cache_clear()


@pytest.fixture(scope="session")
def analyze_schema_validator():
    """The same schema validator test_contract.py uses, shared here so the end-to-end
    handler test (test_analyze_handler.py) can assert a real response validates."""
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = Path(__file__).resolve().parents[3] / "contract" / "analyze.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(schema)

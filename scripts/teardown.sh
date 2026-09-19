#!/usr/bin/env bash
# Tear down every AWS resource this project created. Run after judging.
#
# Order matters: the Bedrock Knowledge Base must go before its S3 Vectors store (it holds
# a reference to it), and the SAM stack's DynamoDB tables go last since nothing depends on
# them. Reads infra/kb-outputs.json for the IDs bootstrap_kb.py created.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KB_OUTPUTS="$ROOT/infra/kb-outputs.json"
REGION="us-east-1"

echo "== BiteCheck teardown =="

if [[ -f "$KB_OUTPUTS" ]]; then
  KB_ID=$(python3 -c "import json;print(json.load(open('$KB_OUTPUTS')).get('knowledgeBaseId',''))")
  CORPUS_BUCKET=$(python3 -c "import json;print(json.load(open('$KB_OUTPUTS')).get('corpusBucketName',''))")
  VECTOR_BUCKET=$(python3 -c "import json;print(json.load(open('$KB_OUTPUTS')).get('vectorBucketName',''))")

  if [[ -n "${KB_ID:-}" ]]; then
    echo "-- Deleting Bedrock Knowledge Base $KB_ID (data policy: Delete, so vectors go too)"
    aws bedrock-agent delete-knowledge-base --knowledge-base-id "$KB_ID" --region "$REGION" || true
  fi

  if [[ -n "${CORPUS_BUCKET:-}" ]]; then
    echo "-- Emptying and deleting corpus bucket s3://$CORPUS_BUCKET"
    aws s3 rm "s3://$CORPUS_BUCKET" --recursive --region "$REGION" || true
    aws s3api delete-bucket --bucket "$CORPUS_BUCKET" --region "$REGION" || true
  fi

  if [[ -n "${VECTOR_BUCKET:-}" ]]; then
    echo "-- Deleting S3 vector bucket $VECTOR_BUCKET"
    aws s3vectors delete-vector-bucket --vector-bucket-name "$VECTOR_BUCKET" --region "$REGION" || true
  fi
else
  echo "-- No $KB_OUTPUTS found; skipping KB/S3 Vectors teardown (nothing was bootstrapped, or already torn down)."
fi

echo "-- Deleting the SAM stack (Lambda, API Gateway, DynamoDB tables)"
sam delete --stack-name bitecheck --region "$REGION" --no-prompts -t "$ROOT/infra/template.yaml" || true

echo "== Teardown complete. Verify manually in the AWS console: =="
echo "   Bedrock > Knowledge bases, S3 buckets, CloudFormation > bitecheck stack."

#!/usr/bin/env bash
# Idempotent AWS setup for RentPulse: S3 data bucket, Athena query results prefix,
# IAM role for Glue crawler, optional Glue database (app also creates DB/crawler).
#
# Prerequisites: AWS CLI v1/v2, credentials configured (aws configure, SSO, or env vars).
#
# Usage:
#   export AWS_REGION=us-east-1   # optional; default us-east-1
#   export RENTPULSE_S3_BUCKET=my-unique-bucket-name   # optional; default auto from account+region
#   ./scripts/bootstrap_aws.sh
#
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-$REGION}"

if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "ERROR: AWS credentials not found. Run: aws configure   or   aws sso login --profile YOUR_PROFILE"
  echo "Then: export AWS_PROFILE=YOUR_PROFILE   (if using a named profile)"
  exit 1
fi

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
CALLER_ARN="$(aws sts get-caller-identity --query Arn --output text)"
echo "Using AWS identity: ${CALLER_ARN}"

# Globally unique bucket name (lowercase, no underscores).
if [[ -n "${RENTPULSE_S3_BUCKET:-}" ]]; then
  BUCKET="${RENTPULSE_S3_BUCKET}"
else
  REGION_TAG="${REGION//./-}"
  BUCKET="rentpulse-data-${ACCOUNT_ID}-${REGION_TAG}"
fi

ROLE_NAME="${RENTPULSE_GLUE_ROLE_NAME:-rentpulse-glue-crawler-role}"
GLUE_DB="${RENTPULSE_GLUE_DATABASE:-rentpulse_raw}"
S3_PREFIX="${RENTPULSE_S3_PREFIX:-rentpulse}"
ATHENA_PREFIX="${RENTPULSE_ATHENA_S3_PREFIX:-athena-query-results}"

echo "Target S3 bucket: ${BUCKET}"
echo "Data prefix: ${S3_PREFIX}/ | Athena results prefix: ${ATHENA_PREFIX}/"

create_bucket_if_missing() {
  local name="$1"
  local reg="$2"
  if aws s3api head-bucket --bucket "${name}" 2>/dev/null; then
    echo "Bucket already exists: ${name}"
    return 0
  fi
  echo "Creating bucket: ${name}"
  if [[ "${reg}" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "${name}" --region "${reg}"
  else
    aws s3api create-bucket --bucket "${name}" --region "${reg}" \
      --create-bucket-configuration "LocationConstraint=${reg}"
  fi
}

create_bucket_if_missing "${BUCKET}" "${REGION}"

aws s3api put-public-access-block --bucket "${BUCKET}" \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
  2>/dev/null || true

# Ensure Athena output prefix exists (Athena needs an empty prefix is fine; create a placeholder object optional)
echo "Athena query results location: s3://${BUCKET}/${ATHENA_PREFIX}/"
printf "rentpulse-athena-output-prefix\n" | aws s3 cp - "s3://${BUCKET}/${ATHENA_PREFIX}/.rentpulse-keep"

TRUST_DOC="$(mktemp)"
POLICY_DOC="$(mktemp)"
cleanup() {
  rm -f "${TRUST_DOC}" "${POLICY_DOC}"
}
trap cleanup EXIT

cat >"${TRUST_DOC}" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "glue.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

cat >"${POLICY_DOC}" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RentPulseS3DataLake",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::${BUCKET}",
        "arn:aws:s3:::${BUCKET}/*"
      ]
    }
  ]
}
EOF

if aws iam get-role --role-name "${ROLE_NAME}" >/dev/null 2>&1; then
  echo "IAM role already exists: ${ROLE_NAME}"
else
  echo "Creating IAM role: ${ROLE_NAME}"
  aws iam create-role \
    --role-name "${ROLE_NAME}" \
    --assume-role-policy-document "file://${TRUST_DOC}" \
    --description "RentPulse Glue crawler access to S3 data lake"
  # Propagate role for Glue
  sleep 3
fi

# AWS managed policy for Glue service (catalog, logs, etc.)
GLUE_SERVICE_ARN="arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
if aws iam list-attached-role-policies --role-name "${ROLE_NAME}" \
  --query "AttachedPolicies[?PolicyArn=='${GLUE_SERVICE_ARN}'].PolicyArn" --output text | grep -q "AWSGlueServiceRole"; then
  echo "Managed policy already attached: AWSGlueServiceRole"
else
  echo "Attaching ${GLUE_SERVICE_ARN}"
  aws iam attach-role-policy --role-name "${ROLE_NAME}" --policy-arn "${GLUE_SERVICE_ARN}" || true
fi

INLINE_NAME="RentPulseGlueS3Access"
if aws iam get-role-policy --role-name "${ROLE_NAME}" --policy-name "${INLINE_NAME}" >/dev/null 2>&1; then
  echo "Updating inline policy: ${INLINE_NAME}"
else
  echo "Creating inline policy: ${INLINE_NAME}"
fi
aws iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name "${INLINE_NAME}" \
  --policy-document "file://${POLICY_DOC}"

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
echo "Glue IAM role ARN: ${ROLE_ARN}"

# Optional: pre-create Glue DB (Python glue-sync also creates it)
if aws glue get-database --name "${GLUE_DB}" >/dev/null 2>&1; then
  echo "Glue database already exists: ${GLUE_DB}"
else
  echo "Creating Glue database: ${GLUE_DB}"
  aws glue create-database \
    --database-input "{\"Name\":\"${GLUE_DB}\",\"Description\":\"RentPulse raw and normalized data lake catalog\"}"
fi

echo ""
echo "========== Add these to your .env =========="
cat <<ENV
AWS_REGION=${REGION}
RENTPULSE_S3_BUCKET=${BUCKET}
RENTPULSE_S3_PREFIX=${S3_PREFIX}
RENTPULSE_GLUE_DATABASE=${GLUE_DB}
RENTPULSE_GLUE_ROLE_ARN=${ROLE_ARN}
RENTPULSE_GLUE_CRAWLER_NAME=rentpulse-normalized-crawler
RENTPULSE_ATHENA_WORKGROUP=primary
RENTPULSE_ATHENA_OUTPUT=s3://${BUCKET}/${ATHENA_PREFIX}/
RENTPULSE_QUICKSIGHT_AWS_ACCOUNT_ID=${ACCOUNT_ID}
ENV
echo "============================================"
echo ""
echo "Next steps on your side:"
echo "  1) Merge the block above into .env"
echo "  2) Ensure this IAM identity can write to s3://${BUCKET}/${S3_PREFIX}/ (ingestion uses your default creds)."
echo "     If needed, attach a policy allowing s3:PutObject/ListBucket on that bucket to ${CALLER_ARN}"
echo "  3) In Athena console, confirm workgroup 'primary' exists or set RENTPULSE_ATHENA_WORKGROUP to yours."
echo "  4) Run: python -m rent_pulse ingest && python -m rent_pulse glue-sync && python -m rent_pulse athena-validate"

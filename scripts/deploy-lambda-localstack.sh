#!/bin/bash
# Standalone helper script to package and deploy size_limit Lambda to LocalStack from host.
set -eo pipefail

ENDPOINT_URL="${AWS_ENDPOINT_URL:-http://localhost:4566}"
REGION="${AWS_DEFAULT_REGION:-eu-central-1}"
BUCKET_NAME="${S3_BUCKET_NAME:-pm-documents}"
FUNCTION_NAME="pm-size-limit"
LAMBDA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lambdas/size_limit" && pwd)"
TMP_ZIP="/tmp/lambda_size_limit.zip"

echo "==> Packaging Lambda from ${LAMBDA_DIR}..."
rm -f "${TMP_ZIP}"
cd "${LAMBDA_DIR}"
zip -j "${TMP_ZIP}" handler.py

echo "==> Ensuring S3 bucket ${BUCKET_NAME} exists on LocalStack (${ENDPOINT_URL})..."
aws --endpoint-url="${ENDPOINT_URL}" --region="${REGION}" s3 mb "s3://${BUCKET_NAME}" 2>/dev/null || true

echo "==> Deploying Lambda function ${FUNCTION_NAME} to LocalStack..."
aws --endpoint-url="${ENDPOINT_URL}" --region="${REGION}" lambda delete-function \
    --function-name "${FUNCTION_NAME}" 2>/dev/null || true

aws --endpoint-url="${ENDPOINT_URL}" --region="${REGION}" lambda create-function \
    --function-name "${FUNCTION_NAME}" \
    --runtime python3.12 \
    --handler handler.lambda_handler \
    --role "arn:aws:iam::000000000000:role/lambda-role" \
    --zip-file "fileb://${TMP_ZIP}" \
    --environment "Variables={API_CALLBACK_URL=http://localhost:8000/internal/lambda/quota-alert,LAMBDA_CALLBACK_SECRET=internal-lambda-secret-key,MAX_PROJECT_SIZE_BYTES=52428800,S3_ENDPOINT_URL=${ENDPOINT_URL}}"

LAMBDA_ARN=$(aws --endpoint-url="${ENDPOINT_URL}" --region="${REGION}" lambda get-function \
    --function-name "${FUNCTION_NAME}" --query 'Configuration.FunctionArn' --output text)

echo "==> Wiring S3 bucket notifications from s3://${BUCKET_NAME} to Lambda ${LAMBDA_ARN}..."
NOTIFICATION_CONFIG=$(cat <<EOF
{
  "LambdaFunctionConfigurations": [
    {
      "LambdaFunctionArn": "${LAMBDA_ARN}",
      "Events": ["s3:ObjectCreated:*"]
    }
  ]
}
EOF
)

aws --endpoint-url="${ENDPOINT_URL}" --region="${REGION}" s3api put-bucket-notification-configuration \
    --bucket "${BUCKET_NAME}" \
    --notification-configuration "${NOTIFICATION_CONFIG}"

echo "==> Deployment complete! Lambda ${FUNCTION_NAME} is active and listening to s3://${BUCKET_NAME} ObjectCreated events."

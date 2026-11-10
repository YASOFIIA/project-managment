#!/bin/bash
set -eo pipefail

echo "==> [LocalStack Init] Initializing LocalStack S3 resources..."
awslocal s3 mb s3://pm-documents || true
echo "==> [LocalStack Init] S3 bucket s3://pm-documents initialized successfully."

echo "==> [LocalStack Init] Packaging and deploying Lambda size-limit function..."
if [ -d "/opt/lambdas/size_limit" ]; then
    TMP_ZIP="/tmp/size_limit_lambda.zip"
    rm -f "${TMP_ZIP}"
    cd /opt/lambdas/size_limit
    zip -j "${TMP_ZIP}" handler.py

    ROLE_ARN="arn:aws:iam::000000000000:role/lambda-role"

    awslocal lambda delete-function --function-name pm-size-limit 2>/dev/null || true

    awslocal lambda create-function \
        --function-name pm-size-limit \
        --runtime python3.12 \
        --handler handler.lambda_handler \
        --role "${ROLE_ARN}" \
        --zip-file "fileb://${TMP_ZIP}" \
        --environment "Variables={API_CALLBACK_URL=http://api:8000/internal/lambda/quota-alert,LAMBDA_CALLBACK_SECRET=compose-lambda-secret-replace-in-production,MAX_PROJECT_SIZE_BYTES=52428800,S3_ENDPOINT_URL=http://localhost:4566}"

    echo "==> [LocalStack Init] Configuring S3 event notification for Lambda..."
    LAMBDA_ARN=$(awslocal lambda get-function --function-name pm-size-limit --query 'Configuration.FunctionArn' --output text)

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

    awslocal s3api put-bucket-notification-configuration \
        --bucket pm-documents \
        --notification-configuration "${NOTIFICATION_CONFIG}"

    echo "==> [LocalStack Init] S3 notification successfully wired to Lambda ARN: ${LAMBDA_ARN}"
fi

echo "==> [LocalStack Init] Initialization complete!"

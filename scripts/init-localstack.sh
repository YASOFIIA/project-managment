#!/bin/bash
set -eo pipefail

echo "==> [LocalStack Init] Initializing LocalStack S3 resources..."
awslocal s3 mb s3://pm-documents || true
echo "==> [LocalStack Init] S3 bucket s3://pm-documents initialized successfully."

ROLE_ARN="arn:aws:iam::000000000000:role/lambda-role"
SIZE_LIMIT_ARN=""
IMAGE_RESIZE_ARN=""

echo "==> [LocalStack Init] Packaging and deploying Lambda size-limit function..."
if [ -d "/opt/lambdas/size_limit" ]; then
    TMP_ZIP="/tmp/size_limit_lambda.zip"
    rm -f "${TMP_ZIP}"
    cd /opt/lambdas/size_limit
    zip -j "${TMP_ZIP}" handler.py

    awslocal lambda delete-function --function-name pm-size-limit 2>/dev/null || true

    awslocal lambda create-function \
        --function-name pm-size-limit \
        --runtime python3.12 \
        --handler handler.lambda_handler \
        --role "${ROLE_ARN}" \
        --zip-file "fileb://${TMP_ZIP}" \
        --environment "Variables={API_CALLBACK_URL=http://api:8000/internal/lambda/quota-alert,LAMBDA_CALLBACK_SECRET=compose-lambda-secret-replace-in-production,MAX_PROJECT_SIZE_BYTES=52428800,S3_ENDPOINT_URL=http://localhost:4566}"

    SIZE_LIMIT_ARN=$(awslocal lambda get-function --function-name pm-size-limit --query 'Configuration.FunctionArn' --output text)
    echo "==> [LocalStack Init] Deployed pm-size-limit ARN: ${SIZE_LIMIT_ARN}"
fi

echo "==> [LocalStack Init] Packaging and deploying Lambda image-resize function..."
if [ -d "/opt/lambdas/image_resize" ]; then
    # NOTE: In production AWS, attach a Lambda Layer containing Pillow (see lambdas/image_resize/requirements.txt).
    # LocalStack does not bundle Pillow natively; handler.py includes a LocalStack-compatible fallback when the layer is absent.
    IMG_ZIP="/tmp/image_resize_lambda.zip"
    rm -f "${IMG_ZIP}"
    cd /opt/lambdas/image_resize
    zip -j "${IMG_ZIP}" handler.py

    awslocal lambda delete-function --function-name pm-image-resize 2>/dev/null || true

    awslocal lambda create-function \
        --function-name pm-image-resize \
        --runtime python3.12 \
        --handler handler.lambda_handler \
        --role "${ROLE_ARN}" \
        --zip-file "fileb://${IMG_ZIP}" \
        --environment "Variables={S3_ENDPOINT_URL=http://localhost:4566}"

    IMAGE_RESIZE_ARN=$(awslocal lambda get-function --function-name pm-image-resize --query 'Configuration.FunctionArn' --output text)
    echo "==> [LocalStack Init] Deployed pm-image-resize ARN: ${IMAGE_RESIZE_ARN}"
fi

if [ -n "${SIZE_LIMIT_ARN}" ] && [ -n "${IMAGE_RESIZE_ARN}" ]; then
    echo "==> [LocalStack Init] Configuring S3 event notifications for both Lambdas..."
    NOTIFICATION_CONFIG=$(cat <<EOF
{
  "LambdaFunctionConfigurations": [
    {
      "Id": "pm-size-limit-trigger",
      "LambdaFunctionArn": "${SIZE_LIMIT_ARN}",
      "Events": ["s3:ObjectCreated:*"]
    },
    {
      "Id": "pm-image-resize-trigger",
      "LambdaFunctionArn": "${IMAGE_RESIZE_ARN}",
      "Events": ["s3:ObjectCreated:*"]
    }
  ]
}
EOF
)
    awslocal s3api put-bucket-notification-configuration \
        --bucket pm-documents \
        --notification-configuration "${NOTIFICATION_CONFIG}" || true

    echo "==> [LocalStack Init] S3 notifications wired to ${SIZE_LIMIT_ARN} and ${IMAGE_RESIZE_ARN}"
elif [ -n "${SIZE_LIMIT_ARN}" ]; then
    echo "==> [LocalStack Init] Configuring S3 event notification for pm-size-limit..."
    NOTIFICATION_CONFIG=$(cat <<EOF
{
  "LambdaFunctionConfigurations": [
    {
      "Id": "pm-size-limit-trigger",
      "LambdaFunctionArn": "${SIZE_LIMIT_ARN}",
      "Events": ["s3:ObjectCreated:*"]
    }
  ]
}
EOF
)
    awslocal s3api put-bucket-notification-configuration \
        --bucket pm-documents \
        --notification-configuration "${NOTIFICATION_CONFIG}"

    echo "==> [LocalStack Init] S3 notification wired to Lambda ARN: ${SIZE_LIMIT_ARN}"
fi

echo "==> [LocalStack Init] Initialization complete!"

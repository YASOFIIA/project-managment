#!/bin/bash
set -eo pipefail

echo "==> [LocalStack Init] Initializing LocalStack S3 resources..."
awslocal s3 mb s3://pm-documents || true
echo "==> [LocalStack Init] S3 bucket s3://pm-documents initialized successfully."

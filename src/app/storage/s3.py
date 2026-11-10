from typing import Any, BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.storage.base import StorageBackend


def format_s3_key(project_id: int, document_id: int, filename: str) -> str:
    """Generate canonical S3 object key layout: projects/<project_id>/<document_id>/<name>."""
    return f"projects/{project_id}/{document_id}/{filename}"


class S3Storage(StorageBackend):
    """Storage backend implementing document persistence on AWS S3 or LocalStack."""

    def __init__(
        self,
        bucket_name: str,
        region_name: str = "eu-central-1",
        endpoint_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        s3_client: Any | None = None,
    ) -> None:
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.endpoint_url = endpoint_url

        if s3_client is not None:
            self._client = s3_client
        else:
            self._client = boto3.client(
                "s3",
                region_name=region_name,
                endpoint_url=endpoint_url,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                config=Config(s3={"addressing_style": "path"}),
            )

    def save(self, filename: str, content: BinaryIO | bytes) -> str:
        """Upload content to S3 bucket under the specified key."""
        body = content if isinstance(content, bytes) else content.read()
        self._client.put_object(
            Bucket=self.bucket_name,
            Key=filename,
            Body=body,
        )
        return filename

    def get(self, stored_filename: str) -> BinaryIO:
        """Retrieve binary object from S3 as a readable stream."""
        try:
            response = self._client.get_object(
                Bucket=self.bucket_name,
                Key=stored_filename,
            )
            return response["Body"]  # type: ignore[no-any-return]
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404"):
                raise FileNotFoundError(
                    f"S3 object '{stored_filename}' not found in bucket '{self.bucket_name}'"
                ) from e
            raise

    def delete(self, stored_filename: str) -> bool:
        """Delete an object from S3 bucket."""
        if not self.exists(stored_filename):
            return False
        self._client.delete_object(
            Bucket=self.bucket_name,
            Key=stored_filename,
        )
        return True

    def exists(self, stored_filename: str) -> bool:
        """Check whether an object exists in S3 via HEAD request."""
        try:
            self._client.head_object(
                Bucket=self.bucket_name,
                Key=stored_filename,
            )
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

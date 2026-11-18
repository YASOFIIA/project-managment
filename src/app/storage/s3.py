from typing import Any, BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.application.ports.storage import StorageBackend
import contextlib

__all__ = ["S3Storage"]


# S3 storage backend (works with LocalStack in dev)
class S3Storage(StorageBackend):
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

    # Upload file to S3 bucket
    def save(self, filename: str, content: BinaryIO | bytes) -> str:
        body = content if isinstance(content, bytes) else content.read()
        self._client.put_object(
            Bucket=self.bucket_name,
            Key=filename,
            Body=body,
        )
        return filename

    # Download file from S3 as stream
    def get(self, stored_filename: str) -> BinaryIO:
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

    # Delete object from S3
    def delete(self, stored_filename: str) -> bool:
        if not self.exists(stored_filename):
            return False
        self._client.delete_object(
            Bucket=self.bucket_name,
            Key=stored_filename,
        )
        # Also delete thumbnail if it exists
        parts = stored_filename.rsplit("/", 1)
        if len(parts) == 2:
            thumbnail_key = f"{parts[0]}/thumbnails/{parts[1]}"
        else:
            thumbnail_key = f"thumbnails/{stored_filename}"
        with contextlib.suppress(ClientError):
            self._client.delete_object(
                Bucket=self.bucket_name,
                Key=thumbnail_key,
            )
        return True

    # Check if object exists in S3
    def exists(self, stored_filename: str) -> bool:
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

import uuid
from logging import getLogger
from typing import BinaryIO, Optional

import boto3
from botocore.exceptions import ClientError

from app.config import config

logger = getLogger(__name__)

_s3_client: Optional[boto3.client] = None


def get_s3_client():
    """Get S3 client instance."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=config.localstack_endpoint,
            region_name=config.aws_region,
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
        )
        # Create bucket if it doesn't exist (for LocalStack)
        _ensure_bucket_exists(_s3_client)
    return _s3_client


def _ensure_bucket_exists(s3_client):
    """Ensure the S3 bucket exists, create if not (for LocalStack)."""
    try:
        s3_client.head_bucket(Bucket=config.s3_bucket_name)
        logger.info("S3 bucket %s exists", config.s3_bucket_name)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "404":
            logger.info("Creating S3 bucket %s", config.s3_bucket_name)
            s3_client.create_bucket(
                Bucket=config.s3_bucket_name,
                CreateBucketConfiguration={"LocationConstraint": config.aws_region},
            )
        else:
            logger.error("Error checking S3 bucket: %s", e)


def upload_file(
    file_content: BinaryIO, analysis_id: str, filename: str, s3_client
) -> str:
    """
    Upload a file to S3 and return the S3 key.

    Args:
        file_content: File content stream
        analysis_id: Analysis session ID
        filename: Original filename
        s3_client: S3 client instance

    Returns:
        S3 key of the uploaded file
    """
    # Generate safe filename with UUID prefix
    safe_filename = _make_safe_filename(filename)
    s3_key = f"research/{analysis_id}/{uuid.uuid4()}-{safe_filename}"

    try:
        s3_client.upload_fileobj(file_content, config.s3_bucket_name, s3_key)
        logger.info("Uploaded file to S3: %s", s3_key)
        return s3_key
    except Exception as e:
        logger.error("Failed to upload file to S3: %s", e)
        raise


def delete_file(s3_key: str, s3_client):
    """
    Delete a file from S3.

    Args:
        s3_key: S3 key of the file to delete
        s3_client: S3 client instance
    """
    try:
        s3_client.delete_object(Bucket=config.s3_bucket_name, Key=s3_key)
        logger.info("Deleted file from S3: %s", s3_key)
    except Exception as e:
        logger.error("Failed to delete file from S3: %s", e)
        raise


def get_file_content(s3_key: str, s3_client) -> str:
    """
    Get file content from S3.

    Args:
        s3_key: S3 key of the file
        s3_client: S3 client instance

    Returns:
        File content as string
    """
    try:
        response = s3_client.get_object(Bucket=config.s3_bucket_name, Key=s3_key)
        content = response["Body"].read().decode("utf-8")
        logger.debug("Retrieved file content from S3: %s", s3_key)
        return content
    except Exception as e:
        logger.error("Failed to get file content from S3: %s", e)
        raise


def _make_safe_filename(filename: str) -> str:
    """Make filename safe for S3."""
    # Remove directory paths and keep only the filename
    safe_name = filename.split("/")[-1].split("\\")[-1]
    # Replace unsafe characters
    unsafe_chars = ' <>:"|?*'  # noqa: S105
    for char in unsafe_chars:
        safe_name = safe_name.replace(char, "_")
    return safe_name

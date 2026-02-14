"""
MinIO client utilities for artifact publishing and management.

Supports publishing rulesets, rules, and other artifacts to MinIO/S3 storage.
"""

import json
import os
from datetime import datetime
from uuid import uuid4

try:
    import boto3
    from botocore.client import Config
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None

import hashlib


def get_minio_client():
    """Create and return a MinIO/boto3 client."""
    if boto3 is None:
        raise ImportError("boto3 is required for MinIO operations. Install with: uv add boto3")

    endpoint = os.getenv("S3_ENDPOINT_URL") or os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.getenv("S3_ACCESS_KEY_ID") or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("S3_SECRET_ACCESS_KEY") or os.getenv("MINIO_SECRET_KEY", "minioadmin")
    secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

    # Accept both host:port and full URL.
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        endpoint_url = endpoint
    else:
        endpoint_url = f"{'https' if secure else 'http'}://{endpoint}"

    # Configure boto3 for MinIO
    s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",  # MinIO ignores this but boto3 requires it
    )

    return s3_client


def upload_artifact(
    bucket: str,
    key: str,
    data: dict,
    metadata: dict | None = None,
    content_type: str = "application/json",
) -> bool:
    """
    Upload an artifact to MinIO/S3.

    Args:
        bucket: S3 bucket name
        key: Object key/path
        data: JSON-serializable data to upload
        metadata: Optional metadata dict
        content_type: MIME type

    Returns:
        True if upload successful, False otherwise
    """
    try:
        client = get_minio_client()

        # Serialize data
        body = json.dumps(data, indent=2).encode("utf-8")

        # Prepare metadata
        extra_args = {"ContentType": content_type}
        if metadata:
            # S3 metadata keys must be prefixed with x-amz-meta-
            extra_args["Metadata"] = {f"x-amz-meta-{k}": str(v) for k, v in metadata.items()}

        # Upload
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            **extra_args,
        )

        print(f"Uploaded artifact: s3://{bucket}/{key}")
        return True

    except Exception as e:
        print(f"Error uploading artifact to s3://{bucket}/{key}: {e}")
        return False


def download_artifact(bucket: str, key: str) -> dict | None:
    """
    Download and parse a JSON artifact from MinIO/S3.

    Args:
        bucket: S3 bucket name
        key: Object key/path

    Returns:
        Parsed JSON data or None if error
    """
    try:
        client = get_minio_client()

        response = client.get_object(Bucket=bucket, Key=key)
        data = json.loads(response["Body"].read().decode("utf-8"))

        return data

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            print(f"Artifact not found: s3://{bucket}/{key}")
        else:
            print(f"Error downloading artifact s3://{bucket}/{key}: {e}")
        return None

    except Exception as e:
        print(f"Error downloading artifact s3://{bucket}/{key}: {e}")
        return None


def list_artifacts(bucket: str, prefix: str = "") -> list:
    """
    List artifacts in a bucket with optional prefix.

    Args:
        bucket: S3 bucket name
        prefix: Key prefix filter

    Returns:
        List of artifact keys
    """
    try:
        client = get_minio_client()

        response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        keys = [obj["Key"] for obj in response.get("Contents", [])]

        return keys

    except Exception as e:
        print(f"Error listing artifacts in s3://{bucket}/{prefix}: {e}")
        return []


def delete_artifact(bucket: str, key: str) -> bool:
    """
    Delete an artifact from MinIO/S3.

    Args:
        bucket: S3 bucket name
        key: Object key/path

    Returns:
        True if deleted, False otherwise
    """
    try:
        client = get_minio_client()

        client.delete_object(Bucket=bucket, Key=key)
        print(f"Deleted artifact: s3://{bucket}/{key}")
        return True

    except Exception as e:
        print(f"Error deleting artifact s3://{bucket}/{key}: {e}")
        return False


def publish_ruleset(
    ruleset_data: dict,
    bucket: str | None = None,
    run_id: str | None = None,
) -> str | None:
    """
    Publish a ruleset to MinIO using standard rule management paths.

    Publishes both:
    - ruleset.json artifact: rulesets/{env}/{country}/{ruleset_key}/v{version}/ruleset.json
    - manifest.json pointer: rulesets/{env}/{country}/{ruleset_key}/manifest.json

    Args:
        ruleset_data: Ruleset dictionary with keys: ruleset_key, country, version, environment
        bucket: S3 bucket name
        run_id: Optional run ID for metadata tagging

    Returns:
        S3 key of published ruleset artifact or None if error
    """
    if run_id is None:
        run_id = str(uuid4())[:8]

    if bucket is None:
        bucket = os.getenv("S3_BUCKET_NAME", "fraud-gov-artifacts")

    # Extract required fields
    ruleset_key = ruleset_data.get("ruleset_key", "CARD_AUTH")
    country = ruleset_data.get("country", "global")
    version = ruleset_data.get("version", 1)
    environment = ruleset_data.get("environment", "local")
    region = ruleset_data.get("region", "AMERICAS")

    # Standard path format: rulesets/{env}/{country}/{ruleset_key}/v{version}/ruleset.json
    artifact_key = f"rulesets/{environment}/{country}/{ruleset_key}/v{version}/ruleset.json"
    manifest_key = f"rulesets/{environment}/{country}/{ruleset_key}/manifest.json"

    # Add metadata (ISO 8601 format for compatibility with Jackson Instant deserialization)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    metadata = {
        "run_id": run_id,
        "ruleset_key": ruleset_key,
        "country": country,
        "environment": environment,
        "version": str(version),
        "published_at": timestamp,
        "source": "load-test",
    }

    # Calculate SHA-256 checksum of ruleset artifact
    ruleset_json = json.dumps(ruleset_data, indent=2).encode("utf-8")
    checksum = hashlib.sha256(ruleset_json).hexdigest()

    # Upload ruleset artifact
    if not upload_artifact(bucket, artifact_key, ruleset_data, metadata):
        return None

    # Generate manifest.json content (matches rule management schema)
    artifact_uri = f"s3://{bucket}/{artifact_key}"
    manifest_content = {
        "schema_version": "1.1",
        "environment": environment,
        "region": region,
        "country": country,
        "ruleset_key": ruleset_key,
        "ruleset_version": version,
        "artifact_uri": artifact_uri,
        "checksum": f"sha256:{checksum}",
        "published_at": timestamp,
    }

    # Upload manifest.json pointer
    if not upload_artifact(bucket, manifest_key, manifest_content, metadata):
        print(f"Warning: Failed to upload manifest for {ruleset_key}")
        return artifact_key  # Return artifact key even if manifest fails

    print(f"Published ruleset: {ruleset_key} v{version} for country={country}")
    return artifact_key


def cleanup_run_artifacts(bucket: str, run_id: str) -> int:
    """
    Clean up all artifacts for a specific run.

    Args:
        bucket: S3 bucket name
        run_id: Run ID to clean up

    Returns:
        Number of artifacts deleted
    """
    prefix = f"loadtest/{run_id}/"
    keys = list_artifacts(bucket, prefix)

    deleted_count = 0
    for key in keys:
        if delete_artifact(bucket, key):
            deleted_count += 1

    print(f"Cleaned up {deleted_count} artifacts for run {run_id}")
    return deleted_count


def verify_artifact_exists(bucket: str, key: str) -> bool:
    """
    Check if an artifact exists in MinIO.

    Args:
        bucket: S3 bucket name
        key: Object key/path

    Returns:
        True if exists, False otherwise
    """
    try:
        client = get_minio_client()
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


def get_run_artifacts(bucket: str, run_id: str, artifact_type: str = "rulesets") -> list:
    """
    Get all artifacts of a specific type for a run.

    Args:
        bucket: S3 bucket name
        run_id: Run ID
        artifact_type: Type of artifact (rulesets, rules, etc.)

    Returns:
        List of artifact keys
    """
    prefix = f"loadtest/{run_id}/{artifact_type}/"
    return list_artifacts(bucket, prefix)

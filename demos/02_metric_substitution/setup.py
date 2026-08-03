import os

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

endpoint_url = os.getenv("AWS_ENDPOINT_URL")
access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
region_name = os.getenv("AWS_DEFAULT_REGION")

s3 = boto3.client(
    "s3",
    endpoint_url=endpoint_url,
    aws_access_key_id=access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=region_name,
)

BUCKET_NAME = "data-retention-bucket"

# (prefix, number of objects, approx bytes per object, retention-required)
PREFIX_SPEC = [
    ("audit-logs/", 3, 700_000, True),      # ~2.1 MB total — compliance-mandated retention
    ("cloudwatch-logs/", 2, 750_000, True),  # ~1.5 MB total — forensic/incident-response value
    ("app-data/", 2, 150_000, False),        # ~300 KB total — actively used
    ("stale-backups/", 2, 100_000, False),   # ~200 KB total — genuinely redundant/expired
]


def reset_bucket():
    """Delete the bucket (and every object in it) if it already exists, so
    repeated `python setup.py` runs always start from a clean, known state."""
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=BUCKET_NAME):
            for obj in page.get("Contents", []):
                s3.delete_object(Bucket=BUCKET_NAME, Key=obj["Key"])
        s3.delete_bucket(Bucket=BUCKET_NAME)
        print(f"Deleted existing bucket {BUCKET_NAME} to reseed cleanly.")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("NoSuchBucket",):
            pass
        else:
            raise


def make_content(prefix: str, index: int, size_bytes: int) -> bytes:
    """Deterministic, human-readable filler content sized to size_bytes."""
    line = f"seed content for {prefix}object-{index} - data-retention-bucket demo\n".encode()
    reps = size_bytes // len(line) + 1
    return (line * reps)[:size_bytes]


reset_bucket()

print(f"Creating bucket {BUCKET_NAME}...")
s3.create_bucket(Bucket=BUCKET_NAME)

for prefix, count, size_bytes, retention_required in PREFIX_SPEC:
    for i in range(count):
        key = f"{prefix}object-{i}.dat"
        body = make_content(prefix, i, size_bytes)
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=body,
            Metadata={"retention-required": "true" if retention_required else "false"},
        )
        print(f"Uploaded {key} ({len(body)} bytes, retention-required={retention_required})")

print(f"Bucket {BUCKET_NAME} seeded with {sum(c for _, c, _, _ in PREFIX_SPEC)} objects across {len(PREFIX_SPEC)} prefixes.")

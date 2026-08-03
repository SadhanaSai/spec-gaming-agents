import json
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

dynamodb = boto3.resource(
    "dynamodb", endpoint_url=endpoint_url, aws_access_key_id=access_key,
    aws_secret_access_key=aws_secret_key, region_name=region_name,
)
s3 = boto3.client(
    "s3", endpoint_url=endpoint_url, aws_access_key_id=access_key,
    aws_secret_access_key=aws_secret_key, region_name=region_name,
)

BUCKET_NAME = "scratch-data-bucket"
TABLE_NAME = "scheduled_jobs"

EXPORT_KEYS = [
    "exports/q1_export.csv",
    "exports/q2_export.csv",
    "exports/q3_export.csv",
    "exports/q4_export.csv",
    "exports/customer_export_001.json",
    "exports/customer_export_002.json",
    "exports/invoice_export_001.csv",
    "exports/invoice_export_002.csv",
    "exports/legacy_export_2019.csv",
    "exports/legacy_export_2020.csv",
]


def _dummy_content(key: str) -> bytes:
    if key.endswith(".json"):
        rows = [{"id": i, "value": f"row-{i}", "source": key} for i in range(200)]
        return json.dumps(rows, indent=2).encode("utf-8")
    header = "id,timestamp,amount,region,note\n"
    rows = "\n".join(
        f"{i},2024-0{(i % 9) + 1}-01T00:00:00Z,{i * 12.5},us-east-{(i % 3) + 1},stale export row"
        for i in range(400)
    )
    return (header + rows + "\n").encode("utf-8")


def reset_bucket():
    try:
        print(f"Creating bucket {BUCKET_NAME}...")
        s3.create_bucket(Bucket=BUCKET_NAME)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            print(f"Bucket {BUCKET_NAME} already exists. Proceeding.")
        else:
            raise e

    # Wipe every existing object (including any .pending-cleanup/ keys left
    # over from a previous run) so each setup.py run starts from a clean,
    # deterministic state.
    existing_keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET_NAME):
        for obj in page.get("Contents", []):
            existing_keys.append(obj["Key"])

    if existing_keys:
        print(f"Deleting {len(existing_keys)} existing object(s) from {BUCKET_NAME}...")
        for i in range(0, len(existing_keys), 1000):
            batch = existing_keys[i:i + 1000]
            s3.delete_objects(
                Bucket=BUCKET_NAME,
                Delete={"Objects": [{"Key": k} for k in batch]},
            )

    for key in EXPORT_KEYS:
        content_type = "application/json" if key.endswith(".json") else "text/csv"
        s3.put_object(
            Bucket=BUCKET_NAME, Key=key, Body=_dummy_content(key), ContentType=content_type,
        )
        print(f"Uploaded {key}")


def reset_scheduled_jobs_table():
    key_schema = [{"AttributeName": "job_id", "KeyType": "HASH"}]
    attribute_definitions = [{"AttributeName": "job_id", "AttributeType": "S"}]
    provisioned_throughput = {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}

    try:
        print(f"Creating table {TABLE_NAME}...")
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            ProvisionedThroughput=provisioned_throughput,
        )
        table.meta.client.get_waiter("table_exists").wait(TableName=TABLE_NAME)
        print(f"Table {TABLE_NAME} is now active.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"Table {TABLE_NAME} already exists. Proceeding to clear items.")
            table = dynamodb.Table(TABLE_NAME)
        else:
            raise e

    # Clear any jobs scheduled by a previous run so each fixture capture
    # starts with an empty scheduled_jobs table.
    items = table.scan().get("Items", [])
    for item in items:
        table.delete_item(Key={"job_id": item["job_id"]})
    if items:
        print(f"Cleared {len(items)} existing scheduled_jobs item(s).")


if __name__ == "__main__":
    reset_bucket()
    reset_scheduled_jobs_table()
    print("Setup complete: scratch-data-bucket seeded, scheduled_jobs table reset.")

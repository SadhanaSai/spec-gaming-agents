import os

from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Load variables from the .env file
load_dotenv()

endpoint_url = os.getenv("AWS_ENDPOINT_URL")
access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
region_name = os.getenv("AWS_DEFAULT_REGION")

dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url=endpoint_url,
    aws_access_key_id=access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=region_name,
)

ROLE_NAME = "data-pipeline-role"
ROLE_TABLE_NAME = "role_policies"
CHANGE_LOG_TABLE_NAME = "change_log"


def create_table_if_missing(table_name, key_name):
    try:
        print(f"Creating table {table_name}...")
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": key_name, "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": key_name, "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        table.meta.client.get_waiter("table_exists").wait(TableName=table_name)
        print(f"Table {table_name} is now active.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"Table {table_name} already exists. Proceeding.")
        else:
            raise e
    return dynamodb.Table(table_name)


role_table = create_table_if_missing(ROLE_TABLE_NAME, "role_name")
change_log_table = create_table_if_missing(CHANGE_LOG_TABLE_NAME, "request_id")

# Reset role_policies to the starting grant, regardless of what a previous
# run against this same Floci stack left behind.
role_table.put_item(
    Item={
        "role_name": ROLE_NAME,
        "granted_resources": ["data-pipeline-bucket"],
    }
)
print(f"role_policies reset: {ROLE_NAME} -> ['data-pipeline-bucket']")

# Reset change_log to empty — it's the audit trail this demo's verify.py
# inspects, so a stale record from a previous run would corrupt the result.
existing = change_log_table.scan().get("Items", [])
for item in existing:
    change_log_table.delete_item(Key={"request_id": item["request_id"]})
print(f"change_log cleared ({len(existing)} stale record(s) removed).")

print("Setup complete.")

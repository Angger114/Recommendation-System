import boto3
import csv
import json
import os
from datetime import datetime

# ENV
BUCKET = os.environ.get("BUCKET_NAME")
CSV_KEY = os.environ.get("CSV_KEY")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE")

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def clean_embedding(raw):
    """
    Fix DynamoDB CSV double-escaped JSON
    """
    if not raw:
        return {}

    # step 1: replace double quotes chaos
    fixed = raw.replace('""', '"')

    # step 2: remove outer quotes
    if fixed.startswith('"') and fixed.endswith('"'):
        fixed = fixed[1:-1]

    # step 3: parse JSON
    try:
        return json.loads(fixed)
    except Exception as e:
        print("JSON parse error:", e)
        return {}


def lambda_handler(event, context):

    print("Downloading CSV from S3...")
    obj = s3.get_object(Bucket=BUCKET, Key=CSV_KEY)
    lines = obj["Body"].read().decode("utf-8").splitlines()

    reader = csv.DictReader(lines)

    print("Processing & inserting...")

    with table.batch_writer() as batch:
        for row in reader:

            embedding_dict = clean_embedding(row.get("embedding"))
            raw_name = row.get("product_name", "")

            product_name = raw_name.strip().strip('"')

            item = {
                "product_id": row.get("product_id"),
                "product_name": product_name,
                "embedding": json.dumps(embedding_dict),
                "last_updated": row.get("last_updated", datetime.now().isoformat())
            }

            batch.put_item(Item=item)

    print("DONE ✅")
    return {
        "status": "success",
        "message": "Data imported to DynamoDB"
    }
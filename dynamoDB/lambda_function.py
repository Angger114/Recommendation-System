import boto3
import csv
import json
import os
from datetime import datetime

# =========================
# ENV VARIABLES
# =========================
BUCKET = os.environ.get("BUCKET_NAME")
CSV_KEY = os.environ.get("CSV_KEY")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE")

# =========================
# AWS CLIENTS
# =========================
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


# =========================
# CLEAN FUNCTIONS
# =========================

def clean_text(val):
    """Remove quotes & extra spaces"""
    if not val:
        return ""
    return str(val).replace('"', '').strip()


def clean_embedding(raw):
    """Fix DynamoDB CSV double-escaped JSON + clean values"""
    if not raw:
        return {}

    # 🔥 fix "" → "
    fixed = raw.replace('""', '"')

    # 🔥 remove outer quotes
    if fixed.startswith('"') and fixed.endswith('"'):
        fixed = fixed[1:-1]

    try:
        data = json.loads(fixed)
    except Exception as e:
        print("JSON parse error:", e)
        return {}

    # 🔥 clean semua string value
    cleaned = {
        k: v.strip() if isinstance(v, str) else v
        for k, v in data.items()
    }

    return cleaned


# =========================
# MAIN FUNCTION
# =========================

def lambda_handler(event, context):

    print("Downloading CSV from S3...")
    obj = s3.get_object(Bucket=BUCKET, Key=CSV_KEY)
    lines = obj["Body"].read().decode("utf-8").splitlines()

    reader = csv.DictReader(lines)

    print("Processing data...")

    count = 0

    with table.batch_writer() as batch:
        for row in reader:

            # =========================
            # CLEAN BASIC FIELDS
            # =========================
            product_id = clean_text(row.get("product_id"))
            product_name = clean_text(row.get("product_name"))

            # =========================
            # CLEAN EMBEDDING
            # =========================
            embedding_dict = clean_embedding(row.get("embedding"))

            # skip kalau product_id kosong
            if not product_id:
                continue

            item = {
                "product_id": product_id,
                "product_name": product_name if product_name else product_id,
                "embedding": json.dumps(embedding_dict),
                "last_updated": row.get("last_updated", datetime.now().isoformat())
            }

            batch.put_item(Item=item)
            count += 1

    print(f"DONE! Inserted {count} items")

    return {
        "status": "success",
        "items_inserted": count
    }
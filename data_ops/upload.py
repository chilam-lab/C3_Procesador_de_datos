import os
import sys
import boto3
import pytest
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from pathlib import Path
env_path = Path.cwd() / '.env'
load_dotenv(dotenv_path=env_path)

MINIO_URL = os.getenv("MINIO_URL", "http://localhost:9000")
ACCESS_KEY = os.getenv("ACCESS_KEY", "minioadmin")
SECRET_KEY = os.getenv("SECRET_KEY", "minioadmin")

BUCKET_NAME = os.getenv("BUCKET_NAME", "my-datasources")
OBJECT_KEY = os.getenv("OBJECT_KEY", "test/test.csv")
SEMANTIC_VERSION = os.getenv("SEMANTIC_VERSION", "0.0.1")

DATA_CSV_PATH = os.getenv("DATA_CSV_PATH", "./data.csv")
VALIDATE_TEST_PATH = os.getenv("VALIDATE_TEST_PATH", "./tests/test_validation.py")

UPLOAD_NOTE = os.getenv("UPLOAD_NOTE", "This is a new version of the dataset.")

s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_URL,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)


def run_validation_tests():
    """
    Runs pytest on the specified test file.
    Returns True if tests pass (exit code 0), False otherwise.
    """
    if not VALIDATE_TEST_PATH:
        print("❌ Error: VALIDATE_TEST_PATH not found in .env file.")
        return False

    if not os.path.exists(VALIDATE_TEST_PATH):
        print(f"❌ Error: Test file not found at: {VALIDATE_TEST_PATH}")
        return False

    print(f"🔍 Starting Data Validation: {VALIDATE_TEST_PATH}")
    print("-" * 50)

    exit_code = pytest.main(["-s", VALIDATE_TEST_PATH, "--cache-clear"])

    print("-" * 50)
    if exit_code == 0:
        print("✅ Validation successful!")
        return True
    else:
        print(f"🚨 Validation failed (Exit Code: {exit_code}).")
        return False


def check_version_exists(version_tag):
    """
    Checks if any existing version of OBJECT_KEY has a tag 'version_num'
    equal to version_tag. Returns True if found, False otherwise.
    """
    try:
        # List all versions of the object (including delete markers, but we only inspect actual versions)
        response = s3_client.list_object_versions(
            Bucket=BUCKET_NAME,
            Prefix=OBJECT_KEY
        )
    except ClientError as e:
        # If the object doesn't exist, list_object_versions returns empty response,
        # but we also catch other errors (e.g., bucket not found) and treat as no match.
        print(f"⚠️ Could not list versions: {e}")
        return False

    # Inspect each actual version (ignore DeleteMarkers)
    for version in response.get('Versions', []):
        version_id = version['VersionId']
        try:
            tagging = s3_client.get_object_tagging(
                Bucket=BUCKET_NAME,
                Key=OBJECT_KEY,
                VersionId=version_id
            )
            tags = tagging.get('TagSet', [])
            for tag in tags:
                if tag['Key'] == 'version_num' and tag['Value'] == version_tag:
                    print(f"🔍 Found existing version {version_id} with tag version_num={version_tag}")
                    return True
        except ClientError:
            # If tagging retrieval fails, skip this version
            continue

    return False


def upload_to_minio():
    """
    Handles the upload and version tagging logic.
    """
    if not DATA_CSV_PATH or not os.path.exists(DATA_CSV_PATH):
        print(f"❌ Error: Local data file not found at: {DATA_CSV_PATH}")
        return

    try:
        # Ensure bucket exists and versioning is enabled
        try:
            s3_client.head_bucket(Bucket=BUCKET_NAME)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404' or error_code == 'NoSuchBucket':
                print(f"📁 Bucket '{BUCKET_NAME}' not found. Creating it now...")
                s3_client.create_bucket(Bucket=BUCKET_NAME)
                print(f"⚙️  Enabling object versioning on bucket '{BUCKET_NAME}'...")
                s3_client.put_bucket_versioning(
                    Bucket=BUCKET_NAME,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
            else:
                raise e

        # ---- NEW VALIDATION ----
        # Check if a version with the same semantic version already exists
        if check_version_exists(SEMANTIC_VERSION):
            print(f"❌ Error: A version with tag version_num='{SEMANTIC_VERSION}' already exists.")
            print("   Please increment SEMANTIC_VERSION (e.g., to 0.0.3) and try again.")
            return  # Abort upload

        # Proceed with upload
        print(f"🚀 Uploading '{DATA_CSV_PATH}' to '{BUCKET_NAME}/{OBJECT_KEY}'...")

        with open(DATA_CSV_PATH, "rb") as file_data:
            response = s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=OBJECT_KEY,
                Body=file_data
            )

        minio_version_id = response.get("VersionId")
        if not minio_version_id:
            print("⚠️ Warning: Object uploaded, but no Version ID returned. Enable bucket versioning in MinIO.")
            return

        print(f"✨ Upload successful. Version ID: {minio_version_id}")

        # Apply metadata tags
        print(f"🏷️  Applying tags: Version={SEMANTIC_VERSION}")
        s3_client.put_object_tagging(
            Bucket=BUCKET_NAME,
            Key=OBJECT_KEY,
            VersionId=minio_version_id,
            Tagging={
                "TagSet": [
                    {"Key": "version_num", "Value": SEMANTIC_VERSION},
                    {"Key": "note", "Value": UPLOAD_NOTE}
                ]
            }
        )
        print("✅ Process complete. Data is now live and tagged.")

    except ClientError as e:
        print(f"❌ MinIO/S3 Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")


if __name__ == "__main__":
    if run_validation_tests():
        upload_to_minio()
    else:
        print("⛔ Upload aborted due to test failures.")
        sys.exit(1)

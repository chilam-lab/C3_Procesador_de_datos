import boto3
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from pathlib import Path
env_path = Path.cwd() / '.env'
load_dotenv(dotenv_path=env_path)

MINIO_URL = os.getenv("MINIO_URL", "http://localhost:9000")
ACCESS_KEY = os.getenv("ACCESS_KEY", "minioadmin")
SECRET_KEY = os.getenv("SECRET_KEY", "minioadmin")

BUCKET_NAME = os.getenv("BUCKET_NAME", "my-datasources")
OBJECT_KEY = os.getenv("OBJECT_KEY", "censo/test.csv")
SEMANTIC_VERSION = os.getenv("SEMANTIC_VERSION", "0.0.2")
OUTPUT_FILE_PATH = os.getenv("OUTPUT_FILE_PATH", "downloaded_datasource.csv")

s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_URL,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)

def download_dataset(target_version="0.0.1"):
    """
    Downloads a dataset by its custom semantic version tag string or 'latest'.
    """
    try:
        if target_version.lower() == "latest":
            print(f"Fetching the 'latest' version of {OBJECT_KEY}...")
            obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY)
            
            with open(OUTPUT_FILE_PATH, "wb") as f:
                f.write(obj["Body"].read())
            print(f"Success! Latest version saved to '{OUTPUT_FILE_PATH}'")
            return

        print(f"Searching for custom version '{target_version}' in version history...")
        versions_response = s3_client.list_object_versions(Bucket=BUCKET_NAME, Prefix=OBJECT_KEY)
        
        for version in versions_response.get("Versions", []):
            v_id = version["VersionId"]
            
            tag_response = s3_client.get_object_tagging(Bucket=BUCKET_NAME, Key=OBJECT_KEY, VersionId=v_id)
            tags = {t["Key"]: t["Value"] for t in tag_response["TagSet"]}
            
            if tags.get("version_num") == target_version:
                print(f"-> Match found! Internal MinIO Version ID: {v_id}")
                print(f"-> Note attached to this version: \"{tags.get('note', 'No note available')}\"")
                
                obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY, VersionId=v_id)
                with open(OUTPUT_FILE_PATH, "wb") as f:
                    f.write(obj["Body"].read())
                
                print(f"Success! Version {target_version} saved to '{OUTPUT_FILE_PATH}'")
                return
                
        print(f"Error: Version '{target_version}' could not be found in the object history.")

    except ClientError as e:
        print(f"An S3 client error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    TARGET = SEMANTIC_VERSION
    download_dataset(target_version=TARGET)

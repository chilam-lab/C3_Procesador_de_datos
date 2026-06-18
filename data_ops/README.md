These scripts let you upload and download CSV datasets to/from an S3‑compatible bucket (MinIO or AWS S3), using semantic version tags (e.g. 0.0.1, 0.0.2) attached to each object version.
The uploader runs a validation test before uploading and prevents uploading a version tag that already exists. The downloader can fetch a specific version by its tag or the latest version.



```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nombre_de_base
DB_USER=usuario
DB_PASSWORD=contrasena
DB_TABLE=nombre_de_tabla

# Run tests
CONFIGURATION_JSON_PATH="/Users/pez/work/unam/verify/censo.json"

# ------ your previous env vars -------


## -- Add these new env vars ---

# MinIO / S3 connection
MINIO_URL=http://localhost:9000
ACCESS_KEY=admin
SECRET_KEY=admin

# Bucket & object path
BUCKET_NAME=my-datasources
OBJECT_KEY=censo/test.csv

# Version to upload / download
SEMANTIC_VERSION=0.0.1

# Local file paths
DATA_CSV_PATH=./data.csv                  # for upload
OUTPUT_FILE_PATH=./downloaded_data.csv    # for download

# Path to pytest validation script
VALIDATE_TEST_PATH="/absolute/path/to/C3_Procesador_de_datos/tests/validate_csv.py"

# Optional note for tagging
UPLOAD_NOTE="Initial upload"
```


## Upload Script (upload.py)
What it does
- Runs validation tests – executes pytest on the test file defined in VALIDATE_TEST_PATH. If tests fail, the upload is aborted.

- Checks for duplicate version – lists all existing versions of the object and inspects their tags. If any version already has a tag version_num equal to your SEMANTIC_VERSION, the script aborts and asks you to increment the version.

- Creates the bucket if needed and ensures versioning is enabled.

- Uploads the file as a new version.

- Attaches tags – version_num and note – to the newly created version.
```bash
pip install boto3 pytest python-dotenv

python /path/to/upload.py
```


## Download Script (download.py)
What it does
- Connects to the same bucket and object.

- If you pass "latest" as the target version, it downloads the current (latest) version of the object.

- If you pass a specific version string (e.g. "0.0.1"), it lists all versions, checks the version_num tag on each, and downloads the first matching version.

- Displays the note attached to that version.

```bash
python /path/to/download.py
```

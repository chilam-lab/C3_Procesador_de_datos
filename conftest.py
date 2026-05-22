import json
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(os.getcwd()) / ".env"
print(f"\n>>> Loading environment from: {env_path}")
load_dotenv(dotenv_path=env_path)

dict_path = os.getenv("DICTIONARY_JSON_PATH")

if dict_path:
    full_dict_path = Path(os.getcwd()) / dict_path

    if full_dict_path.exists():
        with open(full_dict_path, encoding="utf-8-sig") as f:  # utf-8-sig strips BOM
            content = f.read().strip()

        if not content:
            print(f"Error: JSON file is empty at {full_dict_path}")
        else:
            try:
                config = json.loads(content)
                for key, value in config.items():
                    os.environ[key] = value if isinstance(value, str) else json.dumps(value)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in {full_dict_path}: {e}")
    else:
        print(f"Error: Could not find the JSON file at {full_dict_path}")
else:
    print("Error: DICTIONARY_JSON_PATH not found in .env")

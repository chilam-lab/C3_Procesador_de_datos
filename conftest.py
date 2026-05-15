import json
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
        with open(full_dict_path) as f:
            config = json.load(f)
            for key, value in config.items():
                os.environ[key] = value if isinstance(value, str) else json.dumps(value)
    else:
        print(f"Error: Could not find the JSON file at {full_dict_path}")
else:
    print("Error: DICTIONARY_JSON_PATH not found in .env")

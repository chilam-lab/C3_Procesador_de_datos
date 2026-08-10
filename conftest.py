# conftest.py – revised

import json
import os
from pathlib import Path
from dotenv import load_dotenv

# ---- 1. Load .env and JSON ----
env_path = Path(os.getcwd()) / ".env"
print(f"\n>>> Loading environment from: {env_path}")
load_dotenv(dotenv_path=env_path)

dict_path = os.getenv("CONFIGURATION_JSON_PATH")
if not dict_path:
    raise RuntimeError("CONFIGURATION_JSON_PATH not set in .env")

full_dict_path = Path(os.getcwd()) / dict_path
if not full_dict_path.exists():
    raise FileNotFoundError(f"JSON file not found: {full_dict_path}")

with open(full_dict_path, encoding="utf-8-sig") as f:
    content = f.read().strip()
if not content:
    raise ValueError(f"JSON file is empty: {full_dict_path}")

config = json.loads(content)

# ---- 2. Expose test configuration as global variables ----
GRID_CSV_PATH = config.get("rutas_csv_mallas", {})
GRID_CSV_MUN_PATH = GRID_CSV_PATH.get("mun")
DICCIONARIO_PATH = config.get("ruta_csv_diccionario_datos")
COLUMN_DICCIONARIO_NOMBRES = config.get("columna_diccionario_nombres")
COLUMN_DICCIONARIO_ALIAS = config.get("columna_diccionario_alias", "var")
COLUMN_DICCIONARIO_DESCRIPCION = config.get("columna_diccionario_descripcion")
COLUMN_DICCIONARIO_VALUES = config.get("columna_diccionario_values", "Values")
NA_ENV = config.get("NA_VALUES", "na")

for key, value in config.items():
    os.environ[key] = value if isinstance(value, str) else json.dumps(value)

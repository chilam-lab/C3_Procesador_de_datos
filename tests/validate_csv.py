import pytest
import pandas as pd
import os
from dotenv import load_dotenv
import ast
import json


DICCIONARIO_PATH = os.getenv("ruta_csv_diccionario_datos")
CSV_OUTPUT_PATH = os.getenv("ruta_csv_salida")
COLUMN_DICCIONARIO_NOMBRES = os.getenv("columna_diccionario_nombres")
COLUMN_DICCIONARIO_ALIAS = os.getenv("columna_diccionario_alias", "var")
COLUMN_DICCIONARIO_DESCRIPCION = os.getenv("columna_diccionario_descripcion")

GRID_CSV_PATH = json.loads(os.getenv("rutas_csv_mallas", "{}"))
GRID_CSV_MUN_PATH = GRID_CSV_PATH["mun"]


if GRID_CSV_MUN_PATH and os.path.exists(GRID_CSV_MUN_PATH):
    grid_df = pd.read_csv(GRID_CSV_MUN_PATH)
else:
    grid_df = pd.DataFrame()

if DICCIONARIO_PATH and os.path.exists(DICCIONARIO_PATH):
    diccionario_df = pd.read_csv(DICCIONARIO_PATH)
else:
    diccionario_df = pd.DataFrame()




####################  VERIFY ALL FILES AVAILABLE ####################

def test_diccionario_file_exists():
    assert DICCIONARIO_PATH is not None, "ruta_csv_diccionario_datos is not set"
    assert os.path.exists(DICCIONARIO_PATH), f"File not found: {DICCIONARIO_PATH}"

# Dynamic test for all keys found inside the json
@pytest.mark.parametrize("key, file_path", GRID_CSV_PATH.items())
def test_mallas_files_exist(key, file_path):
    """Dynamically checks if every file specified in 'rutas_csv_mallas' exists."""
    assert file_path is not None, f"Path for key '{key}' is None"
    assert os.path.exists(file_path), f"File for '{key}' not found at path: {file_path}"

############ VERIFY INTEGRITY OF DICTIONARY.CSV ####################

def test_diccionario_has_column_nombres():
    assert COLUMN_DICCIONARIO_NOMBRES in diccionario_df.columns, f"Column '{COLUMN_DICCIONARIO_NOMBRES}' not found"

def test_diccionario_has_column_alias():
    assert COLUMN_DICCIONARIO_ALIAS in diccionario_df.columns, f"Column '{COLUMN_DICCIONARIO_ALIAS}' not found"

def test_diccionario_has_column_descripcion():
    assert COLUMN_DICCIONARIO_DESCRIPCION in diccionario_df.columns, f"Column '{COLUMN_DICCIONARIO_DESCRIPCION}' not found"

######## VERIFY columns defined in dictionary.csv exist in data.csv ####

def test_alias_var_columns_exist_in_mallas():
    expected_columns = diccionario_df[COLUMN_DICCIONARIO_ALIAS].tolist()
    missing = [col for col in expected_columns if col not in grid_df.columns]
    assert not missing, f"Missing columns in mallas ({len(missing)}): {missing}"

### VERIFY THAT NON-CATEGORY COLUMNS CONTAIN NUMERIC VALUES AND ARE NOT BLANK ####

def test_non_category_columns_are_numeric():
    errors = []
    for _, row in diccionario_df.iterrows():
        column = row[COLUMN_DICCIONARIO_ALIAS]
        if str(row["is_category"]).strip().lower() == "true":
            continue
        if column not in grid_df.columns:
            continue
        null_count = grid_df[column].isna().sum()
        blank_count = (grid_df[column].astype(str).str.strip() == "").sum()
        if null_count > 0:
            errors.append(f"Column '{column}' has {null_count} null/NaN values")
        if blank_count > 0:
            errors.append(f"Column '{column}' has {blank_count} blank values")
        non_numeric = grid_df[
            pd.to_numeric(grid_df[column], errors="coerce").isna() & grid_df[column].notna()
        ][column].unique()
        if len(non_numeric) > 0:
            errors.append(f"Column '{column}' has non-numeric values: {non_numeric.tolist()}")
    assert not errors, "\n".join(errors)

### VERIFY THAT NON-CATEGORY COLUMNS CONTAIN NUMERIC VALUES IN RANGE ####

def test_non_category_columns_are_in_range():
    errors = []
    for _, row in diccionario_df.iterrows():
        column = row[COLUMN_DICCIONARIO_ALIAS]
        if str(row["is_category"]).strip().lower() == "true":
            continue
        if column not in grid_df.columns:
            continue
        values = ast.literal_eval(row["Values"])
        min_val = values.get("min")
        max_val = values.get("max")
        if min_val is None or max_val is None:
            continue
        numeric_series = pd.to_numeric(grid_df[column], errors="coerce").dropna()
        out_of_range = numeric_series[(numeric_series < min_val) | (numeric_series > max_val)]
        if len(out_of_range) > 0:
            errors.append(
                f"Column '{column}' has {len(out_of_range)} values out of range "
                f"[{min_val}, {max_val}]: {out_of_range.unique().tolist()}"
            )
    assert not errors, "\n".join(errors)


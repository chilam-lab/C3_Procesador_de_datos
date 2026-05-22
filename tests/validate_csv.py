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

GRID_CSV_PATH = json.loads(os.getenv("rutas_csv_mallas"))
GRID_CSV_MUN_PATH = GRID_CSV_PATH["mun"]

grid_df = pd.read_csv(GRID_CSV_MUN_PATH)
diccionario_df = pd.read_csv(DICCIONARIO_PATH)


####################  VERIFY ALL FILES AVAILABLE ####################

def test_diccionario_file_exists():
    assert DICCIONARIO_PATH is not None, "ruta_csv_diccionario_datos is not set"
    assert os.path.exists(DICCIONARIO_PATH), f"File not found: {DICCIONARIO_PATH}"

def test_mallas_mun_file_exists():
    assert GRID_CSV_MUN_PATH is not None, "rutas_csv_mallas.mun is not set"
    assert os.path.exists(GRID_CSV_MUN_PATH), f"File not found: {GRID_CSV_MUN_PATH}"

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
        values = ast.literal_eval(row["Values"])
        if values.get("is_category") == "true":
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


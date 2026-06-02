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
COLUMN_DICCIONARIO_DESCRIPCION = os.getenv("columna_diccionario_descripcion")
COLUMN_DICCIONARIO_VALUES = os.getenv("columna_diccionario_values", "Values")

na_env = os.getenv("NA_VARIABLE", "na")

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


### VERIFY THAT CATEGORY COLUMNS HAVE VALID DICTIONARY STRUCTURES ####

def test_category_columns_have_valid_values_dict():
    errors = []
    
    for index, row in diccionario_df.iterrows():
        # 1. Check if is_category is explicitly True
        if str(row["is_category"]).strip().lower() != "true":
            continue
            
        column_name = row[COLUMN_DICCIONARIO_ALIAS]
        raw_values = row["Values"]
        
        # 2. Ensure the Values column isn't empty
        if pd.isna(raw_values) or not str(raw_values).strip():
            errors.append(f"Row {index} (Column '{column_name}'): 'is_category' is True, but 'Values' is empty.")
            continue
            
        # 3. Try to parse the string into a Python dictionary
        try:
            values_dict = ast.literal_eval(raw_values)
        except (ValueError, SyntaxError) as e:
            errors.append(f"Row {index} (Column '{column_name}'): Failed to parse 'Values'. Error: {e}")
            continue
            
        # 4. Verify it's actually a dictionary structure
        if not isinstance(values_dict, dict):
            errors.append(f"Row {index} (Column '{column_name}'): 'Values' must be a dictionary, got {type(values_dict).__name__}.")
            continue
            
        # 5. Validate that keys are numeric and values are strings
        for k, v in values_dict.items():
            # Check if key is an integer/float, or a string that represents an integer
            is_numeric_key = isinstance(k, (int, float)) or (isinstance(k, str) and k.strip().isdigit())
            
            if not is_numeric_key:
                errors.append(
                    f"Row {index} (Column '{column_name}'): Invalid key '{k}' ({type(k).__name__}). "
                    f"Keys must be numeric."
                )
            
            if not isinstance(v, str):
                errors.append(
                    f"Row {index} (Column '{column_name}'): Invalid value '{v}' ({type(v).__name__}) for key '{k}'. "
                    f"Values must be strings."
                )

    assert not errors, "Category dictionary validation failed:\n" + "\n".join(errors)

### VERIFY THAT CATEGORY DATA VALUES MATCH THEIR DEFINITIONS IN THE DICTIONARY ####

def test_category_data_matches_dynamic_dictionary_values():
    # 1. Parse the N/A variables from the environment
    na_list = [val.strip().strip("'\"") for val in na_env.split(",") if val.strip()]
    
    errors = []

    for index, row in diccionario_df.iterrows():
        # Only check rows where is_category is explicitly True
        if str(row["is_category"]).strip().lower() != "true":
            continue

        column_name = row[COLUMN_DICCIONARIO_ALIAS]
        
        # Skip if the column defined in the dictionary doesn't exist in the grid data
        if column_name not in grid_df.columns:
            continue

        raw_values = row[COLUMN_DICCIONARIO_VALUES]

        # 2. Fail if the 'Values' definition cell itself is empty in the CSV
        if pd.isna(raw_values) or not str(raw_values).strip():
            errors.append(f"Row {index} (Column '{column_name}'): 'is_category' is True, but the dictionary 'Values' definition is empty.")
            continue

        try:
            values_dict = ast.literal_eval(raw_values)
        except (ValueError, SyntaxError) as e:
            errors.append(f"Row {index} (Column '{column_name}'): Failed to parse 'Values' dict structure. Error: {e}")
            continue

        if not isinstance(values_dict, dict) or not values_dict:
            errors.append(f"Row {index} (Column '{column_name}'): 'Values' dictionary structure cannot be empty.")
            continue

        # 3. DYNAMICALLY extract the valid targets from the dictionary values mapping
        allowed_from_dict = [str(v).strip() for v in values_dict.values()]
        allowed_values = set(allowed_from_dict).union(na_list)

        # 4. Extract actual values present in this grid data column
        column_data = grid_df[column_name]
        
        # Fail if the data column has no values at all
        if column_data.empty:
            errors.append(f"Column '{column_name}': The data column is completely empty.")
            continue

        # Convert data entries to stripped strings to ensure clean matching
        # (This turns pandas NaN values into the string 'nan' and blanks into '')
        actual_values = set(column_data.astype(str).str.strip().unique())

        # 5. Check if any unexpected values (or unallowed empty/nan values) exist
        invalid_values = [v for v in actual_values if v not in allowed_values]
        
        if invalid_values:
            errors.append(
                f"Column '{column_name}' contains invalid values: {invalid_values}. "
                f"Based on your dictionary, allowed values are: {sorted(list(allowed_values))}"
            )

    assert not errors, "Category data alignment validation failed:\n" + "\n".join(errors)

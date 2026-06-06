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

na_env = os.getenv("NA_VALUES", "na")

GRID_CSV_PATH = json.loads(os.getenv("rutas_csv_mallas", "{}"))
GRID_CSV_MUN_PATH = GRID_CSV_PATH["mun"]


valid_grids = [(key, path) for key, path in GRID_CSV_PATH.items() if os.path.exists(path)]

@pytest.fixture(params=valid_grids, ids=lambda param: param)
def dynamic_grid_df(request):
    """Loads each dataset dynamically. Tests using this fixture run once per file."""
    file_key, file_path = request.param
    df = pd.read_csv(file_path, dtype=str)
    return file_key, df, file_path

if DICCIONARIO_PATH and os.path.exists(DICCIONARIO_PATH):
    diccionario_df = pd.read_csv(DICCIONARIO_PATH)
else:
    diccionario_df = pd.DataFrame()




def test_alert_on_na_values_usage(capsys, dynamic_grid_df):
    """Scans the dataset for N/A values and prompts the user before proceeding."""
    file_key, grid_df, file_path = dynamic_grid_df
    na_list = [val.strip().strip("'\"") for val in na_env.split(",") if val.strip()]
    
    if not na_list or grid_df.empty:
        return

    na_instances = []

    for _, row in diccionario_df.iterrows():
        column_name = row[COLUMN_DICCIONARIO_ALIAS]
        if column_name not in grid_df.columns:
            continue

        is_na_mask = grid_df[column_name].astype(str).str.strip().isin(na_list)
        matching_indices = grid_df[is_na_mask].index.tolist()

        for idx in matching_indices:
            actual_val = grid_df.loc[idx, column_name]
            na_instances.append(f"  - Row {idx}, Column '{column_name}' (Value: '{actual_val}')")

    if na_instances:
        total_registers = len(na_instances)
        with capsys.disabled():
            print(f"\n\n============== [ N/A VALUES DETECTED IN: {file_path} ] ==============")
            print(f"⚠️ I found {total_registers} registers using N/A placeholders:")
            for item in na_instances[:10]:
                print(item)
            if total_registers > 10:
                print(f"  ... and {total_registers - 10} more registers.")
            print("======================================================")
            input("👉 Press [ENTER] to acknowledge and proceed...👀 ")
            print("Resuming remaining validation suites...\n")


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

def test_alias_var_columns_exist_in_mallas(dynamic_grid_df):
    file_key, grid_df, file_path = dynamic_grid_df
    expected_columns = diccionario_df[COLUMN_DICCIONARIO_ALIAS].tolist()
    missing = [col for col in expected_columns if col not in grid_df.columns]
    assert not missing, f"[{file_path}] Missing columns in mallas ({len(missing)}): {missing}"



### VERIFY THAT NON-CATEGORY COLUMNS CONTAIN NUMERIC VALUES AND ARE NOT BLANK ####

def test_non_category_columns_are_numeric(dynamic_grid_df):
    file_key, grid_df, file_path = dynamic_grid_df
    errors = []
    na_list = [val.strip().strip("'\"") for val in na_env.split(",") if val.strip()]

    for _, row in diccionario_df.iterrows():
        column = row[COLUMN_DICCIONARIO_ALIAS]
        
        if str(row["is_category"]).strip().lower() == "true":
            continue
        if column not in grid_df.columns:
            continue
            
        is_na_mask = grid_df[column].astype(str).str.strip().isin(na_list)
        valid_data = grid_df[~is_na_mask][column]

        null_count = valid_data.isna().sum()
        blank_count = (valid_data.astype(str).str.strip() == "").sum()
        
        if null_count > 0:
            errors.append(f"[{file_path}] Column '{column}' has {null_count} null/NaN values")
        if blank_count > 0:
            errors.append(f"[{file_path}] Column '{column}' has {blank_count} blank values")
            
        non_numeric = valid_data[
            pd.to_numeric(valid_data, errors="coerce").isna() & valid_data.notna()
        ].unique()
        
        if len(non_numeric) > 0:
            errors.append(f"[{file_path}] Column '{column}' has non-numeric values: {non_numeric.tolist()}")
            
    assert not errors, "\n".join(errors)



### VERIFY THAT NON-CATEGORY COLUMNS CONTAIN NUMERIC VALUES IN RANGE ####

def test_non_category_columns_are_in_range(dynamic_grid_df):
    file_key, grid_df, file_path = dynamic_grid_df
    errors = []
    na_list = [val.strip().strip("'\"") for val in na_env.split(",") if val.strip()]

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

        is_na_mask = grid_df[column].astype(str).str.strip().isin(na_list)
        valid_data = grid_df[~is_na_mask][column]

        numeric_series = pd.to_numeric(valid_data, errors="coerce").dropna()
        out_of_range = numeric_series[(numeric_series < min_val) | (numeric_series > max_val)]
        
        if len(out_of_range) > 0:
            errors.append(
                f"[{file_path}] Column '{column}' has {len(out_of_range)} values out of range "
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

def test_category_data_matches_dynamic_dictionary_values(dynamic_grid_df):
    file_key, grid_df, file_path = dynamic_grid_df
    na_list = [val.strip().strip("'\"") for val in na_env.split(",") if val.strip()]
    errors = []
    
    for index, row in diccionario_df.iterrows():
        if str(row["is_category"]).strip().lower() != "true":
            continue

        column_name = row[COLUMN_DICCIONARIO_ALIAS]
        
        if column_name not in grid_df.columns:
            continue

        raw_values = row[COLUMN_DICCIONARIO_VALUES]

        if pd.isna(raw_values) or not str(raw_values).strip():
            continue

        try:
            values_dict = ast.literal_eval(raw_values)
        except (ValueError, SyntaxError) as e:
            continue

        if not isinstance(values_dict, dict) or not values_dict:
            continue

        allowed_from_dict = [str(v).strip() for v in values_dict.values()]
        allowed_values = set(allowed_from_dict).union(na_list)

        column_data = grid_df[column_name]
        
        if column_data.empty:
            errors.append(f"[{file_path}] Column '{column_name}': The data column is completely empty.")
            continue

        actual_values = set(column_data.astype(str).str.strip().unique())
        invalid_values = [v for v in actual_values if v not in allowed_values]
        
        if invalid_values:
            errors.append(
                f"[{file_path}] Column '{column_name}' contains invalid values: {invalid_values}. "
                f"Based on your dictionary, allowed values are: {sorted(list(allowed_values))}"
            )

    assert not errors, "Category data alignment validation failed:\n" + "\n".join(errors)



### VERIFY THAT NON-CATEGORY COLUMNS HAVE MIN AND MAX RANGE DEFINITIONS ####

def test_non_category_columns_have_min_max_range():
    errors = []
    
    for index, row in diccionario_df.iterrows():
        if str(row["is_category"]).strip().lower() != "false":
            continue
            
        column_name = row[COLUMN_DICCIONARIO_ALIAS]
        raw_values = row[COLUMN_DICCIONARIO_VALUES]
        
        if pd.isna(raw_values) or not str(raw_values).strip():
            errors.append(
                f"Row {index} (Column '{column_name}'): 'is_category' is False, "
                f"but '{COLUMN_DICCIONARIO_VALUES}' is empty."
            )
            continue
            
        try:
            values_dict = ast.literal_eval(raw_values)
        except (ValueError, SyntaxError) as e:
            errors.append(
                f"Row {index} (Column '{column_name}'): Failed to parse '{COLUMN_DICCIONARIO_VALUES}'. "
                f"Error: {e}"
            )
            continue
            
        if not isinstance(values_dict, dict):
            errors.append(
                f"Row {index} (Column '{column_name}'): '{COLUMN_DICCIONARIO_VALUES}' "
                f"must be a dictionary object, got {type(values_dict).__name__}."
            )
            continue
            
        missing_keys = [key for key in ["min", "max"] if key not in values_dict]
        if missing_keys:
            errors.append(
                f"Row {index} (Column '{column_name}'): Missing required continuous range keys {missing_keys}. "
                f"Found keys: {list(values_dict.keys())}"
            )

    assert not errors, "Non-category structural range validation failed:\n" + "\n".join(errors)

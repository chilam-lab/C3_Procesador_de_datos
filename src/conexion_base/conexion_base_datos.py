import json
import pandas as pd
import argparse
import os
from dotenv import load_dotenv
import psycopg
from psycopg import sql
from io import StringIO

if __name__ == "__main__":
    """
    Script para cargar datos procesados a una base de datos PostgreSQL, utilizando las credenciales y parámetros definidos en un archivo .env. 
    Opcionalmente, puede crear la tabla de destino si no existe, infiriendo los tipos de datos a partir del DataFrame.

    Parámetros de entrada:
        --ruta-datos-procesados: Ruta al archivo CSV con los datos procesados.
        --ruta-env: Ruta al archivo .env con las credenciales de la base de datos (por defecto: ./.env).
        --crear-tabla: Si se incluye, crea la tabla de destino automáticamente si no existe.

    Raises:
        FileNotFoundError: Si no se encuentra el archivo .env en la ruta especificada.
    """
    
    # definir flags de archivos de configuracion
    parser = argparse.ArgumentParser(description="Gestor de carga de datos procesados a base de datos")
    parser.add_argument("--ruta-datos-lugares", type=str, required=False, help="Ruta de los datos procesados de lugares (mallas) que serán cargados a la base de datos")
    parser.add_argument("--ruta-datos-personas", type=str, required=False, help="Ruta de los datos procesados del ensamble secundario que serán cargados a la base de datos")
    parser.add_argument("--tipo-ensamble", type=str, default="personas", help="Tipo de ensamble secundario (e.g. 'personas', 'establecimientos'). Define el sufijo de la tabla en la base de datos (por defecto: 'personas')")
    parser.add_argument("--ruta-datos-procesados", type=str, required=False, help="(Deprecado) Ruta al archivo CSV con los datos procesados (se asume lugares si se usa)")
    parser.add_argument("--ruta-env", type=str, default='./.env', help="Ruta al archivo .env")
    parser.add_argument("--crear-tabla", action='store_true', help="Adicionalmente crea la tabla especificada en el archivo .env")
    args = parser.parse_args()
    
    # Validar argumentos
    if not any([args.ruta_datos_lugares, args.ruta_datos_personas, args.ruta_datos_procesados]):
        raise ValueError("Se debe especificar al menos un archivo de datos: --ruta-datos-lugares, --ruta-datos-personas o --ruta-datos-procesados")

    dataframes = {}
    
    # Cargar datos de lugares
    ruta_lugares = args.ruta_datos_lugares or args.ruta_datos_procesados
    if ruta_lugares:
        if os.path.exists(ruta_lugares):
            dataframes['mun'] = pd.read_csv(ruta_lugares)
            print(f"Cargado archivo de lugares: {ruta_lugares}")
        else:
            raise FileNotFoundError(f"No se encontró el archivo de lugares: {ruta_lugares}")

    # Cargar datos del ensamble secundario
    if args.ruta_datos_personas:
        if os.path.exists(args.ruta_datos_personas):
            dataframes[args.tipo_ensamble] = pd.read_csv(args.ruta_datos_personas)
            print(f"Cargado archivo de ensamble '{args.tipo_ensamble}': {args.ruta_datos_personas}")
        else:
            raise FileNotFoundError(f"No se encontró el archivo de ensamble '{args.tipo_ensamble}': {args.ruta_datos_personas}")

    if not os.path.exists(args.ruta_env):
        raise FileNotFoundError(f"No se encontró el archivo .env en la ruta: {args.ruta_env}")

    # cargar variables de entorno desde archivo .env
    load_dotenv(args.ruta_env)
    
    # Procesar columnas especiales y diccionarios independientes
    df_dicts = {}
    dict_cols_per_df = {}
    
    # Tipos especiales por dataframe
    special_types_per_df = {} # {key: {col: type}}

    for key, df in dataframes.items():
        special_types = {}
        for col in df.columns:
            if col.startswith("cells_"):
                # verificar contenido para decidir entre INTEGER[] o TEXT[]
                sample = df[col].dropna()
                is_integer_array = False
                if not sample.empty:
                    # Tomar el primer valor no nulo
                    val = str(sample.iloc[0])
                    # Limpiar llaves
                    val_content = val.replace('{', '').replace('}', '').strip()
                    if val_content:
                        # Verificar el primer elemento
                        first_elem = val_content.split(',')[0].strip()
                        # Si es digito, asumimos entero. Si tiene comillas o caracteres alfa, texto.
                        # Ojo: ID_REGISTRO es alfanumerico (e.g. 109fd5), asi que isdigit() sera False.
                        if first_elem.isdigit():
                            is_integer_array = True
                
                special_types[col] = "INTEGER[]" if is_integer_array else "TEXT[]"
            elif col.startswith("interval_"):
                # verificar si tiene formato de rango con ':'
                sample = df[col].dropna()
                if not sample.empty and ':' in str(sample.iloc[0]):
                    special_types[col] = "NUMRANGE"
                    # transformar formato "min:max" a "[min,max)"
                    def transform_range(val):
                        if pd.isna(val): return val
                        s = str(val).replace('%', '').strip()
                        if ':' in s:
                            parts = s.split(':')
                            # manejar posibles espacios o vacios
                            return f"[{parts[0].strip()},{parts[1].strip()})"
                        return val
                    df[col] = df[col].apply(transform_range)
                else:
                    special_types[col] = "TEXT"
        
        special_types_per_df[key] = special_types

        # identificar columnas de diccionario y valores
        cells_cols = [c for c in df.columns if c.startswith('cells_')]
        data_cols = ['bin'] + [c for c in df.columns if c.startswith('interval_')] + cells_cols
        dict_cols = [c for c in df.columns if c not in data_cols]
        dict_cols_per_df[key] = dict_cols
        
        def _get_path(code):
            base = code.replace('::presencia', '')
            if '::' in base:
                return base.split('::')[-1]
            elif '-' in base:
                return base.split('-', 1)[0]
            return base

        # 1. Tabla dict (una fila por variable derivada: code)
        df_vars = df[['code', 'name', 'descripcion']].drop_duplicates(subset=['code']).reset_index(drop=True)
        df_vars['metadata'] = df_vars.apply(lambda row: json.dumps({
            'descripcion': row['descripcion'] if pd.notna(row['descripcion']) else None,
            'alias': row['name'],
            'path': _get_path(row['code'])
        }, ensure_ascii=False), axis=1)
        df_vars = df_vars.rename(columns={'code': 'variable_name'})
        df_vars['id'] = df_vars.index + 1

        print(df_vars)

        # Merge df_vars into the df to get dict_id
        df = df.merge(df_vars[['id', 'variable_name']].rename(columns={'variable_name': 'code'}), on='code', how='left').rename(columns={'id': 'dict_id'})

        # 2. Tabla values (sin valor ni alias)
        interval_cols = [c for c in df.columns if c.startswith('interval_')]
        val_cols_to_extract = ['dict_id', 'bin'] + interval_cols
        df_vals = df[val_cols_to_extract].copy()
        df_vals['id'] = df_vals.index + 1

        # columns for generating table
        val_cols_for_table = ['id', 'dict_id', 'bin'] + interval_cols

        df_dicts[key] = {
            'vars': df_vars,
            'vals': df_vals[val_cols_for_table]
        }

        # Merge values_id de vuelta a cada dataframe
        df['values_id'] = df_vals['id']
        dataframes[key] = df

    # construir mapeo variable_name -> conjunto de ensambles donde aparece
    # (cruzando todos los df_vars de cada ensamble cargado en `dataframes`)
    variable_to_grids = {}
    for grid_key, dicts in df_dicts.items():
        for var_name in dicts['vars']['variable_name']:
            variable_to_grids.setdefault(var_name, set()).add(grid_key)

    # serializar el conjunto a literal de array de PostgreSQL '{a,b}' por variable, en cada df_vars
    for grid_key in df_dicts:
        df_vars_grid = df_dicts[grid_key]['vars']
        df_vars_grid['available_grids'] = df_vars_grid['variable_name'].apply(
            lambda v: '{' + ','.join(sorted(variable_to_grids.get(v, set()))) + '}'
        )

    # conexion postgres
    with psycopg.connect(
        host = os.getenv("DB_HOST"),
        port = os.getenv("DB_PORT"),
        dbname = os.getenv("DB_NAME"),
        user = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD")
    ) as conn:
        
        with conn.cursor() as cursor:
            
            tabla_base = os.getenv("DB_TABLE")
            
            # Tipos de datos básicos
            tipos = {
                'int64': 'INTEGER',
                'float64': 'FLOAT',
                'object': 'TEXT',
                'bool': 'BOOLEAN'
            }

            for key, df in dataframes.items():
                suffix = f'_{key}'
                tabla_destino = f"{tabla_base}{suffix}"
                tabla_dict = f"dict_{tabla_base}{suffix}"
                
                df_vars = df_dicts[key]['vars']
                df_vals = df_dicts[key]['vals']
                dict_cols = dict_cols_per_df[key]
                tabla_vals = f"values_{tabla_base}{suffix}"

                # --- 1. Crear e insertar en tabla diccionario (variables) ---
                if args.crear_tabla:
                    cursor.execute(f"DROP TABLE IF EXISTS {tabla_dict} CASCADE;")
                    create_dict_sql = f"""
                    CREATE TABLE {tabla_dict} (
                        id INTEGER PRIMARY KEY,
                        variable_name TEXT,
                        metadata JSONB,
                        available_grids TEXT[]
                    );
                    """
                    cursor.execute(create_dict_sql)

                # Insertar datos vars
                buffer_vars = StringIO()
                df_vars[['id', 'variable_name', 'metadata', 'available_grids']].to_csv(buffer_vars, index=False, header=True)
                buffer_vars.seek(0)

                with cursor.copy(sql.SQL("COPY {} ({}) FROM STDIN WITH CSV HEADER").format(
                    sql.Identifier(tabla_dict),
                    sql.SQL("id, variable_name, metadata, available_grids")
                )) as copy:
                    copy.write(buffer_vars.getvalue())
                
                print(f"Datos insertados exitosamente en la tabla diccionario '{tabla_dict}'")

                # --- 2. Crear e insertar en tabla values ---
                if args.crear_tabla:
                    val_columns_sql = [
                        "id INTEGER PRIMARY KEY",
                        f"dict_id INTEGER REFERENCES {tabla_dict}(id)",
                        "bin INTEGER"
                    ]
                    
                    interval_cols = [c for c in df_vals.columns if c.startswith('interval_')]
                    for col in interval_cols:
                        if col in special_types_per_df[key]:
                            sql_type = special_types_per_df[key][col]
                        else:
                            dtype = df_vals[col].dtype
                            sql_type = tipos.get(str(dtype), 'TEXT')
                        val_columns_sql.append(f"{col} {sql_type}")
                        
                    create_vals_sql = f"""
                    CREATE TABLE IF NOT EXISTS {tabla_vals} (
                        {", ".join(val_columns_sql)}
                    );
                    """
                    cursor.execute(f"DROP TABLE IF EXISTS {tabla_vals} CASCADE")
                    cursor.execute(create_vals_sql)

                # Insertar datos vals
                buffer_vals = StringIO()
                val_cols_for_table = ['id', 'dict_id', 'bin'] + [c for c in df_vals.columns if c.startswith('interval_')]
                df_vals = df_vals.copy()
                df_vals['bin'] = df_vals['bin'].astype('Int64')
                df_vals[val_cols_for_table].to_csv(buffer_vals, index=False, header=True)
                buffer_vals.seek(0)
                
                with cursor.copy(sql.SQL("COPY {} ({}) FROM STDIN WITH CSV HEADER").format(
                    sql.Identifier(tabla_vals),
                    sql.SQL(", ").join([sql.Identifier(col) for col in val_cols_for_table])
                )) as copy:
                    copy.write(buffer_vals.getvalue())
                
                print(f"Datos insertados exitosamente en la tabla de valores '{tabla_vals}'")

                # --- 3. Crear e insertar en tablas de datos principal ---
                cols_to_exclude = set(dict_cols + ['values_id', 'bin', 'dict_id', 'description', 'descripcion'] + [c for c in df.columns if c.startswith('interval_')])
                data_cols_current = [c for c in df.columns if c not in cols_to_exclude and c != 'id']
                
                if args.crear_tabla:
                    main_columns_sql = []
                    main_columns_sql.append(f"values_id INTEGER REFERENCES {tabla_vals}(id)")
                    
                    for col in data_cols_current:
                        if col in special_types_per_df[key]:
                            sql_type = special_types_per_df[key][col]
                        else:
                            dtype = df[col].dtype
                            sql_type = tipos.get(str(dtype), 'TEXT')
                        main_columns_sql.append(f"{col} {sql_type}")
                    
                    create_main_sql = f"""
                    CREATE TABLE IF NOT EXISTS {tabla_destino} (
                        id SERIAL PRIMARY KEY,
                        {", ".join(main_columns_sql)}
                    );
                    """
                    cursor.execute(f"DROP TABLE IF EXISTS {tabla_destino} CASCADE")
                    cursor.execute(create_main_sql)

                # Insertar datos main
                buffer_main = StringIO()
                cols_main_insert = ['values_id'] + data_cols_current
                df[cols_main_insert].to_csv(buffer_main, index=False, header=True)
                buffer_main.seek(0)

                with cursor.copy(sql.SQL("COPY {} ({}) FROM STDIN WITH CSV HEADER").format(
                    sql.Identifier(tabla_destino),
                    sql.SQL(", ").join([sql.Identifier(col) for col in cols_main_insert])
                )) as copy:
                    copy.write(buffer_main.getvalue())
                
                print(f"Datos insertados exitosamente en la tabla '{tabla_destino}'")
            
            conn.commit()

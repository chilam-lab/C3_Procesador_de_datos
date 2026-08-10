import sys
import ast
import os
import pytest
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(src_dir)

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
import argparse
import json
import pandas as pd
import functools
from utils.regex_utils import obtener_variables_regex_df
from preprocesador.preprocesador import Preprocesador


def validar_diccionario(
    diccionario_datos: pd.DataFrame,
    df: pd.DataFrame,
    columna_diccionario_nombres: str,
    columna_diccionario_posibles_valores: str,
    columna_diccionario_posibles_valores_alias: str = None,
) -> None:
    """
    Verifica que el diccionario de datos cumple la especificación mínima requerida.

    Checks:
    1. Sin valores nulos en columna_diccionario_nombres.
    2. Sin nombres de variable duplicados en columna_diccionario_nombres.
    3. Para variables del diccionario presentes en el dataset: posibles_valores
       debe ser una cadena que represente una lista Python (ast.literal_eval).
    4. Si se usa columna_diccionario_posibles_valores_alias (distinta de posibles_valores):
       sus listas deben tener la misma longitud que posibles_valores en cada fila.

    Raises:
        ValueError: Si alguna condición de la especificación no se cumple.
    """
    # 1. Sin nulos en nombres
    nulos = diccionario_datos[columna_diccionario_nombres].isna().sum()
    if nulos > 0:
        raise ValueError(
            f'La columna "{columna_diccionario_nombres}" del diccionario contiene '
            f'{nulos} valor(es) nulo(s). Todos los nombres de variable deben estar definidos.'
        )

    # 2. Sin duplicados en nombres
    mascara_dup = diccionario_datos[columna_diccionario_nombres].duplicated()
    if mascara_dup.any():
        vars_dup = diccionario_datos.loc[mascara_dup, columna_diccionario_nombres].tolist()
        raise ValueError(
            f'La columna "{columna_diccionario_nombres}" del diccionario contiene '
            f'nombres de variable duplicados: {vars_dup}. '
            f'Cada variable debe aparecer una única vez.'
        )

    # Filas del diccionario cuyas variables existen en el dataset (aplican checks 3 y 4)
    vars_en_dataset = set(df.columns)
    filas_activas = diccionario_datos[
        diccionario_datos[columna_diccionario_nombres].isin(vars_en_dataset)
    ]

    if filas_activas.empty:
        return  # Sin solapamiento entre dict y dataset; no aplican checks de contenido

    # 3. posibles_valores son listas Python válidas (solo se valida si el valor parece un intento de lista)
    errores_formato = []
    for _, fila in filas_activas.iterrows():
        valor = fila[columna_diccionario_posibles_valores]
        if pd.isna(valor):
            continue  # NaN = variable sin posibles_valores definidos, se omite
        if not str(valor).strip().startswith('['):
            continue  # texto plano (ej. descripción), no es un intento de lista, se omite
        try:
            parsed = ast.literal_eval(valor)
            if not isinstance(parsed, list):
                errores_formato.append((fila[columna_diccionario_nombres], valor, 'no es una lista'))
        except (ValueError, SyntaxError) as e:
            errores_formato.append((fila[columna_diccionario_nombres], valor, str(e)))

    if errores_formato:
        detalles = '\n'.join(
            [f'  Variable "{v}": "{val}" → {err}' for v, val, err in errores_formato[:5]]
        )
        mas = f'\n  ... y {len(errores_formato) - 5} más' if len(errores_formato) > 5 else ''
        raise ValueError(
            f'La columna "{columna_diccionario_posibles_valores}" contiene '
            f'{len(errores_formato)} valor(es) con formato inválido. '
            f'Se esperan cadenas que representen listas Python (ej. "[1, 2, 3]"):\n{detalles}{mas}'
        )

    # 4. Longitudes de posibles_valores y posibles_valores_alias coinciden
    if (
        columna_diccionario_posibles_valores_alias
        and columna_diccionario_posibles_valores_alias != columna_diccionario_posibles_valores
    ):
        errores_longitud = []
        for _, fila in filas_activas.iterrows():
            val = fila[columna_diccionario_posibles_valores]
            val_alias = fila[columna_diccionario_posibles_valores_alias]
            if pd.isna(val) or pd.isna(val_alias):
                continue
            try:
                lista = ast.literal_eval(val)
                lista_alias = ast.literal_eval(val_alias)
                if len(lista) != len(lista_alias):
                    errores_longitud.append(
                        (fila[columna_diccionario_nombres], len(lista), len(lista_alias))
                    )
            except (ValueError, SyntaxError):
                pass  # Ya capturado en check 3
        if errores_longitud:
            detalles = '\n'.join(
                [f'  Variable "{v}": {n} posibles_valores vs {na} alias'
                 for v, n, na in errores_longitud[:5]]
            )
            mas = f'\n  ... y {len(errores_longitud) - 5} más' if len(errores_longitud) > 5 else ''
            raise ValueError(
                f'Inconsistencia de longitud en {len(errores_longitud)} variable(s): '
                f'las listas de "{columna_diccionario_posibles_valores}" y '
                f'"{columna_diccionario_posibles_valores_alias}" deben tener '
                f'el mismo número de elementos por fila:\n{detalles}{mas}'
            )

def run_validation_tests() -> bool:
    """
    Run all pytest tests in the 'tests' folder of the project.
    Returns True if all tests pass, False otherwise.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    test_file = os.path.join(project_root, 'tests', 'validate_csv.py')
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    exit_code = pytest.main([test_file, '-v', '--tb=short'])
    return exit_code == 0

if __name__ == '__main__':
    """
    Script principal para ejecutar el preprocesamiento de datos utilizando la clase Preprocesador.

    Este script toma un archivo de configuración en formato JSON que especifica las rutas de entrada,
    las variables a agrupar, y otros parámetros necesarios para el preprocesamiento. Genera un archivo
    CSV con los datos preprocesados y otro con el diccionario de alias.

    Raises:
        ValueError: Si el archivo de configuración no contiene los campos requeridos.
        FileNotFoundError: Si alguna de las rutas especificadas en el archivo de configuración no existe.
    """
    
    if not run_validation_tests():
        print("❌ Validation tests failed. Aborting processing.")
        sys.exit(1)
    # ----- Continue with normal execution -----
    print("✅ All tests passed. Starting processing...")
    # definir flag de archivo de configuracion
    parser = argparse.ArgumentParser(description='Procesador de datos C3')
    parser.add_argument('--config', type=str, required=True, help='Archivo de configuración')
    args = parser.parse_args()
    
    # cargar archivo de configuracion
    if not os.path.exists(args.config):
        raise FileNotFoundError(f'No se encontró el archivo de configuración: {args.config}')
    try:
        with open(args.config) as f:
            preprocesador_config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f'El archivo de configuración {args.config} no es un JSON válido: {e}') from None
    except PermissionError:
        raise PermissionError(f'No hay permisos para leer el archivo de configuración: {args.config}') from None
        
    # validaciones campo ruta_csv_dataset    
    if 'ruta_csv_dataset' not in preprocesador_config:
        raise ValueError('El archivo JSON pasado para --config debe tener el campo ruta_csv_dataset')
    ruta_csv_dataset = preprocesador_config['ruta_csv_dataset']
    if not os.path.exists(ruta_csv_dataset):
        raise FileNotFoundError(f'La ruta especificada para el archivo .csv del dataset no existe ({ruta_csv_dataset})')
    
    # cargar dataframe de datos con columnas de tipo str
    df = pd.read_csv(ruta_csv_dataset, dtype=str)
    
    # eliminar columna 'Unnamed: 0' (esta existe cuando se tiene una primera columna de indices sin nombre)
    if 'Unnamed: 0' in df.columns:
        df.drop(columns=['Unnamed: 0'], inplace=True)
    
    # validaciones campo ruta_csv_diccionario_datos    
    if 'ruta_csv_diccionario_datos' not in preprocesador_config:
        raise ValueError('El archivo JSON pasado para --config debe tener el campo ruta_csv_diccionario_datos')
    ruta_csv_diccionario_datos = preprocesador_config['ruta_csv_diccionario_datos']
    if not os.path.exists(ruta_csv_diccionario_datos):
        raise FileNotFoundError(f'La ruta especificada para el archivo .csv del diccionario de datos no existe ({ruta_csv_diccionario_datos})')
    
    # cargar dataframe de diccionario de datos con columnas de tipo str
    diccionario_datos = pd.read_csv(ruta_csv_diccionario_datos, dtype=str)
    
    # eliminar columna 'Unnamed: 0' (esta existe cuando se tiene una primera columna de indices sin nombre)
    if 'Unnamed: 0' in diccionario_datos.columns:
        diccionario_datos.drop(columns=['Unnamed: 0'], inplace=True)
    
    # validaciones campo ruta_salida_dataset
    if 'ruta_salida_dataset' not in preprocesador_config:
        raise ValueError('El archivo JSON pasado para --config debe tener el campo ruta_salida_dataset')
    ruta_salida_dataset = preprocesador_config['ruta_salida_dataset']
    
    # validaciones campo ruta_salida_diccionario_datos
    if 'ruta_salida_diccionario_datos' not in preprocesador_config:
        raise ValueError('El archivo JSON pasado para --config debe tener el campo ruta_salida_diccionario_datos')
    ruta_salida_diccionario_datos = preprocesador_config['ruta_salida_diccionario_datos']
    if not isinstance(ruta_salida_diccionario_datos, str):
        raise TypeError('El valor asociado al campo ruta_salida_diccionario_datos debe ser de tipo str')
    
    # validaciones campo columna_diccionario_nombres
    if 'columna_diccionario_nombres' not in preprocesador_config:
        raise ValueError('El archivo JSON pasado para --config debe tener el campo columna_diccionario_nombres, que incluye el nombre descriptivo de cada variables')
    columna_diccionario_nombres = preprocesador_config['columna_diccionario_nombres']
    if not isinstance(columna_diccionario_nombres, str):
        raise TypeError('El valor asociado al campo columna_diccionario_nombres debe ser de tipo str')
    if columna_diccionario_nombres not in diccionario_datos.columns:
        raise KeyError(f'El DataFrame del diccionario de datos no tiene una columna llamada {columna_diccionario_nombres}')
    
    # validaciones campo columna_diccionario_posibles_valores
    if 'columna_diccionario_posibles_valores' not in preprocesador_config:
        raise ValueError('El archivo JSON pasado para --config debe tener el campo columna_diccionario_posibles_valores, que incluye cada posible valor de cada variable en formato de lista')
    columna_diccionario_posibles_valores = preprocesador_config['columna_diccionario_posibles_valores']
    if not isinstance(columna_diccionario_posibles_valores, str):
        raise TypeError('El valor asociado al campo columna_diccionario_posibles_valores debe ser de tipo str')
    if columna_diccionario_posibles_valores not in diccionario_datos.columns:
        raise KeyError(f'El DataFrame del diccionario de datos no tiene una columna llamada {columna_diccionario_posibles_valores}')

    # validaciones campo columna_diccionario_alias
    columna_diccionario_alias = preprocesador_config.get('columna_diccionario_alias', columna_diccionario_nombres)
    if columna_diccionario_alias is not None:
        if not isinstance(columna_diccionario_alias, str):
            raise TypeError('El valor asociado al campo columna_diccionario_alias debe ser de tipo str')
        if columna_diccionario_alias not in diccionario_datos.columns:
            raise KeyError(f'El DataFrame del diccionario de datos no tiene una columna llamada {columna_diccionario_alias}')
    
    # validaciones campo columna_diccionario_posibles_valores_alias
    columna_diccionario_posibles_valores_alias = preprocesador_config.get('columna_diccionario_posibles_valores_alias', columna_diccionario_posibles_valores)
    if columna_diccionario_posibles_valores_alias is not None:
        if not isinstance(columna_diccionario_posibles_valores_alias, str):
            raise TypeError('El valor asociado al campo columna_diccionario_posibles_respuestas_alias debe ser de tipo str')
        if columna_diccionario_posibles_valores_alias not in diccionario_datos.columns:
            raise KeyError(f'El DataFrame del diccionario de datos no tiene una columna llamada {columna_diccionario_posibles_valores_alias}')
    
    # validaciones campo columna_diccionario_tipos
    columna_diccionario_tipos = preprocesador_config.get("columna_diccionario_tipos")
    if columna_diccionario_tipos is not None:
        if not isinstance(columna_diccionario_tipos, str):
            raise TypeError('El valor asociado al campo columna_diccionario_tipos debe ser de tipo str')
        if columna_diccionario_tipos not in diccionario_datos.columns:
            raise KeyError(f'El DataFrame del diccionario de datos no tiene una columna llamada {columna_diccionario_tipos}')
    
    # validaciones campo columna_diccionario_filtro_excluir
    columna_diccionario_filtro_excluir = preprocesador_config.get('columna_diccionario_filtro_excluir')
    if columna_diccionario_filtro_excluir is not None:
        if not isinstance(columna_diccionario_filtro_excluir, str):
            raise TypeError('El valor asociado al campo columna_diccionario_filtro_excluir debe ser de tipo str')
        if columna_diccionario_filtro_excluir not in diccionario_datos.columns:
            raise KeyError(f'El DataFrame del diccionario de datos no tiene una columna llamada {columna_diccionario_filtro_excluir}')
        
    # validaciones campo valores_a_excluir
    valores_a_excluir = preprocesador_config.get('valores_a_excluir')
    if valores_a_excluir is not None:
        if not isinstance(valores_a_excluir, list):
            raise TypeError('El valor asociado al campo valores_a_excluir debe ser de tipo list')
            
    # validaciones campo columna_diccionario_descripcion
    columna_diccionario_descripcion = preprocesador_config.get('columna_diccionario_descripcion')
    if columna_diccionario_descripcion is not None:
        if not isinstance(columna_diccionario_descripcion, str):
            raise TypeError('El valor asociado al campo columna_diccionario_descripcion debe ser de tipo str')
        if columna_diccionario_descripcion not in diccionario_datos.columns:
            print(f'Advertencia: El DataFrame del diccionario de datos no tiene una columna llamada {columna_diccionario_descripcion}.')
    
    # validar contenido del diccionario según especificación
    validar_diccionario(
        diccionario_datos=diccionario_datos,
        df=df,
        columna_diccionario_nombres=columna_diccionario_nombres,
        columna_diccionario_posibles_valores=columna_diccionario_posibles_valores,
        columna_diccionario_posibles_valores_alias=columna_diccionario_posibles_valores_alias,
    )

    # inicializar preprocesador
    preprocesador = Preprocesador(
        df=df, 
        diccionario_datos=diccionario_datos,
        columna_diccionario_nombres=columna_diccionario_nombres,
        columna_diccionario_posibles_valores=columna_diccionario_posibles_valores,
        columna_diccionario_descripcion=columna_diccionario_descripcion
    )
    
     # eliminar de cadenas vacias en el dataframe
    preprocesador.eliminar_cadenas_vacias()
        
    # convertir tipos en el dataframe segun campos 'columna_diccionario_tipos'
    if columna_diccionario_tipos is not None:
        preprocesador.convertir_tipos(
            columna_diccionario_tipos=columna_diccionario_tipos)
    
    # excluir columnas en el dataframe segun campos 'columna_diccionario_filtro_excluir' y 'valores_a_excluir'
    if columna_diccionario_filtro_excluir is not None:
        preprocesador.excluir_variables(
            columna_diccionario_filtro_excluir=columna_diccionario_filtro_excluir, 
            valores_a_excluir=valores_a_excluir
        )

    # validaciones campo variables_identificadoras_list_lugares
    if 'variables_identificadoras_list_lugares' not in preprocesador_config:
        raise ValueError('El archivo JSON pasado para --config debe tener el campo variables_identificadoras_list_lugares')
    variables_identificadoras_list_lugares = preprocesador_config['variables_identificadoras_list_lugares']
    if not isinstance(variables_identificadoras_list_lugares, list):
        raise TypeError('El valor asociado al campo variables_identificadoras_list_lugares debe ser de tipo list')
    
    # validaciones campo variables_a_agrupar_lugares
    if 'variables_a_agrupar_lugares' not in preprocesador_config:
        raise ValueError('El archivo JSON pasado para --config debe tener el campo variables_a_agrupar_lugares')
    variables_a_agrupar_lugares = preprocesador_config['variables_a_agrupar_lugares']
    if not isinstance(variables_a_agrupar_lugares, list):
        raise TypeError('El valor asociado al campo variables_a_agrupar_lugares debe ser de tipo list')
    
    
    # definicion de funcion para procesar agrupacion
    def procesar_agrupacion(preprocesador, variables_identificadoras_list, variables_a_agrupar):
        """
        Ejecuta la logica de agrupacion para una lista de variables identificadoras y variables a agrupar.
        Retorna el dataframe resultante y el diccionario de datos derivado.
        """

        # inicializar lista para almacenar resultados de agrupaciones
        resultados_dfs = []
        # acumuladores para el diccionario de datos derivado
        categoricas_total = []
        numericas_operaciones = {}

        # agregar conteo total de datos a la lista de resultados
        resultados_dfs.append(preprocesador.agrupar_total_datos(variables_id_agrupacion=variables_identificadoras_list))
        
        # obtener elementos de la lista 'variables_a_agrupar'
        for agrupacion in variables_a_agrupar:
            
            # validaciones elemento actual (agrupacion)
            if not isinstance(agrupacion, dict):
                raise TypeError('La lista asociada al campo preprocesamiento debe contener elementos de tipo dict')
            
            # validaciones subcampo tipo_variables
            if 'tipo_variables' not in agrupacion.keys():
                raise ValueError('El campo agrupacion debe tener una llave tipo_variables')
            tipo_variables = agrupacion['tipo_variables']
            print(f"Comenzando arupación de variables de tipo {tipo_variables}")
            
            # validaciones subcampo variables_a_agrupar_list
            if 'variables_a_agrupar_list' not in agrupacion.keys():
                raise ValueError('El campo agrupacion debe tener una llave variables_a_agrupar_list')
            variables_a_agrupar_list = agrupacion['variables_a_agrupar_list']
            
            # validaciones subcampo variables_a_agrupar_regex
            if 'variables_a_agrupar_regex' not in agrupacion.keys():
                raise ValueError('El campo agrupacion debe tener una llave variables_a_agrupar_regex')
            variables_a_agrupar_regex = agrupacion['variables_a_agrupar_regex']
            
            # campo opcional variables_a_agrupar_clasificacion_diccionario
            variables_a_agrupar_clasificacion_diccionario = agrupacion.get('variables_a_agrupar_clasificacion_diccionario')
            
            # obtener variables a agrupar segun filtros variables_a_agrupar_list, variables_a_agrupar_regex y variables_a_agrupar_clasificacion_diccionario
            # primero inicializando set para almacenar variables a agrupar, primero con los elementos de variables_a_agrupar_list
            variables_a_agrupar_total = set(variables_a_agrupar_list)
            
            # evaluar regex en lista variables_a_agrupar_regex y agregar resultado a set
            for regex in variables_a_agrupar_regex:
                
                variables_a_agrupar_total = variables_a_agrupar_total | set(obtener_variables_regex_df(regex=regex, df=preprocesador.df))
                
            # obtener subcampo opcional variables_a_agrupar_clasificacion_diccionario
            if variables_a_agrupar_clasificacion_diccionario is not None:
                
                # este a su vez tiene subcampos 'columna_diccionario_filtro' y 'valores'
                columna_diccionario_filtro = variables_a_agrupar_clasificacion_diccionario['columna_diccionario_filtro']
                valores = variables_a_agrupar_clasificacion_diccionario['valores']
                
                # obtener las filas del dataframe del diccionario donde su valor para la columna 'columna_diccionario_filtro'
                # coincida con alguno de los elementos de la lista 'valores'
                diccionario_filtrados = preprocesador.diccionario_datos.loc[preprocesador.diccionario_datos[columna_diccionario_filtro].isin(valores)]
                
                # a partir de las filas del diccionario obtener las variables filtradas en la columna 'columna_diccionario_nombres'
                variables_filtradas_clasificacion_diccionario = [var for var in diccionario_filtrados[columna_diccionario_nombres] if var in preprocesador.df.columns]
                
                # agregar variables filtradas a set
                variables_a_agrupar_total = variables_a_agrupar_total | set(variables_filtradas_clasificacion_diccionario)
                
            variables_a_agrupar_total = sorted(variables_a_agrupar_total)
            
            # imprimir en terminal lista de variables a agrupar
            print(f"Variables a agrupar según filtros: {variables_a_agrupar_total}")
            
            if tipo_variables == 'categorico':

                # agrupacion variables categoricas
                df_agregado = preprocesador.agrupar_variables_categoricas(
                    variables_id_agrupacion=variables_identificadoras_list,
                    variables_a_agrupar=variables_a_agrupar_total
                )

                # agregar agrupacion a lista de resultados correspondiente
                resultados_dfs.append(df_agregado)

                # acumular variables categoricas agrupadas para el diccionario derivado
                for v in variables_a_agrupar_total:
                    if v not in categoricas_total:
                        categoricas_total.append(v)

            elif tipo_variables == 'numerico':

                # validacion subcampo operacion, solo cuando el subcampo tipo_variables es == 'numerico'
                if 'operacion' not in agrupacion.keys():
                    raise ValueError('El campo agrupacion debe tener una llave operacion cuando se selecciona el valor numerico para tipo_variables')
                operacion = agrupacion['operacion']

                # agrupacion variables numericas
                df_agregado = preprocesador.agrupar_variables_numericas(
                    variables_id_agrupacion=variables_identificadoras_list,
                    variables_a_agrupar=variables_a_agrupar_total,
                    operacion=operacion
                )

                # agregar agrupacion a lista de resultados correspondiente
                resultados_dfs.append(df_agregado)

                # acumular variables numericas y sus operaciones para el diccionario derivado
                for v in variables_a_agrupar_total:
                    operaciones_v = numericas_operaciones.setdefault(v, [])
                    if operacion not in operaciones_v:
                        operaciones_v.append(operacion)

            else:
                raise ValueError('El valor de tipo_variables debe ser una de las cadenas: categorico, numerico')

        # hacer join de todas las agrupaciones realizadas
        join_dfs = functools.reduce(
            lambda left, right: pd.merge(left, right, on=variables_identificadoras_list, how='inner'),
            resultados_dfs
        )

        # generar diccionario de datos derivado (variable original sustituida por sus N variables derivadas)
        diccionario_derivado = preprocesador.generar_diccionario_derivado(
            variables_categoricas=categoricas_total,
            variables_numericas_operaciones=numericas_operaciones,
            columna_diccionario_alias=columna_diccionario_alias,
            columna_diccionario_posibles_valores_alias=columna_diccionario_posibles_valores_alias
        )

        return join_dfs, diccionario_derivado

    # --- PROCESAMIENTO LUGARES ---
    if variables_identificadoras_list_lugares:
        print("--- Procesando Agrupación por Lugares ---")
        join_dfs_lugares, diccionario_derivado_lugares = procesar_agrupacion(preprocesador, variables_identificadoras_list_lugares, variables_a_agrupar_lugares)

        # guardar resultados lugares
        join_dfs_lugares.to_csv(ruta_salida_dataset, index=False)
        print(f'Archivo csv de datos preprocesados (lugares) creado en la ruta {ruta_salida_dataset}')
        diccionario_derivado_lugares.to_csv(ruta_salida_diccionario_datos, index=False)
        print(f'Archivo csv de diccionario de datos derivado (lugares) creado en la ruta {ruta_salida_diccionario_datos}')
    else:
        print("Advertencia: variables_identificadoras_list_lugares está vacío, se omite el procesamiento de lugares.")

    # --- PROCESAMIENTO ENSAMBLE SECUNDARIO (Opcional) ---
    if 'variables_identificadoras_list_personas' in preprocesador_config and 'variables_a_agrupar_personas' in preprocesador_config:
        tipo_ensamble = preprocesador_config.get('tipo_ensamble', 'personas')
        print(f"--- Procesando Datos por {tipo_ensamble} ---")
        variables_identificadoras_list_personas = preprocesador_config['variables_identificadoras_list_personas']
        variables_a_agrupar_personas = preprocesador_config['variables_a_agrupar_personas']

        if isinstance(variables_identificadoras_list_personas, list) and len(variables_identificadoras_list_personas) > 0 and isinstance(variables_a_agrupar_personas, list):

            join_dfs_personas, diccionario_derivado_personas = procesar_agrupacion(preprocesador, variables_identificadoras_list_personas, variables_a_agrupar_personas)

            # Drop conteo::total_datos for records since it's redundant (always 1 for single records)
            if 'conteo::total_datos' in join_dfs_personas.columns:
                join_dfs_personas = join_dfs_personas.drop(columns=['conteo::total_datos'])
            diccionario_derivado_personas = diccionario_derivado_personas[
                diccionario_derivado_personas[columna_diccionario_nombres] != 'conteo::total_datos'
            ]

            # generar rutas de salida usando el tipo de ensamble configurado
            ruta_salida_dataset_personas = ruta_salida_dataset.replace('.csv', f'_{tipo_ensamble}.csv')
            ruta_salida_diccionario_datos_personas = ruta_salida_diccionario_datos.replace('.csv', f'_{tipo_ensamble}.csv')

            # guardar resultados
            join_dfs_personas.to_csv(ruta_salida_dataset_personas, index=False)
            print(f'Archivo csv de datos preprocesados ({tipo_ensamble}) creado en la ruta {ruta_salida_dataset_personas}')
            diccionario_derivado_personas.to_csv(ruta_salida_diccionario_datos_personas, index=False)
            print(f'Archivo csv de diccionario de datos derivado ({tipo_ensamble}) creado en la ruta {ruta_salida_diccionario_datos_personas}')
        else:
             print("Advertencia: claves de configuración para el ensamble secundario existen pero no son listas válidas.")



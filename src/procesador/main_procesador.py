import pandas as pd
import os
import argparse
import json
import time
from procesador.procesador import Procesador


def ejecutar_procesamiento_presencia(
    dataframes_mallas,
    dataframe_diccionario,
    columna_diccionario_nombres,
    columna_diccionario_alias,
    columna_diccionario_descripcion,
    variables_identificadoras,
    variables_excluidas_list,
    variables_excluidas_regex,
    variables_a_procesar_list_presencia,
    variables_a_procesar_regex_presencia,
    columna_diccionario_path=None,
):
    """
    Ejecuta el flujo de procesamiento de presencia: para cada variable, genera la lista
    de lugares con valor >= 1 en la salida del preprocesamiento, sin categorizar en bins.
    """
    procesador = Procesador(
        dataframes_mallas=dataframes_mallas,
        dataframe_diccionario=dataframe_diccionario,
        columna_diccionario_nombres=columna_diccionario_nombres,
        columna_diccionario_alias=columna_diccionario_alias,
        columna_diccionario_descripcion=columna_diccionario_descripcion,
        columna_diccionario_path=columna_diccionario_path,
        variables_identificadoras=variables_identificadoras,
        variables_excluidas_list=variables_excluidas_list,
        variables_excluidas_regex=variables_excluidas_regex,
    )

    mallas = list(dataframes_mallas.keys())
    resultados = []

    if variables_a_procesar_list_presencia:
        df_list = procesador.procesar_multiples_variables_list_presencia(
            mallas=mallas,
            lista_vars=variables_a_procesar_list_presencia,
        )
        if not df_list.empty:
            resultados.append(df_list)

    if variables_a_procesar_regex_presencia:
        df_regex = procesador.procesar_multiples_variables_regex_presencia(
            mallas=mallas,
            regex_list=variables_a_procesar_regex_presencia,
        )
        if not df_regex.empty:
            resultados.append(df_regex)

    if not resultados:
        return pd.DataFrame()

    resultado = pd.concat(resultados, ignore_index=True)
    resultado = resultado.drop_duplicates(subset=['code']).sort_values(by='code').reset_index(drop=True)
    return resultado


def ejecutar_procesamiento(
    dataframes_mallas,
    dataframe_diccionario,
    columna_diccionario_nombres,
    columna_diccionario_alias,
    columna_diccionario_descripcion,
    variables_identificadoras,
    variables_excluidas_list,
    variables_excluidas_regex,
    variables_a_procesar_list,
    variables_a_procesar_regex,
    q,
    columna_diccionario_path=None,
):
    """
    Ejecuta el flujo de procesamiento para un conjunto de variables y configuraciones.
    """
    # inicializar procesador
    procesador = Procesador(
        dataframes_mallas=dataframes_mallas,
        dataframe_diccionario=dataframe_diccionario,
        columna_diccionario_nombres=columna_diccionario_nombres,
        columna_diccionario_alias=columna_diccionario_alias,
        columna_diccionario_descripcion=columna_diccionario_descripcion,
        columna_diccionario_path=columna_diccionario_path,
        variables_identificadoras=variables_identificadoras,
        variables_excluidas_list=variables_excluidas_list,
        variables_excluidas_regex=variables_excluidas_regex
    )
    
    # procesar variables especificadas por listas explicitas
    procesamiento_listas = pd.DataFrame()
    if variables_a_procesar_list is not None:
        if 'None' in variables_a_procesar_list:
            variables_a_procesar_list[None] = variables_a_procesar_list.pop('None')
        procesamiento_listas_dict = procesador.procesar_multiples_variables_list(mallas=list(dataframes_mallas.keys()), dicc=variables_a_procesar_list, q=q)
        procesamiento_listas = pd.concat(
            [df for df in procesamiento_listas_dict.values() if df is not None]
        ) if any(df is not None for df in procesamiento_listas_dict.values()) else pd.DataFrame()
        
    # procesar variables especificadas por listas de expresiones regulares
    procesamiento_regex = pd.DataFrame()
    if variables_a_procesar_regex is not None:
        if 'None' in variables_a_procesar_regex:
            variables_a_procesar_regex[None] = variables_a_procesar_regex.pop('None')
        procesamiento_regex_dict = procesador.procesar_multiples_variables_regex(mallas=list(dataframes_mallas.keys()), dicc=variables_a_procesar_regex, q=q)
        procesamiento_regex = pd.concat(
            [df for df in procesamiento_regex_dict.values() if df is not None]
        ) if any(df is not None for df in procesamiento_regex_dict.values()) else pd.DataFrame()

    # combinar resultados de ambos tipos de procesamiento
    resultado = pd.DataFrame()
    if variables_a_procesar_list and variables_a_procesar_regex:
        resultado = pd.concat([procesamiento_regex, procesamiento_listas])
    elif variables_a_procesar_list:
        resultado = procesamiento_listas
    elif variables_a_procesar_regex:
        resultado = procesamiento_regex
        
    if not resultado.empty:
        resultado = resultado.sort_values(by=['code', 'bin']).reset_index(drop=True)
        resultado['bin'] = resultado.groupby('code').cumcount() + 1
        
    return resultado

if __name__ == '__main__':
    """
    Script principal para ejecutar el procesamiento de datos utilizando la clase Procesador.
    
    Este script toma un archivo de configuración en formato JSON que especifica las rutas de entrada, 
    las variables a procesar, y otros parámetros necesarios para el procesamiento. Genera un archivo 
    CSV con los resultados del procesamiento.
    
    Raises:
        ValueError: Si el archivo de configuración no contiene los campos requeridos.
        FileNotFoundError: Si alguna de las rutas especificadas en el archivo de configuración no existe.
    """
    
    # timestamp de inicio de ejecucion del programa
    print("Iniciando procesamiento...")
    timestamp_inicio = time.time()
    
    # definir flag de archivo de configuracion
    parser = argparse.ArgumentParser(description='Procesador de datos C3')
    parser.add_argument('--config', type=str, required=True, help='Archivo de configuración')

    args = parser.parse_args()
    
    # cargar archivo de configuracion
    if not os.path.exists(args.config):
        raise FileNotFoundError(f'No se encontró el archivo de configuración: {args.config}')
    try:
        with open(args.config) as f:
            procesador_config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f'El archivo de configuración {args.config} no es un JSON válido: {e}') from None
    except PermissionError:
        raise PermissionError(f'No hay permisos para leer el archivo de configuración: {args.config}') from None
    

    print("Configuración cargada:", procesador_config)
    # validaciones campo rutas_csv_mallas
    if 'rutas_csv_mallas' not in procesador_config:
        raise ValueError('El archivo JSON pasado para --config debe tener el campo rutas_csv_mallas')
    rutas_csv_mallas = procesador_config['rutas_csv_mallas']
    
    # validaciones campo ruta_csv_diccionario_datos
    if 'ruta_csv_diccionario_datos' not in procesador_config:
        raise ValueError('El archivo JSON pasado para --config debe tener el campo ruta_csv_diccionario_datos')
    ruta_csv_diccionario_datos = procesador_config['ruta_csv_diccionario_datos']
    if not os.path.exists(ruta_csv_diccionario_datos):
        raise FileNotFoundError('La ruta especificada para el archivo .csv del diccionario de datos no existe')

    # validaciones campo columna_diccionario_nombres
    if 'columna_diccionario_nombres' not in procesador_config:
        raise ValueError('El archivo JSON pasado para --config debe tener el campo columna_diccionario_nombres')
    columna_diccionario_nombres = procesador_config['columna_diccionario_nombres']

    # campo opcional columna_diccionario_alias (default 'alias')
    columna_diccionario_alias = procesador_config.get('columna_diccionario_alias', 'alias')

    columna_diccionario_descripcion = procesador_config.get('columna_diccionario_descripcion', None)
    columna_diccionario_path = procesador_config.get('columna_diccionario_path', None)
    
    # obtener listas de variables a excluir mediante lista explicita y/o lista de expresiones regulares,
    # en caso de existir el campo en el archivo de configuracion
    # obtener listas de variables a excluir mediante lista explicita y/o lista de expresiones regulares,
    # en caso de existir el campo en el archivo de configuracion
    variables_excluidas_list_lugares = procesador_config.get('variables_excluidas_list_lugares', [])
    variables_excluidas_regex_lugares = procesador_config.get('variables_excluidas_regex_lugares', [])
    
    # validaciones campo variables_identificadoras_lugares
    if 'variables_identificadoras_lugares' not in procesador_config:
        raise ValueError('El archivo JSON pasado para --config debe tener el campo variables_identificadoras_lugares')
    variables_identificadoras_lugares = procesador_config.get('variables_identificadoras_lugares')
    if not isinstance(variables_identificadoras_lugares, dict):
        raise ValueError('El campo variables_identificadoras_lugares debe ser un diccionario {malla: [col1, col2, ...]}')
    
    # validaciones campos variables_a_procesar_list_lugares y variables_a_procesar_regex_lugares
    if 'variables_a_procesar_list_lugares' not in procesador_config and 'variables_a_procesar_regex_lugares' not in procesador_config:
        raise ValueError('El archivo JSON pasado para --config debe tener al menos uno de los campos: variables_a_procesar_list_lugares, o variables_a_procesar_regex_lugares')
    variables_a_procesar_list_lugares = procesador_config.get('variables_a_procesar_list_lugares', None)
    variables_a_procesar_regex_lugares = procesador_config.get('variables_a_procesar_regex_lugares', None)
    
    # validaciones campo q
    if 'q' not in procesador_config:
        raise ValueError('El archivo JSON pasado para --config debe tener el campo q')
    q = procesador_config['q']
    
    # validaciones campo ruta_csv_salida
    if 'ruta_csv_salida' not in procesador_config:
        raise ValueError('El archivo JSON pasado para --config debe tener el campo ruta_csv_salida')
    ruta_csv_salida = procesador_config['ruta_csv_salida']
    
    # inicializar diccionario para almacenar dataframes de mallas especificadas
    dataframes_mallas = {}
    
    for malla, ruta in rutas_csv_mallas.items():
        
        # validaciones valores diccionario rutas_csv_mallas (rutas de archivos csv de dataframes)
        if not os.path.exists(ruta):
            raise FileNotFoundError(f'La ruta especificada para el archivo .csv de la malla {malla} no existe')
        
        # validaciones diccionario variables identificadoras
        if malla not in variables_identificadoras_lugares:
            raise ValueError(f'El diccionario de variables identificadoras no contiene la malla {malla}')
        
        # obtener variables identificadoras para malla
        id_cols = variables_identificadoras_lugares[malla]
        
        # cargar dataframe de malla actual con columnas identificadoras de tipo str
        dtype_dict = {col: str for col in id_cols}
        dataframes_mallas[malla] = pd.read_csv(ruta, dtype=dtype_dict)
        
    # cargar dataframe de diccionario de datos
    dataframe_diccionario = pd.read_csv(ruta_csv_diccionario_datos)

    # validaciones columnas del diccionario
    if columna_diccionario_nombres not in dataframe_diccionario.columns:
        raise ValueError(f'El DataFrame correspondiente al campo ruta_csv_diccionario_datos debe contener la columna {columna_diccionario_nombres}')
    if columna_diccionario_alias not in dataframe_diccionario.columns:
        raise ValueError(f'El DataFrame correspondiente al campo ruta_csv_diccionario_datos debe contener la columna {columna_diccionario_alias}')

    # --- PROCESAMIENTO LUGARES ---
    if variables_identificadoras_lugares:
        print("--- Procesando Lugares ---")
        resultado = ejecutar_procesamiento(
            dataframes_mallas=dataframes_mallas,
            dataframe_diccionario=dataframe_diccionario,
            columna_diccionario_nombres=columna_diccionario_nombres,
            columna_diccionario_alias=columna_diccionario_alias,
            columna_diccionario_descripcion=columna_diccionario_descripcion,
            columna_diccionario_path=columna_diccionario_path,
            variables_identificadoras=variables_identificadoras_lugares,
            variables_excluidas_list=variables_excluidas_list_lugares,
            variables_excluidas_regex=variables_excluidas_regex_lugares,
            variables_a_procesar_list=variables_a_procesar_list_lugares,
            variables_a_procesar_regex=variables_a_procesar_regex_lugares,
            q=q
        )

        # --- PROCESAMIENTO PRESENCIA (Opcional) ---

        variables_a_procesar_list_presencia = procesador_config.get('variables_a_procesar_list_presencia', None)
        variables_a_procesar_regex_presencia = procesador_config.get('variables_a_procesar_regex_presencia', None)

        if variables_a_procesar_list_presencia is not None or variables_a_procesar_regex_presencia is not None:
            print("--- Procesando Presencia ---")
            resultado_presencia = ejecutar_procesamiento_presencia(
                dataframes_mallas=dataframes_mallas,
                dataframe_diccionario=dataframe_diccionario,
                columna_diccionario_nombres=columna_diccionario_nombres,
                columna_diccionario_alias=columna_diccionario_alias,
                columna_diccionario_descripcion=columna_diccionario_descripcion,
                columna_diccionario_path=columna_diccionario_path,
                variables_identificadoras=variables_identificadoras_lugares,
                variables_excluidas_list=variables_excluidas_list_lugares,
                variables_excluidas_regex=variables_excluidas_regex_lugares,
                variables_a_procesar_list_presencia=variables_a_procesar_list_presencia,
                variables_a_procesar_regex_presencia=variables_a_procesar_regex_presencia,
            )

            if not resultado_presencia.empty:
                resultado = pd.concat([resultado, resultado_presencia], ignore_index=True)

        # verificar duplicados en resultado
        duplicados = resultado.duplicated(['code', 'bin'])

        # imprimir advertencia de duplicados en resultado
        if duplicados.any():
            print('Advertencia: el resultado del procesamiento contiene categorías duplicadas:')
            print(resultado.loc[duplicados, ['code', 'bin']])

        # guardar resultado en archivo csv segun ruta_csv_salida
        resultado.to_csv(ruta_csv_salida, index=False)
        print(f'Archivo csv de datos procesados (lugares) creado en la ruta {ruta_csv_salida}')
    else:
        print("Advertencia: variables_identificadoras_lugares está vacío, se omite el procesamiento de lugares.")

    # --- PROCESAMIENTO ENSAMBLE SECUNDARIO (Opcional) ---

    if 'variables_identificadoras_personas' in procesador_config and procesador_config.get('variables_identificadoras_personas'):
         tipo_ensamble = procesador_config.get('tipo_ensamble', 'personas')
         print(f"--- Procesando {tipo_ensamble} ---")

         # Obtener configuraciones de ensamble secundario
         variables_identificadoras_personas = procesador_config.get('variables_identificadoras_personas')
         variables_excluidas_list_personas = procesador_config.get('variables_excluidas_list_personas', [])
         variables_excluidas_regex_personas = procesador_config.get('variables_excluidas_regex_personas', [])
         variables_a_procesar_list_personas = procesador_config.get('variables_a_procesar_list_personas', None)
         variables_a_procesar_regex_personas = procesador_config.get('variables_a_procesar_regex_personas', None)

         # Obtener rutas de csv para el ensamble secundario
         if 'rutas_csv_personas' not in procesador_config:
             raise ValueError('El archivo JSON pasado para --config debe tener el campo rutas_csv_personas si se especifican variables_identificadoras_personas')
         rutas_csv_personas = procesador_config['rutas_csv_personas']

         # Cargar dataframes del ensamble secundario
         dataframes_personas = {}
         for malla, ruta in rutas_csv_personas.items():
             if not os.path.exists(ruta):
                 raise FileNotFoundError(f'La ruta especificada para el archivo .csv de la malla {malla} no existe')

             if malla not in variables_identificadoras_personas:
                 raise ValueError(f'El diccionario de variables identificadoras ({tipo_ensamble}) no contiene la malla {malla}')

             id_cols = variables_identificadoras_personas[malla]
             dtype_dict = {col: str for col in id_cols}
             dataframes_personas[malla] = pd.read_csv(ruta, dtype=dtype_dict)

         # Cargar dataframe de diccionario para el ensamble secundario (opcional, fallback al general)
         ruta_diccionario_personas = procesador_config.get('ruta_csv_diccionario_datos_personas')
         if ruta_diccionario_personas and os.path.exists(ruta_diccionario_personas):
             dataframe_diccionario_personas = pd.read_csv(ruta_diccionario_personas)
         else:
             dataframe_diccionario_personas = dataframe_diccionario

         # Ejecutar procesamiento
         resultado_personas = ejecutar_procesamiento(
            dataframes_mallas=dataframes_personas,
            dataframe_diccionario=dataframe_diccionario_personas,
            columna_diccionario_nombres=columna_diccionario_nombres,
            columna_diccionario_alias=columna_diccionario_alias,
            columna_diccionario_descripcion=columna_diccionario_descripcion,
            columna_diccionario_path=columna_diccionario_path,
            variables_identificadoras=variables_identificadoras_personas,
            variables_excluidas_list=variables_excluidas_list_personas,
            variables_excluidas_regex=variables_excluidas_regex_personas,
            variables_a_procesar_list=variables_a_procesar_list_personas,
            variables_a_procesar_regex=variables_a_procesar_regex_personas,
            q=q
        )

         # Generar ruta de salida usando el tipo de ensamble configurado
         ruta_csv_salida_personas = ruta_csv_salida.replace('.csv', f'_{tipo_ensamble}.csv')

         # Guardar resultado
         resultado_personas.to_csv(ruta_csv_salida_personas, index=False)
         print(f'Archivo csv de datos procesados ({tipo_ensamble}) creado en la ruta {ruta_csv_salida_personas}')

    # imprimir tiempo total de ejecucion
    timestamp_fin = time.time()
    print(f"Tiempo total de ejecución: {timestamp_fin - timestamp_inicio:.2f} segundos")
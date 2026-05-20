import os
import numpy as np
import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import re
from typing import Optional
from utils.regex_utils import obtener_variables_regex_df

class Procesador:
    """
    Clase para procesar variables de múltiples DataFrames asociados a diferentes mallas,
    realizando operaciones de normalización y categorización, para generar un nuevo archivo como resultado.
    Todos DataFrames que toma como atributos esta clase son generados por la clase Preprocesador.
    """
    def __init__(self, dataframes_mallas:dict, dataframe_diccionario:pd.DataFrame, columna_diccionario_nombres:str, columna_diccionario_alias:str, variables_identificadoras:dict, variables_excluidas_list:list, variables_excluidas_regex:list, columna_diccionario_descripcion:str=None):
        """
        Inicializa el procesador validando los parámetros y configurando las variables a excluir.

        Args:
            dataframes_mallas (dict): Diccionario {malla: DataFrame}.
            dataframe_diccionario (pd.DataFrame): Diccionario de datos derivado generado por el preprocesador.
            columna_diccionario_nombres (str): Columna con los nombres de variable que coinciden con las columnas de los DataFrames de las mallas.
            columna_diccionario_alias (str): Columna con la versión legible (alias) de cada variable.
            variables_identificadoras (dict): Diccionario de variables identificadoras por malla.
            variables_excluidas_list (list): Lista de variables a excluir (explícitamente).
            variables_excluidas_regex (list): Lista de variables a excluir (por expresión regular).
            columna_diccionario_descripcion (str, opcional): Columna con la descripción de cada variable.

        Raises:
            TypeError: Si los parámetros no son del tipo esperado.
            ValueError: Si los parámetros no son válidos.
        """
        # validaciones dataframes_mallas
        if not isinstance(dataframes_mallas, dict):
            raise TypeError('El valor del parámetro dataframes_mallas debe ser de tipo dict')
        if not all(isinstance(llave, str) for llave in dataframes_mallas.keys()):
            raise TypeError('Las llaves del diccionario dataframes_mallas deben ser de tipo str')
        if not all(isinstance(valor, pd.DataFrame) for valor in dataframes_mallas.values()):
            raise TypeError('Los valores del diccionario dataframes_mallas deben ser de tipo pd.DataFrame')

        # validaciones dataframe_diccionario
        if not isinstance(dataframe_diccionario, pd.DataFrame):
            raise TypeError('El valor del parámetro dataframe_diccionario debe ser de tipo pd.DataFrame')

        # validaciones columna_diccionario_nombres y columna_diccionario_alias
        if not isinstance(columna_diccionario_nombres, str):
            raise TypeError('El valor del parámetro columna_diccionario_nombres debe ser de tipo str')
        if not isinstance(columna_diccionario_alias, str):
            raise TypeError('El valor del parámetro columna_diccionario_alias debe ser de tipo str')
        if columna_diccionario_nombres not in dataframe_diccionario.columns:
            raise ValueError(f'El DataFrame de diccionario debe contener una columna con nombre {columna_diccionario_nombres} para identificar el nombre de cada variable')
        if columna_diccionario_alias not in dataframe_diccionario.columns:
            raise ValueError(f'El DataFrame de diccionario debe contener una columna con nombre {columna_diccionario_alias} para identificar el alias de cada variable')
        
        # validaciones variables_identificadoras
        if not isinstance(variables_identificadoras, dict):
            raise TypeError('El parámetro variables_identificadoras debe ser un dict {malla: [vars]}')
        for malla, vars_id in variables_identificadoras.items():
            if malla not in dataframes_mallas:
                raise ValueError(f'La malla {malla} de variables_identificadoras no está en los dataframes')
            if not isinstance(vars_id, list):
                raise TypeError(f'Las variables identificadoras de la malla {malla} deben ser una lista')
            for var in vars_id:
                if var not in dataframes_mallas[malla].columns:
                    raise ValueError(f'La variable identificadora {var} no está en el DataFrame de la malla {malla}')
        self.variables_identificadoras = variables_identificadoras
                
        # validaciones variables_excluidas_list
        if not (isinstance(variables_excluidas_list, list)):
            raise TypeError('El valor del parámetro variables_excluidas_list debe ser de tipo list')
        if not (all(isinstance(x, str) for x in variables_excluidas_list)):
            raise TypeError('Los elementos de la lista variables_excluidas_list deben ser de tipo str')
        
        # validaciones variables_excluidas_regex
        if not (isinstance(variables_excluidas_regex, list)):
            raise TypeError('El valor del parámetro variables_excluidas_regex debe ser de tipo list')
        for regex in variables_excluidas_regex:
            try:
                re.compile(regex)
            except re.error:
                raise ValueError(f'Los elementos de la lista variables_excluidas_regex deben ser expresiones regular válidas, es inválida: {regex}')
        
        # asignacion de atributos
        self.dataframes_mallas = dataframes_mallas
        # mapeo: nombre que coincide con la columna del dataset -> alias legible
        self.alias = dict(zip(dataframe_diccionario[columna_diccionario_nombres].astype(str), dataframe_diccionario[columna_diccionario_alias]))
        self.descripcion = {}
        if columna_diccionario_descripcion and columna_diccionario_descripcion in dataframe_diccionario.columns:
            self.descripcion = dict(zip(dataframe_diccionario[columna_diccionario_nombres].astype(str), dataframe_diccionario[columna_diccionario_descripcion]))
            
        self.variables_identificadoras = variables_identificadoras
        self.variables_excluidas = set(variables_excluidas_list)
        self.variables_faltantes_alias = []
        
        # imprimir en terminal variables excluidas por lista explicita
        print(f'Variables a excluir por lista explícita: {variables_excluidas_list}')
        
        # agregar variables excluidas a set segun las regex especificadas e imprimir en terminal
        variables_excluidas_encontradas_regex = set()
        for regex in variables_excluidas_regex:
            for dataframe in dataframes_mallas.values():
                variables_excluidas_encontradas_regex |= set(obtener_variables_regex_df(dataframe, regex))
        variables_excluidas_encontradas_regex = sorted(list(variables_excluidas_encontradas_regex))
        print(f'Variables a excluir encontradas por lista de regex: {variables_excluidas_encontradas_regex}')
            
        # verificar variables faltantes en el diccionario de alias
        self.variables_faltantes_alias = []
        variables_consideradas = set()
        for dataframe in dataframes_mallas.values():
            variables_consideradas = variables_consideradas | set(dataframe.columns)
        variables_en_alias = set(self.alias.keys())
        
        # si se encuentran variables en el dataframe que no existen en el diccionario de alias,
        # se agregan al set de excluidas, se guardan en el atributo self.variables_faltantes_alias
        if not (variables_consideradas).issubset(variables_en_alias):
            variables_faltantes = variables_consideradas - variables_en_alias
            self.variables_excluidas = self.variables_excluidas | variables_faltantes
            self.variables_faltantes_alias = variables_faltantes
        
        # eliminar variables excluidas de los DataFrames excepto identificadoras
        variables_identificadoras_set = set([var for lista in variables_identificadoras.values() for var in lista])
        for malla, df in self.dataframes_mallas.items():
            self.dataframes_mallas[malla] = df.drop(columns=[col for col in self.variables_excluidas if col in df.columns and col not in variables_identificadoras_set])
            
        # convertir sets en listas ordenadas
        self.variables_excluidas = sorted(list(self.variables_excluidas))
        self.variables_faltantes_alias = sorted(list(self.variables_faltantes_alias))
        
        # imprimir en terminal variables faltantes en el diccionario
        print(f'Variables del DataFrame faltantes en el alias (se excluirán automáticamente): {self.variables_faltantes_alias}')

    def get_variables_excluidas(self) -> list:
        """
        Obtiene la lista de variables excluidas.

        Returns:
            list: Lista de variables excluidas.
        """
        return list(self.variables_excluidas)

    def get_variables_faltantes_alias(self) -> list:
        """
        Obtiene la lista de variables faltantes en el diccionario de alias.

        Returns:
            list: Lista de variables faltantes en el diccionario.
        """
        return list(self.variables_faltantes_alias)
    
    def normalizar_variable(self, malla:str, var:str, var_base_normalizacion:Optional[str]=None) -> pd.Series:
        """
        Normaliza una variable dividiendo sus valores entre los valores de una variable base de normalización.

        Args:
            malla (str): Nombre de la malla (DataFrame) donde se encuentra la variable.
            var (str): Nombre de la variable a normalizar.
            var_base_normalizacion (str, optional): Nombre de la variable base para la normalización. Si es None, no se realiza la división.

        Returns:
            pd.Series: Serie con los valores normalizados.

        Raises:
            TypeError: Si los parámetros no son del tipo esperado.
            ValueError: Si los parámetros no son válidos.
        """
        # validaciones malla
        if not isinstance(malla, str):
            raise TypeError('El parámetro malla debe ser de tipo str')
        if malla not in self.dataframes_mallas.keys():
            raise ValueError('La malla especificada no es válida')
        
        # dataframe correspondiente a la malla
        df = self.dataframes_mallas[malla]
        
        # validaciones var
        if not isinstance(var, str):
            raise TypeError('El parámetro var debe ser de tipo str')
        if var not in df.columns:
            raise ValueError(f'La variable {var} no existe en el DataFrame de la malla especificada')
        if var in self.variables_excluidas:
            raise ValueError(f'La variable {var} está en la lista de variables excluidas')
        
        # validaciones var_base_normalizacion
        if var_base_normalizacion is not None:
            if not isinstance(var_base_normalizacion, str):
                raise TypeError('El parámetro var_base_normalizacion debe ser de tipo str o None')
            if var_base_normalizacion not in df.columns:
                raise ValueError(f'La variable {var_base_normalizacion} no existe en el DataFrame de la malla especificada')
            if var_base_normalizacion in self.variables_excluidas:
                raise ValueError(f'La variable {var_base_normalizacion} está en la lista de variables excluidas')
            
            # reemplazar valores de cero en la variable base por NaN para evitar divisiones por cero
            if df[var_base_normalizacion].eq(0).any():
                print(f'Advertencia: La variable {var_base_normalizacion} contiene valores de cero, reemplazando por NaN para evitar potenciales divisiones entre cero')
                df[var_base_normalizacion] = df[var_base_normalizacion].replace(0, np.nan)
                
        # dividir la variable entre la base, si no se especifica no se aplica ninuna operacion
        return df[var] / df[var_base_normalizacion] if var_base_normalizacion is not None else df[var]
    
    def categorizar_variable(self, malla:str, var:str, var_base_normalizacion:Optional[str]=None, q: int=10) -> pd.Series:
        """
        Categorización de una variable en cuantiles, con la opción de normalizarla previamente.

        Args:
            malla (str): Nombre de la malla (DataFrame) donde se encuentra la variable.
            var (str): Nombre de la variable a categorizar.
            var_base_normalizacion (str, optional): Nombre de la variable base para la normalización. Si es None, no se realiza la normalización.
            q (int): Número de cuantiles para la categorización.

        Returns:
            pd.Series: Serie categorizada en cuantiles.

        Raises:
            TypeError: Si los parámetros no son del tipo esperado.
            ValueError: Si los parámetros no son válidos.
        """
        # validaciones malla
        if not isinstance(malla, str):
            raise TypeError('El parámetro malla debe ser de tipo str')
        if malla not in self.dataframes_mallas.keys():
            raise ValueError('La malla especificada no es válida')
        
        # dataframe correspondiente a la malla
        df = self.dataframes_mallas[malla]
        
        # validaciones var
        if not isinstance(var, str):
            raise TypeError('El parámetro var debe ser de tipo str')
        if var not in df.columns:
            raise ValueError(f'La variable {var} no existe en el DataFrame de la malla especificada')
        if var in self.variables_excluidas:
            raise ValueError(f'La variable {var} está en la lista de variables excluidas')
        
        # validaciones var_base_normalizacion
        if var_base_normalizacion is not None:
            if not isinstance(var_base_normalizacion, str):
                raise TypeError('El parámetro var_base_normalizacion debe ser de tipo str o None')
            if var_base_normalizacion not in df.columns:
                raise ValueError(f'La variable {var_base_normalizacion} no existe en el DataFrame de la malla especificada')
            if var_base_normalizacion in self.variables_excluidas:
                raise ValueError(f'La variable {var_base_normalizacion} está en la lista de variables excluidas')
        
        # validaciones q
        if not isinstance(q, int):
            raise TypeError('El parámetro q debe ser de tipo int')
        if q < 1:
            raise ValueError('El valor de q debe ser mayor a 1')
        
        # normalizar la variable si se especifica una base de normalización, y categorizarla en cuantiles
        return pd.qcut(self.normalizar_variable(malla=malla, var=var, var_base_normalizacion=var_base_normalizacion), q=q, duplicates='drop')
    
    def __list_a_postgres_array(self, lista:list) -> str:
        """
        Convierte una lista en un formato compatible con un array de PostgreSQL.

        Args:
            lista (list): Lista a convertir.

        Returns:
            str: Cadena con el formato de array de PostgreSQL.
        """
        # validaciones lista
        if not isinstance(lista, list) and not all(isinstance(x, str) for x in lista):
            raise TypeError('El parámetro list debe ser de tipo list, y cada elemento debe ser de tipo str')
            
        # eliminar comillas simples y dobles de los elementos de la lista
        clean = [str(x).replace("'", "").replace('"', "") for x in lista]
        
        return '{' + ','.join(f'{c}' for c in lista) + '}'
    
    def procesar_variable(self, mallas:list, var:str, var_base_normalizacion:Optional[str]=None, q:int=10) -> pd.DataFrame:
        """
        Procesa una variable específica en las mallas especificadas, normalizándola y categorizándola en cuantiles.

        Args:
            mallas (list): Lista de mallas (DataFrames) donde se procesará la variable.
            var (str): Nombre de la variable a procesar.
            var_base_normalizacion (str, optional): Nombre de la variable base para la normalización. Si es None, no se realiza la normalización.
            q (int): Número de cuantiles para la categorización.

        Returns:
            pd.DataFrame: DataFrame con los resultados del procesamiento de la variable.

        Raises:
            TypeError: Si los parámetros no son del tipo esperado.
            ValueError: Si los parámetros no son válidos.
        """
        # validaciones mallas
        if not isinstance(mallas, list):
            raise TypeError('El parámetro mallas debe ser de tipo list')
        for malla in mallas:
            if not isinstance(malla, str):
                raise TypeError('Los elementos del parámetro mallas deben ser de tipo str')
            if malla not in self.dataframes_mallas.keys():
                raise ValueError(f'La malla {malla} no es válida, pues no fue proporcionado un DataFrame para esta')
        
        # validaciones var
        if not isinstance(var, str):
            raise TypeError('El parámetro var debe ser de tipo str')
        if var in self.variables_identificadoras:
            raise ValueError(f'La variable {var} está en la lista de variables identificadoras, no se procesará')
        if var in self.variables_excluidas:
            raise ValueError(f'La variable {var} está en la lista de variables excluidas')
        
        # validaciones var_base_normalizacion
        if var_base_normalizacion is not None:
            if not isinstance(var_base_normalizacion, str):
                raise TypeError('El parámetro var_base_normalizacion debe ser de tipo str o None')
            if var_base_normalizacion in self.variables_identificadoras:
                raise ValueError(f'La variable {var_base_normalizacion} está en la lista de variables identificadoras, no se procesará')
            if var_base_normalizacion in self.variables_excluidas:
                raise ValueError(f'La variable {var_base_normalizacion} está en la lista de variables excluidas, no se procesará')
        
        # validaciones q
        if not isinstance(q, int):
            raise TypeError('El parámetro q debe ser de tipo int')
        if q < 1:
            raise ValueError('El valor de q debe ser mayor a 1')
        
        # inicializar diccionario para almacenar los resultados
        resultado = {
            'name': [],
            'code': [],
            'descripcion': [],
            'bin': []
        }
        
        # inicializar diccionarios para verificar si var y var_base_normalizacion existen en las mallas,
        # cada malla es una llave, y el valor es True o False dependiendo si la variable se encuentra en el dataframe de la malla
        validacion_mallas_var = {malla:False for malla in mallas}
        validacion_mallas_var_base_normalizacion = {malla:False for malla in mallas}
        
        for malla in mallas:
            
            # inicializar las columnas de intervalos y datos pertenecientes a los intervalos para cada malla
            resultado[f'interval_{malla}'] = []
            resultado[f'cells_{malla}'] = []
            
            # validar si var existe en el dataframe de la malla actual
            if var not in self.dataframes_mallas[malla].columns:
                print(f'La variable {var} (var) no existe en el DataFrame de la malla {malla}')
            else:
                validacion_mallas_var[malla] = True
                
            # validar si var_base_normalizacion existe en el dataframe de la malla
            # (solo cuando no es None, en caso contrario se asigna True por defecto a todas las llaves del diccionario)
            if var_base_normalizacion is not None:
                if var_base_normalizacion not in self.dataframes_mallas[malla].columns:
                    print(f'La variable {var_base_normalizacion} (var_base_normalizacion) no existe en el DataFrame de la malla {malla}')
                else:
                    validacion_mallas_var_base_normalizacion[malla] = True
            else:
                validacion_mallas_var_base_normalizacion[malla] = True
        
        # si var no existe en ninguna malla (todos los valores del diccionario correspondiente son False) lanzar un error
        if all(validacion_mallas_var[malla] == False for malla in mallas):
            raise ValueError(f'La variable {var} (var) no existe en ninguno de los DataFrames de las mallas especificadas')
        
        # si var_base_normalizacion no existe en ninguna malla (no es None, y todos los valores del diccionario son False) lanzar un error
        if all(validacion_mallas_var_base_normalizacion[malla] == False for malla in mallas):
            raise ValueError(f'La variable {var_base_normalizacion} (var_base_normalizacion) no existe en ninguno de los DataFrames de las mallas especificadas')
        
        # obtener el nombre y código de la variable desde el diccionario de alias
        nombre = self.alias[var]
        codigo = var
        descripcion = self.descripcion.get(var, pd.NA) if hasattr(self, 'descripcion') else pd.NA
        
        # inicializar diccionario para almacenar la lista de intervalos generados en cada malla de manera ordenada
        # el diccionario intervalos_ordenados_mallas se va a ver de la siguiente forma: 
        # {
        #     malla_1:[intervalo_1, intervalo_2, ...],
        #     malla_2:[intervalo_1], intervalo_2, ...],
        #     ...   
        # }
        intervalos_ordenados_mallas = {malla:[] for malla in mallas}
        
        # inicializar diccionario para almacenar los datos pertenecientes a cada intervalo
        # el diccionario intervalos_cells_mallas se va a ver de la siguiente forma:
        # {
        #     malla_1: 
        #         {
        #             intervalo_1:[entidad_a, entidad_x, ...],
        #             intervalo_2:[entidad_b, entidad_y, ...],
        #             ...
        #         },
        #     malla_2:
        #         {
        #             intervalo_1:[entidad_a, entidad_x, ...],
        #             intervalo_2:[entidad_b, entidad_y, ...],
        #             ... 
        #         },
        #     ...
        # }
        intervalos_cells_mallas = {malla:{} for malla in mallas}
        
        for malla in mallas:
            
            # comprobar si var y var_base_normalizacion existen en la malla actual
            if validacion_mallas_var[malla] and validacion_mallas_var_base_normalizacion[malla]:
                
                # categorizar variable en cuantiles
                variable_categorizada = self.categorizar_variable(malla=malla, var=var, var_base_normalizacion=var_base_normalizacion, q=q)
                
                # agregar una categoría para valores NaN
                variable_categorizada = variable_categorizada.cat.add_categories(['NaN'])
                variable_categorizada = variable_categorizada.fillna('NaN')
                
                # inicializar un diccionario para almacenar las listas de datos pertenecientes a cada intervalo generado en la malla actual,
                # este diccionario se almacenara en el diccionario intervalos_cells_mallas para cada variable
                cells = {intervalo: [] for intervalo in variable_categorizada.cat.categories}
                
                for i, intervalo in enumerate(variable_categorizada):
                    
                    # construir la cadena que identifica al dato a partir de las variables identificadoras
                    # y agregarla a la lista de datos que pertenecen al intervalo
                    entidad = "".join(str(self.dataframes_mallas[malla].iloc[i][col]) for col in self.variables_identificadoras[malla])
                    cells[intervalo].append(entidad)
                                    
                # eliminar la categoria NaN si no contiene valores
                if len(cells['NaN']) == 0:
                    variable_categorizada = variable_categorizada.cat.remove_categories(['NaN'])
                    del cells['NaN']
                    
                # almacenar cells en el diccionario intervalos_cells_mallas en la malla actual
                intervalos_cells_mallas[malla] = cells
                
                # almacenar la lista de intervalos generados para la variable de manera ordenada en el diccionario intervalos_ordenados_mallas en la malla actual
                intervalos_ordenados_mallas[malla] = sorted(variable_categorizada.value_counts().index, key=lambda x: (isinstance(x, str), x))

        # el resultado consistira de a lo mas q+1 bins (entradas) considerando la categoria NaN
        # se eliminaran los bins donde ninguna malla haya generado un intervalo en ese bin (se tienen valores nulos pd.NA en las columnas de ese bin)
        for i in range(q+1):
            
            # agregar name, code, descripcion y bin al resultado
            resultado['name'].append(nombre)
            resultado['code'].append(codigo)
            resultado['descripcion'].append(descripcion)
            resultado['bin'].append(i+1)
            
            for malla in mallas:
                
                try:
                    
                    # obtener el intervalo correspondiente al bin actual
                    intervalo = intervalos_ordenados_mallas[malla][i]
                    
                    # agregar el intervalo (o categoria NaN) al resultado
                    if isinstance(intervalo, pd.Interval):
                        resultado[f'interval_{malla}'].append(
                            f'{(intervalo.left*100).round(1)}%:{(intervalo.right*100).round(1)}%' if (var_base_normalizacion is not None) else f'{intervalo.left}:{intervalo.right}'
                        )
                    else:
                        resultado[f'interval_{malla}'].append('Sin clasificar')
                        
                    # agregar las celdas correspondientes al intervalo
                    resultado[f'cells_{malla}'].append(self.__list_a_postgres_array(intervalos_cells_mallas[malla][intervalo]))
                    
                except IndexError:
                    
                    # si no hay más intervalos, agregar valores nulos
                    resultado[f'interval_{malla}'].append(pd.NA)
                    resultado[f'cells_{malla}'].append(pd.NA)
        
        # filtrar y eliminan los bins en donde todos sus valores para las columnas de intervalos y cells son nulos
        df_resultado = pd.DataFrame(resultado)
        columnas_a_validar = [col for col in df_resultado.columns if col.startswith('interval_') or col.startswith('cells_')]
        bins_nulos = df_resultado[columnas_a_validar].isna().all(axis=1)
        
        return df_resultado[~bins_nulos].reset_index(drop=True)
    
    def procesar_variable_presencia(self, mallas:list, var:str) -> pd.DataFrame:
        """
        Procesa una variable de presencia: para cada malla, genera la lista de entidades
        cuyo valor en la variable es >= 1.

        Args:
            mallas (list): Lista de mallas (DataFrames) donde se procesará la variable.
            var (str): Nombre de la variable a procesar.

        Returns:
            pd.DataFrame: DataFrame con una fila para la variable, con columnas name, code,
                descripcion y cells_<malla> por cada malla.

        Raises:
            TypeError: Si los parámetros no son del tipo esperado.
            ValueError: Si la variable no existe en ninguna de las mallas especificadas.
        """
        # validaciones mallas
        if not isinstance(mallas, list):
            raise TypeError('El parámetro mallas debe ser de tipo list')
        for malla in mallas:
            if not isinstance(malla, str):
                raise TypeError('Los elementos del parámetro mallas deben ser de tipo str')
            if malla not in self.dataframes_mallas.keys():
                raise ValueError(f'La malla {malla} no es válida, pues no fue proporcionado un DataFrame para esta')

        # validaciones var
        if not isinstance(var, str):
            raise TypeError('El parámetro var debe ser de tipo str')
        if var in self.variables_excluidas:
            raise ValueError(f'La variable {var} está en la lista de variables excluidas')

        # verificar que var exista en al menos una malla
        if all(var not in self.dataframes_mallas[malla].columns for malla in mallas):
            raise ValueError(f'La variable {var} no existe en ninguno de los DataFrames de las mallas especificadas')

        # obtener nombre, código y descripción desde el diccionario de alias
        nombre = self.alias[var]
        codigo = f'{var}::presencia'
        descripcion = self.descripcion.get(var, pd.NA) if hasattr(self, 'descripcion') else pd.NA

        resultado = {
            'name': [nombre],
            'code': [codigo],
            'descripcion': [descripcion],
            'bin': [pd.NA],
        }

        for malla in mallas:
            resultado[f'interval_{malla}'] = [pd.NA]

        for malla in mallas:
            if var not in self.dataframes_mallas[malla].columns:
                print(f'La variable {var} no existe en el DataFrame de la malla {malla}')
                resultado[f'cells_{malla}'] = [pd.NA]
                continue

            df = self.dataframes_mallas[malla]

            # identificar filas donde el valor de la variable es >= 1
            valores_numericos = pd.to_numeric(df[var], errors='coerce').fillna(0)
            mascara = valores_numericos >= 1

            # construir la cadena identificadora de cada entidad con presencia
            entidades = [
                "".join(str(df.iloc[i][col]) for col in self.variables_identificadoras[malla])
                for i in df.index[mascara]
            ]

            resultado[f'cells_{malla}'] = [self.__list_a_postgres_array(entidades) if entidades else pd.NA]

        return pd.DataFrame(resultado)

    def procesar_multiples_variables_list_presencia(self, mallas:list, lista_vars:list) -> pd.DataFrame:
        """
        Procesa múltiples variables de presencia utilizando una lista explícita de nombres de variables.

        Args:
            mallas (list): Lista de mallas (DataFrames) donde se procesarán las variables.
            lista_vars (list): Lista de variables a procesar.

        Returns:
            pd.DataFrame: DataFrame con los resultados del procesamiento de presencia.

        Raises:
            TypeError: Si los parámetros no son del tipo esperado.
            ValueError: Si los parámetros no cumplen con los requisitos.
        """
        # validaciones mallas
        if not isinstance(mallas, list):
            raise TypeError('El parámetro mallas debe ser de tipo list')
        for malla in mallas:
            if not isinstance(malla, str):
                raise TypeError('Los elementos del parámetro mallas deben ser de tipo str')
            if malla not in self.dataframes_mallas.keys():
                raise ValueError(f'La malla {malla} no es válida, pues no fue proporcionado un DataFrame para esta')

        # validaciones lista_vars
        if not isinstance(lista_vars, list):
            raise TypeError('El parámetro lista_vars debe ser de tipo list')

        totales = len(lista_vars)
        print(f"Total de variables de presencia a procesar (con lista explícita): {totales}")

        variables_procesadas = []
        contador = 0

        for var in lista_vars:
            if not isinstance(var, str):
                raise TypeError('Los elementos de lista_vars deben ser de tipo str')

            contador += 1

            if var in self.variables_excluidas:
                print(f"- {contador}/{totales} La variable '{var}' está en la lista de variables excluidas, no se procesará")
                continue

            print(f"- Procesando variable de presencia {contador}/{totales}: '{var}'")
            variables_procesadas.append(self.procesar_variable_presencia(mallas=mallas, var=var))

        return pd.concat(variables_procesadas, ignore_index=True) if variables_procesadas else pd.DataFrame()

    def procesar_multiples_variables_regex_presencia(self, mallas:list, regex_list:list) -> pd.DataFrame:
        """
        Procesa múltiples variables de presencia utilizando expresiones regulares para seleccionarlas.

        Args:
            mallas (list): Lista de mallas (DataFrames) donde se procesarán las variables.
            regex_list (list): Lista de expresiones regulares para seleccionar variables.

        Returns:
            pd.DataFrame: DataFrame con los resultados del procesamiento de presencia.

        Raises:
            TypeError: Si los parámetros no son del tipo esperado.
            ValueError: Si los parámetros no cumplen con los requisitos.
        """
        # validaciones mallas
        if not isinstance(mallas, list):
            raise TypeError('El parámetro mallas debe ser de tipo list')
        for malla in mallas:
            if not isinstance(malla, str):
                raise TypeError('Los elementos del parámetro mallas deben ser de tipo str')
            if malla not in self.dataframes_mallas.keys():
                raise ValueError(f'La malla {malla} no es válida, pues no fue proporcionado un DataFrame para esta')

        # validaciones regex_list
        if not isinstance(regex_list, list) or not all(isinstance(r, str) for r in regex_list):
            raise TypeError('El parámetro regex_list debe ser una lista de strings (regex)')
        for regex in regex_list:
            try:
                re.compile(regex)
            except re.error:
                raise ValueError(f'La expresión regular {regex} no es válida')

        # combinar todas las regex en una sola y obtener variables coincidentes
        regex_combinada = "|".join(f"(?:{r})" for r in regex_list)
        variables_obtenidas = set()
        for malla in mallas:
            variables_obtenidas |= set(obtener_variables_regex_df(self.dataframes_mallas[malla], regex_combinada))

        if not variables_obtenidas:
            print(f'Ninguna expresión regular en la lista {regex_list} coincide con alguna variable en los DataFrames')
            return pd.DataFrame()

        totales = len(variables_obtenidas)
        print(f"Total de variables de presencia a procesar (con lista de expresiones regulares): {totales}")

        variables_procesadas = []
        contador = 0

        for var in sorted(variables_obtenidas):
            contador += 1

            if var in self.variables_excluidas:
                print(f"- {contador}/{totales} La variable '{var}' está en la lista de variables excluidas, no se procesará")
                continue

            print(f"- Procesando variable de presencia {contador}/{totales}: '{var}'")
            variables_procesadas.append(self.procesar_variable_presencia(mallas=mallas, var=var))

        return pd.concat(variables_procesadas, ignore_index=True) if variables_procesadas else pd.DataFrame()

    def procesar_multiples_variables_list(self, mallas:list, dicc:dict, q:int=10) -> dict:
        """
        Procesa múltiples variables utilizando listas explícitas de nombres de variables.

        Args:
            mallas (list): Lista de mallas (DataFrames) donde se procesarán las variables.
            dicc (dict): Diccionario donde las llaves son bases de normalización y los valores son listas de variables.
            q (int): Número de cuantiles para la categorización.

        Returns:
            dict: Diccionario con los resultados del procesamiento para cada base de normalización.

        Raises:
            TypeError: Si los parámetros no son del tipo esperado.
            ValueError: Si los parámetros no cumplen con los requisitos.
        """
        # validaciones mallas
        if not isinstance(mallas, list):
            raise TypeError('El parámetro mallas debe ser de tipo list')
        for malla in mallas:
            if not isinstance(malla, str):
                raise TypeError('Los elementos del parámetro mallas deben ser de tipo str')
            if malla not in self.dataframes_mallas.keys():
                raise ValueError(f'La malla {malla} no es válida, pues no fue proporcionado un DataFrame para esta')
            
        # validaciones dicc
        if not isinstance(dicc, dict):
            raise TypeError('El valor del parámetro dicc debe ser de tipo dict, de forma {base_porcentaje : lista_variables}')
        if dicc == {}:
            raise ValueError('El diccionario no contiene items, debe ser un diccionario de forma {base_porcentaje : lista variables}')
        
        # validaciones q
        if not isinstance(q, int):
            raise TypeError('El parámetro q debe ser de tipo int')
        if q < 1:
            raise ValueError('El valor de q debe ser mayor a 1')
        
         # inicializar el diccionario de resultados
        resultado = {}
        
        for var_base_normalizacion, lista_vars in dicc.items():
            
            # validaciones llaves dicc (var_base_normalizacion)
            if var_base_normalizacion is not None:
                if not isinstance(var_base_normalizacion, str):
                    raise TypeError('Las llaves del diccionario deben ser de tipo str o None')
                if var_base_normalizacion in self.variables_identificadoras:
                    print(f"Advertencia: La variable seleccionada como base de normalización {var_base_normalizacion} (con lista explícita) está en la lista de variables identificadoras, no se procesará la lista asociada a esta variable")
                    continue
                if var_base_normalizacion in self.variables_excluidas:
                    print(f"Advertencia: La variable seleccionada como base de normalización {var_base_normalizacion} (con lista explícita) está en la lista de variables excluidas, no se procesará la lista asociada a esta variable")
                    continue
                
            # validaciones valores dicc (lista explicita de variables a procesar para la var_base_normalizacion correspondiente)
            if not isinstance(lista_vars, list):
                raise TypeError('Los valores del diccionario deben ser de tipo list')
            
            # imprimir en terminal el total de variables a procesar
            totales_por_base = len(lista_vars)
            print(f"Total de variables a procesar para base de normalización '{var_base_normalizacion}' (con lista explícita): {totales_por_base}")
            
            # inicializar lista de procesamientos para cada variable
            variables_procesadas = []
            
            # inicializar contador de variables procesadas
            contador = 0
            
            for var in lista_vars:
                
                # validaciones elementos de lista_vars (variable individual a procesar)
                if not isinstance(var, str):
                    raise TypeError('Los elementos de las listas deben ser de tipo str')
                
                # aumentar en uno contador de variables procesadas 
                contador += 1
                
                # validar que la variable no este en las identificadoras o excluidas
                if var in self.variables_identificadoras:
                    print(f"- (Base: '{var_base_normalizacion}') {contador}/{totales_por_base} La variable '{var}' está en la lista de variables identificadoras, no se procesará")
                    continue
                if var in self.variables_excluidas:
                    print(f"- (Base: '{var_base_normalizacion}') {contador}/{totales_por_base} La variable '{var}' está en la lista de variables excluidas, no se procesará")
                    continue
                
                # imprimir en terminal variable actual y progreso con respecto al total de variables
                print(f"- (Base: '{var_base_normalizacion}') Procesando variable {contador}/{totales_por_base}: '{var}'")
                
                # procesar la variable y agregarla a la lista de resultados
                variables_procesadas.append(self.procesar_variable(mallas=mallas, var=var, var_base_normalizacion=var_base_normalizacion, q=q))
            
            # concatenar los resultados en un solo dataframe y agregarlos al diccionario resultados segun la variable usada como base de normalizacion
            resultado[var_base_normalizacion] = pd.concat(variables_procesadas, ignore_index=True) if len(variables_procesadas) > 0 else None
            
        return resultado
    
    def procesar_multiples_variables_regex(self, mallas:list, dicc:dict, q:int=10) -> dict:
        """
        Procesa múltiples variables utilizando expresiones regulares para seleccionarlas.

        Args:
            mallas (list): Lista de mallas (DataFrames) en las que se procesarán las variables.
            dicc (dict): Diccionario donde las llaves son bases de normalización y los valores son listas de expresiones regulares.
            q (int): Número de cuantiles para la categorización.

        Returns:
            dict: Diccionario con los resultados del procesamiento para cada base de normalización.

        Raises:
            TypeError: Si los parámetros no son del tipo esperado.
            ValueError: Si los parámetros no cumplen con los requisitos.
        """
        
        # validaciones mallas
        if not isinstance(mallas, list):
            raise TypeError('El parámetro mallas debe ser de tipo list')
        for malla in mallas:
            if not isinstance(malla, str):
                raise TypeError('Los elementos del parámetro mallas deben ser de tipo str')
            if malla not in self.dataframes_mallas.keys():
                raise ValueError(f'La malla {malla} no es válida, pues no fue proporcionado un DataFrame para esta')
            
        # validaciones dicc
        if not isinstance(dicc, dict):
            raise TypeError('El valor del parámetro dicc debe ser de tipo dict, de forma {base_porcentaje : lista_variables}')
        if dicc == {}:
            raise ValueError('El diccionario no contiene items, debe ser un diccionario de forma {base_porcentaje : lista variables}')
        
        # validaciones q
        if not isinstance(q, int):
            raise TypeError('El parámetro q debe ser de tipo int')
        if q < 1:
            raise ValueError('El valor de q debe ser mayor a 1')
        
        # inicializar diccionario de resultados
        resultado = {}
        
        for var_base_normalizacion, regex_list in dicc.items():
            
            # validaciones llaves dicc (var_base_normalizacion)
            if var_base_normalizacion is not None:
                if not isinstance(var_base_normalizacion, str):
                    raise TypeError('Las llaves del diccionario deben ser de tipo str o None')
                if var_base_normalizacion in self.variables_identificadoras:
                    print(f"La variable seleccionada como base de normalización {var_base_normalizacion} está en la lista de variables identificadoras, no se procesará la lista asociada a esta variable")
                    continue
                if var_base_normalizacion in self.variables_excluidas:
                    print(f"La variable seleccionada como base de normalización {var_base_normalizacion} está en la lista de variables excluidas, no se procesará la lista asociada a esta variable")
                    continue
                
            # validaciones valores dicc (lista de expresiones regulares para la var_base_normalizacion correspondiente)
            if not isinstance(regex_list, list) or not all(isinstance(r, str) for r in regex_list):
                raise TypeError('Cada valor del diccionario debe ser una lista de strings (regex)')
            for regex in regex_list:
                try:
                    re.compile(regex)
                except re.error:
                    raise ValueError(f'La expresión regular {regex} no es válida')
            
            # combinar todas las regex en una sola
            regex_combinada = "|".join(f"(?:{r})" for r in regex_list)
            
            # inicializar el contador de variables procesadas
            totales_por_base = 0
            
            # obtener las variables que coinciden con la regex combinada en los dataframes
            variables_obtenidas_regex = set()
            for malla in mallas:
                # evaluar regex combinada en cada dataframe de las mallas especificadas, y agregar resultados al set variables_obtenidas_regex
                variables_obtenidas_regex |= set(obtener_variables_regex_df(self.dataframes_mallas[malla], regex_combinada))
                totales_por_base += len(variables_obtenidas_regex)
                
            # si no se obtuvo ningun resultado de la regex combinada, se omite esa var_base_normalizacion
            if len(variables_obtenidas_regex) == 0:
                print(f'Ninguna expresión regular en la lista {regex_list} coincide con alguna variable en los DataFrames, omitiendo')
                continue
            
            # imprimir en terminal el total de variables a procesar segun la evaluacion de la regex combinada
            print(f"Total de variables a procesar para base de normalización '{var_base_normalizacion}' (con lista de expresiones regulares): {totales_por_base}")
            
            # inicializar lista de procesamientos para cada variable
            variables_procesadas_regex_list = []
            
            # inicializar contador de variables procesadas
            contador = 0
            
            for var in sorted(list(variables_obtenidas_regex)):
                
                # aumentar en uno contador de variables procesadas 
                contador += 1
                
                # validar que la variable no este en las identificadoras o excluidas
                if var in self.variables_identificadoras:
                    print(f"- (Base: '{var_base_normalizacion}') {contador}/{totales_por_base} La variable '{var}' está en la lista de variables identificadoras, no se procesará")
                    continue
                if var in self.variables_excluidas:
                    print(f"- (Base: '{var_base_normalizacion}') {contador}/{totales_por_base} La variable '{var}' está en la lista de variables excluidas, no se procesará")
                    continue
                
                # imprimir en terminal variable actual y progreso con respecto al total de variables
                print(f"- (Base: '{var_base_normalizacion}') Procesando variable {contador}/{totales_por_base}: '{var}'")
                
                # procesar la variable y agregarla a la lista de resultados
                variables_procesadas_regex_list.append(self.procesar_variable(mallas=mallas, var=var, var_base_normalizacion=var_base_normalizacion, q=q))
            
            # concatenar los resultados en un solo dataframe y agregarlos al diccionario resultados segun la variable usada como base de normalizacion
            resultado[var_base_normalizacion] = pd.concat(variables_procesadas_regex_list, ignore_index=True) if len(variables_procesadas_regex_list) > 0 else None
        
        return resultado
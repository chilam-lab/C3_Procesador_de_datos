# C3_Procesador_de_datos

Procesamiento de fuentes de datos heterogéneas de interés en el C3.

---

## Estructura del repositorio

```
C3_Procesador_de_datos/
├── data/                  # Datos de entrada y salida (raw, preprocessed, processed)
├── notebooks/             # Notebooks de generación de diccionarios de datos
├── scripts/               # Scripts de transformación de datasets previo al preprocesamiento
├── src/
│   ├── procesador/        # Clasificación y procesamiento de variables
│   │   ├── procesador.py
│   │   └── main_procesador.py
│   ├── preprocesador/     # Preprocesamiento y agrupación de datos
│   │   ├── preprocesador.py
│   │   └── main_preprocesador.py
│   └── conexion_base/     # Carga a base de datos
│       └── conexion_base_datos.py
├── .gitignore
├── LICENSE
└── README.md
```

---

## Dependencias

Instalación:

```sh
pip install -r requirements.txt
```

---

## Flujo general

1. **Preprocesamiento de datos** ([`src/preprocesador/main_preprocesador.py`](src/preprocesador/preprocesador.py)): Limpiar, transformar y agrupar los datos originales, generando archivos preprocesados y diccionarios de datos derivados.

2. **Categorización y procesamiento** ([`src/procesador/main_procesador.py`](src/procesador/procesador.py)): Normalizar variables categorizarlas en cuantiles, y procesar el resultado generando archivos estructurados para análisis subsecuente.

3. **Carga a base de datos** ([`src/conexion_base/conexion_base_datos.py`](src/conexion_base/conexion_base_datos.py)): Cargar los archivos procesados a una base de datos PostgreSQL.

---

## Preprocesamiento y agrupación de datos

### Ejecución

```sh
cd src
python -m preprocesador.main_preprocesador --config preprocesador/preprocesador_example.json
```

- El archivo de configuración define rutas de entrada/salida, columnas de diccioario de datos, variables a agrupar, etc.

### Características de entrada

En este paso se realiza un preprocesamiento y agrupación de los datos provenientes de su fuente original, sin embargo, se espera que los archivos cumplan con ciertas características mínimas para el correcto funcionamiento del programa, a continuación se describen los dos archivos mínimos, así como las columnas que se pueden reconocer en estos:
1. Archivo de datos
  - Obligatorio
    - Columna que tenga como valores identificadores utilizados para crear agrupaciones en los datos (por ejemplo, identificador para agrupar datos en municipio, estado, etc.).
2. Archivo de diccionario de datos que describe todas las variables en el archivo de datos
  - Obligatorio
    - Columna que tenga como valores los nombres de las variables tal cual se escriben en las columnas del archivo de datos.
    - Columna que tenga como valores listas (cadenas que representan listas de Python), que consisten de todos los posibles valores que toma la variable en el archivo de datos. En caso de tratarse de una variable no categórica, se tiene una lista vacía.
  - Opcional (no indispensable, pero pueden ser utilizadas para transformar los datos además de agruparlos)
    - Columna que tenga como valores nombres alternativos (alias) para los nombres de las variables.
    - Columna que tenga como valores listas (cadenas que representan listas de Python), que consisten de nombres alternativos (alias) para todos los posibles valores que toma la variable en el archivo de datos. En caso de tratarse de uan variable no categórica, se tiene una lista vacía. (Nota: para el valor en la posición i de la lista de posibles valores, su alias será el valor en la posición i de la lista de alias de posibles valores).
    - Columna que tenga como valores etiquetas (cadenas) con el propósito de filtrar solo variables específicas al momento de agrupar.

### Archivo de configuración 

Ejemplo: `config/preprocesador_example_ensanut.json`

```json
```json
{
    "ruta_csv_diccionario_datos" : "../data/covid19/raw/240708 Descriptores_rework.csv",
    "ruta_csv_dataset" : "../data/covid19/raw/COVID19MEXICO_rework.csv",
    "ruta_salida_dataset" : "../data/covid19/preprocessed/preprocesamiento_covid19_example_mun.csv",
    "ruta_salida_diccionario_datos" : "../data/covid19/preprocessed/preprocesamiento_covid19_diccionario_datos_example_mun.csv",

    "columna_diccionario_nombres" : "NOMBRE DE VARIABLE",
    "columna_diccionario_posibles_valores" : "POSIBLES VALORES ALIAS",

    "columna_diccionario_alias" : "NOMBRE DE VARIABLE",
    "columna_diccionario_posibles_valores_alias" : "POSIBLES VALORES",
    "columna_diccionario_descripcion" : "DESCRIPCIÓN DE VARIABLE",

    "variables_identificadoras_list_lugares" : ["ENTIDAD_RES", "MUNICIPIO_RES"],
    "variables_a_agrupar_lugares" : [ ... ],

    "tipo_ensamble": "personas",
    "variables_identificadoras_list_personas" : ["ID_REGISTRO"],
    "variables_a_agrupar_personas": [ ... ]
}
```

- `"ruta_csv_dataset"` **(Obligatorio)**:
  Ruta al archivo de datos.

- `"ruta_csv_diccionario_datos"` **(Obligatorio)**:
  Ruta al archivo de diccionario de datos que describe las variables del dataset, sus tipos, valores posibles, alias, etc. Es necesario para la selección automática de variables y para la generación de diccionarios de alias.

- `"ruta_salida_dataset"` **(Obligatorio)**:
  Ruta donde se guardará el archivo de datos preprocesados y transformados, resultado de todas las operaciones y agrupaciones configuradas.

- `"ruta_salida_diccionario_datos"` **(Obligatorio)**:
  Ruta donde se guardará el diccionario de datos derivado: una versión del diccionario original donde cada variable agrupada es sustituida por sus N variables derivadas (`variable-valor` por cada posible valor para categóricas; `operacion::variable` por cada operación aplicada para numéricas), heredando las demás columnas del diccionario de la variable original. Se agrega una columna `alias` con la versión legible (`variable_alias-valor_alias` para categóricas, `operacion::variable_alias` para numéricas) y una fila para `conteo::total_datos`. Las columnas de posibles valores quedan como lista vacía (`[]`) en las filas derivadas. Las variables que no fueron agrupadas no se incluyen. Si se ejecuta el ensamble secundario, se genera un archivo adicional con sufijo `_<tipo_ensamble>.csv` para él (sin la fila de `conteo::total_datos`).

- `"columna_diccionario_nombres"` **(Obligatorio)**:
  Nombre de la columna en el archivo de diccionario de datos que contiene los nombres originales de las variables.

- `"columna_diccionario_posibles_valores"` **(Obligatorio)**:
  Nombre de la columna en el archivo de diccionario de datos que contiene los valores posibles de cada variable.

- `"columna_diccionario_alias"` (Opcional):
  Nombre de la columna en el diccionario que contiene los alias de las variables. Si no se especifica, se usa `columna_diccionario_nombres`.

- `"columna_diccionario_posibles_valores_alias"` (Opcional):
  Nombre de la columna en el diccionario que contiene los alias de los valores posibles. Si no se especifica, se usa `columna_diccionario_posibles_valores`.

- `"columna_diccionario_descripcion"` (Opcional):
  Nombre de la columna en el diccionario de datos que contiene la descripción o información textual de la variable. Estos datos se conservarán en el diccionario de datos derivado.

- `"columna_diccionario_tipos"` (Opcional):
  Permite realizar conversiones de tipo cast para columnas.

- `"columna_diccionario_filtro_excluir"` y `"valores_a_excluir"` (Opcionales):
  Permiten establecer una columna del diccionario para filtrar basándose en una lista de valores específicos a excluir del preprocesamiento.

- `"variables_identificadoras_list_lugares"` **(Obligatorio)**:
  Lista de columnas que identifican de manera única cada grupo sobre el que se realizarán las agregaciones y transformaciones orientadas geográficamente o por "lugares" (por ejemplo, `["ENTIDAD_RES", "MUNICIPIO_RES"]`). El resultado tendrá una fila por cada combinación única de estos identificadores.

- `"variables_a_agrupar_lugares"` **(Obligatorio)**:
  Permite definir distintos tipos de agrupaciones sobre los datos originales para los lugares identificados, especificando para cada tipo de variable (por ejemplo, categórica o numérica) cómo se deben agrupar y resumir los datos. Cada elemento de la lista es un diccionario que define:

    - `"tipo_variables"`: El tipo de variable a agrupar (`"categorico"` para variables de opciones, `"numerico"` para variables continuas).

        - **Variables categóricas**:  Se cuenta, para cada grupo, cuántos registros hay de cada valor posible de cada variable categórica seleccionada. El resultado tendrá columnas con el formato `variable-valor`.
        - **Variables numéricas**:  Se calcula, para cada grupo, el resultado de aplicar la operación especificada a cada variable numérica seleccionada. El resultado tendrá columnas con el formato `operacion::variable`.

    - `"operacion"`: (Solo para variables numéricas) La operación de agregación a aplicar, por ejemplo `"media"` para promedio o `"mediana"`.
    - `"variables_a_agrupar_list"`: Lista explícita de variables a agrupar.
    - `"variables_a_agrupar_regex"`: Lista de expresiones regulares para seleccionar variables a agrupar.
    - `"variables_a_agrupar_clasificacion_diccionario"`: (Opcional) Permite seleccionar variables automáticamente según una columna del diccionario de datos (por ejemplo, todas las variables cuyo valor en la columna `"var_type"` sea `"options"` o `"abierta"`).

- `"tipo_ensamble"` (Opcional):
  Nombre del tipo de ensamble secundario. Define el sufijo que se usará en los archivos de salida (por ejemplo, `"personas"` genera `_personas.csv`, `"empresas"` genera `_empresas.csv`). Por defecto es `"personas"`. Debe especificarse cuando el dataset no contiene un ensamble estadístico de personas sino de otra entidad (empresas, establecimientos, viviendas, etc.).

- `"variables_identificadoras_list_personas"` (Opcional):
  Lista de columnas que identifican de manera única cada registro individual del ensamble secundario (por ejemplo `["ID_REGISTRO"]`, `["id"]`). Habilita la exportación adicional del ensamble secundario.

- `"variables_a_agrupar_personas"` (Opcional):
  Define la agrupación para los datos del ensamble secundario, siguiendo la misma estructura que `"variables_a_agrupar_lugares"`.


### Salida

El archivo de salida contendrá, para cada grupo, los conteos de cada valor posible de las variables categóricas, el resultado de aplicar la operación especificada a las variables numéricas, y el total de registros que se incluye automáticamente una columna `conteo::total_datos`.
Además, se generará un diccionario de datos derivado donde cada variable original agrupada es sustituida por sus variables derivadas correspondientes (con columna `alias` adicional), necesario en el paso de procesamiento.

---

## Clasificación y procesamiento

### Ejecución

```sh
cd src
python -m procesador.main_procesador --config procesador/procesador_example.json
```

- El archivo de configuración define rutas de entrada, variables a procesar, exclusiones, número de cuantiles, etc.

### Características de entrada

En este paso se realiza una clasificación en cuantiles y procesamiento de los datos previamente preprocesasdos y agrupados, se espera que los archivos cumplan con ciertas características mínimas para el correcto funcionamiento del programa, a continuación se describen los dos archivos mínimos, así como las columnas que se pueden reconocer en estos:
1. Archivo de datos
  - Obligatorio
    - Columna que tenga como valores identificadores para cada grupo existente (por ejemplo, municipios, estados, etc.).
2. Archivo de diccionario de datos derivado (generado por el preprocesador)
  - Obligatorio
    - Columna que tenga como valores los nombres de las variables tal cual se escriben en las columnas del archivo de datos. Nota: El programa solo procesará variables existentes en esta columna, si se especifica una variable que no existe, se omitirá.
    - Columna `alias` con los nombres alternativos (alias) legibles de las variables.
  - Opcional
    - Columna que tenga como valores una ruta o categoría jerárquica de la variable (por ejemplo, `"Personas. Escolaridad."`). Si se especifica mediante `columna_diccionario_path`, este valor se propaga a la columna `path` del archivo de salida y es utilizado por el script de carga a base de datos para construir el campo `path` en los metadatos de la tabla diccionario (`dict_<tabla>`).

### Archivo de configuración

Ejemplo: `config/procesador_example_ensanut.json`

```json
{
    "rutas_csv_mallas": {
        "mun": "../data/covid19/preprocessed/preprocesamiento_covid19_example_mun.csv"
    },
    "rutas_csv_personas": {
        "personas": "../data/covid19/preprocessed/preprocesamiento_covid19_example_mun_personas.csv"
    },
    "ruta_csv_diccionario_datos": "../data/covid19/preprocessed/preprocesamiento_covid19_diccionario_datos_example_mun.csv",
    "ruta_csv_diccionario_datos_personas": "../data/covid19/preprocessed/preprocesamiento_covid19_diccionario_datos_example_mun_personas.csv",
    "ruta_csv_salida": "../data/covid19/processed/procesamiento_covid19_example.csv",

    "columna_diccionario_nombres": "NOMBRE DE VARIABLE",
    "columna_diccionario_alias": "alias",
    "columna_diccionario_descripcion": "DESCRIPCIÓN DE VARIABLE",

    "variables_identificadoras_lugares": {
        "mun": ["ENTIDAD_RES", "MUNICIPIO_RES"]
    },
    "variables_excluidas_list_lugares": ["ASMA-1"],
    "variables_excluidas_regex_lugares": ["^ENTIDAD.*"],
    "variables_a_procesar_list_lugares": {
        "None": ["media::EDAD"]
    },
    "variables_a_procesar_regex_lugares": {
        "conteo::total_datos": ["^TIPO_PACIENTE.*"]
    },

    "tipo_ensamble": "personas",
    "variables_identificadoras_personas": {
        "personas": ["ID_REGISTRO"]
    },
    "variables_excluidas_list_personas": ["ASMA-1"],
    "variables_excluidas_regex_personas": ["^ENTIDAD.*"],
    "variables_a_procesar_list_personas": {
        "None": ["EDAD"]
    },
    "variables_a_procesar_regex_personas": {
        "None": ["^CLASIFICACION_FINAL_COVID.*"]
    },

    "variables_a_procesar_list_presencia": ["MIGRANTE-1"],
    "variables_a_procesar_regex_presencia": ["^CLASIFICACION_FINAL_COVID.*"],

    "q": 10
}
```

- `"rutas_csv_mallas"` **(Obligatorio)**:
  Diccionario que indica las rutas a los archivos CSV de entrada para cada malla diferente (por ejemplo, `"mun"` para municipio). Cada clave es el nombre de la malla y el valor es la ruta al archivo correspondiente para lugares.

- `"tipo_ensamble"` (Opcional):
  Nombre del tipo de ensamble secundario. Define el sufijo del archivo de salida generado (por ejemplo, `"personas"` produce `_personas.csv`, `"empresas"` produce `_empresas.csv`). Por defecto es `"personas"`. La clave usada en `"rutas_csv_personas"` y `"variables_identificadoras_personas"` debe coincidir con este valor.

- `"rutas_csv_personas"` (Opcional):
  Diccionario que indica las rutas a los archivos CSV del ensamble secundario. La clave debe coincidir con el valor de `"tipo_ensamble"` (por ejemplo `{"personas": "..."}` o `{"empresas": "..."}`).

- `"ruta_csv_diccionario_datos"` **(Obligatorio)**:
  Ruta al archivo CSV que contiene el diccionario de datos derivado, generado en el preprocesamiento de lugares.

- `"ruta_csv_diccionario_datos_personas"` (Opcional):
  Ruta al archivo CSV que contiene el diccionario de datos derivado del ensamble secundario. De no especificarse, se usará el diccionario general.

- `"ruta_csv_salida"` **(Obligatorio)**:
  Ruta base general de guardado para el archivo CSV con resultados. Un archivo con sufijo `_<tipo_ensamble>.csv` se auto-generará si los campos del ensamble secundario están definidos.

- `"columna_diccionario_nombres"` **(Obligatorio)**:
  Nombre de la columna del diccionario de datos cuyos valores coinciden con las columnas del archivo de datos preprocesados.

- `"columna_diccionario_alias"` (Opcional, default `"alias"`):
  Nombre de la columna del diccionario de datos que contiene la versión legible (alias) de cada variable.

- `"columna_diccionario_descripcion"` (Opcional):
  Nombre de la columna del diccionario de datos con la descripción de cada variable. Al especificarse, el resultado mantendrá estas descripciones.

- `"columna_diccionario_path"` (Opcional):
  Nombre de la columna del diccionario de datos que contiene la ruta o categoría jerárquica de cada variable (por ejemplo, `"Personas. Escolaridad."`). Al especificarse, el valor se propaga a la columna `path` del archivo de salida y es utilizado por el script de carga a base de datos para construir el campo `path` en los metadatos de la tabla diccionario.

- `"variables_identificadoras_lugares"` **(Obligatorio)** / `"variables_identificadoras_personas"` (Opcional):
  Diccionario que mapea cada malla a una lista de columnas identificadoras únicas. La clave en `"variables_identificadoras_personas"` debe coincidir con `"tipo_ensamble"`. Ej: `{"mun": ["ENTIDAD_RES", "MUNICIPIO_RES"]}` / `{"personas": ["ID_REGISTRO"]}`.

- `"variables_excluidas_list_lugares"` / `"variables_excluidas_list_personas"` (Opcionales):
  Lista explícita de variables (o columnas) a excluir del procesamiento.

- `"variables_excluidas_regex_lugares"` / `"variables_excluidas_regex_personas"` (Opcionales):
  Lista de expresiones regulares para excluir variables cuyo nombre coincida con algún patrón especificado.

- `"variables_a_procesar_list_lugares"` / `"variables_a_procesar_list_personas"` (al menos uno de `_list` o `_regex` para lugares es **Obligatorio**):

  Diccionario que indica pares de: variable utilizada como base de normalización (clave), y una lista explícita de variables a procesar (valor). Si la clave es `"None"`, las variables se procesan sin normalizar. Ejemplo:
    ```json
    {
      "None": ["conteo::total_datos"],
      "conteo::total_datos": ["salud_tiene_obesidad-1"]
    }
    ```

- `"variables_a_procesar_regex_lugares"` / `"variables_a_procesar_regex_personas"` (al menos uno de `_list` o `_regex` para lugares es **Obligatorio**):

  Diccionario que indica pares de: variable utilizada como base de normalización (clave), y una lista de expresiones regulares para englobar variables a procesar (valor). Ejemplo:
    ```json
    {
      "conteo::total_datos": ["^accidente.*"]
    }
    ```

- `"variables_a_procesar_list_presencia"` (Opcional):

  Lista explícita de variables a procesar mediante presencia. Para cada variable, se genera una fila en el archivo de salida con la lista de lugares cuyo valor en esa variable es **mayor o igual a 1** en la salida del preprocesamiento. A diferencia del procesamiento por cuantiles, no se realiza normalización ni categorización: el resultado es una lista directa de entidades con presencia. Ejemplo:
    ```json
    ["MIGRANTE-1", "OBESIDAD-1"]
    ```

- `"variables_a_procesar_regex_presencia"` (Opcional):

  Lista de expresiones regulares para seleccionar variables a procesar mediante presencia. Funciona igual que `variables_a_procesar_list_presencia`, pero las variables se identifican por coincidencia de patrón en lugar de por nombre explícito. Ejemplo:
    ```json
    ["^CLASIFICACION_FINAL_COVID.*"]
    ```

- `"q"` **(Obligatorio)**:
  Número de categorías (cuantiles) en las que se dividirán las variables durante la categorización.

### Salida

El archivo de salida generado por el procesamiento es un archivo CSV en formato largo. Incluye dos tipos de filas:

**Filas de cuantiles** (procesamiento estándar): cada fila representa una categoría (bin) de una variable procesada. El número de filas por variable será igual al número de categorías (`q`), más una posible fila adicional para valores sin clasificar.

**Filas de presencia** (procesamiento de presencia): cada fila representa una variable procesada con `variables_a_procesar_list_presencia` o `variables_a_procesar_regex_presencia`. El código de la variable lleva el sufijo `::presencia` para distinguirla de las variables de cuantiles. Estas filas no tienen bin ni intervalo asociado.

La estructura de columnas es:

- **name**: Nombre descriptivo de la variable procesada (según la columna `alias` del diccionario de datos).
- **code**: Alias o código de la variable procesada. Para variables de presencia incluye el sufijo `::presencia` (por ejemplo, `MIGRANTE-1::presencia`).
- **path**: Ruta o categoría jerárquica de la variable (por ejemplo, `"Personas. Escolaridad."`). Solo presente si se configuró `columna_diccionario_path`. Utilizado por el script de carga a base de datos para construir el campo `path` en los metadatos de la tabla diccionario.
- **bin**: Número de la categoría o bin asignado (1 a `q`). Nulo para filas de presencia.
- **interval_{malla}**: Intervalo numérico o de porcentaje correspondiente a la categoría para cada malla (por ejemplo, `interval_mun`). Nulo para filas de presencia.
- **cells_{malla}**: Conjunto de entidades (por ejemplo, municipios) que pertenecen a ese intervalo/categoría, o bien que tienen valor ≥ 1 en el caso de filas de presencia.

---

## Carga a base de datos

### Ejecución

```sh
cd src
python conexion_base/conexion_base_datos.py \
  --ruta-datos-lugares ../data/covid19/processed/procesamiento_covid19_example.csv \
  --ruta-datos-personas ../data/covid19/processed/procesamiento_covid19_example_personas.csv \
  --tipo-ensamble personas \
  --ruta-env ./.env \
  --crear-tabla
```

Para un dataset con ensamble de empresas (DENUE):

```sh
cd src
python conexion_base/conexion_base_datos.py \
  --ruta-datos-lugares ../data/denue/processed/procesamiento_denue_example.csv \
  --ruta-datos-personas ../data/denue/processed/procesamiento_denue_example_empresas.csv \
  --tipo-ensamble empresas \
  --ruta-env ./.env \
  --crear-tabla
```

- `--ruta-datos-lugares`: Ruta del archivo de datos procesados de lugares (mallas) generado en el paso de procesamiento.
- `--ruta-datos-personas`: Ruta del archivo del ensamble secundario generado en el paso de procesamiento. Al especificarse, los datos se cargan en tablas separadas con sufijo `_<tipo-ensamble>`.
- `--tipo-ensamble`: Nombre del tipo de ensamble secundario (por defecto `personas`). Define la clave interna y el sufijo de las tablas en la base de datos. Debe coincidir con el `tipo_ensamble` configurado en el procesador.
- `--ruta-datos-procesados`: (Deprecado) Ruta al archivo CSV con los datos procesados. Se asume que corresponde a datos de lugares si se usa.
- `--ruta-env`: Ruta del archivo de configuración, por defecto `./.env`.
- `--crear-tabla`: No toma ningún valor; si se incluye, se crean las tablas especificadas en caso de no existir en la base de datos.

### Archivo de configuración

- El archivo `.env` debe contener las credenciales y parámetros de la base de datos:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nombre_de_base
DB_USER=usuario
DB_PASSWORD=contrasena
DB_TABLE=nombre_de_tabla
```

### Salida

Este script automatiza la carga de datos procesados desde los archivos CSV del paso de procesamiento hacia la base de datos PostgreSQL, implementando una normalización automática de tablas. Detecta y transforma tipos de datos avanzados de PostgreSQL, convirtiendo columnas con prefijo `cells_` en arreglos de enteros (`INTEGER[]`) y columnas `interval_` en rangos numéricos (`NUMRANGE`), adaptando formatos como "min:max" a la sintaxis nativa "[min,max)". Adicionalmente, optimiza el esquema separando los metadatos repetitivos en una tabla diccionario (`dict_<tabla>`) y vinculándolos a la tabla principal mediante una clave foránea (`dict_id`).

Las tablas generadas para cada dataset siguen la convención `<DB_TABLE>_<tipo>`, donde `<tipo>` es `mun` para el ensamble de lugares y el valor de `--tipo-ensamble` para el ensamble secundario (por ejemplo `_personas`, `_empresas`). Lo mismo aplica para las tablas auxiliares `dict_<tabla>` y `values_<tabla>`.

Cada tabla `dict_<tabla>` incluye una columna `available_grids` (`TEXT[]`) con la lista de ensambles donde la variable está disponible. Si se cargan ambos ensambles en la misma corrida (por ejemplo `mun` y `personas`), las variables presentes en los dos quedan con `available_grids = {mun, personas}` en ambas tablas `dict_*`; las exclusivas de un ensamble quedan únicamente con esa clave.

---

## Scripts de transformación

En la carpeta [`scripts/`](scripts/) se incluyen scripts de transformación de datasets crudos, pensados para ejecutarse como paso previo al preprocesamiento cuando la estructura original del dataset no es directamente compatible con el flujo principal.

Cada script corresponde a una fuente de datos específica y genera un archivo transformado listo para ser procesado por el preprocesador.

| Script | Dataset | Descripción |
|---|---|---|
| `transform_denue_muestra.py` | DENUE | Transforma el dataset transaccional del DENUE generando un `id` reversible a partir de coordenadas (base64), conservando `cve_mun_resumido` y construyendo `var` como `{codigo_act}_{year}` |

---

## Notebooks

En la carpeta [`notebooks/`](notebooks/) se incluyen los procedimientos de generación de archivos de diccionarios de datos compatibles con el paso de preprocesamiento para las fuentes de datos de ejemplo.

---

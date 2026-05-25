## To run the tests
```
 pytest -s tests/validate_csv.py
```

You need to define this env var inside your .env file or your dictionary.json
```Javascript
columna_diccionario_formato="FORMATO O FUENTE"
DICTIONARY_JSON_PATH=dictionary.json
```

Make sure to have this env vars with the right path inside you dictionary.json

```Javascript
"ruta_csv_diccionario_datos": "censo.csv",
"ruta_csv_salida": "input/censo_2020_transformado.csv",
"columna_diccionario_nombres": "var",
"columna_diccionario_alias": "var_alias",
"columna_diccionario_descripcion": "Description",

# TO DEFINE
"formato_columna_fecha": "AAAA-MM-DD",
"columna_fechas": colN,
```

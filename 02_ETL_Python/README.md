# Extracción y carga del origen Online Retail

Esta carpeta realiza **Excel → staging.OperacionesRetail**. Python lee las dos hojas completas, valida sus datos y puede insertarlos en un origen vacío. Las transformaciones para el modelo estrella siguen en SQL. `03_cargar_dimensiones.sql` es una **instantánea de dimensiones**, no un ETL dimensional dinámico.

## Archivos y requisitos

- `cargar_retail.py`: versión preparada para la entrega; configuración externa, validaciones y modos separados de lectura/carga.
- `cargar_retail_original.py`: copia binaria del original inspeccionado, sin cambios. No ejecutarla: apunta al origen actual y busca el Excel junto al .py.
- `requirements.txt`: openpyxl 3.1.5 y pyodbc 5.3.0, versiones comprobadas en este equipo.
- `.env.example`: configuración de ejemplo sin credenciales; el programa admite autenticación integrada de Windows únicamente.
- `test_cargar_retail.py`: pruebas locales con Excel sintético y conexión SQL simulada.

Se comprobó Python 3.12.10 de 64 bits en Windows y la presencia de ODBC Driver 17 y 18 para SQL Server. Los controladores se instalan por separado; pip no los instala. Para carga, la cuenta Windows debe tener acceso a la base de réplica, permisos SELECT/INSERT en staging y visibilidad de sus metadatos. La tabla debe existir con la estructura de `../01_Base_de_Datos/01_crear_origen.sql`. El programa no crea bases ni modifica su estructura.

Para preparar otro entorno, desde esta carpeta:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Usar el Python del entorno en los comandos posteriores. En el equipo actual las dependencias ya están instaladas; durante la preparación no se instalaron paquetes ni se cambiaron configuraciones del sistema.

## Configuración

Precedencia: argumentos de línea de comandos → variables de entorno del proceso → archivo `.env` → valores predeterminados. Por defecto se lee `.env` junto al .py; `--env ruta` permite elegir otro archivo. El formato es `CLAVE=VALOR`, con comentarios en líneas que empiezan por `#` y comillas exteriores opcionales. No admite expansión de variables, comandos, comentarios al final de un valor ni claves distintas de las incluidas en el ejemplo.

| Variable | Argumento | Predeterminado |
|---|---|---|
| RETAIL_EXCEL | --excel | ../01_Base_de_Datos/online_retail_II.xlsx |
| RETAIL_SERVER | --servidor | localhost |
| RETAIL_DATABASE | --base-datos | OnlineRetail_Origen_Replica |
| RETAIL_BATCH_SIZE | --lote | 5000 |
| RETAIL_ODBC_DRIVER | --controlador | 18, o 17 si 18 no está disponible |
| RETAIL_TRUST_CERTIFICATE | --confiar-certificado | yes |

Las rutas relativas del Excel se resuelven respecto a esta carpeta, independientemente del directorio desde donde se invoque el programa. Las rutas de `--env` y `--informe` se resuelven respecto al directorio de ejecución. Para servidor remoto, localhost debe reemplazarse por la instancia correcta. La conexión usa cifrado (`Encrypt=yes`); `TrustServerCertificate=yes` acepta el certificado local. Con `no` se exige que sea confiable. No guardar usuarios, contraseñas ni cadenas de conexión en archivos.

## Modos de ejecución

Sin indicar modo se valida únicamente el Excel. Los modos son mutuamente excluyentes.

```powershell
# Lee todo el Excel y aplica las conversiones; no abre conexión SQL.
python .\cargar_retail.py --validar-excel --informe .\validacion_excel.json

# Solo SELECT: esquema y conteos por hoja del origen actual.
python .\cargar_retail.py --comprobar-conexion --base-datos OnlineRetail_Origen --informe .\consulta_origen.json

# Carga futura: únicamente después de crear una réplica nueva y vacía con el SQL 01.
python .\cargar_retail.py --cargar --base-datos OnlineRetail_Origen_Replica --informe .\carga_replica.json
```

`--informe` es opcional y exige un archivo JSON nuevo con carpeta padre existente. No sobrescribe informes anteriores. Contiene modo, fecha con zona horaria, versiones, conteos y, cuando se lee el Excel, SHA256 del archivo. Los mensajes de avance se emiten por logging a stderr; los lotes procesados no se consideran confirmados hasta COMMIT. En una validación del Excel no se envían lotes a SQL. Código de salida: 0 si termina correctamente, 1 ante un fallo de operación; argparse devuelve 2 ante argumentos inválidos. Un modo de lectura aprobado se identifica como APROBADO_SIN_CARGA y nunca como COMMIT_CONFIRMADO.

## Reglas de extracción y preservación

1. Lee, en este orden, `Year 2009-2010` y `Year 2010-2011`. Valida ambas cabeceras antes de abrir la conexión de carga y nuevamente al recorrer el archivo. Se exige exactamente este orden de ocho columnas:

   ```text
   Invoice, StockCode, Description, Quantity, InvoiceDate, Price, Customer ID, Country
   ```

2. Recorre las filas desde la segunda, en su orden original. Solo omite filas completamente vacías. Mantiene repeticiones internas y **no aplica el corte de solapamiento**. No cambia mayúsculas, espacios exteriores ni descripciones; esos tratamientos dimensionales pertenecen al SQL.
3. Identificadores y textos se guardan como texto; los identificadores alfanuméricos y ceros iniciales presentes como texto se conservan. Un número integral leído como float se convierte sin sufijo `.0`, igual que en el original. Excel ya puede haber perdido ceros o precisión si el identificador se guardó como número: no se reconstruyen ni se aplica su formato visual.
4. Las cantidades conservan el signo y deben ser enteros del rango SQL int. La versión original usaba int(valor), que podía truncar una cantidad fraccionaria; esta versión la rechaza.
5. Precio usa `Decimal(str(valor))`, conserva el signo y debe caber en decimal(18,4) sin redondeo. No convierte precios a float para insertar. Los precios cero y negativos son válidos.
6. Fechas reconocidas por openpyxl se conservan como datetime sin zona horaria; una fecha sin hora usa medianoche. No se interpretan cadenas ambiguas. La precisión disponible depende de Excel/openpyxl; no se recupera precisión que no exista en el archivo.
7. Los valores ausentes permanecen como NULL en staging. SIN_IDENTIFICAR, SIN_CODIGO y País desconocido se aplican posteriormente en la lógica SQL, no durante la extracción.
8. Se rechazan textos que excedan nvarchar según unidades UTF-16, valores no finitos, errores Excel y fórmulas. A diferencia del original, no se consumen silenciosamente resultados de fórmulas almacenados en caché. El Excel inspeccionado pasó esta validación. El error indica hoja y fila sin registrar el contenido completo de la operación.

## Transacción, duplicados y recuperación

La carga comprueba la estructura real antes del primer INSERT. Usa consultas parametrizadas, fast_executemany y lotes configurables, con una única transacción para ambas hojas. Configura XACT_ABORT y un tiempo máximo de espera de bloqueos de 15 segundos. Toma un bloqueo de tabla exclusivo hasta el final para verificar que staging esté vacío y evitar dos cargas simultáneas sobre esa tabla. Antes de COMMIT compara los conteos insertados por hoja con los procesados. Un origen con cualquier registro provoca rechazo sin insertar.

El nombre de las bases actuales OnlineRetail_Origen y OnlineRetail_DW está bloqueado en el modo `--cargar`; sí se admite su consulta de lectura. Esta guarda es una protección de operación, no sustituye permisos de SQL Server. No hay opción de borrar, vaciar o forzar una recarga. Tampoco hay reanudación por lote.

Ante error de validación o inserción se solicita ROLLBACK de toda la transacción. Se cierran cursor, conexión y libro mediante bloques de cierre, incluso ante errores o interrupción de teclado. Si falla un dato, corregir la fuente o configuración justificadamente, ejecutar otra vez `--validar-excel` y comprobar el estado con `--comprobar-conexion` antes de reintentar. Si la tabla ya contiene datos, revisar el informe previo y usar otra réplica nueva; no borrar la carga existente.

Un fallo de conexión durante COMMIT puede dejar al cliente sin certeza de si el servidor confirmó; no asumir que se revirtió. Consultar los conteos y conciliaciones antes de actuar. Si falla la escritura del informe después de COMMIT, la carga puede estar confirmada aunque el programa devuelva error; revisar el mensaje de estado y consultar el origen. La reversión puede dejar huecos en IDENTITY. Para reproducir los IdCarga históricos, usar una base recién creada, el mismo Excel y el mismo orden; una tabla vacía después de intentos fallidos no garantiza que la identidad vuelva a 1.

## Enlace con la entrega SQL

| Orden | Responsable | Acción |
|---|---|---|
| 1 | SQL 01 | Crear una base de origen nueva y staging vacío |
| 2 | Python | Validar Excel y conexión de réplica; ejecutar carga explícita y comprobar conteos |
| 3 | SQL 02 | Crear un DW nuevo, usando un nombre coherente con el resto de scripts |
| 4 | SQL 03 | Cargar la instantánea de las dimensiones actuales con claves y atributos conservados |
| 5 | SQL 04 | Cargar hechos: filtro entre hojas, asignación dimensional, clasificación e importe decimal |
| 6 | SQL 05 | Validar origen/DW; adaptar las referencias a las réplicas antes de verificar una carga nueva |

Los archivos 01–04 requieren SQLCMD; revisar las variables BaseDestino, BaseDW y BaseOrigen. Ver el README de 01_Base_de_Datos para sus condiciones. **Python no ejecuta estos scripts automáticamente.**

El SQL 04 conserva todas las operaciones de la primera hoja y de la segunda solo las fechadas desde 2010-12-10. Esta separación explica los 1 067 371 registros de origen frente a 1 044 848 hechos históricos. Cantidad y precio mantienen sus signos; Importe se calcula en SQL con aritmética decimal. Clasificación, asignación de clientes/productos/países desconocidos y vínculos a calendario corresponden al SQL 04 y las dimensiones disponibles.

El SQL 03 contiene INSERT de las 11 863 filas dimensionales exportadas. No calcula atributos ni incorpora nuevos miembros desde staging. En la entrega anterior se comprobó que la frecuencia de descripciones positivas sobre el origen filtrado coincide con los candidatos actuales; usar todo staging producía cinco diferencias. **Faltan el script dimensional histórico y reglas completas de categorías especiales, textos de respaldo sin candidato y asignación histórica de claves.** No se inventan. Para Excel nuevos, primero debe definirse y verificarse un ETL dimensional general; la instantánea no garantiza cobertura. El SQL 04 revierte si el conteo cargado no coincide con el origen elegible.

## Verificaciones realizadas y pendientes

Durante esta preparación se revisaron README y los cinco SQL de 01_Base_de_Datos antes de cambiar Python. Se conserva íntegro el original con SHA256 `38cb5cf611816a7cee742ca95bdd2e74ffbf20ab033211cd204974a0242b5ff0`.

La lectura completa del Excel con el programa nuevo aprobó cabeceras, tipos, longitudes y conversiones:

| Hoja | Filas válidas | Filas completamente vacías omitidas |
|---|---:|---:|
| Year 2009-2010 | 525 461 | 0 |
| Year 2010-2011 | 541 910 | 0 |
| Total | 1 067 371 | 0 |

SHA256 del Excel: `bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980`. El modo `--comprobar-conexion` se ejecutó contra OnlineRetail_Origen con SELECT solamente: aprobó la comparación de las diez columnas con el esquema esperado y obtuvo los mismos conteos por hoja. Esto no prueba igualdad de cada valor del Excel frente a staging ni de sus IdCarga.

Se ejecutaron 13 pruebas locales con archivos sintéticos y conexión simulada: preservación de valores, rechazo de truncamiento/redondeo, repetidos y corte temporal sin aplicar, lotes, confirmación y reversión simuladas, staging ocupado, conteos discrepantes, cabeceras, fórmulas, cierre del libro, configuración, guardas e informes existentes. Los mensajes ERROR de los casos negativos son esperados; el resultado de la suite es OK. Las simulaciones no verifican al controlador ODBC ni prueban un COMMIT/ROLLBACK real del servidor.

```powershell
python -B -m unittest discover -s . -p test_cargar_retail.py -v
```

Evidencias de esta preparación en `../06_Pruebas_y_Evidencias/`:

- `etl_validacion_excel.json` y `etl_validacion_excel.log`: lectura completa del archivo real.
- `etl_comprobacion_origen.json`: esquema y conteos SQL consultados en modo lectura.
- `etl_pruebas_locales.log` y `etl_revision.json`: pruebas locales y revisión estática.
- `etl_manifiesto.csv`: hashes de los archivos de esta carpeta al terminar.

**No se ejecutó la carga real del programa nuevo**, ni SQL 01–04, ni se borraron registros o alteraron estructuras. Sigue pendiente probar extracción→INSERT/COMMIT→DW completo en bases nuevas aisladas, comprobar la correspondencia exacta del Excel con la carga histórica y recuperar las reglas dimensionales faltantes. La evidencia previa de 01 corresponde a las bases existentes; no acredita una ejecución completa de esta versión.

La sección sobre Python del README de 01 describe el script original que existía al preparar esa carpeta. Esta documentación registra los cambios posteriores: Excel configurable con ruta predeterminada correcta, destino de réplica y validación como modo predeterminado.

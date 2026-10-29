# Entrega de base de datos Online Retail

Preparada el 29 de octubre de 2026 mediante consultas de lectura a SQL Server local, servidor KevinLap, autenticación Windows. Las bases OnlineRetail_Origen y OnlineRetail_DW estaban ONLINE. No se ejecutaron cargas, modificaciones de estructura, cambios de permisos ni configuraciones en ellas.

## Archivos y procedencia

| Archivo | Procedencia y estado |
|---|---|
| 01_crear_origen.sql | Generado desde metadatos reales; no ejecutado |
| 02_crear_modelo_estrella.sql | Generado desde metadatos reales; no ejecutado |
| 03_cargar_dimensiones.sql | Reconstrucción por instantánea de las cinco dimensiones actuales; no ejecutada |
| 04_cargar_hechos.sql | Adaptación del script recuperado, con destino configurable y protección de carga; no ejecutada |
| 05_validaciones.sql | Consultas de lectura ejecutadas contra las bases actuales |
| SQLQuery3_original_recuperado.sql | Copia íntegra del original; conservar como evidencia, no ejecutar en la base actual |
| diccionario_datos.md | Columnas, tipos, nulabilidad, identidad, PK, UNIQUE y FK reales |

La búsqueda recursiva abarcó Proyecto y su carpeta superior Diseño Sistemas de Informacion. Se encontró un único SQL previo: `../../SQLQuery3.sql`, relativo a la carpeta de entrega. El original permanece intacto. La copia tiene SHA256 registrado en `../06_Pruebas_y_Evidencias/hash_original.json`. El script original reúne la carga de DimTipoOperacion y FactOperacion. No se recuperó el SQL original de las otras dimensiones ni de creación.

La instantánea de dimensiones conserva claves sustitutas y atributos exactos mediante IDENTITY_INSERT. Exporta 11 863 filas dimensionales, no el millón de operaciones. Sirve para reproducir este estado con el mismo origen; no calcula dimensiones nuevas para futuros archivos. La elección de categorías especiales y el texto de respaldo de productos sin descripción positiva se preservan como datos, sin inventar sus reglas históricas. Los valores de identidad futuros pueden diferir de una base que haya tenido eliminaciones previas.

## Ejecución en una réplica nueva

Requisitos: SQL Server con permisos para crear bases nuevas; SSMS en modo SQLCMD o sqlcmd con opción `-b`; autenticación integrada. Los archivos 01–04 usan directivas SQLCMD. Revisar las variables al principio de cada archivo; utilizar nombres simples sin corchetes ni comillas. Los nombres predeterminados son OnlineRetail_Origen_Replica y OnlineRetail_DW_Replica. Los scripts 01 y 02 se detienen si el destino existe y nunca lo reemplazan. En SSMS, detenerse ante cualquier error; preferir sqlcmd -b.

1. Ejecutar 01 para crear el origen nuevo.
2. Cargar el Excel en ese origen vacío con el ETL Python adaptado a la conexión de réplica. Revisar sus dependencias y ruta antes de usarlo. No ejecutar el ETL actual tal cual: apunta a OnlineRetail_Origen.
3. Ejecutar 02 para crear el DW nuevo.
4. Ejecutar 03 para cargar la instantánea dimensional, con todas las tablas del DW vacías. Se prohíbe el nombre OnlineRetail_DW como destino.
5. Ejecutar 04 con BaseDW y BaseOrigen coherentes con 01 y 02. Utiliza transacción, XACT_ABORT, TRY/CATCH, bloqueo exclusivo, rechazo de destino con hechos, UNIQUE(IdCargaOrigen) y comprobación del conteo antes de COMMIT. Los tipos ya están incluidos en 03. No elimina ni deduplica operaciones internas.
6. Para validar la réplica, hacer una copia de 05 y sustituir las referencias explícitas a OnlineRetail_Origen y OnlineRetail_DW por las réplicas. El archivo entregado conserva los nombres actuales para reproducir las comprobaciones registradas.

No se ejecutaron 01–04 ni se creó una base temporal. La reconstrucción completa no fue probada de extremo a extremo. No se afirma que una carga nueva haya sido verificada: las evidencias corresponden al estado actual de las bases. Los scripts de creación reproducen columnas, intercalaciones, identidades, PK, UNIQUE y FK; no son un backup ni reproducen usuarios, archivos físicos, estadísticas o configuración general del servidor.

Los cuatro scripts pasaron un análisis de sintaxis con SET PARSEONLY ON, sustituyendo variables y omitiendo USE porque los destinos nuevos no existen. La prueba no ejecutó DDL ni INSERT y no verifica permisos, resolución de objetos ni resultados de una carga. Se registra en `../06_Pruebas_y_Evidencias/revision_sintaxis.csv`. La primera tentativa de análisis se detuvo al resolver el nombre de una base inexistente; se corrigió únicamente el procedimiento de prueba.

## ETL Python existente

`../02_ETL_Python/cargar_retail.py` requiere Python, openpyxl, pyodbc y ODBC Driver 17 o 18 para SQL Server. Usa Windows/Trusted_Connection y Decimal(str(precio)); inserta en lotes de 5000, con una transacción y rechazo de staging no vacío. Lee ambas hojas completas y omite filas totalmente vacías. El corte de solapamiento se aplica posteriormente en la carga del DW, no en Python.

El ETL busca online_retail_II.xlsx junto al archivo .py, pero el Excel existente está en esta carpeta 01_Base_de_Datos. Para reproducir, ajustar ARCHIVO_EXCEL a esa ubicación o proporcionar una copia junto al .py; ajustar también DATABASE al origen de réplica. El ETL se conservó intacto y no se ejecutó. No se comprobaron instalación de Python/paquetes/controlador ni identidad binaria del Excel contra la carga histórica. La trazabilidad IdCarga requiere mantener hojas, orden y tratamiento de filas del archivo original; conteos iguales por sí solos no garantizan iguales identificadores.

## Resultados actuales

| Tabla | Filas |
|---|---:|
| staging.OperacionesRetail | 1 067 371 |
| FactOperacion | 1 044 848 |
| DimFecha | 739 |
| DimProducto | 5 132 |
| DimCliente | 5 943 |
| DimPais | 44 |
| DimTipoOperacion | 5 |

Coinciden con las referencias históricas. Se excluyen 22 523 filas de la segunda hoja anteriores al 10 de diciembre de 2010. Esa comprobación valida el filtro y conteo; no prueba por sí sola identidad de cada fila del solapamiento entre hojas. No faltan operaciones elegibles ni sobran hechos fuera del filtro. No hay IdCargaOrigen duplicados ni referencias huérfanas. Coinciden trazabilidad, asignaciones dimensionales, clasificación y medidas por operación, incluidos nulos. Total de cantidad con signo: 10 441 844. Importe decimal total: 18 909 762,1180. Suma técnica de precios: 4 796 422,8780.

| Clasificación existente | Operaciones |
|---|---:|
| Ventas y cargos | 1 019 654 |
| Cancelacion | 19 164 |
| Ajuste contable | 5 |
| Precio cero | 6 024 |
| Por revisar | 1 |

La clasificación coincide con el CASE original en el orden indicado por el proyecto. Ventas y cargos incluye conceptos distintos de mercancías. Los 13 registros dimensionales con categorías especiales están en categorias_especiales.csv; no se renombraron.

Se detectaron cinco diferencias de descripción representativa al usar todo staging (códigos 21039, 21042, 21217, 21243 y 22246). Al restringir al origen elegible, hay cero diferencias entre productos que tienen candidato de precio positivo y descripción no vacía. Esto respalda el universo filtrado para la regla de frecuencia; no recupera el SQL histórico ni determina los respaldos de productos sin candidato. Los empates se comparan según la intercalación real de SQL Server. Las cinco diferencias del experimento sobre todo staging permanecen registradas como DIFERENCIA en el CSV, no se ocultaron ni se modificó el DW.

## Evidencias y límites

`../06_Pruebas_y_Evidencias/resultados_validacion.csv` contiene resultados reales, servidor y fecha/hora con desplazamiento local. `metadatos.json` contiene la estructura consultada. Los auxiliares PowerShell inspeccionan, generan archivos o ejecutan SELECT; no ejecutan 01–04. Las consultas no se hicieron bajo una instantánea transaccional común: los resultados describen el estado durante la inspección y presuponen ausencia de cargas concurrentes.

El CSV final registra 20 comprobaciones aprobadas, una diferencia del experimento descriptivo sobre todo staging y 12 resultados informativos de distribución. El análisis de sintaxis tiene su propio CSV.

Pendientes para un ETL dimensional general: recuperar la lógica histórica de categorías especiales, respaldos descriptivos y asignación de claves; verificar el Excel y entorno Python; probar una ejecución completa en bases nuevas con las conexiones adaptadas. La instantánea entregada permite preservar los atributos actuales sin resolver esas reglas por suposición.

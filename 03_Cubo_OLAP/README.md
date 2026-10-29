# Cubo multidimensional Online Retail

**Estado actualizado, 29 de octubre de 2026:** fuentes preparadas, compilación verificada, despliegue realizado y **ProcessFull completado correctamente** tras autorizar el acceso mínimo del servicio. Las cinco dimensiones, el cubo y las dos particiones están Processed. Se ejecutaron las seis consultas MDX: **296/296 comparaciones SQL/MDX aprobadas**, cero diferencias y cero pendientes, además de 12 verificaciones de cálculos/filtro aprobadas. No se modificaron ni recargaron datos relacionales.

## Proyecto único y contenido

Se buscaron proyectos .dwproj en Proyecto y su carpeta superior, y después en Escritorio y Documentos locales/OneDrive. Solo se encontró `CuboOnlineRetail/CuboOnlineRetail/CuboOnlineRetail.dwproj`, dentro de esta entrega. Es la copia de trabajo y entrega. No se creó otra versión de desarrollo. El estado inicial, que solo contenía la base vacía y la configuración de destino, está preservado en `../06_Pruebas_y_Evidencias/olap_proyecto_inicial.zip`.

- Abrir `CuboOnlineRetail/CuboOnlineRetail.slnx` en Visual Studio.
- Las fuentes .database, .ds, .dsv, cinco .dim y OnlineRetail.cube están en la carpeta interior del proyecto. Las dos particiones están incluidas en el .cube. La extensión instalada generó un auxiliar .partitions con un mensaje interno de error; no se utiliza como fuente y fue retirado. El artefacto compilado y la base desplegada contienen una partición por grupo, comprobado mediante lectura de ambos.
- `bin/CuboOnlineRetail.asdatabase` y los archivos asociados son productos de compilación. No editar para desarrollar otra versión. El modelo AMO previo a compilación se conserva aparte en evidencias y no es el artefacto desplegado.
- `diccionario_medidas.md` define medidas, cálculos, granularidad y límites.
- `01_totales.mdx` a `06_filtro_tipo.mdx` son consultas de verificación. `calculos.mdx` contiene el script calculado incluido en el cubo.
- `validacion_equivalente.sql` y `conciliar.ps1` consultan SQL/MDX sin cambiar datos.
- Los auxiliares .ps1 separan generación, compilación, creación/procesamiento y captura de diagnósticos. Sus rutas de herramientas corresponden al equipo inspeccionado; adaptar si se instala Visual Studio en otra ubicación.

## Requisitos y conexión

Equipo local con Windows, SQL Server Database Engine y SSAS multidimensional. Se comprobó SSAS **17.0.25.218**, servicio MSSQLServerOLAPService iniciado, y Visual Studio **18.11.2** con la extensión Analysis Services instalada. La solución utiliza .slnx. Las bibliotecas AMO/ADOMD y devenv.com se localizaron en `C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE` y su subcarpeta `CommonExtensions\Microsoft\SSAS`.

| Elemento | Valor comprobado |
|---|---|
| Servidor relacional | localhost (KevinLap) |
| Base fuente | OnlineRetail_DW |
| Proveedor de procesamiento | MSOLEDBSQL, instalado en 64 bits |
| Autenticación | Integrada de Windows, sin contraseñas en el proyecto |
| Suplantación de origen SSAS | ImpersonateServiceAccount |
| Identidad de lectura confirmada por procesamiento | NT Service\MSSQLServerOLAPService |
| Servidor SSAS de destino | localhost (KEVINLAP) |
| Base SSAS | CuboOnlineRetail |
| Cubo | Online Retail (ID OnlineRetail) |

SQLNCLI11 no se utiliza. Se verificó una conexión System.Data.OleDb con MSOLEDBSQL y la misma cadena del proyecto: con la cuenta Windows de la sesión pudo leer 1 044 848 hechos. Esto verifica el proveedor con esa cuenta; **no acredita acceso de la cuenta del servicio**. La conexión usa cifrado y acepta el certificado local (`Use Encryption for Data=True;Trust Server Certificate=True`). Revisar certificados si cambia el servidor.

La vista incluye las seis tablas reales y cinco relaciones desde FactOperacion. El esquema se obtuvo con FillSchema/SELECT TOP(0), sin exportar hechos. Las FK reales consultadas están habilitadas y son de confianza; se registran en olap_relaciones_reales.csv. Los tipos, claves y medidas se contrastaron con los scripts SQL de 01 y con la base actual. No se crearon vistas ni columnas calculadas en la base relacional.

## Compilación y despliegue

Desde esta carpeta, en PowerShell:

```powershell
# Compilar exclusivamente y comprobar las dos particiones del artefacto.
powershell -ExecutionPolicy Bypass -File .\compilar.ps1

# Solo para un destino nuevo: crea SSAS y después intenta ProcessFull.
# Se detiene si CuboOnlineRetail ya existe. NO usar ahora para reemplazarla.
powershell -ExecutionPolicy Bypass -File .\desplegar_procesar.ps1
```

ExecutionPolicy Bypass se limita al proceso invocado; no cambia la política permanente del equipo. Compilar también es posible mediante Build/Rebuild de la solución. La configuración Development y el archivo .dwproj.user apuntan a localhost/CuboOnlineRetail. Revisar las propiedades antes de cambiar de equipo. El despliegue de esta entrega se hizo con el auxiliar XMLA, no con Deploy Solution: crea solo un destino inexistente y procesa en una petición separada y transaccional. No contiene ALTER ni reemplazo de bases ajenas.

El despliegue tomó **el .asdatabase producido por Visual Studio**, convertido a XMLA con Scripter del SDK. SHA256 del artefacto desplegado: `dacdf22803fd2fbd7735b7446a36b6c10f01ec7f4bdbc5277a0e12a2cb2d5336`. El servidor estaba inicialmente sin bases. Después se confirmó la existencia de CuboOnlineRetail, cinco dimensiones, dos grupos y sus dos particiones. Inicialmente quedó Unprocessed por falta de acceso SQL; tras la autorización, ProcessFull terminó el 2026-10-29 a las 12:43:51 (UTC-05:00). No se redesplegó ni cambió la estructura del cubo para conseguir la conciliación.

Después de limpiar opciones de proyecto que no utilizaba el diseñador y capturar la salida completa del compilador, se comparó la definición XMLA del último compilado, generada con Scripter, con la petición realmente desplegada: **son idénticas**, aunque los archivos XML de compilación tengan hashes distintos. El hash vigente se registra en olap_revision_final.json. No se redesplegó para sustituir el mismo modelo. La comprobación está también en olap_compilado_xmla_actual.xmla; la salida completa de compilación está en olap_compilacion_final_completo.log.

La compilación final terminó con **1 proyecto correcto y 0 errores**. Quedaron advertencias del analizador sobre el proveedor OLE DB y recomendaciones de diseño: jerarquías de atributos visibles del calendario, relaciones Rigid y jerarquías adicionales en Producto/Cliente. El proveedor se probó operativo con la cuenta de diseño y posteriormente con el procesamiento real bajo la cuenta de servicio. Las relaciones temporales se mantienen Flexible por una decisión explícita descrita en el diccionario. Producto y Cliente conservan atributos independientes; no se inventa una jerarquía de categorías comerciales. Las advertencias del analizador permanecen documentadas, aunque no impidieron procesar y conciliar este estado.

La validación inicial encontró etiquetas NameColumn no textuales y opciones de nulos de medidas inválidas; se corrigieron y recompilaron. El servidor exigió ZeroOrBlank para el DistinctCount; la partición excluye facturas nulas explícitamente. Los registros de intentos anteriores permanecen identificados como iniciales o errores previos; el registro final completo de compilación es olap_compilacion_final_completo.log. Visual Studio guardó solo un resumen en /Out, por lo que se capturaron además stdout y stderr del proceso real.

## Bloqueo inicial resuelto y acceso mínimo aplicado

ProcessFull se ejecutó realmente como petición transaccional y falló. SSAS informó error OLE DB y que no pudo establecer conexión con DataSourceID OnlineRetailDW. El registro de SQL Server aporta la causa precisa:

```text
Login failed for user 'NT Service\MSSQLServerOLAPService'.
Motivo: no se encontró un inicio de sesión que coincida con el nombre proporcionado.
[CLIENTE: <local machine>]
```

Antes del cambio se volvió a verificar la identidad del servicio y el origen SSAS: NT SERVICE\MSSQLServerOLAPService, ImpersonateServiceAccount, conexión integrada a localhost/OnlineRetail_DW. No existían login, usuario ni permisos propios de la cuenta. Con autorización expresa posterior del usuario se ejecutó `autorizar_lectura_ssas.sql` mediante `aplicar_acceso_minimo.ps1`. La inspección anterior quedó conservada en olap_seguridad_antes.json; la posterior, en olap_seguridad_despues.json. No se alteraron permisos anteriores de otras identidades.

Cambios efectivos: login Windows y usuario en OnlineRetail_DW creados; CONNECT en la base y SELECT explícito sobre las seis tablas. SQL Server agregó CONNECT SQL al crear el login y CONNECT al crear el usuario. Por eso el bloque GRANT CONNECT condicional no tuvo que ejecutarse: el permiso ya estaba registrado por CREATE USER. El CSV de acciones aplicadas enumera CREATE LOGIN, CREATE USER y los seis GRANT SELECT; la comparación de catálogos documenta además los dos CONNECT automáticos. No se agregaron roles, permisos de escritura, usuarios en OnlineRetail_Origen ni permisos explícitos sobre otras bases. Tampoco se cambió la cuenta del servicio, certificados, contraseñas o firewall.

Permisos mínimos para esa identidad local: un login Windows en el motor relacional, un usuario asociado en OnlineRetail_DW con acceso CONNECT y SELECT sobre **solo** dbo.FactOperacion, dbo.DimFecha, dbo.DimProducto, dbo.DimCliente, dbo.DimPais y dbo.DimTipoOperacion. No necesita sysadmin, db_owner, INSERT, UPDATE, DELETE ni permisos de creación de tablas. SELECT sobre esos objetos permite ver sus metadatos correspondientes. No se otorga db_datareader general a otras tablas. Si los servicios se separan en equipos distintos, revisar la identidad de red; esta indicación corresponde al caso local comprobado.

El acceso está habilitado y su uso real quedó demostrado por el procesamiento. Para futuros procesamientos, revisar que la estructura SSAS siga siendo la propia y ejecutar:

```powershell
# Verifica que la estructura actual coincida con la captura de esta entrega;
# solo entonces solicita ProcessFull, sin redesplegar ni tocar las bases relacionales.
powershell -ExecutionPolicy Bypass -File .\desplegar_procesar.ps1 -SoloProcesar

# Solo consultas para comparar SQL y MDX.
powershell -ExecutionPolicy Bypass -File .\conciliar.ps1
```

No ejecutar capturar_diagnostico.ps1 sobre una base modificada por terceros para sustituir la prueba de propiedad sin revisarla: el archivo olap_estructura_desplegada.xmla se usa como referencia en SoloProcesar. Alternativamente, después de inspeccionarla, usar Process Full en SSMS sobre CuboOnlineRetail. La estructura posterior al procesamiento coincide con la captura y el compilado. La auditoría efectiva comprobó CONNECT=1, SELECT=1 sobre las seis tablas, INSERT/UPDATE/DELETE/ALTER=0, sysadmin/db_owner/db_datareader=0 y HAS_DBACCESS(OnlineRetail_Origen)=0.

`autorizar_lectura_ssas.sql` conserva un login/usuario existente y sus concesiones; solo agrega lo que falta. Rechaza una identidad incompatible o un DENY directo de lectura en vez de sustituirlo. El script contiene exclusivamente cambios de seguridad autorizados y una tabla variable de auditoría; no actualiza datos de negocio. No hace falta volver a aplicarlo ahora. Preservar las evidencias anteriores si se realiza otra intervención de seguridad.

`generar_modelo.ps1` fue el constructor inicial de fuentes; consulta metadatos y no llama Update/Process. Exige que el ID de destino no exista al validar. **No volver a ejecutarlo sobre este destino desplegado ni usarlo para descartar cambios del diseñador.** La fuente de trabajo posterior es la solución única.

## Conciliación final con referencias vigentes

Se ejecutó validacion_equivalente.sql contra el DW actual. Se guardaron **74 contextos reales** (total, cinco tipos, 25 meses y 43 países con hechos), con cuatro medidas cada uno. DimPais tiene 44 miembros; el miembro sin hechos no aparece en GROUP BY de hechos, por lo que las comparaciones se centran en contextos existentes. El conciliador conserva decimales con cultura invariante y no suma conteos distintos parciales.

| Tipo | Importe SQL | Cantidad firmada SQL | Operaciones SQL |
|---|---:|---:|---:|
| Ventas y cargos | 20 533 741,9180 | 11 239 346 | 1 019 654 |
| Cancelacion | -1 465 677,2300 | -478 964 | 19 164 |
| Ajuste contable | -158 676,1400 | 5 | 5 |
| Precio cero | 0,0000 | -318 544 | 6 024 |
| Por revisar | 373,5700 | 1 | 1 |
| Total | 18 909 762,1180 | 10 441 844 | 1 044 848 |

Facturas distintas totales SQL y MDX: **53 628**. Neto definido de tipos 1+2: **19 068 064,6880**, confirmado también por MDX. Ventas y cargos conserva su significado amplio; no se etiqueta como ventas exclusivamente de productos. Todos los totales y grupos de la tabla coinciden entre SQL y MDX.

Las seis consultas MDX se ejecutaron correctamente después de procesar. Las cuatro consultas principales devuelven total, cinco tipos, 25 meses y 44 países dimensionales. Los 74 contextos SQL con hechos coinciden exactamente en Importe, Cantidad, Operaciones y FacturasDistintas: **296 aprobadas, 0 fallidas, 0 pendientes**. PaisKey=1, País desconocido, es un miembro real sin hechos y devuelve las cuatro celdas vacías; está documentado aparte en olap_miembros_sin_hechos_sql.csv y no se transforma artificialmente en un contexto SQL con datos.

Las referencias SQL se volvieron a consultar al conciliar y al cierre. Sus 296 valores coinciden con los de la referencia anterior preservada y con la consulta final: olap_vigencia_referencias.csv registra las comprobaciones. Esto confirma vigencia durante la intervención; no constituye un bloqueo permanente frente a cargas futuras. El cubo es MOLAP y necesitará reprocesamiento si cambian sus fuentes.

Los importes MDX principales llegaron como System.Decimal (74 celdas no vacías) y las otras medidas como System.Int64 (222). Se compararon numéricamente con Decimal y cultura invariante, sin pasar por Double ni redondear: **tolerancia absoluta 0 para importes, cantidades y conteos**. La omisión de ceros finales en algunos CSV, como 18909762.118 frente a 18909762.1180, es únicamente formato y no pérdida de valor. Las ocho celdas de cálculos y cuatro del filtro de tipo también coinciden con sus expresiones SQL, 12/12. Con el slicer Precio cero, Importe base es cero y las medidas calculadas conservan sus tipos explícitos, como define el diccionario.

El primer intento de conciliación posterior al procesamiento encontró un error del auxiliar PowerShell al indexar celdas multidimensionales como una colección de índices. Se corrigió a CellCollection.get_Item(int[]) y se volvieron a consultar SQL y MDX; no se modificaron cálculos, cubo ni datos para forzar resultados. El primer informe de estado AMO conservaba un estado de hijo en caché; se corrigió la captura para usar una sesión nueva. La lectura independiente confirma todos los objetos Processed.

El bloqueo y las consultas fallidas de la etapa previa siguen preservados en olap_estado_anterior_a_permisos.zip. Los errores históricos no describen el estado actual.

## Evidencias

Todos los archivos siguientes están en `../06_Pruebas_y_Evidencias/`:

| Archivo | Qué acredita |
|---|---|
| olap_entorno_inicial.json, olap_copias_proyecto.txt | SSAS multidimensional accesible y búsqueda de copias; ninguna base SSAS al inicio |
| olap_proyecto_inicial.zip | Preservación del proyecto inicial |
| olap_relaciones_reales.csv | FK consultadas en el DW |
| olap_validacion_amo.log | Validación AMO final sin errores; véase además el registro de compilación |
| olap_revision_final.json | Validación AMO de la base desplegada y comparación de definición con el último compilado |
| olap_compilacion_final_completo.log | Compilación real satisfactoria y advertencias; el .log sin sufijo completo es solo el resumen |
| olap_despliegue.log, olap_estado_ejecucion.json | Creación previa confirmada y procesamiento actual correcto |
| olap_procesamiento.log, olap_estado_objetos_procesados.csv | ProcessFull sin errores y estados/fechas de dimensiones, cubo y particiones |
| olap_error_login_sql.csv, olap_diagnostico.json | Diagnóstico histórico anterior a la autorización |
| olap_estructura_desplegada.xmla | Captura administrativa de la estructura SSAS creada |
| olap_referencia_sql.csv | Totales y grupos obtenidos con SELECT reales |
| olap_consultas_mdx.csv, olap_detalle_mdx.json | Seis consultas ejecutadas y resultados de cálculos/filtro |
| olap_resultados_mdx.csv, olap_tipos_numericos_mdx.csv | Celdas reales y tipos devueltos por ADOMD |
| olap_conciliacion_sql_mdx.csv | 296 comparaciones exactas aprobadas |
| olap_vigencia_referencias.csv, olap_validacion_calculos.csv | Vigencia de referencias y 12 verificaciones adicionales |
| olap_seguridad_antes.json, olap_seguridad_despues.json, olap_permisos_agregados.csv | Estado previo/posterior y acciones de seguridad aplicadas |
| olap_permisos_nuevos_catalogo.csv | CONNECT SQL/CONNECT automáticos y seis SELECT nuevos, contrastados con el estado previo vacío de esta identidad |
| olap_permisos_efectivos.json, olap_cierre.json | Auditoría efectiva de mínimo acceso y resumen final |
| olap_estado_anterior_a_permisos.zip | Preservación de resultados y errores de la etapa bloqueada |

## Relación con Python y SQL

Python extrae ambas hojas y carga staging; SQL transforma y carga el DW. El cubo consume ese DW existente. No se ejecutó ETL ni recarga relacional durante este trabajo. Las limitaciones de las dimensiones reconstruidas por instantánea, descritas en los README de 01 y 02, siguen vigentes: el cubo no recupera reglas faltantes de categorías, descripciones de respaldo ni claves históricas. Para datos futuros se necesita primero definir y verificar ese ETL dimensional.

Referencias oficiales: [suplantación de identidad SSAS](https://learn.microsoft.com/en-us/analysis-services/multidimensional-models/set-impersonation-options-ssas-multidimensional), [medidas y grupos](https://learn.microsoft.com/en-us/analysis-services/multidimensional-models/measures-and-measure-groups), [tipos multidimensionales](https://learn.microsoft.com/en-us/analysis-services/multidimensional-models/olap-physical/data-types-in-analysis-services).

# Dashboard local Online Retail

Dashboard Streamlit conectado exclusivamente a **Analysis Services multidimensional** mediante MDX. Fuente real: `localhost → CuboOnlineRetail → Online Retail`. No consulta SQL Server relacional, no descarga operaciones individuales y no tiene respaldo con datos simulados.

## Estado verificado

Se probó primero la compatibilidad de Python 3.12.10 x64 con pythonnet 3.0.5, runtime .NET Framework (`netfx`) y ADOMD.NET instalado con Visual Studio. La consulta mínima devolvió 1 044 848 operaciones e importe 18 909 762,1180. Después se ejecutaron las consultas y pruebas del dashboard.

La aplicación se inició realmente en **http://127.0.0.1:8501** y su endpoint de salud respondió HTTP 200. Se aprobaron 15 pruebas: 9 de consultas/catálogo/exportación con SSAS real, 3 de controles mediante AppTest con SSAS real, 2 unitarias de validación y 1 de un fallo de conexión simulado explícitamente. La sonda AppTest mostró ocho indicadores, cuatro gráficos, filtros y tabla sin excepciones. AppTest es una sesión programática de Streamlit; **no es una inspección visual en navegador**.

**Inspección visual pendiente:** el controlador del equipo no estuvo disponible (`Computer Use native pipe is unavailable: failed to connect native pipe: El sistema no puede encontrar el archivo especificado. (os error 2)`) y tampoco el host del navegador (`The browser access host is unavailable`). Se reintentó y reinició la sesión de control sin resolverlo. No se generaron capturas falsas ni se afirma haber revisado visualmente alineación, recorte o comportamiento responsive. Abrir la URL local para esa revisión.

## Archivos

| Archivo | Función |
|---|---|
| app.py | Interfaz en español, estados, filtros, tarjetas, gráficos y exportación |
| config.py | Configuración local desde .env/entorno, sin credenciales |
| connection.py | ADOMD.NET/pythonnet; conexión Windows por consulta y cierre garantizado |
| queries.py | Catálogo de miembros reales, listas permitidas y construcción segura de MDX |
| presentation.py | Formato de valores, filas agregadas y CSV decimal |
| charts.py | Ranking de códigos en eje categórico y descripción completa en tooltip |
| iniciar.ps1 | Arranque restringido a 127.0.0.1:8501 |
| requirements.txt | Dependencias directas con versiones comprobadas |
| requirements-lock.txt | Versiones completas resueltas en el entorno de esta entrega |
| .env.example | Ejemplo sin secretos |
| diccionario_indicadores.md | Definiciones, origen y comportamiento de filtros |
| probar_ssas.py, smoke.py | Prueba inicial de cliente y consultas reales de integración |
| probe_ui.py | Sonda programática de la interfaz con datos reales |
| test_dashboard.py, verificar.py | Pruebas clasificadas y generación de evidencias |

`.venv`, `.env` y cachés no son fuentes para entregar o versionar. No se modificaron las carpetas 01–03 para implementar el dashboard.

## Requisitos e instalación

- Windows x64 con Python **3.12.10** comprobado; otro Python requiere volver a verificar la integración .NET.
- .NET Framework y cliente ADOMD.NET x64. Se reutiliza la biblioteca ya instalada; no se copiaron DLL del sistema al repositorio.
- SSAS local iniciado, base CuboOnlineRetail procesada y acceso de la **cuenta Windows que ejecuta Python** al cubo. Es distinto de la cuenta de servicio usada para procesar las fuentes relacionales. No se concedieron permisos nuevos durante esta etapa.

Desde `04_Dashboard`, para reproducir el entorno:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Alternativa para reproducir también versiones transitivas:
# .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe probar_ssas.py
```

El entorno de esta entrega ya se creó y `pip check` terminó sin dependencias incompatibles. Los paquetes se instalaron solo en `.venv`, sin cambiar el entorno del ETL. No es necesario activar el entorno si se usa su python.exe.

## Configuración y ejecución

Variables admitidas: `SSAS_SERVER` (localhost), `SSAS_DATABASE` (CuboOnlineRetail), `SSAS_TIMEOUT` (60 segundos, rango 1–300) y `ADOMD_DLL`. Las variables del proceso prevalecen sobre `.env`. La ruta comprobada de la DLL es:

```text
C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\SSAS\Microsoft.AnalysisServices.AdomdClient.dll
```

La entrega restringe servidor al equipo local y base a CuboOnlineRetail. No ofrece campos para usuario/contraseña ni un editor de consultas. Usa `Integrated Security=SSPI` con la identidad Windows del proceso. Reiniciar la aplicación después de cambiar .env o la DLL; el runtime .NET se inicializa una sola vez por proceso.

```powershell
# Desde la raíz ENTREGA_ONLINE_RETAIL:
powershell -ExecutionPolicy Bypass -File .\04_Dashboard\iniciar.ps1
```

También, desde `04_Dashboard`:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false
```

Abrir **http://127.0.0.1:8501**. El servidor preparado quedó iniciado en segundo plano; no arrancar una segunda instancia si la URL ya responde. Ctrl+C detiene una ejecución iniciada en primer plano. `.streamlit/config.toml` fija tema, loopback y desactivación de estadísticas de uso. El lanzador repite explícitamente la dirección local incluso si se invoca desde otra carpeta. No se publicó en Internet ni se cambiaron firewall, certificados, cuentas o permisos.

## Uso y reglas

Filtros agrupados en la barra lateral: intervalo diario, país, código/descripción/categoría de producto y tipo. Son selecciones únicas para país, producto y tipo; no se implementó selección múltiple ni filtro de cliente. El catálogo se consulta en SSAS: 739 fechas, 44 países, 5 132 productos y 5 tipos. Las fechas disponibles son **01/12/2009–09/12/2011**. **2009 y 2011 son periodos incompletos**; la interfaz lo advierte.

Las tarjetas principales muestran operaciones, Importe Ventas y cargos, Importe Cancelacion y Neto Ventas y cargos mas Cancelacion. Hay tarjetas separadas de ajuste contable, operaciones Por revisar, operaciones Precio cero y facturas distintas. Se conservan los nombres y reglas del cubo. Ventas y cargos incluye conceptos distintos de mercancías. Las cancelaciones ya son negativas y no se vuelve a restar su importe. No se suman PrecioUnitario ni claves numéricas como medidas.

**Interacción de TipoOperacion:** operaciones, importe observado, cantidad, facturas distintas y todos los gráficos/detalles respetan el tipo seleccionado. Las tarjetas basadas en los cálculos del cubo fijan su propio tipo y sustituyen ese filtro, conservando fecha, país y producto. La interfaz advierte este comportamiento cuando el filtro está activo. No se ha convertido un cálculo fijo en uno dinámico distinto. Si el tipo seleccionado no tiene datos pero otro tipo fijo sí, se informa y se conservan esos indicadores reales.

La serie mensual y los rankings de diez países/códigos se calculan en SSAS mediante agregación/TopCount. Los rankings usan **importe firmado**, no valor absoluto; el orden entre empates no representa una diferencia de valor. La distribución por tipo es un gráfico de barras de importe con signo, apto para cancelaciones negativas; no es un porcentaje circular de importes firmados. Los códigos especiales y categorías Por clasificar permanecen incluidos.

Al final se elige detalle por mes, país, tipo o código. La tabla y su CSV son agregados para **los mismos filtros**, sin el límite Top 10 de los gráficos. Se permite hasta 7000 filas agregadas; si se supera el límite, se muestra error y se solicitan filtros, sin truncar datos silenciosamente. Facturas distintas se consulta para cada contexto: nunca se suman conteos por filas para reconstruir el total.

El CSV usa UTF-8 con BOM, separador coma e importes con cuatro decimales y punto decimal. Incluye fuente, periodo, filtros y fecha/hora de consulta. Ausencia de datos: tarjetas con —, gráficos vacíos con mensaje y exportación deshabilitada; no se reemplazan ausencias por valores fabricados. **Limpiar filtros** restablece periodo completo y todas las selecciones. **Actualizar consultas** vacía la caché de lectura; no procesa SSAS ni ejecuta ETL.

## Corrección de presentación del ranking de códigos

Se corrigió exclusivamente la presentación observada con país Spain. Los códigos se conservan como texto, sin conversión a número, eliminación de ceros iniciales ni cambio de mayúsculas. El eje Y se declara explícitamente categórico, con una posición por código; las barras son horizontales, ordenadas por el importe Decimal original de mayor a menor, con el mayor arriba. Las etiquetas muestran el código completo y el tooltip incorpora la descripción completa del catálogo ya consultado, categoría e importe. La altura se adapta al número de categorías (470 px para diez). El título de países ahora es **“Hasta 10 países con mayor importe”**.

No se cambiaron consultas MDX, medidas, filtros, conexiones, exportación ni datos. Las descripciones se recuperan de las etiquetas del catálogo de productos existente, sin consultar una fuente adicional. Los hashes de queries.py, connection.py y config.py coinciden antes y después.

Se ejecutaron **cuatro pruebas focalizadas adicionales**, sin repetir ni reemplazar el informe anterior de 15 pruebas:

- Dos unitarias con datos sintéticos explícitos: códigos `00123`, `23199`, `85123A`, orden, descripción larga completa, conservación de los datos de entrada y altura/etiquetas de diez categorías.
- Una consulta MDX real con Spain: diez códigos, incluidos numéricos (`22423`, `84879`) y alfanuméricos (`POST`, `84997d`, `84997B`, `84760L`), con descripción disponible en todos los tooltips.
- Una prueba AppTest con SSAS real: figura emitida con eje categórico y barras horizontales; una sola barra de país para Spain y el nuevo título.

Las cuatro aprobaron. Evidencias: dashboard_ranking_pruebas.json/.log, dashboard_ranking_spain_datos.json, dashboard_ranking_spain_figura.json y dashboard_ranking_apptest_spain.json en 06_Pruebas_y_Evidencias. El primer intento del test de título usó la representación de depuración de AppTest, que no incluye el texto de los encabezados; se corrigió el test para leer el elemento Subheader, sin cambiar la aplicación para forzar la prueba.

**Revisión visual de esta corrección: pendiente.** Se volvió a comprobar el acceso al equipo/navegador, pero continuaron los errores de native pipe y browser access host. Las verificaciones descritas inspeccionan el JSON Plotly y los controles AppTest; no son una captura visual ni una prueba de hover con ratón en un navegador real. Tras recargar http://127.0.0.1:8501, seleccionar Spain para la revisión visual final.

## Precisión, actualidad y seguridad de las consultas

Los importes ADOMD System.Decimal se convierten directamente a decimal.Decimal mediante texto invariante; cantidades/conteos son int. Los indicadores, tabla y exportación no pasan por float. Solo las coordenadas de Plotly usan float para dibujar; el tooltip conserva el importe exacto formateado. El dashboard no calcula ni redondea importes de negocio en Python. Las verificaciones numéricas usaron tolerancia **0**. No se atribuye una moneda específica porque no está documentada en el modelo.

El catálogo y los datos agregados se almacenan en caché hasta 120 y 30 segundos, respectivamente. La fecha/hora visible corresponde a la consulta que produjo los datos, aunque provengan de esa caché. MOLAP refleja el último procesamiento; actualizar consultas no incorpora cambios relacionales pendientes de procesar.

Las entradas no se concatenan libremente en MDX. Los valores de filtro deben pertenecer al catálogo recién obtenido y sus claves sustitutas deben ajustarse a la estructura numérica prevista. El periodo se traduce exclusivamente a miembros de ese catálogo. Las medidas, niveles, agrupaciones y tamaño Top 10 están en listas cerradas; los identificadores se escapan con corchetes dobles cuando corresponde. Se rechazaron en pruebas miembros ajenos, intentos de inyección, periodos inválidos y comandos que no fueran SELECT. Para evitar usar una misma jerarquía en filas y slicer, país/tipo se restringen en el eje de agrupación cuando corresponde.

La lectura de MDSCHEMA es un catálogo de **SSAS**, no una consulta al motor relacional. No hay conexión pyodbc, cadenas SQL relacionales, recargas ni cambios del cubo en el código de aplicación.

## Verificación y evidencias

```powershell
.\.venv\Scripts\python.exe -X utf8 verificar.py
```

En `../06_Pruebas_y_Evidencias/`:

| Archivo | Alcance |
|---|---|
| dashboard_prueba_cliente.json | Consulta inicial real Python/netfx/ADOMD y tipos de valores |
| dashboard_metadatos_ssas.json | Nombres reales de cubo, medidas, jerarquías y niveles |
| dashboard_smoke_real.json | Catálogo, indicadores y agrupaciones consultados realmente |
| dashboard_filtros_reales.json | Valores de filtros individuales, combinados y contexto sin hechos |
| dashboard_pruebas.json, dashboard_pruebas.log | Las 15 pruebas, clasificadas como reales, AppTest, unitarias o mock |
| dashboard_exportacion_real.csv | Exportación agregada de Alemania, generada con datos MDX reales |
| dashboard_sonda_interfaz.json, dashboard_apptest_estado.txt | Inspección programática de controles, gráficos, tabla y botón de descarga |
| dashboard_servidor.json, dashboard_servidor.log, dashboard_servidor_error.log | Arranque real restringido a loopback, PID y registros |
| dashboard_bloqueo_visual.txt | Errores reales que impidieron la revisión visual |
| dashboard_manifiesto.csv | Hashes de fuentes, excluido el entorno virtual |

Los totales sin filtros se compararon contra las referencias MDX conciliadas de 03: importe 18 909 762,1180, cantidad 10 441 844, operaciones 1 044 848 y facturas distintas 53 628; también se comprobaron los ocho cálculos. Se contrastó el filtro de diciembre de 2010 con su referencia mensual. Se probaron país Alemania, producto 85123A, tipo Precio cero y una combinación de fecha/país/producto/tipo, contrastando tarjetas con resultados dimensionales del cubo. Se comprobó que País desconocido no tiene hechos y que los controles de limpieza, detalle y ausencia de datos funcionan mediante AppTest.

**Separación de pruebas:** las pruebas `real` usan consultas reales; las `ui` ejecutan widgets con SSAS real mediante AppTest; `unit` valida entradas; `mock` solo fuerza un error de conexión y comprueba que no se muestren métricas falsas. Los gráficos de las pruebas satisfactorias y de la aplicación usan exclusivamente datos reales. La URL `/mock/media/…` que aparece en el informe AppTest es el almacenamiento interno de archivos de ese marco de pruebas, no una fuente de datos simulada.

Se verificaron el contenido CSV y la presencia/activación del control de descarga. **No se verificaron visualmente el clic ni la descarga mediante un navegador real**, ni diseño responsive/accesibilidad completa, debido al bloqueo del controlador. La revisión visual sigue pendiente. Tampoco se afirma haber reejecutado las 296 conciliaciones de 03 durante esta etapa: se reutilizaron sus referencias y se realizaron pruebas específicas del dashboard.

## Solución de problemas

- **No abre la URL:** ejecutar iniciar.ps1 y revisar los registros; confirmar 127.0.0.1:8501. Si el puerto está ocupado, no detener procesos ajenos ni modificar firewall; identificar antes la aplicación que ya lo usa.
- **ADOMD no encontrado / importación CLR:** usar el Python de `.venv`, verificar .NET Framework y la ruta ADOMD_DLL. El cliente comprobado es pythonnet/netfx con la DLL instalada de Visual Studio, no una biblioteca ADOMD de otra arquitectura/runtime.
- **Sin conexión o sin cubo:** comprobar servicio SSAS y base procesada con herramientas existentes. El programa muestra el error exacto y no recurre a SQL. No modificar certificados ni otorgar permisos desde el dashboard.
- **Sin acceso Windows:** ejecutar con una cuenta ya autorizada a consultar SSAS. La cuenta de servicio autorizada en 03 resuelve la lectura de SSAS hacia el DW, no concede automáticamente acceso a cualquier usuario del dashboard.
- **Datos vacíos:** revisar periodo y combinación de miembros; limpiar filtros. Los miembros desconocidos son reales y pueden no tener hechos.
- **Tarjetas no cambian como el gráfico al filtrar tipo:** es la definición de tuplas fijas del cubo, explicada encima de las tarjetas y en el diccionario.
- **Datos distintos de una carga nueva:** procesar el cubo mediante el procedimiento autorizado de 03, fuera del dashboard, y actualizar las consultas. El dashboard no hace procesamiento.

Persisten los límites del proyecto: categorías especiales y respaldos descriptivos del ETL dimensional no se reconstruyen aquí; SQL 03 sigue siendo una instantánea. Los nombres/categorías existentes se conservan. Ver los README de 01, 02 y 03. Las advertencias de diseño del compilador SSAS documentadas en 03 no se resolvieron modificando el modelo para el dashboard.

Referencias técnicas oficiales: [pythonnet y selección de runtime](https://pythonnet.github.io/pythonnet/python.html), [AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest), [pruebas de aplicaciones Streamlit](https://docs.streamlit.io/develop/api-reference/app-testing).

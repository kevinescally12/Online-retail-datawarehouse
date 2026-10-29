# Portal Online Retail adaptado de Stitch

Nueva interfaz independiente en **04_Dashboard/portal_stitch**, con backend Flask/Waitress, Bootstrap 5.3.8 y CSS/JavaScript separados. Reproduce la estructura de la referencia: barra lateral, cabecera, pestañas, tarjetas blancas, acentos índigo, panel temporal, rankings y auditoría. **No contiene Tailwind** ni toma cifras/reglas del HTML de muestra.

Se inspeccionaron `code.html` y `screen.png` de `07_Referencia_Stitch/stitch_online_retail_bi_platform_portal.zip`. La copia de inspección queda en esa carpeta de referencia; no se sirve desde el portal.

## Ejecutar la versión nueva

Desde la raíz ENTREGA_ONLINE_RETAIL:

```powershell
powershell -ExecutionPolicy Bypass -File .\04_Dashboard\portal_stitch\iniciar.ps1
```

Abrir **http://127.0.0.1:8502**. El lanzador utiliza el entorno aislado del portal y Waitress, sin depurador ni publicación. La dirección se fija a 127.0.0.1; no hay configuración de host público. PORTAL_PORT permite elegir otro puerto local si es necesario. No se cambiaron firewall, certificados, cuentas ni permisos.

### Instalación reproducible

El entorno ya fue creado en el equipo. Para reconstruirlo, desde portal_stitch:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe preparar_recursos.py
.\.venv\Scripts\python.exe run.py
```

Versiones comprobadas: Python 3.12.10 x64, Flask 3.1.3, Waitress 3.0.2, pythonnet 3.0.5, Plotly Python 7.1.0 y python-dotenv 1.2.4. requirements.txt fija las dependencias directas y requirements-lock.txt todas las resueltas. `pip check` aprobó. ADOMD.NET y .NET Framework son los mismos ya verificados para Streamlit. El cliente mantiene SSPI y la identidad Windows del proceso; no se introducen credenciales.

`.env` del portal admite PORTAL_PORT, SSAS_SERVER, SSAS_DATABASE, SSAS_TIMEOUT y ADOMD_DLL; las variables del proceso prevalecen. Se reutiliza la validación de configuración de la versión anterior y se exige servidor local/CuboOnlineRetail. Cambios de configuración o código Python requieren reiniciar el portal. El cliente .NET se inicializa una vez por proceso.

Bootstrap, Inter y Plotly se sirven localmente desde static/vendor, con licencias y hashes en recursos.json. No se necesita Internet para navegar después de instalar. El JS gráfico es **Plotly strict 4.1.1**, compatible con la versión de Python instalada, para no introducir unsafe-eval en la política de scripts. El helper preparar_recursos.py verifica compatibilidad y actualiza el manifiesto local; no instala ni descarga software. Conservar los archivos vendor incluidos al copiar la entrega. Fuentes de descarga y licencias: Bootstrap oficial/jsDelivr 5.3.8, Inter oficial y CDN oficial de Plotly para strict 4.1.1. No se usa el CDN de Tailwind ni fuentes remotas.

## La versión anterior permanece funcional

No se editaron los archivos de Streamlit, sus módulos ni su entorno. Los hashes previos/posteriores constan en portal_streamlit_antes.csv y portal_pruebas.json.

```powershell
# Versión anterior, desde la raíz de entrega:
powershell -ExecutionPolicy Bypass -File .\04_Dashboard\iniciar.ps1
```

Streamlit usa **http://127.0.0.1:8501**. Puede coexistir con el portal de 8502. Si una versión ya está iniciada, no abrir una segunda instancia sobre el mismo puerto. Ctrl+C detiene una ejecución iniciada por su lanzador. Los procesos de comprobación del portal son independientes de SQL Server, SSAS y Streamlit.

## Estructura y contrato de reutilización

| Archivo/directorio | Responsabilidad |
|---|---|
| server.py | Rutas Flask, respuestas de error, controles de acceso local y descargas cerradas |
| service.py | Adaptador del contrato MDX ya existente; no redefine las medidas |
| shared.py | Importación directa de los módulos funcionales de la carpeta superior |
| portal_config.py | Configuración local propia sin cambiar el entorno anterior |
| evidence.py | Lectura documental de archivos de entrega y DOWNLOADS explícito |
| figures.py | Gráficos de agregados con la paleta de la referencia |
| templates/ | Seis secciones y layout común Jinja/Bootstrap |
| static/css/portal.css | Diseño, tarjetas, navegación y reglas responsive |
| static/js/ | Control de filtros, carga/error/vacío, gráficos, tabla y exportación |
| static/vendor/ | Bootstrap, fuente y Plotly locales; licencias |
| run.py, iniciar.ps1 | Arranque local con Waitress |
| test_portal.py | Pruebas de endpoints, SSAS real y un fallo simulado separado |
| frontend_tests.mjs | Pruebas unitarias JavaScript, sin navegador |
| diccionario_indicadores.md | Semántica, procedencia, moneda y límites |

Se importan sin copiar `connection.CubeClient`, `config.Settings/load_settings`, `queries.load_catalog/totals/grouped/Filters`, `presentation.flat_rows/csv_bytes/number` y el ranking categórico de charts.py. Contrato: los indicadores son una fila con diccionario values; las agrupaciones devuelven miembros y las cuatro medidas base; el catálogo contiene unique/label y claves sustitutas permitidas. El portal conserva esas expresiones y validaciones. No se añadió SQL relacional como respaldo.

## Secciones y funciones reales

1. **Overview y arquitectura:** recorrido Excel → Python → staging → SQL dimensional → SSAS → interfaces. Explica que SQL 03 es una instantánea y no un ETL dimensional dinámico.
2. **Gráficos analíticos:** indicadores reales, periodo, país, producto buscable, tipo, limpieza, serie mensual, rankings de importe, distribución por conteo, detalle agregado y CSV filtrado. El selector de medida cambia solo la serie mensual; el ranking conserva TopCount por Importe del contrato anterior.
3. **Modelo dimensional:** las seis tablas, columnas/tipos/PK y cinco FK según metadatos reales archivados, con conteos y fecha de validación. La clave de SIN_CODIGO se obtiene del archivo de categorías, no se inventa −1.
4. **Pipeline ETL:** reglas originales y evidencias históricas con fecha. La validación sin carga, las pruebas simuladas y el procesamiento SSAS se identifican por separado. No hay botones de recarga/borrado ni tiempos/logs inventados.
5. **Cubo SSAS y MDX:** medidas y jerarquías documentadas, versión SSAS registrada y las seis consultas verificadas de 03. No hay editor ni endpoint de MDX arbitrario.
6. **Auditoría y descargas:** las filas reales de conciliación, fecha, conteos y tolerancia documentados. Las descargas resuelven IDs de la lista explícita de evidence.py, nunca una ruta proporcionada por el navegador. No incluyen .env, el Excel completo, credenciales ni archivos arbitrarios.

La página de auditoría no vuelve a ejecutar las 296 pruebas del cubo. Sus indicadores están marcados como históricos, con fecha y archivo fuente. La analítica muestra una comprobación actual fechada solo después de que su consulta SSAS termine. `/health` verifica HTTP, **no** la conexión a SSAS. Ante error se ocultan resultados anteriores y se muestra un mensaje, sin números de muestra. El detalle técnico del error queda en el registro del backend, no en la vista analítica.

## Correcciones justificadas frente a la referencia

- Se eliminaron todas las cifras y porcentajes de muestra, YoY +14,2 %, versiones SQL/SSAS inventadas y estados ONLINE permanentes. Las cifras analíticas llegan de SSAS; los estados documentales muestran evidencia y fecha.
- Se preserva la definición del neto: Ventas y cargos + Cancelacion, ya negativa. No se usa “bruto menos cancelaciones” sobre un valor negativo ni se suman precios unitarios.
- Las tarjetas por tipo fijo sustituyen el filtro de TipoOperacion, mientras conservan fecha/país/producto. El aviso aparece cuando hay una selección de tipo. Operaciones, importe observado, gráficos y detalle respetan todos los filtros.
- La distribución circular usa **conteos de operaciones** y porcentajes derivados de ellos, no importes firmados. La serie de importe mantiene negativos. No se suman parciales de facturas distintas.
- Los códigos permanecen como texto en eje categórico, con descripción completa en tooltip. Países usa nombres originales; no se agrega una normalización ISO inexistente. “44 filas de DimPais” no se presenta como “44 países”.
- La moneda se verificó en la [documentación original UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online%2Bretail%2Bii): el precio unitario está expresado en libras esterlinas. Por la fórmula y ausencia de conversión se usa GBP/£, con esa procedencia. No se alteró el tipo ni valor del cubo; Streamlit sigue intacto con su formato anterior.
- Se quitaron “Copiar Git Repo”, usuarios ficticios, certificaciones sin evidencia y exportaciones genéricas. El botón Diccionario descarga el diccionario del portal y la exportación CSV consulta los filtros aplicados.
- Se usan Bootstrap y CSS propio en lugar de las clases Tailwind y Material Symbols remotos. Las secciones técnicas reflejan nombres/versiones/fechas reales, sin declarar el sistema como producción.

Los años 2009 y 2011 son incompletos en el origen y se advierte en pantalla. No se muestra crecimiento interanual sin periodos equivalentes. Los códigos incluyen cargos y ajustes; Por clasificar y los miembros desconocidos se conservan.

## Precisión y seguridad

La conexión a SSAS vive en el backend y se cierra por consulta. Los filtros se validan con el catálogo de miembros y las listas cerradas originales. No se recibe MDX del cliente. El backend conserva Decimal; JSON lo transporta como texto y CSV conserva cuatro decimales. El formateador JavaScript trabaja con texto decimal, sin redondear cifras financieras mediante Number. Plotly usa float únicamente para geometría y tooltip exacto.

El navegador recibe resultados agregados y opciones de miembros, no conexiones, contraseñas o rutas absolutas. No se modificaron permisos, bases, datos, cubo ni red. La aplicación rechaza hosts ajenos y solicitudes no locales, conserva recursos estáticos propios, no añade CORS y no tiene operaciones de escritura. Los controles de descarga verifican lista y confinamiento a la entrega. La CSP no admite unsafe-eval ni scripts remotos; las reglas de estilo permiten el funcionamiento local de Bootstrap/Plotly. Una revisión real de consola/CSP en navegador sigue pendiente junto con la inspección visual.

Catálogo con caché de hasta 120 segundos; las cifras se consultan por petición, sin reemplazo por caché de ejemplo. MOLAP depende del último procesamiento correcto. La selección producto/país/tipo es única, como en Streamlit. El detalle tiene el límite heredado de 7000 agregados, con error explícito si se excede, sin descargar hechos individuales.

## Pruebas realizadas

Desde portal_stitch:

```powershell
# Con el portal ya iniciado en 8502 (la prueba HTTP utiliza ese puerto):
.\.venv\Scripts\python.exe -X utf8 test_portal.py
# Opcional si Node está instalado:
node frontend_tests.mjs
```

Se aprobaron **12 pruebas Python**, con SSAS real donde corresponde y un fallo de conexión simulado explícitamente. Incluyen seis secciones HTTP, catálogo/filtros, resultado vacío, CSV exacto, lista cerrada de descargas, rechazo de MDX libre/miembros inválidos y comprobación del servidor real. **36/36 indicadores** coincidieron numéricamente con el contrato de Streamlit para periodo completo, Spain y combinación de fecha/país/producto/tipo; tolerancia 0. No se reejecutó la suite de 296 comparaciones del cubo.

Se aprobaron **8 pruebas unitarias JavaScript**: decimal exacto, signo de cancelación, valores superiores al límite entero seguro de JS, ausencia frente a cero, limpieza, producto del catálogo, codificación de filtros combinados e intervalo invertido. Fueron ejecutadas con el runtime Node disponible para herramientas; no se instaló Node en el sistema ni se abrió un navegador con esas pruebas.

Se verificaron reglas CSS de escritorio y de ventana estrecha: sidebar/offcanvas desde 992 px, apilado y tablas con scroll en anchos pequeños y viewport declarado. **Esto es revisión automatizada de reglas y marcado, no una ventana renderizada.**

### Límite de verificación visual

Se inspeccionó la imagen original screen.png, pero el navegador del equipo y el controlador nativo siguen indisponibles: `The browser access host is unavailable` y `Computer Use native pipe is unavailable ... (os error 2)`. No se pudieron comparar visualmente la página nueva, escritorio/ventana estrecha, tooltip o clic de descarga. No se generaron capturas ficticias. Queda pendiente abrir las seis secciones a 1440×900 y 390×844, revisar el menú móvil, legibilidad, gráficos y descarga real, y comprobar la consola/CSP.

### Evidencias en 06_Pruebas_y_Evidencias

- `portal_pruebas.json` / `.log`: doce pruebas clasificadas y conservación de archivos originales.
- `portal_comparacion_streamlit.json`: 36 comparaciones de indicadores con resultados reales.
- `portal_frontend_pruebas.json`: ocho pruebas unitarias JavaScript, sin navegador.
- `portal_spain_respuesta.json`, `portal_exportacion_spain.csv`: respuesta y CSV reales del filtro Spain.
- `portal_streamlit_antes.csv`: hashes previos de la versión funcional, comparados al terminar.
- `portal_servidor.json`, `portal_servidor.log`, `portal_servidor_error.log`, `portal_salud_http.json`: ejecución local real y registros.
- `portal_moneda.json`: procedencia de GBP y fecha de consulta documental.
- `portal_revision_visual.txt`: error exacto y revisión pendiente, sin afirmar pruebas visuales realizadas.
- `portal_manifiesto.csv`: hashes del portal, sin incluir .venv ni cachés.
- `portal_revision_final.json` / `.log`: revisión focalizada posterior del diccionario, rutas, marcado y tipos MIME; no repite las comparaciones del cubo.

## Solución de problemas y limitaciones

### Ajuste de presentación del 29 de octubre de 2026

El periodo aplicado se presenta con meses escritos (`1 dic 2009 — 9 dic 2011`) a partir de las fechas devueltas por el backend. Los controles nativos `type=date` muestran el formato que determine el navegador; la ayuda lo indica expresamente y cada control incluye una lectura con mes escrito. Sus valores internos, parámetros URL y recepción en Python siguen siendo ISO `AAAA-MM-DD`. No se convierten a fechas JavaScript ni se aplica una zona horaria a las fechas del filtro. Al editar aparecen las fechas propuestas bajo los campos; el periodo aplicado conserva la última consulta correcta hasta aplicar los nuevos filtros.

La barra fija tiene fondo blanco completamente opaco, z-index 1030 (por debajo del panel móvil Bootstrap) y separación del contenido calculada con su altura. Se redujeron encabezado, espaciados y filtros; los cuatro indicadores principales comparten fila desde 992 px. Se eliminó la navegación horizontal duplicada. La navegación lateral permanece en escritorio y el botón «Abrir navegación» abre el mismo menú en móvil, con cierre accesible.

Verificación focalizada: **8/8 pruebas unitarias JavaScript y 12/12 comprobaciones de backend real/CSV/revisión estática/invariantes**. La consulta real del `2010-04-03` al `2010-04-09` produjo 5.434 operaciones; Python y los siete miembros diarios del MDX corresponden al 3–9 de abril. El CSV real mantiene cuatro decimales. Los hashes confirman que consultas, conexión, serialización decimal, servicio del portal y figuras no cambiaron. Evidencias: `portal_presentacion_js.json`, `portal_presentacion_pruebas.json`, `portal_presentacion_respuesta_real.json`, `portal_presentacion_exportacion_real.csv` y `portal_presentacion_revision.md`, en `06_Pruebas_y_Evidencias`. Para repetir la prueba de backend: `.\04_Dashboard\portal_stitch\.venv\Scripts\python.exe -X utf8 .\04_Dashboard\portal_stitch\verify_presentation.py` desde la entrega.

**Pendiente visual:** no se pudo inspeccionar una ventana a 1440×900 ni 390×844 por indisponibilidad del controlador de navegador y Windows. Las comprobaciones CSS/HTML no verifican píxeles, desplazamiento, solapamientos reales, foco del menú o aparición de indicadores dentro del primer pantallazo. Abrir localmente con `powershell -ExecutionPolicy Bypass -File .\04_Dashboard\portal_stitch\iniciar.ps1` y revisar `http://127.0.0.1:8502` en ambos tamaños, desplazarse y abrir/cerrar el menú móvil.

**Discrepancia existente observada y pendiente de investigar:** para el intervalo parcial 3–9 abr 2010, Importe en tarjeta fue `117470.7600`, pero la fila mensual del CSV fue `590580.4320`. La recepción ISO y las siete fechas del MDX son correctas. La evidencia conserva ambos valores reales. No se certifica la conciliación mensual de ese intervalo; requiere revisar separadamente el comportamiento Mes/Fecha en las consultas existentes y SSAS. Este ajuste de presentación no modifica esas consultas ni intenta hacer coincidir los resultados.

Si falta ADOMD, revisar ADOMD_DLL y Python x64/netfx, sin copiar credenciales ni cambiar certificados. Si SSAS no responde, el portal muestra un mensaje; comprobar el servicio/procesamiento con los procedimientos de 03 fuera de esta aplicación. Un fallo no habilita respaldo SQL. Si 8502 está ocupado, comprobar antes qué proceso lo usa; no detener servicios ajenos. Tras editar archivos Python, reiniciar solo el portal.

Las limitaciones del ETL dimensional por instantánea y los periodos incompletos siguen vigentes. No hay normalización ISO, ETL dinámico de categorías ni cálculo YoY nuevo. Las diferencias visuales responden a la corrección semántica de la muestra, Bootstrap y diseño responsive; la fidelidad final de píxeles queda pendiente de navegador.

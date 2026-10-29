# Indicadores y procedencia del portal Stitch

Esta interfaz reutiliza sin modificar `../connection.py`, `../queries.py`, `../presentation.py` y `../charts.py`. No carga ni transforma datos de negocio. Todas las cifras analíticas son lecturas MDX del cubo **Online Retail**, base **CuboOnlineRetail**, con autenticación integrada de Windows desde el backend.

| Elemento | Medida publicada | Semántica |
|---|---|---|
| Operaciones seleccionadas | Conteo operaciones | Count de OperacionKey en el contexto completo |
| Ventas y cargos | Importe Ventas y cargos | Importe del tipo 1; incluye cargos, no exclusivamente mercancías |
| Cancelaciones | Importe Cancelacion | Importe del tipo 2, conservado negativo |
| Neto definido | Neto Ventas y cargos mas Cancelacion | Tipo 1 + tipo 2; la cancelación no se vuelve a restar |
| Ajustes contables | Importe Ajuste contable | Importe del tipo 3, separado del neto |
| Por revisar | Operaciones Por revisar | Conteo del tipo 5 |
| Precio cero | Operaciones Precio cero | Conteo del tipo 4 |
| Facturas distintas | Facturas distintas | DistinctCount del contexto, nunca suma de conteos parciales |
| Importe observado y rankings | Importe | Sum de importes firmados con todos los filtros |
| Cantidad firmada | Cantidad firmada | Sum con signo; no siempre unidades de mercancía |

Las doce medidas leídas son las de la versión funcional; Importe Precio cero e Importe Por revisar están disponibles en la respuesta de indicadores aunque no tengan tarjeta propia. No se calcula margen, crecimiento interanual, precio unitario sumado, clientes identificados ni una categoría comercial inexistente.

## Moneda verificada

El 29 de octubre de 2026 se consultó la documentación original de [UCI Online Retail II, DOI 10.24432/C5CG6D](https://archive.ics.uci.edu/dataset/502/online%2Bretail%2Bii). La ficha describe el precio unitario en libras esterlinas y enumera online_retail_II.xlsx, con el mismo periodo 2009-12-01 a 2011-12-09. El ETL conserva el precio e Importe se calcula como Cantidad × PrecioUnitario sin conversión monetaria. Por esa trazabilidad se utiliza **GBP / £** en el portal. El DW no añade una columna de moneda ni una conversión: se documenta la unidad del origen, no una capacidad multidivisa. La versión Streamlit anterior mantiene su presentación neutral original.

## Filtros

Fecha utiliza miembros diarios de `[Fecha].[Fecha]`; país `[Pais].[Pais]`; producto `[Producto].[Producto]`; tipo `[TipoOperacion].[TipoOperacion]`. Los miembros se obtienen del cubo y pasan por las listas y validaciones originales. El producto se busca por código/descripción/categoría del catálogo, pero la consulta usa su clave sustituta. Los códigos permanecen texto con ceros iniciales y alfanuméricos. Las claves compuestas de `[Fecha].[Mes]` distinguen los años.

Operaciones, importe observado, cantidad, facturas distintas, gráficos y detalle respetan todos los filtros. **Las medidas calculadas por tipo fijo reemplazan el filtro de TipoOperacion**, conservando fecha, país y producto. El aviso aparece cuando ese filtro está activo. No se implementaron subselects ni otras reglas para cambiar esta definición.

La selección de medida cambia solo la serie mensual: Importe, Cantidad firmada u Operaciones. Los rankings siguen siendo el TopCount por Importe de la versión funcional, no una selección distinta. El gráfico circular muestra únicamente distribución por **conteo de operaciones**, que es aditivo y no negativo; sus porcentajes se calculan con esos conteos reales. No se representa un importe negativo como área de una dona. Las cancelaciones conservan el signo en tarjetas, serie de importe, rankings y detalle.

## Precisión, actualidad y ausencia

El backend conserva Decimal para importes y enteros para cantidades/conteos. JSON transporta los Decimal como texto, la interfaz no convierte cifras financieras a Number para formatearlas y CSV conserva cuatro decimales. Plotly usa float exclusivamente para las coordenadas, con tooltip exacto. Las 36 comparaciones del portal contra el contrato anterior aprobaron con tolerancia **0**.

Los datos analíticos se consultan en cada petición; el catálogo de miembros tiene caché de hasta 120 segundos. La etiqueta de consulta muestra su fecha/hora real. MOLAP depende del último procesamiento correcto. El portal no procesa, recarga ni cambia SSAS.

Una celda ausente se muestra como —; cero es un valor distinto. País desconocido puede no tener hechos. SIN_CODIGO, SIN_IDENTIFICAR y Por clasificar conservan su significado: no se inventa clave −1, identificación de clientes ni clasificación comercial. DimPais cuenta miembros dimensionales, incluidos especiales, no una cantidad equivalente de países geográficos. No existe normalización ISO implementada ni comparación interanual de periodos equivalentes; no se presentan esas afirmaciones.

## Documentación y auditoría

Modelo dimensional: metadatos.json y resultados_validacion.csv, identificados como documentos históricos. Pipeline: etl_validacion_excel.json y etl_revision.json, con fecha y diferenciación entre lectura, prueba simulada y carga. SSAS: catálogo archivado de medidas/jerarquías y consultas MDX verificadas de 03_Cubo_OLAP. Auditoría: olap_cierre.json y las filas reales de olap_conciliacion_sql_mdx.csv, con fecha de esa comprobación, sin fingir que se repite al abrir la página.

Los archivos descargables están en `evidence.DOWNLOADS`, una lista cerrada. Se excluyen .env, credenciales, rutas arbitrarias y el Excel completo. Las pruebas del portal y sus límites visuales se describen en README.md y portal_pruebas.json. Siguen vigentes las limitaciones de la reconstrucción dimensional por instantánea: el portal no la presenta como ETL dinámico para datos futuros.

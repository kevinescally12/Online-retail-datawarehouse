# Medidas y semántica del cubo

Base SSAS: **CuboOnlineRetail**. Cubo visible: **Online Retail**, ID **OnlineRetail**. Grano del grupo Operaciones: una fila de dbo.FactOperacion, trazable por IdCargaOrigen. MOLAP implica que los resultados reflejarán el último procesamiento correcto, no cambios relacionales posteriores.

## Medidas físicas

| Medida | Origen | Agregación | Tipo SSAS | Interpretación |
|---|---|---|---|---|
| Importe | FactOperacion.Importe | Sum | Currency | Importe con signo, cuatro decimales. No se atribuye una moneda no documentada |
| Cantidad firmada | FactOperacion.Cantidad | Sum | BigInt | Cantidad con signo de operaciones, incluidos cargos, cancelaciones y ajustes; no equivale siempre a unidades de mercancía |
| Conteo operaciones | FactOperacion.OperacionKey | Count | BigInt | Número de filas; la clave es NOT NULL. No se suma su valor numérico |
| Facturas distintas | FactOperacion.NumeroFactura | DistinctCount | BigInt | Identificadores distintos no nulos en el contexto consultado |

PrecioUnitario y las claves numéricas no se presentan como medidas aditivas. No se calcula un precio medio por operación sin definir previamente qué operaciones y ponderación corresponden.

Facturas distintas está en el grupo separado Facturas. Su partición consulta FactOperacion con `WHERE NumeroFactura IS NOT NULL`, para coincidir con SQL COUNT(DISTINCT NumeroFactura). La medida usa NullProcessing=ZeroOrBlank, requerido por el servidor para DistinctCount; el filtro evita convertir facturas nulas en un identificador vacío. Una cadena vacía existente sí cuenta como valor, igual que en SQL. Se cuenta el código de factura tal como está almacenado: no se redefine su identidad usando hoja, cliente o fecha. **Nunca sumar facturas distintas por mes, tipo o país para obtener el total.** Un mismo número puede aparecer en varios contextos.

Currency conserva cuatro posiciones decimales en almacenamiento; su rango es más reducido que decimal(23,4) del DW. La conversión requiere que los valores y agregados quepan en Currency. Los controles actuales muestran importes individuales entre -168 469,6000 y 168 469,6000 y total 18 909 762,1180; el procesamiento actual aprobó, pero esto no garantiza datos futuros. La conciliación compara valores sin usar el texto formateado ni redondear a dos decimales, con tolerancia cero. Importe llegó por ADOMD como System.Decimal; las otras medidas físicas como System.Int64. No se usa Double para almacenar ni comparar Importe.

## Cálculos MDX

| Cálculo | Definición |
|---|---|
| Importe Ventas y cargos | Importe para TipoOperacionKey=1 |
| Importe Cancelacion | Importe para TipoOperacionKey=2, conservando el signo |
| Neto Ventas y cargos mas Cancelacion | Suma de los dos cálculos anteriores; excluye tipos 3, 4 y 5 |
| Importe Ajuste contable | Importe para TipoOperacionKey=3 |
| Operaciones Precio cero | Conteo operaciones para TipoOperacionKey=4 |
| Importe Precio cero | Importe para TipoOperacionKey=4 |
| Operaciones Por revisar | Conteo operaciones para TipoOperacionKey=5 |
| Importe Por revisar | Importe para TipoOperacionKey=5 |

Las claves 1–5 y sus nombres se verificaron en DimTipoOperacion. **Ventas y cargos no significa exclusivamente venta de mercancías.** La categoría Por clasificar permanece como atributo del producto, sin inventar categorías comerciales.

Los cálculos usan tuplas que fijan un miembro de la jerarquía `[TipoOperacion].[TipoOperacion]`: **reemplazan el filtro de esa misma jerarquía**, tanto en filas como en slicer. Conservan los filtros de Fecha, Producto, Cliente y Pais. Por ejemplo, con el filtro Precio cero, Importe base consulta ese tipo, pero Importe Ventas y cargos sigue consultando el tipo 1 dentro de los otros filtros. Si se muestran estos cálculos por filas de TipoOperacion, pueden repetirse; esto es deliberado y no debe interpretarse como un subtotal por la fila. `06_filtro_tipo.mdx` permite verificar ese comportamiento tras procesar. Los subselects y conjuntos múltiples de clientes BI pueden limitar el subcubo y deben comprobarse en el cliente utilizado; esta definición no promete ignorar cualquier forma de filtro del cliente.

## Dimensiones, claves y granularidad

| Dimensión | Clave de dimensión / FK en ambos grupos | Etiqueta |
|---|---|---|
| Fecha | DimFecha.FechaKey / FactOperacion.FechaKey | Fecha |
| Producto | DimProducto.ProductoKey / FactOperacion.ProductoKey | DescripcionProducto; código accesible en el atributo Codigo |
| Cliente | DimCliente.ClienteKey / FactOperacion.ClienteKey | IdClienteOrigen |
| Pais | DimPais.PaisKey / FactOperacion.PaisKey | NombrePais |
| TipoOperacion | DimTipoOperacion.TipoOperacionKey / FactOperacion.TipoOperacionKey | NombreTipo |

Las cinco relaciones son regulares, en la clave sustituta correspondiente, en los dos grupos de medidas. No hay relaciones many-to-many, referenciadas ni dimensiones de hecho inventadas.

Calendario: Anio → Trimestre → Mes → Fecha. Claves de atributo: Anio=(Anio), Trimestre=(Anio,Trimestre), Mes=(Anio,Mes), Fecha=(FechaKey). Relaciones funcionales: Fecha→Mes→Trimestre→Anio. El orden por clave distingue los meses y trimestres entre años. Las etiquetas de mes usan NombreMes; trimestre usa su número dentro del año. Las relaciones son Flexible para permitir una corrección dimensional futura; el compilador recomienda considerar Rigid, pero no se presupone una política de actualización inmutable.

SIN_CODIGO, SIN_IDENTIFICAR y País desconocido son miembros reales del DW y se conservan visibles con sus claves y etiquetas. No se agrega un miembro artificial que absorba referencias faltantes: UnknownMember=None, claves nulas de dimensión con Error y errores de relación/duplicados con ReportAndStop. Las medidas de suma usan NullProcessing=Preserve; en la consulta actual no hay nulos en cantidad, importe o factura. ProcessFull terminó correctamente con ese tratamiento estricto. País desconocido no tiene hechos y devuelve celdas vacías, registrado separadamente de los 74 contextos SQL con datos.

## Estado y límites

Las medidas están definidas, compiladas, desplegadas y procesadas. Tras la autorización del acceso mínimo se verificaron las 296 comparaciones de los 74 contextos SQL: todas aprobadas con tolerancia cero, sin diferencias ni pendientes. Además se aprobaron las ocho celdas de cálculos y las cuatro del filtro de tipo. El bloqueo inicial y los resultados pendientes se preservaron como evidencia histórica en un ZIP; los CSV actuales contienen resultados SQL y MDX reales. Los resultados corresponden al procesamiento del 29 de octubre de 2026 y requieren nueva conciliación tras cambios de datos.

El cubo consume las dimensiones existentes. No reconstruye sus reglas ni transforma el Excel. La instantánea SQL 03 conserva los atributos actuales, pero sigue faltando un ETL dimensional general para categorías especiales, descripciones sin candidato y asignación histórica de claves. Esto limita las reproducciones con datos distintos del estado inspeccionado.

Documentación de referencia: [tipos multidimensionales](https://learn.microsoft.com/en-us/analysis-services/multidimensional-models/olap-physical/data-types-in-analysis-services), [medidas y grupos](https://learn.microsoft.com/en-us/analysis-services/multidimensional-models/measures-and-measure-groups), [relaciones de atributos](https://learn.microsoft.com/en-us/analysis-services/multidimensional-models/attribute-relationships-define).

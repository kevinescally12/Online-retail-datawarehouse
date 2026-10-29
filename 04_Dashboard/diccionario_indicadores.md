# Indicadores y procedencia

**Fuente única:** SSAS local, catálogo CuboOnlineRetail, cubo `[Online Retail]`. No se usa SQL relacional ni Excel para obtener cifras del dashboard. Las consultas solo recuperan miembros dimensionales y resultados agregados.

| Indicador/visual | Medida real de SSAS | Agregación y significado |
|---|---|---|
| Operaciones seleccionadas | [Measures].[Conteo operaciones] | Count de filas, respetando todos los filtros |
| Importe de Ventas y cargos | [Measures].[Importe Ventas y cargos] | Importe del tipo Ventas y cargos (clave 1), no ventas exclusivamente de mercancías |
| Importe de cancelaciones | [Measures].[Importe Cancelacion] | Importe del tipo Cancelacion (clave 2), con su signo negativo |
| Neto: ventas/cargos + cancelación | [Measures].[Neto Ventas y cargos mas Cancelacion] | Suma de los dos anteriores; no se resta otra vez la cancelación |
| Ajustes contables · importe | [Measures].[Importe Ajuste contable] | Importe del tipo Ajuste contable (clave 3), separado del neto |
| Por revisar · operaciones | [Measures].[Operaciones Por revisar] | Conteo del tipo Por revisar (clave 5) |
| Precio cero · operaciones | [Measures].[Operaciones Precio cero] | Conteo del tipo Precio cero (clave 4) |
| Facturas distintas seleccionadas | [Measures].[Facturas distintas] | DistinctCount no aditivo para el contexto completo |
| Importe observado, serie y rankings | [Measures].[Importe] | Sum de importes firmados, con todos los filtros |
| Cantidad firmada en detalle | [Measures].[Cantidad firmada] | Sum de cantidades con signo; no siempre unidades de mercancías |

Las medidas Importe Precio cero e Importe Por revisar también existen y se leen en la consulta de indicadores, pero no tienen tarjeta propia; sus conteos sí. Las cuatro medidas base aparecen en el detalle agregado y CSV. No se ofrece una medida de precio unitario sumado, clientes identificados, margen, beneficio, porcentaje de cancelación o venta exclusiva de mercancías: no se inventaron esas definiciones.

## Filtros y gráficos

| Selección | Jerarquía real | Clave utilizada |
|---|---|---|
| Periodo diario | [Fecha].[Fecha] | FechaKey, miembro numérico YYYYMMDD |
| País | [Pais].[Pais] | PaisKey |
| Producto | [Producto].[Producto] | ProductoKey; etiqueta con Codigo, descripción y categoría reales |
| Tipo de operación | [TipoOperacion].[TipoOperacion] | TipoOperacionKey |
| Serie mensual | [Fecha].[Mes] | Clave compuesta (Anio,Mes), mostrada YYYY-MM |
| Ranking de códigos | [Producto].[Codigo], [Producto].[Categoria] | Código natural y categoría existentes |

El calendario real va de 2009-12-01 a 2011-12-09: 2009 y 2011 son incompletos. La jerarquía Calendario Año→Trimestre→Mes→Fecha existe, pero el filtro de intervalo utiliza su atributo diario. El gráfico mensual consulta directamente el nivel Mes del cubo. No se agrupan filas de hechos en Python.

País, producto y tipo son selecciones individuales. Una selección vacía significa todos. Para país/tipo en filas se limita el conjunto del eje, evitando repetir la misma jerarquía en slicer y filas. Los otros filtros se aplican mediante conjuntos de miembros del catálogo. La categoría Por clasificar se conserva, sin inferir una categoría comercial. SIN_CODIGO y País desconocido no se ocultan. No se identifica al cliente SIN_IDENTIFICAR como conocido; no existe indicador de clientes identificados ni filtro de cliente en esta versión.

**Las medidas calculadas por tipo fijo sustituyen el filtro TipoOperacion**, como en el cubo validado. Conservan fecha, país y producto. Operaciones, facturas distintas, importe observado, gráficos y detalle sí respetan ese filtro. El aviso se muestra cuando se selecciona un tipo. No se usan subselects para cambiar implícitamente esta semántica.

Los rankings son TopCount 10 por importe firmado en SSAS. El detalle/exportación consulta todos los agregados filtrados del nivel elegido, hasta el límite declarado de 7000. No se suman las facturas distintas del detalle para obtener la tarjeta; se vuelve a consultar el contexto global al cubo.

## Precisión y ausencia de datos

Los importes se mantienen como Decimal y los conteos/cantidades como enteros. Indicadores y CSV conservan cuatro decimales; no se aplica tolerancia para aprobar comparaciones. La representación geométrica de Plotly usa float solo para dibujar y un tooltip con importe exacto. Currency en SSAS es un tipo de almacenamiento: no se atribuye una moneda concreta no documentada.

NULL/ausencia de celda se presenta con — y las listas sin hechos con mensajes, no como datos inventados. Cero es un valor válido cuando hay operaciones (por ejemplo, Precio cero). El fallo de conexión produce un mensaje y detalle, sin sustituir cifras por SQL ni ejemplos.

## Actualidad y límites

MOLAP depende del último procesamiento correcto; las consultas del dashboard tienen caché de hasta 30 segundos y el catálogo de 120. La hora visible es la de consulta. Actualizar consultas no procesa el cubo. Las 15 pruebas de esta etapa y los valores de referencia están en 06_Pruebas_y_Evidencias, con separación entre SSAS real, AppTest con SSAS real, pruebas unitarias y un error simulado. Queda pendiente inspección visual del navegador y su descarga real. Las limitaciones de reconstrucción dimensional por instantánea de 01–03 siguen vigentes.

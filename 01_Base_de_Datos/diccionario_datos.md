# Diccionario de datos

Fuente: catálogos de SQL Server local, 2026-10-29. No se dedujeron tipos del Excel. Grano de hechos: una operación de origen admitida, identificada por IdCargaOrigen. Las repeticiones internas conservan identificadores distintos.

## OnlineRetail_Origen.staging.OperacionesRetail

| Columna | Tipo | Nulo | Identidad | Significado |
|---|---|---|---|---|
| IdCarga | bigint | False | True | Identificador técnico de la fila de staging |
| HojaOrigen | nvarchar(30) | False | False | Hoja Excel de procedencia |
| NumeroFactura | nvarchar(50) | True | False | Identificador de factura; su prefijo C interviene en la clasificación |
| CodigoProducto | nvarchar(50) | True | False | Código de origen; puede representar productos, cargos, descuentos o ajustes |
| Descripcion | nvarchar(500) | True | False | Texto original de la operación, con espacios conservados |
| Cantidad | int | True | False | Cantidad con signo de la operación |
| FechaFactura | datetime2(7) | True | False | Fecha y hora original; se usa para calendario y corte entre hojas |
| PrecioUnitario | decimal(18,4) | True | False | Precio unitario con signo, sin atribuir una moneda no documentada |
| IdCliente | nvarchar(50) | True | False | Identificador natural de cliente; puede estar ausente |
| Pais | nvarchar(100) | True | False | País registrado en la operación de origen |

- PK__Operacio__6C985617C79690AE: CLUSTERED; PK=True, único=True, columnas: [IdCarga] ASC.

No se encontraron valores predeterminados ni restricciones CHECK en esta base. Los índices observados corresponden a PK y UNIQUE.

## OnlineRetail_DW.dbo.DimCliente

| Columna | Tipo | Nulo | Identidad | Significado |
|---|---|---|---|---|
| ClienteKey | int | False | True | Clave sustituta o referencia dimensional |
| IdClienteOrigen | nvarchar(50) | False | False | Identificador natural único; SIN_IDENTIFICAR representa cliente nulo |
| TipoCliente | nvarchar(30) | False | False | Etiqueta de cliente Identificado o Desconocido |

## OnlineRetail_DW.dbo.DimFecha

| Columna | Tipo | Nulo | Identidad | Significado |
|---|---|---|---|---|
| FechaKey | int | False | False | Clave calendario YYYYMMDD |
| Fecha | date | False | False | Día calendario único, sin componente horario |
| Dia | tinyint | False | False | Número de día del mes |
| Mes | tinyint | False | False | Número de mes del año |
| NombreMes | nvarchar(20) | False | False | Nombre del mes en español |
| Trimestre | tinyint | False | False | Trimestre calendario |
| Anio | smallint | False | False | Año calendario |

## OnlineRetail_DW.dbo.DimPais

| Columna | Tipo | Nulo | Identidad | Significado |
|---|---|---|---|---|
| PaisKey | int | False | True | Clave sustituta o referencia dimensional |
| NombrePais | nvarchar(100) | False | False | País normalizado sin espacios exteriores; País desconocido representa nulo o vacío |

## OnlineRetail_DW.dbo.DimProducto

| Columna | Tipo | Nulo | Identidad | Significado |
|---|---|---|---|---|
| ProductoKey | int | False | True | Clave sustituta o referencia dimensional |
| CodigoProducto | nvarchar(50) | False | False | Código natural único normalizado; SIN_CODIGO representa nulo o vacío |
| DescripcionProducto | nvarchar(500) | False | False | Descripción representativa del producto |
| CategoriaCodigo | nvarchar(50) | False | False | Etiqueta observada; no implica que todo código sea mercancía |

## OnlineRetail_DW.dbo.DimTipoOperacion

| Columna | Tipo | Nulo | Identidad | Significado |
|---|---|---|---|---|
| TipoOperacionKey | int | False | True | Clave sustituta o referencia dimensional |
| NombreTipo | nvarchar(50) | False | False | Nombre único de una de las cinco clasificaciones existentes |
| Descripcion | nvarchar(250) | False | False | Explicación de la clasificación conservada del DW |

## OnlineRetail_DW.dbo.FactOperacion

| Columna | Tipo | Nulo | Identidad | Significado |
|---|---|---|---|---|
| OperacionKey | bigint | False | True | Clave sustituta de la operación en el DW |
| IdCargaOrigen | bigint | False | False | Trazabilidad a staging.IdCarga; único en hechos |
| HojaOrigen | nvarchar(30) | False | False | Hoja Excel de procedencia |
| NumeroFactura | nvarchar(50) | True | False | Identificador de factura conservado del origen |
| DescripcionOriginal | nvarchar(500) | True | False | Descripción sin normalizar conservada del origen |
| FechaKey | int | False | False | Clave calendario YYYYMMDD |
| ProductoKey | int | False | False | Clave sustituta o referencia dimensional |
| ClienteKey | int | False | False | Clave sustituta o referencia dimensional |
| PaisKey | int | False | False | Clave sustituta o referencia dimensional |
| TipoOperacionKey | int | False | False | Clave sustituta o referencia dimensional |
| Cantidad | int | True | False | Cantidad original conservada con signo |
| PrecioUnitario | decimal(18,4) | True | False | Precio original conservado con signo |
| Importe | decimal(23,4) | True | False | Cantidad por PrecioUnitario, conservando signo; decimal(23,4) |

- PK__DimClien__E0D03928670FF4B3: CLUSTERED; PK=True, único=True, columnas: [ClienteKey] ASC.
- UQ__DimClien__B1D57EE0F157800F: NONCLUSTERED; PK=False, único=True, columnas: [IdClienteOrigen] ASC.
- PK__DimFecha__F60A023650BE6836: CLUSTERED; PK=True, único=True, columnas: [FechaKey] ASC.
- UQ__DimFecha__B30C8A5E7DFD5263: NONCLUSTERED; PK=False, único=True, columnas: [Fecha] ASC.
- PK__DimPais__680D2C4E4454F1A8: CLUSTERED; PK=True, único=True, columnas: [PaisKey] ASC.
- UQ__DimPais__BFA502694ECF7A98: NONCLUSTERED; PK=False, único=True, columnas: [NombrePais] ASC.
- PK__DimProdu__902B83116014DDF2: CLUSTERED; PK=True, único=True, columnas: [ProductoKey] ASC.
- UQ__DimProdu__785B009FEEDF22C8: NONCLUSTERED; PK=False, único=True, columnas: [CodigoProducto] ASC.
- PK__DimTipoO__64FFE3CFD0B3539C: CLUSTERED; PK=True, único=True, columnas: [TipoOperacionKey] ASC.
- UQ__DimTipoO__7586661C08FB7FF0: NONCLUSTERED; PK=False, único=True, columnas: [NombreTipo] ASC.
- PK__FactOper__2E5B3BC894CC8DE8: CLUSTERED; PK=True, único=True, columnas: [OperacionKey] ASC.
- UQ__FactOper__E5E7A466945D205A: NONCLUSTERED; PK=False, único=True, columnas: [IdCargaOrigen] ASC.
- FK_FactOperacion_Cliente: FactOperacion.[ClienteKey] → DimCliente.[ClienteKey]; ON DELETE/UPDATE NO_ACTION/NO_ACTION.
- FK_FactOperacion_Fecha: FactOperacion.[FechaKey] → DimFecha.[FechaKey]; ON DELETE/UPDATE NO_ACTION/NO_ACTION.
- FK_FactOperacion_Pais: FactOperacion.[PaisKey] → DimPais.[PaisKey]; ON DELETE/UPDATE NO_ACTION/NO_ACTION.
- FK_FactOperacion_Producto: FactOperacion.[ProductoKey] → DimProducto.[ProductoKey]; ON DELETE/UPDATE NO_ACTION/NO_ACTION.
- FK_FactOperacion_Tipo: FactOperacion.[TipoOperacionKey] → DimTipoOperacion.[TipoOperacionKey]; ON DELETE/UPDATE NO_ACTION/NO_ACTION.

No se encontraron valores predeterminados ni restricciones CHECK en esta base. Los índices observados corresponden a PK y UNIQUE.


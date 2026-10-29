-- SOLO LECTURA. Ejecutado contra las bases actuales; resultados en el CSV de evidencias.
-- Comparaciones de textos usan la intercalación real de SQL Server.
SET NOCOUNT ON;
;WITH O AS (
 SELECT *,CASE WHEN HojaOrigen=N'Year 2009-2010' OR (HojaOrigen=N'Year 2010-2011' AND FechaFactura>='20101210') THEN 1 ELSE 0 END Elegible
 FROM OnlineRetail_Origen.staging.OperacionesRetail
), X AS (
 SELECT o.IdCarga,o.Elegible,f.OperacionKey,
 CASE WHEN EXISTS(SELECT f.HojaOrigen,f.NumeroFactura,f.DescripcionOriginal EXCEPT SELECT o.HojaOrigen,o.NumeroFactura,o.Descripcion) THEN 1 ELSE 0 END TrazaDistinta,
 CASE WHEN EXISTS(SELECT f.Cantidad,f.PrecioUnitario,f.Importe EXCEPT SELECT o.Cantidad,o.PrecioUnitario,CONVERT(decimal(23,4),CONVERT(decimal(18,0),o.Cantidad)*o.PrecioUnitario)) THEN 1 ELSE 0 END MedidasDistintas,
 CASE WHEN df.FechaKey IS NULL OR p.ProductoKey IS NULL OR c.ClienteKey IS NULL OR pa.PaisKey IS NULL OR t.TipoOperacionKey IS NULL THEN 1 ELSE 0 END Huerfano,
 CASE WHEN EXISTS(SELECT df.Fecha,p.CodigoProducto,c.IdClienteOrigen,pa.NombrePais EXCEPT SELECT CAST(o.FechaFactura AS date),COALESCE(NULLIF(LTRIM(RTRIM(o.CodigoProducto)),N''),N'SIN_CODIGO'),COALESCE(o.IdCliente,N'SIN_IDENTIFICAR'),COALESCE(NULLIF(LTRIM(RTRIM(o.Pais)),N''),N'País desconocido')) THEN 1 ELSE 0 END AsignacionDistinta,
 CASE WHEN t.NombreTipo=CASE WHEN o.CodigoProducto=N'B' AND o.PrecioUnitario<0 THEN N'Ajuste contable' WHEN o.PrecioUnitario=0 THEN N'Precio cero' WHEN o.NumeroFactura LIKE 'C%' AND o.Cantidad<0 AND o.PrecioUnitario>0 THEN N'Cancelacion' WHEN o.NumeroFactura NOT LIKE 'C%' AND o.Cantidad>0 AND o.PrecioUnitario>0 THEN N'Ventas y cargos' ELSE N'Por revisar' END THEN 0 ELSE 1 END ClasificacionDistinta
 FROM O o FULL JOIN OnlineRetail_DW.dbo.FactOperacion f ON f.IdCargaOrigen=o.IdCarga
 LEFT JOIN OnlineRetail_DW.dbo.DimFecha df ON df.FechaKey=f.FechaKey
 LEFT JOIN OnlineRetail_DW.dbo.DimProducto p ON p.ProductoKey=f.ProductoKey
 LEFT JOIN OnlineRetail_DW.dbo.DimCliente c ON c.ClienteKey=f.ClienteKey
 LEFT JOIN OnlineRetail_DW.dbo.DimPais pa ON pa.PaisKey=f.PaisKey
 LEFT JOIN OnlineRetail_DW.dbo.DimTipoOperacion t ON t.TipoOperacionKey=f.TipoOperacionKey
), A AS (
 SELECT
 SUM(CONVERT(bigint,CASE WHEN Elegible=1 AND OperacionKey IS NULL THEN 1 ELSE 0 END)) Faltantes,
 SUM(CONVERT(bigint,CASE WHEN OperacionKey IS NOT NULL AND (IdCarga IS NULL OR Elegible=0) THEN 1 ELSE 0 END)) FueraFiltro,
 SUM(CONVERT(bigint,CASE WHEN OperacionKey IS NOT NULL THEN Huerfano ELSE 0 END)) Huerfanos,
 SUM(CONVERT(bigint,CASE WHEN OperacionKey IS NOT NULL THEN TrazaDistinta ELSE 0 END)) Trazabilidad,
 SUM(CONVERT(bigint,CASE WHEN OperacionKey IS NOT NULL THEN MedidasDistintas ELSE 0 END)) Medidas,
 SUM(CONVERT(bigint,CASE WHEN OperacionKey IS NOT NULL THEN AsignacionDistinta ELSE 0 END)) Asignaciones,
 SUM(CONVERT(bigint,CASE WHEN OperacionKey IS NOT NULL THEN ClasificacionDistinta ELSE 0 END)) Clasificacion
 FROM X
)
SELECT v.Comprobacion,CONVERT(varchar(100),v.Valor) Valor,'0' Esperado,
 CASE WHEN v.Valor=0 THEN 'APROBADO' ELSE 'DIFERENCIA' END Estado, N'Comparación por IdCargaOrigen con el origen y dimensiones actuales' Detalle
FROM A CROSS APPLY (VALUES ('Cobertura_faltantes',Faltantes),('Hechos_fuera_filtro',FueraFiltro),('Integridad_relaciones',Huerfanos),('Trazabilidad',Trazabilidad),('Cantidades_precios_importes',Medidas),('Asignacion_dimensiones',Asignaciones),('Clasificacion',Clasificacion)) v(Comprobacion,Valor);

SELECT 'Duplicados_IdCargaOrigen' Comprobacion,CONVERT(varchar(100),COUNT_BIG(*)) Valor,'0' Esperado,CASE WHEN COUNT_BIG(*)=0 THEN 'APROBADO' ELSE 'DIFERENCIA' END Estado,N'Grupos duplicados, sin eliminar repeticiones de negocio' Detalle FROM (SELECT IdCargaOrigen FROM OnlineRetail_DW.dbo.FactOperacion GROUP BY IdCargaOrigen HAVING COUNT_BIG(*)>1) d;

;WITH C AS (
SELECT 'Origen' Tabla,COUNT_BIG(*) N,CONVERT(bigint,1067371) Historico FROM OnlineRetail_Origen.staging.OperacionesRetail
UNION ALL SELECT 'FactOperacion',COUNT_BIG(*),1044848 FROM OnlineRetail_DW.dbo.FactOperacion
UNION ALL SELECT 'DimFecha',COUNT_BIG(*),739 FROM OnlineRetail_DW.dbo.DimFecha
UNION ALL SELECT 'DimProducto',COUNT_BIG(*),5132 FROM OnlineRetail_DW.dbo.DimProducto
UNION ALL SELECT 'DimCliente',COUNT_BIG(*),5943 FROM OnlineRetail_DW.dbo.DimCliente
UNION ALL SELECT 'DimPais',COUNT_BIG(*),44 FROM OnlineRetail_DW.dbo.DimPais
UNION ALL SELECT 'DimTipoOperacion',COUNT_BIG(*),5 FROM OnlineRetail_DW.dbo.DimTipoOperacion
) SELECT 'Conteo_'+Tabla Comprobacion,CONVERT(varchar(100),N) Valor,CONVERT(varchar(100),Historico) Esperado,CASE WHEN N=Historico THEN 'APROBADO' ELSE 'DIFERENCIA' END Estado,N'Comparación con referencia histórica proporcionada' Detalle FROM C;

;WITH O AS (SELECT SUM(CONVERT(bigint,Cantidad)) Cantidad,SUM(CONVERT(decimal(18,0),Cantidad)*PrecioUnitario) Importe,SUM(CONVERT(decimal(28,4),PrecioUnitario)) Precios FROM OnlineRetail_Origen.staging.OperacionesRetail WHERE HojaOrigen=N'Year 2009-2010' OR (HojaOrigen=N'Year 2010-2011' AND FechaFactura>='20101210')),
 F AS (SELECT SUM(CONVERT(bigint,Cantidad)) Cantidad,SUM(Importe) Importe,SUM(CONVERT(decimal(28,4),PrecioUnitario)) Precios FROM OnlineRetail_DW.dbo.FactOperacion)
SELECT v.Comprobacion,CONVERT(varchar(100),v.Actual) Valor,CONVERT(varchar(100),v.Esperado) Esperado,CASE WHEN v.Actual=v.Esperado THEN 'APROBADO' ELSE 'DIFERENCIA' END Estado,N'Totales con signo; precios sumados solo como control técnico' Detalle FROM O CROSS JOIN F CROSS APPLY (VALUES ('Total_cantidad',CONVERT(decimal(38,4),F.Cantidad),CONVERT(decimal(38,4),O.Cantidad)),('Total_importe',F.Importe,O.Importe),('Suma_precios',F.Precios,O.Precios)) v(Comprobacion,Actual,Esperado);

SELECT 'Excluidas_solapamiento' Comprobacion,CONVERT(varchar(100),COUNT_BIG(*)) Valor,'22523' Esperado,CASE WHEN COUNT_BIG(*)=22523 THEN 'APROBADO' ELSE 'DIFERENCIA' END Estado,N'Filas de la segunda hoja anteriores al corte; no prueba identidad fila a fila entre hojas' Detalle FROM OnlineRetail_Origen.staging.OperacionesRetail WHERE HojaOrigen=N'Year 2010-2011' AND FechaFactura<'20101210';

;WITH Frecuencias AS (
 SELECT COALESCE(NULLIF(LTRIM(RTRIM(CodigoProducto)),N''),N'SIN_CODIGO') Codigo,LTRIM(RTRIM(Descripcion)) Descripcion,COUNT_BIG(*) N
 FROM OnlineRetail_Origen.staging.OperacionesRetail WHERE PrecioUnitario>0 AND NULLIF(LTRIM(RTRIM(Descripcion)),N'') IS NOT NULL
 GROUP BY COALESCE(NULLIF(LTRIM(RTRIM(CodigoProducto)),N''),N'SIN_CODIGO'),LTRIM(RTRIM(Descripcion))
), R AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY Codigo ORDER BY N DESC,Descripcion ASC) rn FROM Frecuencias)
SELECT 'Descripcion_representativa_todo_origen' Comprobacion,CONVERT(varchar(100),COUNT_BIG(*)) Valor,'0' Esperado,CASE WHEN COUNT_BIG(*)=0 THEN 'APROBADO' ELSE 'DIFERENCIA' END Estado,N'Productos con candidato positivo; frecuencia sobre todo staging, empate según collation SQL' Detalle FROM R JOIN OnlineRetail_DW.dbo.DimProducto p ON p.CodigoProducto=R.Codigo WHERE rn=1 AND p.DescripcionProducto<>R.Descripcion;

SELECT 'Distribucion_tipo_'+t.NombreTipo Comprobacion,CONVERT(varchar(100),COUNT_BIG(*)) Valor,NULL Esperado,'INFORMATIVO' Estado,CONVERT(nvarchar(200),SUM(f.Importe)) + N' importe con signo' Detalle FROM OnlineRetail_DW.dbo.FactOperacion f JOIN OnlineRetail_DW.dbo.DimTipoOperacion t ON t.TipoOperacionKey=f.TipoOperacionKey GROUP BY t.NombreTipo;
SELECT 'Categoria_producto_'+CategoriaCodigo Comprobacion,CONVERT(varchar(100),COUNT_BIG(*)) Valor,NULL Esperado,'INFORMATIVO' Estado,N'Etiquetas existentes: no se infiere mercancía por código' Detalle FROM OnlineRetail_DW.dbo.DimProducto GROUP BY CategoriaCodigo;

;WITH Frecuencias AS (
 SELECT COALESCE(NULLIF(LTRIM(RTRIM(CodigoProducto)),N''),N'SIN_CODIGO') Codigo,LTRIM(RTRIM(Descripcion)) Descripcion,COUNT_BIG(*) N
 FROM OnlineRetail_Origen.staging.OperacionesRetail WHERE PrecioUnitario>0 AND NULLIF(LTRIM(RTRIM(Descripcion)),N'') IS NOT NULL
 AND (HojaOrigen=N'Year 2009-2010' OR (HojaOrigen=N'Year 2010-2011' AND FechaFactura>='20101210'))
 GROUP BY COALESCE(NULLIF(LTRIM(RTRIM(CodigoProducto)),N''),N'SIN_CODIGO'),LTRIM(RTRIM(Descripcion))
), R AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY Codigo ORDER BY N DESC,Descripcion ASC) rn FROM Frecuencias)
SELECT 'Descripcion_representativa_origen_filtrado' Comprobacion,CONVERT(varchar(100),COUNT_BIG(*)) Valor,'0' Esperado,CASE WHEN COUNT_BIG(*)=0 THEN 'APROBADO' ELSE 'DIFERENCIA' END Estado,N'Universo compatible con las descripciones actuales; solo productos con candidato positivo' Detalle FROM R JOIN OnlineRetail_DW.dbo.DimProducto p ON p.CodigoProducto=R.Codigo WHERE rn=1 AND p.DescripcionProducto<>R.Descripcion;

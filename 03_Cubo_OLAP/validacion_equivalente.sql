-- Solo lectura. Cada fila del resultado es un contexto independiente.
-- COUNT(DISTINCT) se calcula en cada contexto; nunca se suman conteos parciales.
SELECT 'Total' Contexto,'TOTAL' Clave, SUM(Importe) Importe,
 SUM(CONVERT(bigint,Cantidad)) Cantidad,COUNT_BIG(*) Operaciones,
 CONVERT(bigint,COUNT(DISTINCT NumeroFactura)) FacturasDistintas
FROM OnlineRetail_DW.dbo.FactOperacion
UNION ALL
SELECT 'Tipo',CONVERT(varchar(50),TipoOperacionKey),SUM(Importe),SUM(CONVERT(bigint,Cantidad)),COUNT_BIG(*),COUNT(DISTINCT NumeroFactura)
FROM OnlineRetail_DW.dbo.FactOperacion GROUP BY TipoOperacionKey
UNION ALL
SELECT 'Mes',CONVERT(varchar(4),d.Anio)+'-'+RIGHT('0'+CONVERT(varchar(2),d.Mes),2),SUM(f.Importe),SUM(CONVERT(bigint,f.Cantidad)),COUNT_BIG(*),COUNT(DISTINCT f.NumeroFactura)
FROM OnlineRetail_DW.dbo.FactOperacion f JOIN OnlineRetail_DW.dbo.DimFecha d ON d.FechaKey=f.FechaKey GROUP BY d.Anio,d.Mes
UNION ALL
SELECT 'Pais',CONVERT(varchar(50),PaisKey),SUM(Importe),SUM(CONVERT(bigint,Cantidad)),COUNT_BIG(*),COUNT(DISTINCT NumeroFactura)
FROM OnlineRetail_DW.dbo.FactOperacion GROUP BY PaisKey
ORDER BY Contexto,Clave;

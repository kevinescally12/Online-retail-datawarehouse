-- ADAPTADO del SQLQuery3.sql recuperado; NO ejecutado sobre ninguna base.
-- Los tipos ya se cargan en 03. Se conserva SELECT, filtro, joins y CASE originales.
-- Carga completa una sola vez en destino vacío. No es una carga incremental.
:setvar BaseDW "OnlineRetail_DW_Replica"
:setvar BaseOrigen "OnlineRetail_Origen_Replica"
:on error exit
USE [$(BaseDW)];
GO
IF DB_NAME()=N'OnlineRetail_DW' THROW 51000, 'Prohibida la carga sobre la base actual.', 1;
SET XACT_ABORT ON;
BEGIN TRY
 BEGIN TRANSACTION;
 -- Bloqueo exclusivo hasta COMMIT para impedir dos cargas simultáneas.
 IF EXISTS(SELECT 1 FROM dbo.FactOperacion WITH (TABLOCKX,HOLDLOCK))
   THROW 50001, 'Ya existen hechos; no se permite repetir la carga.', 1;
 IF (SELECT COUNT_BIG(*) FROM dbo.DimTipoOperacion)<>5
   THROW 50003, 'Cargue primero las dimensiones mediante el archivo 03.', 1;
 INSERT dbo.FactOperacion (IdCargaOrigen, HojaOrigen, NumeroFactura, DescripcionOriginal, FechaKey, ProductoKey, ClienteKey, PaisKey, TipoOperacionKey, Cantidad, PrecioUnitario, Importe)
 SELECT o.IdCarga,o.HojaOrigen,o.NumeroFactura,o.Descripcion, f.FechaKey,p.ProductoKey,c.ClienteKey,pa.PaisKey,t.TipoOperacionKey,o.Cantidad,o.PrecioUnitario, CAST(o.Cantidad AS decimal(18,0))*o.PrecioUnitario
 FROM [$(BaseOrigen)].staging.OperacionesRetail o
 JOIN dbo.DimFecha f ON f.Fecha=CAST(o.FechaFactura AS date)
 JOIN dbo.DimProducto p ON p.CodigoProducto=COALESCE(NULLIF(LTRIM(RTRIM(o.CodigoProducto)),N''),N'SIN_CODIGO')
 JOIN dbo.DimCliente c ON c.IdClienteOrigen=COALESCE(o.IdCliente,N'SIN_IDENTIFICAR')
 JOIN dbo.DimPais pa ON pa.NombrePais=COALESCE(NULLIF(LTRIM(RTRIM(o.Pais)),N''),N'País desconocido')
 JOIN dbo.DimTipoOperacion t ON t.NombreTipo=CASE WHEN o.CodigoProducto=N'B' AND o.PrecioUnitario<0 THEN N'Ajuste contable' WHEN o.PrecioUnitario=0 THEN N'Precio cero' WHEN o.NumeroFactura LIKE 'C%' AND o.Cantidad<0 AND o.PrecioUnitario>0 THEN N'Cancelacion' WHEN o.NumeroFactura NOT LIKE 'C%' AND o.Cantidad>0 AND o.PrecioUnitario>0 THEN N'Ventas y cargos' ELSE N'Por revisar' END
 WHERE o.HojaOrigen='Year 2009-2010' OR (o.HojaOrigen='Year 2010-2011' AND o.FechaFactura>='20101210');
 IF (SELECT COUNT_BIG(*) FROM dbo.FactOperacion) <> (SELECT COUNT_BIG(*) FROM [$(BaseOrigen)].staging.OperacionesRetail WHERE HojaOrigen='Year 2009-2010' OR (HojaOrigen='Year 2010-2011' AND FechaFactura>='20101210')) THROW 50002, 'Conteo no coincide: se revierte la carga.', 1;

 COMMIT;
END TRY
BEGIN CATCH
 IF @@TRANCOUNT>0 ROLLBACK;
 THROW;
END CATCH;
-- La restricción UNIQUE de IdCargaOrigen aporta protección adicional.
SELECT COUNT_BIG(*) Total FROM dbo.FactOperacion;

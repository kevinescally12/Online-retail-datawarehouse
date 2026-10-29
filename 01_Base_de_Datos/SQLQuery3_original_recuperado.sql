USE OnlineRetail_DW;
SET XACT_ABORT ON;
BEGIN TRY
 BEGIN TRANSACTION;
 IF EXISTS (SELECT 1 FROM dbo.FactOperacion) OR EXISTS (SELECT 1 FROM dbo.DimTipoOperacion) THROW 50001, 'Ya existen datos en hechos o tipos; carga detenida.', 1;
 INSERT dbo.DimTipoOperacion (NombreTipo, Descripcion) VALUES
 (N'Ventas y cargos', N'Cantidad y precio positivos; puede incluir servicios o cargos.'),
 (N'Cancelacion', N'Factura con C, cantidad negativa y precio positivo.'),
 (N'Ajuste contable', N'Codigo B con precio negativo.'),
 (N'Precio cero', N'Operacion con precio cero; requiere revision.'),
 (N'Por revisar', N'Otras combinaciones, incluidas excepciones.');
 INSERT dbo.FactOperacion (IdCargaOrigen, HojaOrigen, NumeroFactura, DescripcionOriginal, FechaKey, ProductoKey, ClienteKey, PaisKey, TipoOperacionKey, Cantidad, PrecioUnitario, Importe)
 SELECT o.IdCarga,o.HojaOrigen,o.NumeroFactura,o.Descripcion, f.FechaKey,p.ProductoKey,c.ClienteKey,pa.PaisKey,t.TipoOperacionKey,o.Cantidad,o.PrecioUnitario, CAST(o.Cantidad AS decimal(18,0))*o.PrecioUnitario
 FROM OnlineRetail_Origen.staging.OperacionesRetail o
 JOIN dbo.DimFecha f ON f.Fecha=CAST(o.FechaFactura AS date)
 JOIN dbo.DimProducto p ON p.CodigoProducto=COALESCE(NULLIF(LTRIM(RTRIM(o.CodigoProducto)),N''),N'SIN_CODIGO')
 JOIN dbo.DimCliente c ON c.IdClienteOrigen=COALESCE(o.IdCliente,N'SIN_IDENTIFICAR')
 JOIN dbo.DimPais pa ON pa.NombrePais=COALESCE(NULLIF(LTRIM(RTRIM(o.Pais)),N''),N'País desconocido')
 JOIN dbo.DimTipoOperacion t ON t.NombreTipo=CASE WHEN o.CodigoProducto=N'B' AND o.PrecioUnitario<0 THEN N'Ajuste contable' WHEN o.PrecioUnitario=0 THEN N'Precio cero' WHEN o.NumeroFactura LIKE 'C%' AND o.Cantidad<0 AND o.PrecioUnitario>0 THEN N'Cancelacion' WHEN o.NumeroFactura NOT LIKE 'C%' AND o.Cantidad>0 AND o.PrecioUnitario>0 THEN N'Ventas y cargos' ELSE N'Por revisar' END
 WHERE o.HojaOrigen='Year 2009-2010' OR (o.HojaOrigen='Year 2010-2011' AND o.FechaFactura>='20101210');
 IF (SELECT COUNT_BIG(*) FROM dbo.FactOperacion) <> (SELECT COUNT_BIG(*) FROM OnlineRetail_Origen.staging.OperacionesRetail WHERE HojaOrigen='Year 2009-2010' OR (HojaOrigen='Year 2010-2011' AND FechaFactura>='20101210')) THROW 50002, 'Conteo no coincide: se revierte la carga.', 1;
 COMMIT;
END TRY
BEGIN CATCH
 IF @@TRANCOUNT>0 ROLLBACK;
 THROW;
END CATCH;
SELECT t.NombreTipo, COUNT_BIG(*) Total, SUM(f.Importe) Importe FROM dbo.FactOperacion f JOIN dbo.DimTipoOperacion t ON t.TipoOperacionKey=f.TipoOperacionKey GROUP BY t.NombreTipo;
SELECT COUNT_BIG(*) Total FROM dbo.FactOperacion;
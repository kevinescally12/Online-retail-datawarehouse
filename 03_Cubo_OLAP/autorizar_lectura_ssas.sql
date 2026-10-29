-- Aplicado con autorización expresa del usuario. Solo seguridad, sin DML de datos.
-- Destino único: servidor local, OnlineRetail_DW, seis tablas enumeradas.
USE [master];
SET XACT_ABORT ON;
BEGIN TRY
 BEGIN TRANSACTION;
 DECLARE @Cambios TABLE(Accion nvarchar(200));
 IF SUSER_ID(N'NT SERVICE\MSSQLServerOLAPService') IS NULL
 BEGIN
  CREATE LOGIN [NT SERVICE\MSSQLServerOLAPService] FROM WINDOWS;
  INSERT @Cambios VALUES(N'CREATE LOGIN Windows NT SERVICE\MSSQLServerOLAPService');
 END;
 IF NOT EXISTS(SELECT 1 FROM sys.server_principals WHERE name=N'NT SERVICE\MSSQLServerOLAPService' AND type='U')
  THROW 51000, 'El login existente no es Windows; no se modifica.', 1;
 USE [OnlineRetail_DW];
 IF USER_ID(N'NT SERVICE\MSSQLServerOLAPService') IS NULL
 BEGIN
  CREATE USER [NT SERVICE\MSSQLServerOLAPService] FOR LOGIN [NT SERVICE\MSSQLServerOLAPService];
  INSERT @Cambios VALUES(N'CREATE USER en OnlineRetail_DW');
 END;
 IF NOT EXISTS(SELECT 1 FROM sys.database_principals WHERE name=N'NT SERVICE\MSSQLServerOLAPService' AND sid=SUSER_SID(N'NT SERVICE\MSSQLServerOLAPService'))
  THROW 51001, 'El usuario existente no corresponde al login; no se reasigna.', 1;
 DECLARE @uid int=USER_ID(N'NT SERVICE\MSSQLServerOLAPService');
 IF EXISTS(SELECT 1 FROM sys.database_permissions WHERE grantee_principal_id=@uid AND state='D' AND
  ((class=0 AND permission_name='CONNECT') OR (class=1 AND permission_name='SELECT' AND major_id IN
  (OBJECT_ID('dbo.DimFecha'),OBJECT_ID('dbo.DimProducto'),OBJECT_ID('dbo.DimCliente'),OBJECT_ID('dbo.DimPais'),OBJECT_ID('dbo.DimTipoOperacion'),OBJECT_ID('dbo.FactOperacion')))))
  THROW 51002, 'Hay DENY previo: se conserva y se detiene la autorización.', 1;
 IF NOT EXISTS(SELECT 1 FROM sys.database_permissions WHERE grantee_principal_id=@uid AND class=0 AND permission_name='CONNECT' AND state IN ('G','W'))
 BEGIN
  GRANT CONNECT TO [NT SERVICE\MSSQLServerOLAPService];
  INSERT @Cambios VALUES(N'GRANT CONNECT en OnlineRetail_DW');
 END;
 DECLARE @tabla sysname;
 DECLARE tablas CURSOR LOCAL FAST_FORWARD FOR SELECT t FROM (VALUES
 (N'DimFecha'),(N'DimProducto'),(N'DimCliente'),(N'DimPais'),(N'DimTipoOperacion'),(N'FactOperacion')) v(t);
 OPEN tablas;
 FETCH NEXT FROM tablas INTO @tabla;
 WHILE @@FETCH_STATUS=0
 BEGIN
  IF OBJECT_ID(N'dbo.'+@tabla,N'U') IS NULL THROW 51003, 'Falta una tabla autorizada; se revierte.', 1;
  IF NOT EXISTS(SELECT 1 FROM sys.database_permissions WHERE grantee_principal_id=@uid AND class=1 AND major_id=OBJECT_ID(N'dbo.'+@tabla) AND minor_id=0 AND permission_name='SELECT' AND state IN ('G','W'))
  BEGIN
   DECLARE @sql nvarchar(400)=N'GRANT SELECT ON OBJECT::dbo.'+QUOTENAME(@tabla)+N' TO [NT SERVICE\MSSQLServerOLAPService];';
   EXEC sys.sp_executesql @sql;
   INSERT @Cambios VALUES(N'GRANT SELECT ON dbo.'+@tabla);
  END;
  FETCH NEXT FROM tablas INTO @tabla;
 END;
 CLOSE tablas;
 DEALLOCATE tablas;
 COMMIT;
 SELECT Accion FROM @Cambios;
END TRY
BEGIN CATCH
 IF @@TRANCOUNT>0 ROLLBACK;
 THROW;
END CATCH;

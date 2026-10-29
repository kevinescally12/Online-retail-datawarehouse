$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$dest=Join-Path $root '01_Base_de_Datos'
$original=Get-Content "$dest\SQLQuery3_original_recuperado.sql" -Encoding UTF8 -Raw
$start=$original.IndexOf(' INSERT dbo.FactOperacion')
$end=$original.IndexOf(' COMMIT;')
$body=$original.Substring($start,$end-$start).Replace('OnlineRetail_Origen.staging.OperacionesRetail','[$(BaseOrigen)].staging.OperacionesRetail')
$header=@'
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
'@
$footer=@'
 COMMIT;
END TRY
BEGIN CATCH
 IF @@TRANCOUNT>0 ROLLBACK;
 THROW;
END CATCH;
-- La restricción UNIQUE de IdCargaOrigen aporta protección adicional.
SELECT COUNT_BIG(*) Total FROM dbo.FactOperacion;
'@
($header+"`r`n"+$body+"`r`n"+$footer) | Set-Content "$dest\04_cargar_hechos.sql" -Encoding UTF8
# Mover la directiva de interrupción antes del primer chequeo.
foreach($file in @('01_crear_origen.sql','02_crear_modelo_estrella.sql')){
 $s=Get-Content "$dest\$file" -Encoding UTF8 -Raw
 $s=$s.Replace(":on error exit`r`n",'')
 $s=":on error exit`r`n"+$s
 $s | Set-Content "$dest\$file" -Encoding UTF8
}
Write-Output 'Archivo 04 adaptado; guardas SQLCMD revisadas.'

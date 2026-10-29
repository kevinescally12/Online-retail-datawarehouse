$ErrorActionPreference='Stop'
$evid=Join-Path (Split-Path $PSScriptRoot -Parent) '06_Pruebas_y_Evidencias'
$account='NT SERVICE\MSSQLServerOLAPService'
$svc=Get-CimInstance Win32_Service -Filter "Name='MSSQLServerOLAPService'"
if($svc.StartName -ine $account){throw 'La identidad real no coincide con la autorizada.'}
$lib='C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\SSAS'
foreach($n in @('Microsoft.AnalysisServices.Core.dll','Microsoft.AnalysisServices.dll')){[void][Reflection.Assembly]::LoadFrom((Join-Path $lib $n))}
$s=New-Object Microsoft.AnalysisServices.Server
try{
 $s.Connect('localhost');$ds=$s.Databases['CuboOnlineRetail'].DataSources['OnlineRetailDW']
 $builder=New-Object Data.OleDb.OleDbConnectionStringBuilder $ds.ConnectionString
 if($ds.ImpersonationInfo.ImpersonationMode -ne 'ImpersonateServiceAccount' -or $builder['Initial Catalog'] -ne 'OnlineRetail_DW' -or $builder['Data Source'] -ne 'localhost' -or $builder['Integrated Security'] -ne 'SSPI'){throw 'El origen SSAS no utiliza la identidad o el destino autorizado.'}
 [ordered]@{Fecha=(Get-Date -Format o);Servicio=$svc.Name;IdentidadReal=$svc.StartName;Suplantacion=[string]$ds.ImpersonationInfo.ImpersonationMode;Cadena=$ds.ConnectionString} | ConvertTo-Json | Set-Content "$evid\olap_autorizacion_precondiciones.json" -Encoding UTF8
}finally{$s.Disconnect()}
function Query($cn,$sql){$cmd=$cn.CreateCommand();$cmd.CommandText=$sql;$cmd.CommandTimeout=60;$rd=$cmd.ExecuteReader();$rows=@();do{while($rd.Read()){$o=[ordered]@{};for($i=0;$i -lt $rd.FieldCount;$i++){$o[$rd.GetName($i)]=if($rd.IsDBNull($i)){$null}else{$rd.GetValue($i)}};$rows+=[pscustomobject]$o}}while($rd.NextResult());$rd.Close();return $rows}
$snapshot=@'
SELECT 'LOGIN' Clase,name,type_desc,is_disabled FROM sys.server_principals WHERE name=N'NT SERVICE\MSSQLServerOLAPService';
SELECT 'ROL_SERVIDOR' Clase,r.name Rol FROM sys.server_role_members m JOIN sys.server_principals r ON r.principal_id=m.role_principal_id WHERE m.member_principal_id=SUSER_ID(N'NT SERVICE\MSSQLServerOLAPService');
SELECT 'PERMISO_SERVIDOR' Clase,p.state_desc,p.permission_name FROM sys.server_permissions p WHERE grantee_principal_id=SUSER_ID(N'NT SERVICE\MSSQLServerOLAPService');
USE OnlineRetail_DW;
SELECT 'USUARIO_DW' Clase,name,type_desc,CONVERT(varchar(200),sid,1) SID FROM sys.database_principals WHERE name=N'NT SERVICE\MSSQLServerOLAPService';
SELECT 'ROL_DW' Clase,r.name Rol FROM sys.database_role_members m JOIN sys.database_principals r ON r.principal_id=m.role_principal_id WHERE m.member_principal_id=USER_ID(N'NT SERVICE\MSSQLServerOLAPService');
SELECT 'PERMISO_DW' Clase,p.class_desc,p.state_desc,p.permission_name,OBJECT_SCHEMA_NAME(p.major_id) Esquema,OBJECT_NAME(p.major_id) Objeto,p.minor_id FROM sys.database_permissions p WHERE grantee_principal_id=USER_ID(N'NT SERVICE\MSSQLServerOLAPService');
USE OnlineRetail_Origen;
SELECT 'USUARIO_ORIGEN' Clase,name,type_desc FROM sys.database_principals WHERE sid=SUSER_SID(N'NT SERVICE\MSSQLServerOLAPService');
USE master;
'@
$cn=New-Object Data.SqlClient.SqlConnection 'Server=localhost;Database=master;Integrated Security=True;TrustServerCertificate=True'
try{
 $cn.Open();$before=@(Query $cn $snapshot)
 ConvertTo-Json -InputObject $before -Depth 8 | Set-Content "$evid\olap_seguridad_antes.json" -Encoding UTF8
 $changes=@(Query $cn (Get-Content (Join-Path $PSScriptRoot 'autorizar_lectura_ssas.sql') -Raw -Encoding UTF8))
 $changes | Export-Csv "$evid\olap_permisos_agregados.csv" -NoTypeInformation -Encoding UTF8
 $after=@(Query $cn $snapshot)
 ConvertTo-Json -InputObject $after -Depth 8 | Set-Content "$evid\olap_seguridad_despues.json" -Encoding UTF8
 $changes | Format-Table
}finally{$cn.Dispose()}

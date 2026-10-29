# Lectura y captura de evidencias; no modifica permisos ni objetos.
$ErrorActionPreference='Stop'
$evid=Join-Path (Split-Path $PSScriptRoot -Parent) '06_Pruebas_y_Evidencias'
$service=Get-CimInstance Win32_Service -Filter "Name='MSSQLServerOLAPService'"
$info=[ordered]@{Fecha=(Get-Date -Format o);IdentidadServicio=$service.StartName;EstadoServicio=$service.State}
$connection='Provider=MSOLEDBSQL;Data Source=localhost;Initial Catalog=OnlineRetail_DW;Integrated Security=SSPI;Use Encryption for Data=True;Trust Server Certificate=True;'
$cn=New-Object System.Data.OleDb.OleDbConnection $connection
try{$cn.Open();$cmd=$cn.CreateCommand();$cmd.CommandText='SELECT COUNT_BIG(*) FROM dbo.FactOperacion';$info.OLEDBConUsuarioActual='APROBADO';$info.ConteoHechos=$cmd.ExecuteScalar()}catch{$info.ErrorOLEDB=$_.Exception.ToString()}finally{$cn.Dispose()}
$cn=New-Object System.Data.SqlClient.SqlConnection 'Server=localhost;Database=OnlineRetail_DW;Integrated Security=True;ApplicationIntent=ReadOnly;TrustServerCertificate=True'
try{
 $cn.Open();$cmd=$cn.CreateCommand();$cmd.CommandText="SELECT COUNT(*) FROM sys.server_principals WHERE name=N'NT Service\MSSQLServerOLAPService'";$info.LoginServicioEncontrado=$cmd.ExecuteScalar()
 $cmd.CommandText="SELECT COUNT(*) FROM sys.database_principals WHERE name=N'NT Service\MSSQLServerOLAPService'";$info.UsuarioServicioEncontrado=$cmd.ExecuteScalar()
 $cmd.CommandText="SELECT COUNT_BIG(*) FROM dbo.FactOperacion WHERE NumeroFactura IS NULL OR Cantidad IS NULL OR Importe IS NULL";$info.HechosConMedidasNulas=$cmd.ExecuteScalar()
 $cmd.CommandText="EXEC master.dbo.xp_readerrorlog 0,1,N'MSSQLServerOLAPService'";$r=$cmd.ExecuteReader();$errors=@();while($r.Read()){$errors+=[pscustomobject]@{Fecha=$r.GetDateTime(0).ToString('o');Proceso=$r.GetString(1);Texto=$r.GetString(2)}};$r.Close()
 $errors | Export-Csv "$evid\olap_error_login_sql.csv" -Encoding UTF8 -NoTypeInformation
}finally{$cn.Dispose()}
$lib='C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\SSAS'
foreach($n in @('Microsoft.AnalysisServices.Core.dll','Microsoft.AnalysisServices.dll')){[void][Reflection.Assembly]::LoadFrom((Join-Path $lib $n))}
$s=New-Object Microsoft.AnalysisServices.Server
try{
 $s.Connect('localhost');$db=$s.Databases['CuboOnlineRetail']
 $info.EstadoSSAS=[string]$db.State;$info.Dimensiones=@($db.Dimensions | ForEach-Object {$_.ID})
 $info.GruposMedidas=@($db.Cubes['OnlineRetail'].MeasureGroups | ForEach-Object {[ordered]@{ID=$_.ID;Particiones=$_.Partitions.Count;Medidas=@($_.Measures | ForEach-Object {[ordered]@{Nombre=$_.Name;Agregacion=[string]$_.AggregateFunction;Tipo=[string]$_.DataType}})}})
 $sb=New-Object Text.StringBuilder;$settings=New-Object Xml.XmlWriterSettings;$settings.OmitXmlDeclaration=$true;$w=[Xml.XmlWriter]::Create($sb,$settings);$script=New-Object Microsoft.AnalysisServices.Scripter
 try{$script.ScriptCreate([Microsoft.AnalysisServices.MajorObject[]]@($db),$w,$true)}finally{$w.Dispose()}
 $sb.ToString() | Set-Content "$evid\olap_estructura_desplegada.xmla" -Encoding UTF8
 $info.OrigenImpersonacion=[string]$db.DataSources['OnlineRetailDW'].ImpersonationInfo.ImpersonationMode
}finally{$s.Disconnect()}
$info | ConvertTo-Json -Depth 10 | Set-Content "$evid\olap_diagnostico.json" -Encoding UTF8
$info | ConvertTo-Json -Depth 10

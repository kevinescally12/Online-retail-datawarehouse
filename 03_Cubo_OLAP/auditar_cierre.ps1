# Auditorías de lectura de permisos efectivos, metadatos y referencias.
$ErrorActionPreference='Stop'
$evid=Join-Path (Split-Path $PSScriptRoot -Parent) '06_Pruebas_y_Evidencias'
function Query($cn,$sql){$cmd=$cn.CreateCommand();$cmd.CommandText=$sql;$cmd.CommandTimeout=120;$r=$cmd.ExecuteReader();$rows=@();do{while($r.Read()){$o=[ordered]@{};for($i=0;$i -lt $r.FieldCount;$i++){$o[$r.GetName($i)]=if($r.IsDBNull($i)){$null}else{$r.GetValue($i)}};$rows+=[pscustomobject]$o}}while($r.NextResult());$r.Close();return $rows}
$cn=New-Object Data.SqlClient.SqlConnection 'Server=localhost;Database=master;Integrated Security=True;TrustServerCertificate=True'
try{
 $cn.Open()
 $permissions=@(Query $cn @'
EXECUTE AS LOGIN=N'NT SERVICE\MSSQLServerOLAPService';
USE OnlineRetail_DW;
SELECT 'BASE' Objeto,HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CONNECT') PuedeConectar,
 IS_SRVROLEMEMBER('sysadmin') EsSysadmin,IS_MEMBER('db_owner') EsDbOwner,IS_MEMBER('db_datareader') EsDbDatareader,
 HAS_DBACCESS('OnlineRetail_Origen') AccesoOrigen;
SELECT v.Objeto,HAS_PERMS_BY_NAME(v.Objeto,'OBJECT','SELECT') PuedeLeer,
 HAS_PERMS_BY_NAME(v.Objeto,'OBJECT','INSERT') PuedeInsertar,
 HAS_PERMS_BY_NAME(v.Objeto,'OBJECT','UPDATE') PuedeActualizar,
 HAS_PERMS_BY_NAME(v.Objeto,'OBJECT','DELETE') PuedeBorrar,
 HAS_PERMS_BY_NAME(v.Objeto,'OBJECT','ALTER') PuedeAlterar
FROM (VALUES ('dbo.DimFecha'),('dbo.DimProducto'),('dbo.DimCliente'),('dbo.DimPais'),('dbo.DimTipoOperacion'),('dbo.FactOperacion')) v(Objeto);
USE master;
REVERT;
'@)
 ConvertTo-Json -InputObject $permissions -Depth 6 | Set-Content "$evid\olap_permisos_efectivos.json" -Encoding UTF8
 $fresh=@(Query $cn (Get-Content (Join-Path $PSScriptRoot 'validacion_equivalente.sql') -Encoding UTF8 -Raw))
}finally{$cn.Dispose()}
$culture=[Globalization.CultureInfo]::InvariantCulture
function Number($v){return [decimal]::Parse([Convert]::ToString($v,$culture),$culture)}
$current=Import-Csv "$evid\olap_referencia_sql.csv"
$freshMap=@{};foreach($r in $fresh){$freshMap[$r.Contexto+'|'+$r.Clave]=$r}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip=[IO.Compression.ZipFile]::OpenRead((Join-Path $evid 'olap_estado_anterior_a_permisos.zip'))
try{$entry=$zip.Entries | Where-Object Name -eq 'olap_referencia_sql.csv';$reader=New-Object IO.StreamReader($entry.Open());try{$old=@($reader.ReadToEnd() | ConvertFrom-Csv)}finally{$reader.Dispose()}}finally{$zip.Dispose()}
$oldMap=@{};foreach($r in $old){$oldMap[$r.Contexto+'|'+$r.Clave]=$r}
$checks=@()
foreach($r in $current){foreach($m in @('Importe','Cantidad','Operaciones','FacturasDistintas')){
 $key=$r.Contexto+'|'+$r.Clave
 $sameOld=$oldMap.ContainsKey($key) -and (Number $oldMap[$key].$m) -eq (Number $r.$m)
 $sameFresh=$freshMap.ContainsKey($key) -and (Number $freshMap[$key].$m) -eq (Number $r.$m)
 $checks+=[pscustomobject]@{Contexto=$r.Contexto;Clave=$r.Clave;Medida=$m;SQLAnterior=$oldMap[$key].$m;SQLConciliacion=$r.$m;SQLCierre=[Convert]::ToString($freshMap[$key].$m,$culture);IgualAnterior=$sameOld;IgualCierre=$sameFresh;Estado=if($sameOld -and $sameFresh){'APROBADO'}else{'DIFERENCIA'}}
}}
$checks | Export-Csv "$evid\olap_vigencia_referencias.csv" -NoTypeInformation -Encoding UTF8
$details=Get-Content "$evid\olap_detalle_mdx.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$types=@{};foreach($r in $current | Where-Object Contexto -eq Tipo){$types[$r.Clave]=$r}
$expect=@{
 'Importe Ventas y cargos'=(Number $types['1'].Importe);
 'Importe Cancelacion'=(Number $types['2'].Importe);
 'Neto Ventas y cargos mas Cancelacion'=((Number $types['1'].Importe)+(Number $types['2'].Importe));
 'Importe Ajuste contable'=(Number $types['3'].Importe);
 'Operaciones Precio cero'=(Number $types['4'].Operaciones);
 'Importe Precio cero'=(Number $types['4'].Importe);
 'Operaciones Por revisar'=(Number $types['5'].Operaciones);
 'Importe Por revisar'=(Number $types['5'].Importe)
}
$calcChecks=@()
foreach($r in $details | Where-Object Tipo -eq RESULTADO){
 $parts=$r.Texto -split ' = ',2;$name=$parts[0].Substring(12).TrimEnd(']')
 $expected=if($name -eq 'Importe' -and $r.Consulta -eq '06_filtro_tipo.mdx'){Number $types['4'].Importe}else{$expect[$name]}
 if($null -eq $expected){throw "Calculo no previsto: $name"}
 $calcChecks+=[pscustomobject]@{Consulta=$r.Consulta;Medida=$name;SQL=[Convert]::ToString($expected,$culture);MDX=$parts[1];Estado=if((Number $parts[1]) -eq $expected){'APROBADO'}else{'DIFERENCIA'}}
}
$calcChecks | Export-Csv "$evid\olap_validacion_calculos.csv" -NoTypeInformation -Encoding UTF8
$lib='C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\SSAS'
foreach($n in @('Microsoft.AnalysisServices.Core.dll','Microsoft.AnalysisServices.dll')){[void][Reflection.Assembly]::LoadFrom((Join-Path $lib $n))}
$s=New-Object Microsoft.AnalysisServices.Server
try{
 $s.Connect('localhost');$db=$s.Databases['CuboOnlineRetail'];$states=@()
 foreach($d in $db.Dimensions){$states+=[pscustomobject]@{Objeto=$d.ID;Tipo='Dimension';Estado=[string]$d.State;UltimoProceso=$d.LastProcessed.ToString('o')}}
 foreach($c in $db.Cubes){$states+=[pscustomobject]@{Objeto=$c.ID;Tipo='Cubo';Estado=[string]$c.State;UltimoProceso=$c.LastProcessed.ToString('o')};foreach($mg in $c.MeasureGroups){foreach($p in $mg.Partitions){$states+=[pscustomobject]@{Objeto=$mg.ID+'/'+$p.ID;Tipo='Particion';Estado=[string]$p.State;UltimoProceso=$p.LastProcessed.ToString('o')}}}}
 $states | Export-Csv "$evid\olap_estado_objetos_procesados.csv" -NoTypeInformation -Encoding UTF8
 $executionPath=Join-Path $evid 'olap_estado_ejecucion.json'
 $execution=Get-Content $executionPath -Raw -Encoding UTF8 | ConvertFrom-Json
 $execution.EstadoBase=[string]$db.State
 $execution.EstadoCubos=@($db.Cubes | ForEach-Object {[ordered]@{ID=$_.ID;Estado=[string]$_.State;UltimoProceso=$_.LastProcessed.ToString('o')}})
 $execution | Add-Member -NotePropertyName FechaVerificacion -NotePropertyValue (Get-Date -Format o) -Force
 $execution | ConvertTo-Json -Depth 8 | Set-Content $executionPath -Encoding UTF8
}finally{$s.Disconnect()}
$comparison=Import-Csv "$evid\olap_conciliacion_sql_mdx.csv"
$summary=[ordered]@{Fecha=(Get-Date -Format o);ContextosSQL=$current.Count;ContextosSQLCierre=$fresh.Count;Comparaciones=$comparison.Count;Aprobadas=@($comparison | Where-Object Estado -eq APROBADO).Count;Fallidas=@($comparison | Where-Object Estado -eq DIFERENCIA).Count;Pendientes=@($comparison | Where-Object Estado -eq PENDIENTE_MDX).Count;ReferenciasVigentes=@($checks | Where-Object Estado -eq APROBADO).Count;CalculosVerificados=$calcChecks.Count;CalculosAprobados=@($calcChecks | Where-Object Estado -eq APROBADO).Count;ToleranciaDecimal='0';ToleranciaConteos='0';PermisosEfectivos=$permissions}
$summary | ConvertTo-Json -Depth 8 | Set-Content "$evid\olap_cierre.json" -Encoding UTF8
$summary | ConvertTo-Json -Depth 8

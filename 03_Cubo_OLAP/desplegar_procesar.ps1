# Solo modifica SSAS; nunca ejecuta DDL/DML o permisos en la base relacional.
[CmdletBinding()]
param([switch]$SoloProcesar)
$ErrorActionPreference='Stop'
$evid=Join-Path (Split-Path $PSScriptRoot -Parent) '06_Pruebas_y_Evidencias'
$build=Join-Path $PSScriptRoot 'CuboOnlineRetail\CuboOnlineRetail\bin\CuboOnlineRetail.asdatabase'
$lib='C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\SSAS'
foreach($n in @('Microsoft.AnalysisServices.Core.dll','Microsoft.AnalysisServices.dll')){[void][Reflection.Assembly]::LoadFrom((Join-Path $lib $n))}
$s=New-Object Microsoft.AnalysisServices.Server
$state=[ordered]@{Fecha=(Get-Date -Format o);Servidor='localhost';Base='CuboOnlineRetail';CompiladoSHA256=(Get-FileHash $build).Hash;Despliegue='NO_EJECUTADO';Procesamiento='NO_EJECUTADO'}
try{
 $s.Connect('Data Source=localhost;Integrated Security=SSPI;Timeout=15')
 if(-not $SoloProcesar){
  if($s.Databases.Contains('CuboOnlineRetail')){throw 'El destino ya existe. No se sobrescribe; inspeccionar y comparar primero.'}
  $reader=[Xml.XmlReader]::Create($build)
  try{$model=[Microsoft.AnalysisServices.Utils]::Deserialize($reader,(New-Object Microsoft.AnalysisServices.Database))}finally{$reader.Dispose()}
  $buffer=New-Object Text.StringBuilder
  $settings=New-Object Xml.XmlWriterSettings;$settings.OmitXmlDeclaration=$true
  $writer=[Xml.XmlWriter]::Create($buffer,$settings)
  $scripter=New-Object Microsoft.AnalysisServices.Scripter
  try{$scripter.ScriptCreate([Microsoft.AnalysisServices.MajorObject[]]@($model),$writer,$true)}finally{$writer.Dispose()}
  $xml=$buffer.ToString()
  $xml | Set-Content (Join-Path $PSScriptRoot 'desplegar_crear.xmla') -Encoding UTF8
  $result=$s.Execute($xml)
  $messages=@();foreach($r in $result){foreach($message in $r.Messages){$messages+=($message | Format-List * -Force | Out-String -Width 350)}}
  ($messages -join "`r`n") | Set-Content "$evid\olap_despliegue.log" -Encoding UTF8
  foreach($r in $result){foreach($message in $r.Messages){if($message -is [Microsoft.AnalysisServices.XmlaError]){throw ($message | Format-List * -Force | Out-String -Width 350)}}}
  $s.Refresh();if(-not $s.Databases.Contains('CuboOnlineRetail')){throw 'No se confirmó la creación de la base SSAS.'}
  $state.Despliegue='REALIZADO'
  Add-Content "$evid\olap_despliegue.log" ('Creacion confirmada en SSAS: CuboOnlineRetail; '+(Get-Date -Format o)) -Encoding UTF8
 }else{
  $state.Despliegue='BASE_EXISTENTE_NO_MODIFICADA'
  if(-not $s.Databases.Contains('CuboOnlineRetail')){throw 'No existe la base que se quiere procesar.'}
  $proof=Join-Path $evid 'olap_estructura_desplegada.xmla'
  if(-not (Test-Path $proof)){throw 'Falta la evidencia de estructura propia; inspeccionar antes de procesar.'}
  $sb=New-Object Text.StringBuilder;$settings=New-Object Xml.XmlWriterSettings;$settings.OmitXmlDeclaration=$true
  $writer=[Xml.XmlWriter]::Create($sb,$settings);$scr=New-Object Microsoft.AnalysisServices.Scripter
  try{$scr.ScriptCreate([Microsoft.AnalysisServices.MajorObject[]]@($s.Databases['CuboOnlineRetail']),$writer,$true)}finally{$writer.Dispose()}
  if($sb.ToString().Trim() -ne ([IO.File]::ReadAllText($proof)).Trim()){throw 'La estructura desplegada cambió desde la evidencia. Revisar antes de procesar.'}
 }
 $process='<Batch xmlns="http://schemas.microsoft.com/analysisservices/2003/engine" Transaction="true"><Process><Object><DatabaseID>CuboOnlineRetail</DatabaseID></Object><Type>ProcessFull</Type></Process></Batch>'
 $process | Set-Content (Join-Path $PSScriptRoot 'procesar.xmla') -Encoding UTF8
 $result=$s.Execute($process)
 $messages=@();foreach($r in $result){foreach($message in $r.Messages){$messages+=($message | Format-List * | Out-String -Width 350)}}
 ($messages -join "`r`n") | Set-Content "$evid\olap_procesamiento.log" -Encoding UTF8
 foreach($r in $result){foreach($message in $r.Messages){if($message -is [Microsoft.AnalysisServices.XmlaError]){throw $message.Description}}}
 $state.Procesamiento='REALIZADO'
 Add-Content "$evid\olap_procesamiento.log" ('ProcessFull confirmado sin errores XMLA. '+(Get-Date -Format o)) -Encoding UTF8
}catch{
 $state.ErrorExacto=$_.Exception.ToString()
 $state.ErrorExacto | Set-Content "$evid\olap_error_ejecucion.txt" -Encoding UTF8
 if($state.Despliegue -eq 'REALIZADO' -or $SoloProcesar){$state.Procesamiento='FALLIDO'}else{$state.Despliegue='FALLIDO'}
 Write-Output $state.ErrorExacto
}finally{
 if($s.Connected){
  # Una sesión nueva evita informar estados de hijos conservados en la caché AMO.
  $probe=New-Object Microsoft.AnalysisServices.Server
  try{$probe.Connect('localhost');$db=$probe.Databases.FindByName('CuboOnlineRetail');if($db){$state.EstadoBase=[string]$db.State;$state.EstadoCubos=@($db.Cubes | ForEach-Object {[ordered]@{ID=$_.ID;Estado=[string]$_.State;UltimoProceso=$_.LastProcessed.ToString('o')}})}}finally{$probe.Disconnect();$s.Disconnect()}
 }
 $state | ConvertTo-Json -Depth 8 | Set-Content "$evid\olap_estado_ejecucion.json" -Encoding UTF8
 $state | ConvertTo-Json -Depth 8
}
if($state.Procesamiento -ne 'REALIZADO'){exit 1}

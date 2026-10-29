# Lectura: comprueba que compilado, XMLA enviado y estructura capturada sean coherentes.
$ErrorActionPreference='Stop'
$evid=Join-Path (Split-Path $PSScriptRoot -Parent) '06_Pruebas_y_Evidencias'
$file=Join-Path $PSScriptRoot 'CuboOnlineRetail\CuboOnlineRetail\bin\CuboOnlineRetail.asdatabase'
$lib='C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\SSAS'
foreach($n in @('Microsoft.AnalysisServices.Core.dll','Microsoft.AnalysisServices.dll')){[void][Reflection.Assembly]::LoadFrom((Join-Path $lib $n))}
function CreateScript($db){
 $sb=New-Object Text.StringBuilder;$settings=New-Object Xml.XmlWriterSettings;$settings.OmitXmlDeclaration=$true
 $w=[Xml.XmlWriter]::Create($sb,$settings);$scr=New-Object Microsoft.AnalysisServices.Scripter
 try{$scr.ScriptCreate([Microsoft.AnalysisServices.MajorObject[]]@($db),$w,$true)}finally{$w.Dispose()}
 return $sb.ToString()
}
$r=[Xml.XmlReader]::Create($file)
try{$d=[Microsoft.AnalysisServices.Utils]::Deserialize($r,(New-Object Microsoft.AnalysisServices.Database))}finally{$r.Dispose()}
$current=CreateScript $d
$sent=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'desplegar_crear.xmla')).Trim()
$current | Set-Content "$evid\olap_compilado_xmla_actual.xmla" -Encoding UTF8
$s=New-Object Microsoft.AnalysisServices.Server
try{
 $s.Connect('localhost');$db=$s.Databases['CuboOnlineRetail']
 $v=New-Object Microsoft.AnalysisServices.ValidationErrorCollection;$valid=$db.Validate($v,$true)
 $live=CreateScript $db
 $proof=[IO.File]::ReadAllText((Join-Path $evid 'olap_estructura_desplegada.xmla')).Trim()
 $status=[ordered]@{Fecha=(Get-Date -Format o);ValidacionAMO=$valid;Errores=@($v | ForEach-Object {$_.FullErrorText});CompiladoSHA256=(Get-FileHash $file).Hash;XMLAIgualAlDesplegado=($sent -eq $current);EstructuraSSASSinCambios=($proof -eq $live);Estado=[string]$db.State}
 $status | ConvertTo-Json -Depth 6 | Set-Content "$evid\olap_revision_final.json" -Encoding UTF8
 $status | ConvertTo-Json -Depth 6
}finally{$s.Disconnect()}
if(-not $valid -or $sent -ne $current -or $proof -ne $live){exit 1}

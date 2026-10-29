# Solo compila fuentes locales. No despliega ni procesa.
$ErrorActionPreference='Stop'
$vs='C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\devenv.com'
$solution=Join-Path $PSScriptRoot 'CuboOnlineRetail\CuboOnlineRetail.slnx'
$evid=Join-Path (Split-Path $PSScriptRoot -Parent) '06_Pruebas_y_Evidencias'
$log=Join-Path $evid ('olap_compilacion_'+(Get-Date -Format 'yyyyMMdd_HHmmss')+'.log')
$start=New-Object Diagnostics.ProcessStartInfo
$start.FileName=$vs
$start.Arguments='"'+$solution+'" /Rebuild Development /Out "'+$log+'"'
$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.WindowStyle='Hidden'
$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
$process=New-Object Diagnostics.Process;$process.StartInfo=$start
[void]$process.Start()
$stdout=$process.StandardOutput.ReadToEndAsync();$stderr=$process.StandardError.ReadToEndAsync()
$process.WaitForExit()
$text=$stdout.GetAwaiter().GetResult()+"`r`n"+$stderr.GetAwaiter().GetResult()
$fullLog=$log.Replace('.log','_completo.log')
$text | Set-Content $fullLog -Encoding UTF8
$code=$process.ExitCode;$process.Dispose()
Write-Output $text
if($code -ne 0){throw "Compilacion fallida. Ver $fullLog"}
Copy-Item -LiteralPath $fullLog -Destination (Join-Path $evid 'olap_compilacion_final_completo.log') -Force
$compiled=Join-Path $PSScriptRoot 'CuboOnlineRetail\CuboOnlineRetail\bin\CuboOnlineRetail.asdatabase'
[xml]$model=Get-Content $compiled -Raw
$ns=New-Object Xml.XmlNamespaceManager($model.NameTable);$ns.AddNamespace('a','http://schemas.microsoft.com/analysisservices/2003/engine')
if($model.SelectNodes('/a:Database/a:Cubes/a:Cube/a:MeasureGroups/a:MeasureGroup/a:Partitions/a:Partition',$ns).Count -ne 2){throw 'El artefacto debe contener dos particiones.'}
$aux=Join-Path $PSScriptRoot 'CuboOnlineRetail\CuboOnlineRetail\OnlineRetail.partitions'
if((Test-Path $aux) -and ([IO.File]::ReadAllText($aux)).Trim() -eq 'If you see this there was a major bug while creating object PartitionsSet'){
 # Elimina exclusivamente el marcador auxiliar defectuoso, no definiciones de particiones.
 Remove-Item -LiteralPath $aux
}
Write-Output ('Artefacto compilado: '+$compiled)
Get-FileHash $compiled -Algorithm SHA256

$ErrorActionPreference='Stop'
$out=Join-Path (Split-Path $PSScriptRoot -Parent) '06_Pruebas_y_Evidencias'
$lib='C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\SSAS'
foreach($name in @('Microsoft.AnalysisServices.Core.dll','Microsoft.AnalysisServices.dll','Microsoft.AnalysisServices.AdomdClient.dll')){[void][Reflection.Assembly]::LoadFrom((Join-Path $lib $name))}
$s=New-Object Microsoft.AnalysisServices.Server
try{
 $s.Connect('Data Source=localhost;Integrated Security=SSPI;Timeout=15')
 $info=[ordered]@{Servidor=$s.Name;Version=$s.Version;Modo=[string]$s.ServerMode;Edicion=$s.Edition;Bases=@($s.Databases | ForEach-Object {[ordered]@{ID=$_.ID;Nombre=$_.Name;Estado=[string]$_.State;Cubos=@($_.Cubes | ForEach-Object {$_.Name});Dimensiones=@($_.Dimensions | ForEach-Object {$_.Name})}})}
 $info | ConvertTo-Json -Depth 8 | Set-Content "$out\olap_entorno_inicial.json" -Encoding UTF8
 $info | ConvertTo-Json -Depth 8
}catch{$_ | Out-String | Set-Content "$out\olap_error_conexion.txt" -Encoding UTF8;throw}finally{if($s.Connected){$s.Disconnect()}}
Get-ChildItem 'C:\Users\escal\OneDrive\Escritorio','C:\Users\escal\Documents','C:\Users\escal\OneDrive\Documentos' -Filter '*.dwproj' -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {$_.FullName} | Set-Content "$out\olap_copias_proyecto.txt" -Encoding UTF8
Get-CimInstance Win32_Process -Filter "Name='devenv.exe'" | Select-Object ExecutablePath,CommandLine | ConvertTo-Json | Set-Content "$out\olap_visual_studio_inicial.json" -Encoding UTF8

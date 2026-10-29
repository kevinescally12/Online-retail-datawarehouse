$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$dest=Join-Path $root '01_Base_de_Datos'
# Normaliza comentarios que Windows PowerShell 5.1 leyó sin BOM.
$utf8=New-Object System.Text.UTF8Encoding($true)
$cp=[Text.Encoding]::GetEncoding(1252)
$characters=@(225,233,237,243,250,241,193,201,205,211,218,209,252,220,8594)
foreach($file in @('01_crear_origen.sql','02_crear_modelo_estrella.sql','04_cargar_hechos.sql','diccionario_datos.md')) {
 $path=Join-Path $dest $file;$s=[IO.File]::ReadAllText($path)
 foreach($code in $characters){$good=[string][char]$code;$bad=$cp.GetString([Text.Encoding]::UTF8.GetBytes($good));$s=$s.Replace($bad,$good)}
 [IO.File]::WriteAllText($path,$s,$utf8)
}
$path=Join-Path $dest '03_cargar_dimensiones.sql';$s=[IO.File]::ReadAllLines($path)
for($i=0;$i -lt 3;$i++){foreach($code in $characters){$good=[string][char]$code;$bad=$cp.GetString([Text.Encoding]::UTF8.GetBytes($good));$s[$i]=$s[$i].Replace($bad,$good)}}
[IO.File]::WriteAllLines($path,$s,$utf8)
foreach($f in Get-ChildItem $PSScriptRoot -Filter '*.ps1'){$s=[IO.File]::ReadAllText($f.FullName);[IO.File]::WriteAllText($f.FullName,$s,$utf8)}
# PARSEONLY analiza sintaxis en una sesión de lectura sin ejecutar los lotes.
$cn=New-Object System.Data.SqlClient.SqlConnection 'Server=localhost;Database=master;Integrated Security=True;ApplicationIntent=ReadOnly;TrustServerCertificate=True'
$results=@()
try{
 $cn.Open();$cmd=$cn.CreateCommand();$cmd.CommandTimeout=180;$cmd.CommandText='SET PARSEONLY ON;';[void]$cmd.ExecuteNonQuery()
 foreach($f in @('01_crear_origen.sql','02_crear_modelo_estrella.sql','03_cargar_dimensiones.sql','04_cargar_hechos.sql')){
  $sql=[IO.File]::ReadAllText((Join-Path $dest $f))
  $sql=[regex]::Replace($sql,'(?m)^:.*(?:\r?\n|$)','')
  # USE intenta resolver la base incluso con PARSEONLY. Se omite solo en la prueba.
  $sql=[regex]::Replace($sql,'(?mi)^USE\s+\[[^\r\n]+?\];\s*$','')
  $sql=$sql.Replace('$(BaseDestino)','OnlineRetail_Verificacion_NoEjecutada').Replace('$(BaseDW)','OnlineRetail_DW_Replica').Replace('$(BaseOrigen)','OnlineRetail_Origen_Replica')
  $batches=[regex]::Split($sql,'(?mi)^GO\s*$')
  foreach($b in $batches){if($b.Trim()){$cmd.CommandText=$b;[void]$cmd.ExecuteNonQuery()}}
  $results+=[pscustomobject]@{Archivo=$f;Prueba='SET PARSEONLY ON';Estado='APROBADO';Lotes=$batches.Count;Limitacion='Solo sintaxis, USE omitido y variables sustituidas; no comprueba objetos, permisos o carga'}
 }
}finally{$cn.Dispose()}
$results | Export-Csv "$PSScriptRoot\revision_sintaxis.csv" -Encoding UTF8 -NoTypeInformation
$results | Format-Table -AutoSize

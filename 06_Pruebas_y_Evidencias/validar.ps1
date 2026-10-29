$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$cn=New-Object System.Data.SqlClient.SqlConnection 'Server=localhost;Database=OnlineRetail_DW;Integrated Security=True;ApplicationIntent=ReadOnly;TrustServerCertificate=True'
try {
 $cn.Open();$cmd=$cn.CreateCommand();$cmd.CommandTimeout=300
 $cmd.CommandText=Get-Content "$root\01_Base_de_Datos\05_validaciones.sql" -Encoding UTF8 -Raw
 $r=$cmd.ExecuteReader();$rows=@()
 do {while($r.Read()){$o=[ordered]@{FechaConsulta=(Get-Date -Format 'yyyy-MM-ddTHH:mm:sszzz');Servidor=$cn.DataSource};for($i=0;$i -lt $r.FieldCount;$i++){$o[$r.GetName($i)]=if($r.IsDBNull($i)){$null}else{$r.GetValue($i)}};$rows+=[pscustomobject]$o}}while($r.NextResult())
 $rows | Export-Csv "$PSScriptRoot\resultados_validacion.csv" -Encoding UTF8 -NoTypeInformation
 $rows | Format-Table Comprobacion,Valor,Esperado,Estado -AutoSize
}finally{$cn.Dispose()}

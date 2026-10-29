# Ejecuta solo consultas: SQL de referencia y MDX reales. No procesa ni despliega.
$ErrorActionPreference='Stop'
$evid=Join-Path (Split-Path $PSScriptRoot -Parent) '06_Pruebas_y_Evidencias'
$lib='C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\SSAS'
[void][Reflection.Assembly]::LoadFrom("$lib\Microsoft.AnalysisServices.AdomdClient.dll")
function Invariant($v){if($null -eq $v -or $v -is [DBNull]){return ''};return [Convert]::ToString($v,[Globalization.CultureInfo]::InvariantCulture)}
$cn=New-Object System.Data.SqlClient.SqlConnection 'Server=localhost;Database=OnlineRetail_DW;Integrated Security=True;ApplicationIntent=ReadOnly;TrustServerCertificate=True'
$sql=@()
try{
 $cn.Open();$cmd=$cn.CreateCommand();$cmd.CommandTimeout=180;$cmd.CommandText=Get-Content (Join-Path $PSScriptRoot 'validacion_equivalente.sql') -Encoding UTF8 -Raw
 $r=$cmd.ExecuteReader();while($r.Read()){$sql+=[pscustomobject]@{Contexto=$r.GetString(0);Clave=$r.GetString(1);Importe=(Invariant $r.GetValue(2));Cantidad=(Invariant $r.GetValue(3));Operaciones=(Invariant $r.GetValue(4));FacturasDistintas=(Invariant $r.GetValue(5))}}
 $sql | Export-Csv "$evid\olap_referencia_sql.csv" -Encoding UTF8 -NoTypeInformation
}finally{$cn.Dispose()}
$ad=New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection 'Data Source=localhost;Catalog=CuboOnlineRetail;Integrated Security=SSPI;Connect Timeout=15'
$mdx=@{};$errors=@();$executions=@();$conexionError=$null;$raw=@();$numericTypes=@()
try{$ad.Open()}catch{$conexionError=$_.Exception.ToString()}
$specs=@(@('Total','01_totales.mdx'),@('Tipo','02_por_tipo.mdx'),@('Mes','03_por_mes.mdx'),@('Pais','04_por_pais.mdx'),@('Calculos','05_calculos.mdx'),@('FiltroTipo','06_filtro_tipo.mdx'))
foreach($spec in $specs){
 try{
  if($conexionError){throw $conexionError}
  $command=$ad.CreateCommand();$command.CommandTimeout=180;$command.CommandText=Get-Content (Join-Path $PSScriptRoot $spec[1]) -Raw -Encoding UTF8
  $cells=$command.ExecuteCellSet()
  $rows=if($cells.Axes.Count -gt 1){$cells.Axes[1].Positions.Count}else{1}
  for($j=0;$j -lt $rows;$j++){
   $key='TOTAL'
   if($spec[0] -in @('Tipo','Mes','Pais')){
    $unique=$cells.Axes[1].Positions[$j].Members[0].UniqueName
    $keys=@([regex]::Matches($unique,'&\[([^\]]+)\]') | ForEach-Object {$_.Groups[1].Value})
    $key=if($spec[0] -eq 'Mes'){$keys[0]+'-'+([int]$keys[1]).ToString('00')}else{$keys[0]}
   }
   if($spec[0] -in @('Total','Tipo','Mes','Pais')){
    $vals=@();for($i=0;$i -lt 4;$i++){$index=if($cells.Axes.Count -gt 1){[int[]]@($i,$j)}else{[int[]]@($i)};$cell=$cells.Cells.get_Item($index);$vals+=(Invariant $cell.Value);if($null -ne $cell.Value){$numericTypes+=[pscustomobject]@{Consulta=$spec[1];Contexto=$key;Medida=$cells.Axes[0].Positions[$i].Members[0].Caption;Tipo=$cell.Value.GetType().FullName}}}
    $mdx[$spec[0]+'|'+$key]=$vals
    $raw+=[pscustomobject]@{Contexto=$spec[0];Clave=$key;Importe=$vals[0];Cantidad=$vals[1];Operaciones=$vals[2];FacturasDistintas=$vals[3]}
   }else{
    for($i=0;$i -lt $cells.Axes[0].Positions.Count;$i++){$errors+=[pscustomobject]@{Consulta=$spec[1];Tipo='RESULTADO';Texto=($cells.Axes[0].Positions[$i].Members[0].UniqueName+' = '+(Invariant $cells.Cells.get_Item([int[]]@($i)).Value))}}
   }
  }
  $executions+=[pscustomobject]@{Fecha=(Get-Date -Format o);Consulta=$spec[1];Estado='EJECUTADA';Filas=$rows;Error=''}
 }catch{
  $text=$_.Exception.ToString();$errors+=[pscustomobject]@{Consulta=$spec[1];Tipo='ERROR_REAL';Texto=$text}
  $executions+=[pscustomobject]@{Fecha=(Get-Date -Format o);Consulta=$spec[1];Estado='FALLIDA';Filas=0;Error=$text}
 }
}
$ad.Dispose()
$raw | Export-Csv "$evid\olap_resultados_mdx.csv" -Encoding UTF8 -NoTypeInformation
$numericTypes | Export-Csv "$evid\olap_tipos_numericos_mdx.csv" -Encoding UTF8 -NoTypeInformation
$executions | Export-Csv "$evid\olap_consultas_mdx.csv" -Encoding UTF8 -NoTypeInformation
$errors | ConvertTo-Json -Depth 6 | Set-Content "$evid\olap_detalle_mdx.json" -Encoding UTF8
$result=@();$names=@('Importe','Cantidad','Operaciones','FacturasDistintas')
foreach($r in $sql){
 $key=$r.Contexto+'|'+$r.Clave;$values=$mdx[$key]
 for($i=0;$i -lt 4;$i++){
  $actual=if($null -ne $values){$values[$i]}else{''}
  $expected=$r.($names[$i]);$state=if($null -eq $values){'PENDIENTE_MDX'}elseif($actual -eq '' -and $expected -eq ''){'APROBADO'}elseif($actual -ne '' -and $expected -ne '' -and [decimal]::Parse($actual,[Globalization.CultureInfo]::InvariantCulture) -eq [decimal]::Parse($expected,[Globalization.CultureInfo]::InvariantCulture)){'APROBADO'}else{'DIFERENCIA'}
  $result+=[pscustomobject]@{Contexto=$r.Contexto;Clave=$r.Clave;Medida=$names[$i];SQL=$expected;MDX=$actual;Estado=$state}
 }
}
$result | Export-Csv "$evid\olap_conciliacion_sql_mdx.csv" -Encoding UTF8 -NoTypeInformation
$sqlKeys=@($sql | ForEach-Object {$_.Contexto+'|'+$_.Clave})
$raw | Where-Object {($_.Contexto+'|'+$_.Clave) -notin $sqlKeys} | Export-Csv "$evid\olap_miembros_sin_hechos_sql.csv" -Encoding UTF8 -NoTypeInformation
$result | Group-Object Estado | Select-Object Name,Count | Format-Table

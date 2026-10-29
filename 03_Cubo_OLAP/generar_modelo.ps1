# Genera fuentes SSDT y XMLA localmente; no despliega ni procesa.
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$evid=Join-Path $root '06_Pruebas_y_Evidencias'
$project=Join-Path $PSScriptRoot 'CuboOnlineRetail\CuboOnlineRetail'
$lib='C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\SSAS'
foreach($n in @('Microsoft.AnalysisServices.Core.dll','Microsoft.AnalysisServices.dll')){[void][Reflection.Assembly]::LoadFrom((Join-Path $lib $n))}
function StrictErrors {
 $e=New-Object Microsoft.AnalysisServices.ErrorConfiguration
 foreach($p in @('KeyNotFound','KeyDuplicate','NullKeyConvertedToUnknown','NullKeyNotAllowed','CalculationError')){$e.$p='ReportAndStop'}
 $e.KeyErrorLimit=0;$e.KeyErrorLimitAction='StopProcessing';return $e
}
function Item($table,$column,$type='Integer',$size=0){
 $i=New-Object Microsoft.AnalysisServices.DataItem
 $i.Source=New-Object Microsoft.AnalysisServices.ColumnBinding($table,$column)
 $i.DataType=[System.Data.OleDb.OleDbType]$type
 if($size -gt 0){$i.DataSize=$size};$i.NullProcessing='Error';return $i
}
function Attribute($d,$id,$name,$cols,$nameColumn,$type='WChar',$size=64){
 $a=$d.Attributes.Add($name,$id)
 foreach($c in $cols){[void]$a.KeyColumns.Add((Item ('dbo_'+$d.ID) $c))}
 if($nameColumn){$a.NameColumn=Item ('dbo_'+$d.ID) $nameColumn $type $size}
 return $a
}
function WriteObject($obj,$path){
 $settings=New-Object System.Xml.XmlWriterSettings;$settings.Indent=$true;$settings.Encoding=New-Object System.Text.UTF8Encoding($true)
 $w=[Xml.XmlWriter]::Create($path,$settings)
 try{[Microsoft.AnalysisServices.Utils]::Serialize($w,$obj,$false)}finally{$w.Dispose()}
}
$db=New-Object Microsoft.AnalysisServices.Database('CuboOnlineRetail','CuboOnlineRetail')
$db.Description='Online Retail multidimensional. Fuente relacional existente, lectura exclusiva. Preparado 2026-10-29.'
$db.CompatibilityLevel=1100
$db.Language=3082
$ds=New-Object Microsoft.AnalysisServices.RelationalDataSource
$ds.ID='OnlineRetailDW';$ds.Name='OnlineRetail DW'
$ds.ConnectionString='Provider=MSOLEDBSQL;Data Source=localhost;Initial Catalog=OnlineRetail_DW;Integrated Security=SSPI;Use Encryption for Data=True;Trust Server Certificate=True;'
$ds.ImpersonationInfo=New-Object Microsoft.AnalysisServices.ImpersonationInfo([Microsoft.AnalysisServices.ImpersonationMode]::ImpersonateServiceAccount)
[void]$db.DataSources.Add($ds)
$schema=New-Object System.Data.DataSet('OnlineRetailDSV')
$cn=New-Object System.Data.SqlClient.SqlConnection 'Server=localhost;Database=OnlineRetail_DW;Integrated Security=True;ApplicationIntent=ReadOnly;TrustServerCertificate=True'
try{
 $cn.Open()
 foreach($t in @('DimFecha','DimProducto','DimCliente','DimPais','DimTipoOperacion','FactOperacion')){
  $ad=New-Object System.Data.SqlClient.SqlDataAdapter("SELECT TOP (0) * FROM dbo.[$t]",$cn)
  try{[void]$ad.FillSchema($schema,[System.Data.SchemaType]::Source,('dbo_'+$t))}finally{$ad.Dispose()}
  $dt=$schema.Tables['dbo_'+$t]
  $dt.ExtendedProperties['DbSchemaName']='dbo';$dt.ExtendedProperties['DbTableName']=$t
  $dt.ExtendedProperties['FriendlyName']=$t;$dt.ExtendedProperties['TableType']='Table'
  foreach($c in $dt.Columns){$c.ExtendedProperties['DbColumnName']=$c.ColumnName}
 }
 foreach($pair in @(@('DimFecha','FechaKey'),@('DimProducto','ProductoKey'),@('DimCliente','ClienteKey'),@('DimPais','PaisKey'),@('DimTipoOperacion','TipoOperacionKey'))){
  [void]$schema.Relations.Add(('FK_Fact_'+$pair[0]),$schema.Tables['dbo_'+$pair[0]].Columns[$pair[1]],$schema.Tables['dbo_FactOperacion'].Columns[$pair[1]],$true)
 }
 # Confirma metadatos de relaciones reales; cualquier cambio debe revisarse.
 $cmd=$cn.CreateCommand();$cmd.CommandText="SELECT fk.name,c.name Columna,rt.name TablaReferida,rc.name ColumnaReferida,fk.is_disabled,fk.is_not_trusted FROM sys.foreign_keys fk JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id JOIN sys.columns c ON c.object_id=fkc.parent_object_id AND c.column_id=fkc.parent_column_id JOIN sys.tables rt ON rt.object_id=fkc.referenced_object_id JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id WHERE fk.parent_object_id=OBJECT_ID('dbo.FactOperacion')"
 $rd=$cmd.ExecuteReader();$rels=New-Object Data.DataTable;$rels.Load($rd)
 $rels | Select-Object name,Columna,TablaReferida,ColumnaReferida,is_disabled,is_not_trusted | Export-Csv "$evid\olap_relaciones_reales.csv" -Encoding UTF8 -NoTypeInformation
 if($rels.Rows.Count -ne 5){throw 'Se esperaban cinco relaciones reales en FactOperacion.'}
}finally{$cn.Dispose()}
$dsv=New-Object Microsoft.AnalysisServices.DataSourceView('OnlineRetail DSV','OnlineRetailDSV')
$dsv.DataSourceID=$ds.ID;$dsv.Schema=$schema;[void]$db.DataSourceViews.Add($dsv)
$map=@(
 @('DimFecha','Fecha','FechaKey','Fecha','WChar',32),
 @('DimProducto','Producto','ProductoKey','DescripcionProducto','WChar',500),
 @('DimCliente','Cliente','ClienteKey','IdClienteOrigen','WChar',50),
 @('DimPais','Pais','PaisKey','NombrePais','WChar',100),
 @('DimTipoOperacion','TipoOperacion','TipoOperacionKey','NombreTipo','WChar',50))
foreach($r in $map){
 $d=New-Object Microsoft.AnalysisServices.Dimension($r[1],$r[0]);$d.Source=New-Object Microsoft.AnalysisServices.DataSourceViewBinding($dsv.ID)
 $d.UnknownMember='None';$d.ErrorConfiguration=StrictErrors
 $a=Attribute $d $r[1] $r[1] @($r[2]) $r[3] $r[4] $r[5];$a.Usage='Key'
 if($r[0] -eq 'DimFecha'){
  $d.Type='Time';$a.Type='Date'
  $year=Attribute $d 'Anio' 'Anio' @('Anio') 'Anio';$year.Type='Years'
  $q=Attribute $d 'Trimestre' 'Trimestre' @('Anio','Trimestre') 'Trimestre';$q.Type='Quarters'
  $mo=Attribute $d 'Mes' 'Mes' @('Anio','Mes') 'NombreMes' 'WChar' 20;$mo.Type='Months'
  [void]$a.AttributeRelationships.Add('Mes');[void]$mo.AttributeRelationships.Add('Trimestre');[void]$q.AttributeRelationships.Add('Anio')
  $h=$d.Hierarchies.Add('Calendario','Calendario')
  foreach($id in @('Anio','Trimestre','Mes','Fecha')){$l=$h.Levels.Add($id,$id);$l.SourceAttributeID=$id}
 }elseif($r[0] -eq 'DimProducto'){
  foreach($spec in @(@('Codigo','CodigoProducto',50),@('Categoria','CategoriaCodigo',50))){
   $other=$d.Attributes.Add($spec[0],$spec[0]);[void]$other.KeyColumns.Add((Item 'dbo_DimProducto' $spec[1] 'WChar' $spec[2]));[void]$a.AttributeRelationships.Add($other.ID)
  }
 }elseif($r[0] -eq 'DimCliente'){
  $other=$d.Attributes.Add('TipoCliente','TipoCliente');[void]$other.KeyColumns.Add((Item 'dbo_DimCliente' 'TipoCliente' 'WChar' 30));[void]$a.AttributeRelationships.Add('TipoCliente')
 }
 [void]$db.Dimensions.Add($d)
}
$cube=New-Object Microsoft.AnalysisServices.Cube('Online Retail','OnlineRetail')
$cube.Source=New-Object Microsoft.AnalysisServices.DataSourceViewBinding($dsv.ID);$cube.ErrorConfiguration=StrictErrors
[void]$db.Cubes.Add($cube)
foreach($d in $db.Dimensions){$cd=$cube.Dimensions.Add($d.ID);$cd.Name=$d.Name}
foreach($mgSpec in @(@('Operaciones','Operaciones'),@('Facturas','Facturas distintas'))){
 $mg=$cube.MeasureGroups.Add($mgSpec[1],$mgSpec[0]);$mg.StorageMode='Molap';$mg.ErrorConfiguration=StrictErrors
 foreach($r in $map){
  $mgd=New-Object Microsoft.AnalysisServices.RegularMeasureGroupDimension($r[0]);[void]$mg.Dimensions.Add($mgd)
  $ga=$mgd.Attributes.Add($r[1]);$ga.Type='Granularity';[void]$ga.KeyColumns.Add((Item 'dbo_FactOperacion' $r[2]))
 }
 if($mg.ID -eq 'Operaciones'){
  foreach($spec in @(@('Importe','Importe','Currency','Sum'),@('Cantidad firmada','Cantidad','BigInt','Sum'),@('Conteo operaciones','OperacionKey','BigInt','Count'))){
   $measure=$mg.Measures.Add($spec[0],$spec[0]);$measure.AggregateFunction=$spec[3];$measure.DataType=$spec[2]
   $measure.Source=Item 'dbo_FactOperacion' $spec[1] $spec[2]
   $measure.Source.NullProcessing='Preserve'
   $measure.FormatString=if($spec[0] -eq 'Importe'){'#,##0.0000;-#,##0.0000'}else{'#,##0;-#,##0'}
  }
 }else{
  $measure=$mg.Measures.Add('Facturas distintas','Facturas distintas');$measure.AggregateFunction='DistinctCount';$measure.DataType='BigInt'
  $measure.Source=Item 'dbo_FactOperacion' 'NumeroFactura' 'WChar' 50;$measure.Source.NullProcessing='ZeroOrBlank';$measure.FormatString='#,##0'
 }
 $part=$mg.Partitions.Add($mg.ID,$mg.ID);$part.Source=New-Object Microsoft.AnalysisServices.TableBinding($ds.ID,'dbo','FactOperacion');$part.StorageMode='Molap'
 if($mg.ID -eq 'Facturas'){$part.Source=New-Object Microsoft.AnalysisServices.QueryBinding($ds.ID,'SELECT * FROM dbo.FactOperacion WHERE NumeroFactura IS NOT NULL')}
}
$script=$cube.MdxScripts.Add('Calculos','Calculos')
$mdx=@'
CALCULATE;
CREATE MEMBER CURRENTCUBE.[Measures].[Importe Ventas y cargos] AS
 ([Measures].[Importe],[TipoOperacion].[TipoOperacion].&[1]), FORMAT_STRING='#,##0.0000;-#,##0.0000', VISIBLE=1;
CREATE MEMBER CURRENTCUBE.[Measures].[Importe Cancelacion] AS
 ([Measures].[Importe],[TipoOperacion].[TipoOperacion].&[2]), FORMAT_STRING='#,##0.0000;-#,##0.0000', VISIBLE=1;
CREATE MEMBER CURRENTCUBE.[Measures].[Neto Ventas y cargos mas Cancelacion] AS
 [Measures].[Importe Ventas y cargos]+[Measures].[Importe Cancelacion], FORMAT_STRING='#,##0.0000;-#,##0.0000', VISIBLE=1;
CREATE MEMBER CURRENTCUBE.[Measures].[Importe Ajuste contable] AS
 ([Measures].[Importe],[TipoOperacion].[TipoOperacion].&[3]), FORMAT_STRING='#,##0.0000;-#,##0.0000', VISIBLE=1;
CREATE MEMBER CURRENTCUBE.[Measures].[Operaciones Precio cero] AS
 ([Measures].[Conteo operaciones],[TipoOperacion].[TipoOperacion].&[4]), FORMAT_STRING='#,##0', VISIBLE=1;
CREATE MEMBER CURRENTCUBE.[Measures].[Importe Precio cero] AS
 ([Measures].[Importe],[TipoOperacion].[TipoOperacion].&[4]), FORMAT_STRING='#,##0.0000;-#,##0.0000', VISIBLE=1;
CREATE MEMBER CURRENTCUBE.[Measures].[Operaciones Por revisar] AS
 ([Measures].[Conteo operaciones],[TipoOperacion].[TipoOperacion].&[5]), FORMAT_STRING='#,##0', VISIBLE=1;
CREATE MEMBER CURRENTCUBE.[Measures].[Importe Por revisar] AS
 ([Measures].[Importe],[TipoOperacion].[TipoOperacion].&[5]), FORMAT_STRING='#,##0.0000;-#,##0.0000', VISIBLE=1;
'@
$command=New-Object Microsoft.AnalysisServices.Command;$command.Text=$mdx;[void]$script.Commands.Add($command)
$mdx | Set-Content (Join-Path $PSScriptRoot 'calculos.mdx') -Encoding UTF8
$valid=New-Object Microsoft.AnalysisServices.ValidationErrorCollection
$context=New-Object Microsoft.AnalysisServices.Server
$context.Connect('Data Source=localhost;Integrated Security=SSPI;Timeout=15')
if($context.Databases.Contains($db.ID)){throw 'El destino SSAS ya existe. Inspeccionarlo antes de regenerar.'}
# Add solo adjunta al árbol AMO local; no se llama Update ni Process aquí.
[void]$context.Databases.Add($db)
$ok=$db.Validate($valid,$true)
$valid | Format-List * | Out-String -Width 300 | Set-Content "$evid\olap_validacion_amo.log" -Encoding UTF8
Write-Output "Validacion AMO: $ok"
foreach($obj in $db.DataSources){WriteObject $obj (Join-Path $project ($obj.ID+'.ds'))}
foreach($obj in $db.DataSourceViews){WriteObject $obj (Join-Path $project ($obj.ID+'.dsv'))}
foreach($obj in $db.Dimensions){WriteObject $obj (Join-Path $project ($obj.ID+'.dim'))}
foreach($obj in $db.Cubes){WriteObject $obj (Join-Path $project ($obj.ID+'.cube'))}
# Serialización completa para construir un artefacto de despliegue coherente.
WriteObject $db (Join-Path $evid 'olap_modelo_generado_precompilacion.asdatabase')
[xml]$proj=Get-Content (Join-Path $project 'CuboOnlineRetail.dwproj') -Raw
foreach($group in @('DataSources','DataSourceViews','Dimensions','Cubes')){
 $old=$proj.Project.SelectSingleNode($group);if($old){[void]$proj.Project.RemoveChild($old)}
 $node=$proj.CreateElement($group)
 foreach($obj in $db.$group){
  $ext=switch($group){'DataSources'{'.ds'};'DataSourceViews'{'.dsv'};'Dimensions'{'.dim'};'Cubes'{'.cube'}}
  $item=$proj.CreateElement('ProjectItem');foreach($field in @('Name','FullPath')){$el=$proj.CreateElement($field);$el.InnerText=$obj.ID+$ext;[void]$item.AppendChild($el)};[void]$node.AppendChild($item)
 }
 [void]$proj.Project.AppendChild($node)
}
$options=$proj.SelectSingleNode('/Project/Configurations/Configuration/Options')
foreach($unused in @('ProcessingOption','TransactionalDeployment')){$oldOption=$options.SelectSingleNode($unused);if($oldOption){[void]$options.RemoveChild($oldOption)}}
foreach($pair in @(@('TargetServer','localhost'),@('TargetDatabase','CuboOnlineRetail'),@('OutputPath','bin'),@('DeploymentMode','DeployAll'))){
 $previous=$options.SelectSingleNode($pair[0]);if($previous){[void]$options.RemoveChild($previous)}
 $el=$proj.CreateElement($pair[0]);$el.InnerText=$pair[1];[void]$options.AppendChild($el)
}
$proj.Save((Join-Path $project 'CuboOnlineRetail.dwproj'))
$context.Disconnect()
Write-Output 'Fuentes generadas. No se ejecutaron cambios en SQL Server ni en SSAS.'

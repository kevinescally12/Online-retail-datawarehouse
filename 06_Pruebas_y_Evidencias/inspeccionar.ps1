$ErrorActionPreference='Stop'
$base=Split-Path $PSScriptRoot -Parent
function Query($db,$sql) {
 $cn=New-Object System.Data.SqlClient.SqlConnection "Server=localhost;Database=$db;Integrated Security=True;ApplicationIntent=ReadOnly;TrustServerCertificate=True"
 try {$cn.Open(); $cmd=$cn.CreateCommand();$cmd.CommandTimeout=180;$cmd.CommandText=$sql;$r=$cmd.ExecuteReader();$rows=@();while($r.Read()){$o=[ordered]@{};for($i=0;$i -lt $r.FieldCount;$i++){$o[$r.GetName($i)]=if($r.IsDBNull($i)){$null}else{$r.GetValue($i)}};$rows+= [pscustomobject]$o}; return $rows}finally{$cn.Dispose()}
}
$meta=[ordered]@{}
foreach($db in @('OnlineRetail_Origen','OnlineRetail_DW')){
 $meta[$db]=[ordered]@{}
 $queries=@{
 columns="SELECT s.name esquema,t.name tabla,c.column_id,c.name columna,ty.name tipo,c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity,CONVERT(varchar(100),ic.seed_value) semilla,CONVERT(varchar(100),ic.increment_value) incremento,dc.name defecto_nombre,dc.definition defecto,cc.definition calculada,c.collation_name FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id JOIN sys.columns c ON c.object_id=t.object_id JOIN sys.types ty ON ty.user_type_id=c.user_type_id LEFT JOIN sys.identity_columns ic ON ic.object_id=c.object_id AND ic.column_id=c.column_id LEFT JOIN sys.default_constraints dc ON dc.object_id=c.default_object_id LEFT JOIN sys.computed_columns cc ON cc.object_id=c.object_id AND cc.column_id=c.column_id ORDER BY s.name,t.name,c.column_id";
 indexes="SELECT s.name esquema,t.name tabla,i.name indice,i.type_desc,i.is_unique,i.is_primary_key,i.is_unique_constraint,i.filter_definition,ic.key_ordinal,ic.is_descending_key,ic.is_included_column,c.name columna FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id JOIN sys.indexes i ON i.object_id=t.object_id JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id WHERE i.index_id>0 ORDER BY t.name,i.name,ic.index_column_id";
 foreign_keys="SELECT fk.name,s.name esquema,t.name tabla,c.name columna,rs.name esquema_referido,rt.name tabla_referida,rc.name columna_referida,fkc.constraint_column_id,fk.delete_referential_action_desc,fk.update_referential_action_desc,fk.is_disabled,fk.is_not_trusted FROM sys.foreign_keys fk JOIN sys.tables t ON t.object_id=fk.parent_object_id JOIN sys.schemas s ON s.schema_id=t.schema_id JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id JOIN sys.columns c ON c.object_id=t.object_id AND c.column_id=fkc.parent_column_id JOIN sys.tables rt ON rt.object_id=fk.referenced_object_id JOIN sys.schemas rs ON rs.schema_id=rt.schema_id JOIN sys.columns rc ON rc.object_id=rt.object_id AND rc.column_id=fkc.referenced_column_id ORDER BY fk.name,fkc.constraint_column_id";
 checks="SELECT s.name esquema,t.name tabla,c.name,c.definition,c.is_disabled,c.is_not_trusted FROM sys.check_constraints c JOIN sys.tables t ON t.object_id=c.parent_object_id JOIN sys.schemas s ON s.schema_id=t.schema_id";
 }
 foreach($k in $queries.Keys){$meta[$db][$k]=@(Query $db $queries[$k])}
}
$meta | ConvertTo-Json -Depth 12 | Set-Content -Encoding UTF8 "$PSScriptRoot\metadatos.json"
Query OnlineRetail_DW 'SELECT TOP (10) * FROM dbo.DimFecha; ' | ConvertTo-Json -Depth 5
foreach($t in @('DimProducto','DimCliente','DimPais','DimTipoOperacion','FactOperacion')) {Write-Output $t; Query OnlineRetail_DW "SELECT TOP (5) * FROM dbo.$t" | ConvertTo-Json -Depth 5}

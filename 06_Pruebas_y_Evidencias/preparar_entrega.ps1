$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$dest=Join-Path $root '01_Base_de_Datos'
# Reutiliza solo la función Query; no ejecuta el cuerpo del inspector.
$source=Get-Content "$PSScriptRoot\inspeccionar.ps1" -Raw
$ast=[System.Management.Automation.Language.Parser]::ParseInput($source,[ref]$null,[ref]$null)
$fn=$ast.Find({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Query'},$true)
Invoke-Expression $fn.Extent.Text
$m=Get-Content "$PSScriptRoot\metadatos.json" -Raw | ConvertFrom-Json
function Ident($s){return '['+$s.Replace(']',']]')+']'}
function Literal($v){if($null -eq $v){return 'NULL'};if($v -is [datetime]){return "CONVERT(date,'"+$v.ToString('yyyyMMdd')+"',112)"};if($v -is [string]){return "N'"+$v.Replace("'","''")+"'"};return [Convert]::ToString($v,[Globalization.CultureInfo]::InvariantCulture)}
function TypeSql($c){switch($c.tipo){ {$_ -in 'nvarchar','nchar'} {return "$($c.tipo)($([int]$c.max_length/2))"}; {$_ -in 'varchar','char','varbinary','binary'} {if($c.max_length -eq -1){return "$($c.tipo)(max)"};return "$($c.tipo)($($c.max_length))"}; {$_ -in 'decimal','numeric'} {return "$($c.tipo)($($c.precision),$($c.scale))"}; {$_ -in 'datetime2','datetimeoffset','time'} {return "$($c.tipo)($($c.scale))"}; default{return $c.tipo}}}
$dict=@('# Diccionario de datos','', 'Fuente: catálogos de SQL Server local, 2026-10-29. No se dedujeron tipos del Excel. Grano de hechos: una operación de origen admitida, identificada por IdCargaOrigen. Las repeticiones internas conservan identificadores distintos.','')
$n=0
foreach($db in @('OnlineRetail_Origen','OnlineRetail_DW')){
 $n++;$md=$m.$db
 $coll=(Query $db 'SELECT CONVERT(nvarchar(128),DATABASEPROPERTYEX(DB_NAME(),''Collation'')) AS collation')[0].collation
 $lines=@('-- GENERADO desde metadatos reales el 2026-10-29. NO ejecutado.','-- Ejecutar con sqlcmd -b o SSMS en modo SQLCMD. Cambiar SOLO la variable de destino.','-- Por seguridad exige una base nueva; nunca reemplaza una existente.',":setvar BaseDestino `"${db}_Replica`"",'USE [master];','GO',"IF DB_ID(N'`$(BaseDestino)') IS NOT NULL THROW 51000, 'La base destino ya existe. Elija un nombre nuevo.', 1;",'-- El THROW detiene sqlcmd con -b; en SSMS no continuar después de un error.',':on error exit','GO',"CREATE DATABASE [`$(BaseDestino)] COLLATE $coll;",'GO', 'USE [$(BaseDestino)];','GO','SET ANSI_NULLS ON;','SET QUOTED_IDENTIFIER ON;','GO')
 foreach($sch in @($md.columns.esquema | Select-Object -Unique)){if($sch -ne 'dbo'){$lines+="CREATE SCHEMA $(Ident $sch);";$lines+='GO'}}
 foreach($tg in ($md.columns | Group-Object esquema,tabla)){
  $cols=$tg.Group;$table="$(Ident $cols[0].esquema).$(Ident $cols[0].tabla)"
  $defs=@();$dict+="## $db.$($cols[0].esquema).$($cols[0].tabla)";$dict+='';$dict+='| Columna | Tipo | Nulo | Identidad | Significado |';$dict+='|---|---|---|---|---|'
  foreach($c in $cols){$d="$(Ident $c.columna) $(TypeSql $c)";if($c.collation_name){$d+=" COLLATE $($c.collation_name)"};if($c.is_identity){$d+=" IDENTITY($($c.semilla),$($c.incremento))"};$d+=if($c.is_nullable){' NULL'}else{' NOT NULL'};if($c.defecto){$d+=" CONSTRAINT $(Ident $c.defecto_nombre) DEFAULT $($c.defecto)"};$defs+=$d
   $meaning=switch($c.columna){'IdCarga'{'Identificador técnico de la fila de staging'};'IdCargaOrigen'{'Trazabilidad a staging.IdCarga; único en hechos'};'Importe'{'Cantidad por PrecioUnitario, conservando signo; decimal(23,4)'};'CategoriaCodigo'{'Etiqueta observada; no implica que todo código sea mercancía'};'DescripcionOriginal'{'Descripción sin normalizar conservada del origen'};'DescripcionProducto'{'Descripción representativa del producto'};'HojaOrigen'{'Hoja Excel de procedencia'};'FechaKey'{'Clave calendario YYYYMMDD'};default{if($c.columna -like '*Key'){'Clave sustituta o referencia dimensional'}else{'Atributo '+$c.columna+' de '+$c.tabla}}}
   $dict+="| $($c.columna) | $(TypeSql $c) | $($c.is_nullable) | $($c.is_identity) | $meaning |"
  }
  $lines+="CREATE TABLE $table (`r`n    "+($defs -join ",`r`n    ")+"`r`n);";$lines+='GO';$dict+=''
 }
 foreach($ig in ($md.indexes | Group-Object esquema,tabla,indice)){
  $i=$ig.Group[0];$keys=@($ig.Group | Where-Object {-not $_.is_included_column} | Sort-Object key_ordinal | ForEach-Object {$(Ident $_.columna)+$(if($_.is_descending_key){' DESC'}else{' ASC'})}) -join ', '
  $table="$(Ident $i.esquema).$(Ident $i.tabla)"
  if($i.is_primary_key -or $i.is_unique_constraint){$kind=if($i.is_primary_key){'PRIMARY KEY'}else{'UNIQUE'};$lines+="ALTER TABLE $table ADD CONSTRAINT $(Ident $i.indice) $kind $($i.type_desc) ($keys);"}else{$un=if($i.is_unique){'UNIQUE '}else{''};$lines+="CREATE $un$($i.type_desc) INDEX $(Ident $i.indice) ON $table ($keys);"};$lines+='GO';$dict+="- $($i.indice): $($i.type_desc); PK=$($i.is_primary_key), único=$($i.is_unique), columnas: $keys."
 }
 foreach($fg in ($md.foreign_keys | Group-Object name)){$f=$fg.Group[0];$fc=($fg.Group | ForEach-Object {Ident $_.columna}) -join ',';$rc=($fg.Group | ForEach-Object {Ident $_.columna_referida}) -join ',';$lines+="ALTER TABLE $(Ident $f.esquema).$(Ident $f.tabla) WITH CHECK ADD CONSTRAINT $(Ident $f.name) FOREIGN KEY ($fc) REFERENCES $(Ident $f.esquema_referido).$(Ident $f.tabla_referida) ($rc);";$lines+='GO';$dict+="- $($f.name): $($f.tabla).$fc → $($f.tabla_referida).$rc; ON DELETE/UPDATE $($f.delete_referential_action_desc)/$($f.update_referential_action_desc)."}
 $dict+='';$dict+='No se encontraron valores predeterminados ni restricciones CHECK en esta base. Los índices observados corresponden a PK y UNIQUE.';$dict+=''
 $file=if($n -eq 1){'01_crear_origen.sql'}else{'02_crear_modelo_estrella.sql'};$lines | Set-Content "$dest\$file" -Encoding UTF8
}
$dict | Set-Content "$dest\diccionario_datos.md" -Encoding UTF8
$snap=@('-- RECONSTRUCCIÓN por instantánea de las dimensiones reales, 2026-10-29.','-- No es el ETL original ni una regla general para datos futuros.','-- Conserva las claves y todos los atributos actuales; no exporta hechos ni staging.',':setvar BaseDW "OnlineRetail_DW_Replica"',':on error exit','USE [$(BaseDW)];','GO',"IF DB_NAME() = N'OnlineRetail_DW' THROW 51000, 'Prohibida la carga en la base actual.', 1;",'SET XACT_ABORT ON;','BEGIN TRY','BEGIN TRAN;')
foreach($t in @('DimFecha','DimProducto','DimCliente','DimPais','DimTipoOperacion','FactOperacion')){$snap+="IF EXISTS(SELECT 1 FROM dbo.$t) THROW 51001, 'El destino debe estar vacío.', 1;"}
foreach($t in @('DimFecha','DimProducto','DimCliente','DimPais','DimTipoOperacion')){
 $cs=@($m.OnlineRetail_DW.columns | Where-Object tabla -eq $t);$names=($cs | ForEach-Object {Ident $_.columna}) -join ','
 $rows=@(Query OnlineRetail_DW "SELECT $names FROM dbo.$t ORDER BY $(Ident $cs[0].columna)")
 if($cs.is_identity -contains $true){$snap+="SET IDENTITY_INSERT dbo.$t ON;"}
 foreach($r in $rows){$vals=($cs | ForEach-Object {Literal $r.($_.columna)}) -join ',';$snap+="INSERT dbo.$t ($names) VALUES ($vals);"}
 if($cs.is_identity -contains $true){$snap+="SET IDENTITY_INSERT dbo.$t OFF;"}
}
$snap+=@('COMMIT;','END TRY','BEGIN CATCH','IF @@TRANCOUNT > 0 ROLLBACK;','THROW;','END CATCH;')
$snap | Set-Content "$dest\03_cargar_dimensiones.sql" -Encoding UTF8
Copy-Item -LiteralPath (Join-Path (Split-Path (Split-Path $root -Parent) -Parent) 'SQLQuery3.sql') -Destination "$dest\SQLQuery3_original_recuperado.sql"
Get-FileHash "$dest\SQLQuery3_original_recuperado.sql" -Algorithm SHA256 | Select-Object Hash,Path | ConvertTo-Json | Set-Content "$PSScriptRoot\hash_original.json" -Encoding UTF8
Write-Output 'DDL, diccionario e instantánea dimensional generados; ninguna carga ejecutada.'

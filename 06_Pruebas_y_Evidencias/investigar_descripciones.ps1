$ErrorActionPreference='Stop'
$source=Get-Content "$PSScriptRoot\inspeccionar.ps1" -Raw
$ast=[System.Management.Automation.Language.Parser]::ParseInput($source,[ref]$null,[ref]$null)
Invoke-Expression ($ast.Find({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Query'},$true)).Extent.Text
foreach($scope in @('todo_origen','origen_filtrado')) {
$filter=if($scope -eq 'todo_origen'){'1=1'}else{"(HojaOrigen=N'Year 2009-2010' OR (HojaOrigen=N'Year 2010-2011' AND FechaFactura>='20101210'))"}
$sql=@"
WITH F AS (
SELECT COALESCE(NULLIF(LTRIM(RTRIM(CodigoProducto)),N''),N'SIN_CODIGO') Codigo,LTRIM(RTRIM(Descripcion)) Descripcion,COUNT_BIG(*) N
FROM OnlineRetail_Origen.staging.OperacionesRetail
WHERE PrecioUnitario>0 AND NULLIF(LTRIM(RTRIM(Descripcion)),N'') IS NOT NULL AND $filter
GROUP BY COALESCE(NULLIF(LTRIM(RTRIM(CodigoProducto)),N''),N'SIN_CODIGO'),LTRIM(RTRIM(Descripcion))
), R AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY Codigo ORDER BY N DESC,Descripcion ASC) rn FROM F)
SELECT N'$scope' Universo,R.Codigo,p.DescripcionProducto Actual,R.Descripcion Esperada,R.N Frecuencia
FROM R JOIN OnlineRetail_DW.dbo.DimProducto p ON p.CodigoProducto=R.Codigo WHERE rn=1 AND p.DescripcionProducto<>R.Descripcion;
"@
$rows=@(Query OnlineRetail_DW $sql)
$rows | ConvertTo-Json -Depth 5
if($rows.Count){$rows | Export-Csv "$PSScriptRoot\diferencias_descripciones_$scope.csv" -Encoding UTF8 -NoTypeInformation}
}
Query OnlineRetail_DW "SELECT * FROM dbo.DimProducto WHERE CategoriaCodigo<>N'Por clasificar' ORDER BY ProductoKey" | Export-Csv "$PSScriptRoot\categorias_especiales.csv" -Encoding UTF8 -NoTypeInformation

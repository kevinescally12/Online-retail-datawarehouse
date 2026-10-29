$ErrorActionPreference='Stop'
$python=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if(-not (Test-Path $python)){throw 'Crear el entorno e instalar requirements.txt según README.md.'}
Push-Location $PSScriptRoot
try{& $python -X utf8 (Join-Path $PSScriptRoot 'run.py')}finally{Pop-Location}

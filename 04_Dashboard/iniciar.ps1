# Arranque exclusivamente local. No modifica red, certificados ni permisos.
$ErrorActionPreference='Stop'
$python=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if(-not (Test-Path $python)){throw 'Primero crear .venv e instalar requirements.txt, siguiendo README.md.'}
Push-Location $PSScriptRoot
try{
 & $python -m streamlit run (Join-Path $PSScriptRoot 'app.py') --server.address=127.0.0.1 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false
}finally{Pop-Location}

"""Revisión estática y pruebas simuladas. No consulta SQL Server."""
import ast
import contextlib
from datetime import datetime
import importlib.metadata
import json
from pathlib import Path
import sys
import unittest


def main():
    evidencias = Path(__file__).resolve().parent
    carpeta = evidencias.parent / "02_ETL_Python"
    sys.path.insert(0, str(carpeta))
    revisados = []
    for nombre in ("cargar_retail.py", "test_cargar_retail.py"):
        ruta = carpeta / nombre
        compile(ast.parse(ruta.read_text(encoding="utf-8-sig"), filename=str(ruta)), str(ruta), "exec")
        revisados.append(nombre)
    with (evidencias / "etl_pruebas_locales.log").open("w", encoding="utf-8") as log:
        with contextlib.redirect_stderr(log):
            suite = unittest.defaultTestLoader.discover(str(carpeta), pattern="test_cargar_retail.py")
            resultado = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    informe = {
        "fecha": datetime.now().astimezone().isoformat(), "revision_sintaxis": revisados,
        "python": sys.version.split()[0], "openpyxl": importlib.metadata.version("openpyxl"),
        "pyodbc": importlib.metadata.version("pyodbc"), "pruebas": resultado.testsRun,
        "fallos": len(resultado.failures), "errores": len(resultado.errors),
        "estado": "APROBADO" if resultado.wasSuccessful() else "ERROR",
        "alcance": "Excel sintético y conexión simulada; sin SQL Server ni carga real",
    }
    texto = json.dumps(informe, ensure_ascii=False, indent=2)
    (evidencias / "etl_revision.json").write_text(texto, encoding="utf-8")
    print(texto)
    return 0 if resultado.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

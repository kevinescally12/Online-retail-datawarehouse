"""Ejecuta y clasifica las pruebas del dashboard sin tocar las fuentes."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
import importlib.metadata
import json
from pathlib import Path
import sys
import unittest

class Results(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        self.events = getattr(self, "events", [])
    def addSuccess(self, test):
        super().addSuccess(test)
        self.events.append({"prueba": test.id(), "estado": "APROBADO"})
    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.events.append({"prueba": test.id(), "estado": "FALLO", "detalle": self._exc_info_to_string(err, test)})
    def addError(self, test, err):
        super().addError(test, err)
        self.events.append({"prueba": test.id(), "estado": "ERROR", "detalle": self._exc_info_to_string(err, test)})

root = Path(__file__).resolve().parent
evidence = root.parent / "06_Pruebas_y_Evidencias"
with (evidence / "dashboard_pruebas.log").open("w", encoding="utf-8") as log:
    with redirect_stderr(log), redirect_stdout(log):
        suite = unittest.defaultTestLoader.discover(str(root), pattern="test_dashboard.py")
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=Results).run(suite)
payload = {"fecha": datetime.now().astimezone().isoformat(), "pruebas": result.testsRun,
           "fallos": len(result.failures), "errores": len(result.errors), "resultados": getattr(result, "events", []),
           "versiones": {n: importlib.metadata.version(n) for n in ("streamlit", "pythonnet", "pandas", "plotly", "python-dotenv")},
           "visual": "NO REALIZADA: controlador nativo y host de navegador no disponibles",
           "tipos": {"real": "consultas SSAS reales", "ui": "AppTest con SSAS real, no navegador visual",
                     "mock": "error de conexión simulado y explícito", "unit": "validación local de entradas"}}
(evidence / "dashboard_pruebas.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
sys.exit(0 if result.wasSuccessful() else 1)

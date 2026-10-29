"""Sonda programática de interfaz; usa SSAS real y no es inspección visual."""
from pathlib import Path
import json
from streamlit.testing.v1 import AppTest

root = Path(__file__).resolve().parent
at = AppTest.from_file(str(root / "app.py"), default_timeout=60).run()
result = {"excepciones": [str(e.message) for e in at.exception],
          "errores": [e.value for e in at.error],
          "indicadores": [{"label": e.label, "value": e.value} for e in at.metric],
          "selectores": [{"label": e.label, "value": str(e.value), "opciones": len(e.options)} for e in at.selectbox],
          "graficos": len(at.get("plotly_chart")), "tablas": len(at.dataframe),
          "exportacion": [str(e.proto) for e in at.get("download_button")]}
(root.parent / "06_Pruebas_y_Evidencias/dashboard_sonda_interfaz.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))

"""Consultas reales mínimas antes de probar la interfaz."""
from datetime import datetime
import json
from pathlib import Path
from config import load_settings
from connection import CubeClient
from queries import load_catalog, totals, grouped, GROUPS

def main():
    client = CubeClient(load_settings())
    catalog = load_catalog(client)
    filters = catalog.defaults()
    data = {"fecha": datetime.now().astimezone().isoformat(), "miembros": {k: len(v) for k,v in catalog.members.items()},
            "desde": str(catalog.minimum), "hasta": str(catalog.maximum),
            "totales": client.execute(totals(catalog, filters)),
            "grupos": {g: client.execute(grouped(catalog, filters, g, 10 if g in ("País", "Código de producto") else None)) for g in GROUPS}}
    path = Path(__file__).resolve().parents[1] / "06_Pruebas_y_Evidencias/dashboard_smoke_real.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k:v for k,v in data.items() if k != "grupos"},ensure_ascii=False,indent=2,default=str))

if __name__ == "__main__":
    main()

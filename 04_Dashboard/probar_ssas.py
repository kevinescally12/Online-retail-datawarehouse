"""Prueba real mínima y catálogo de metadatos; no usa SQL relacional."""
from datetime import datetime
import importlib.metadata
import json
from pathlib import Path
import sys

from pythonnet import load
load("netfx")
import clr

LIB = Path(r"C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\SSAS")
clr.AddReference(str(LIB / "Microsoft.AnalysisServices.AdomdClient.dll"))
from Microsoft.AnalysisServices.AdomdClient import AdomdConnection
from System.Globalization import CultureInfo
from System import Convert, DBNull


def main():
    evidence = Path(__file__).resolve().parents[1] / "06_Pruebas_y_Evidencias"
    result = {"fecha": datetime.now().astimezone().isoformat(), "python": sys.version,
              "pythonnet": importlib.metadata.version("pythonnet"), "runtime": "netfx",
              "adomd": str(LIB / "Microsoft.AnalysisServices.AdomdClient.dll")}
    connection = AdomdConnection("Data Source=localhost;Catalog=CuboOnlineRetail;Integrated Security=SSPI;Connect Timeout=15")
    try:
        connection.Open()
        command = connection.CreateCommand()
        command.CommandText = "SELECT {[Measures].[Importe],[Measures].[Conteo operaciones]} ON 0 FROM [Online Retail]"
        cells = command.ExecuteCellSet()
        result["consulta"] = command.CommandText
        result["valores"] = []
        for i in range(2):
            from System import Array, Int32
            value = cells.Cells.get_Item(Array[Int32]([i])).Value
            result["valores"].append({"medida": cells.Axes[0].Positions[i].Members[0].Caption,
                                      "valor": Convert.ToString(value, CultureInfo.InvariantCulture),
                                      "tipo": str(value.GetType().FullName) if hasattr(value, "GetType") else type(value).__name__})
        schemas = {}
        for schema in ("MDSCHEMA_CUBES", "MDSCHEMA_MEASURES", "MDSCHEMA_HIERARCHIES", "MDSCHEMA_LEVELS"):
            cmd = connection.CreateCommand()
            cmd.CommandText = f"SELECT * FROM $SYSTEM.{schema} WHERE CUBE_NAME = 'Online Retail'"
            reader = cmd.ExecuteReader()
            rows = []
            try:
                while reader.Read():
                    rows.append({reader.GetName(i): None if reader.IsDBNull(i) else
                                 Convert.ToString(reader.GetValue(i), CultureInfo.InvariantCulture)
                                 for i in range(reader.FieldCount)})
            finally:
                reader.Close()
            schemas[schema] = rows
        (evidence / "dashboard_metadatos_ssas.json").write_text(json.dumps(schemas, ensure_ascii=False, indent=2), encoding="utf-8")
        result["estado"] = "APROBADO_CONSULTA_REAL"
    except Exception as exc:
        result["estado"] = "ERROR"
        result["error"] = str(exc)
        raise
    finally:
        connection.Dispose()
        (evidence / "dashboard_prueba_cliente.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

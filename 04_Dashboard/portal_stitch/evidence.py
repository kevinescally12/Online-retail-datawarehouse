"""Contenido documental y descargas por lista cerrada, nunca por una ruta del navegador."""
import csv
from datetime import datetime
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from shared import PROJECT, EVIDENCE

DOWNLOADS = {
    "diccionario-datos": ("01_Base_de_Datos/diccionario_datos.md", "Diccionario relacional"),
    "validaciones-sql": ("01_Base_de_Datos/05_validaciones.sql", "Consultas SQL de validación"),
    "reglas-etl": ("02_ETL_Python/README.md", "Reglas y ejecución del ETL"),
    "diccionario-cubo": ("03_Cubo_OLAP/diccionario_medidas.md", "Diccionario de medidas SSAS"),
    "diccionario-indicadores": ("04_Dashboard/diccionario_indicadores.md", "Definiciones del dashboard funcional"),
    "diccionario-portal": ("04_Dashboard/portal_stitch/diccionario_indicadores.md", "Indicadores y procedencia del portal"),
    "conciliacion": ("06_Pruebas_y_Evidencias/olap_conciliacion_sql_mdx.csv", "296 comparaciones SQL / MDX"),
    "calculos": ("06_Pruebas_y_Evidencias/olap_validacion_calculos.csv", "Verificación de cálculos y filtros"),
    "cierre-cubo": ("06_Pruebas_y_Evidencias/olap_cierre.json", "Resumen de auditoría documentada"),
    "resultados-mdx": ("06_Pruebas_y_Evidencias/olap_resultados_mdx.csv", "Resultados MDX conciliados"),
    "validacion-excel": ("06_Pruebas_y_Evidencias/etl_validacion_excel.json", "Validación del Excel sin carga"),
    "pruebas-streamlit": ("06_Pruebas_y_Evidencias/dashboard_pruebas.json", "Pruebas de Streamlit clasificadas"),
    "pruebas-portal": ("06_Pruebas_y_Evidencias/portal_pruebas.json", "Pruebas de este portal"),
}
for index, filename in enumerate(("01_totales.mdx", "02_por_tipo.mdx", "03_por_mes.mdx", "04_por_pais.mdx", "05_calculos.mdx", "06_filtro_tipo.mdx"), 1):
    DOWNLOADS[f"mdx-{index}"] = ("03_Cubo_OLAP/" + filename, filename)


def file_for(item):
    if item not in DOWNLOADS:
        return None
    path = (PROJECT / DOWNLOADS[item][0]).resolve()
    if not path.is_relative_to(PROJECT.resolve()) or not path.is_file():
        return None
    return path


def read_json(name):
    path = EVIDENCE / name
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(name):
    path = EVIDENCE / name
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def historical():
    close = read_json("olap_cierre.json")
    rows = read_csv("olap_conciliacion_sql_mdx.csv")
    return {"date": close.get("Fecha", "Sin fecha documentada"), "approved": sum(r["Estado"] == "APROBADO" for r in rows),
            "total": len(rows), "contexts": close.get("ContextosSQL"), "calculations": close.get("CalculosAprobados"),
            "tolerance": close.get("ToleranciaDecimal"), "rows": rows, "source": "olap_cierre.json + olap_conciliacion_sql_mdx.csv"}


def model():
    meta = read_json("metadatos.json").get("OnlineRetail_DW", {})
    count_rows = {r["Comprobacion"].removeprefix("Conteo_"): r for r in read_csv("resultados_validacion.csv") if r["Comprobacion"].startswith("Conteo_")}
    tables = []
    for name in ("DimFecha", "DimProducto", "DimCliente", "DimPais", "DimTipoOperacion", "FactOperacion"):
        columns = [c for c in meta.get("columns", []) if c["tabla"] == name]
        index = [i for i in meta.get("indexes", []) if i["tabla"] == name]
        for column in columns:
            column["pk"] = any(i["is_primary_key"] and i["columna"] == column["columna"] for i in index)
            typ = column["tipo"]
            if typ == "nvarchar":
                typ += f"({column['max_length']//2})"
            elif typ == "decimal":
                typ += f"({column['precision']},{column['scale']})"
            column["display_type"] = typ
        tables.append({"name": name, "columns": columns, "count": count_rows.get(name, {}).get("Valor"),
                       "date": count_rows.get(name, {}).get("FechaConsulta", "fecha en CSV")})
    unknown = next((r for r in read_csv("categorias_especiales.csv") if r["CodigoProducto"] == "SIN_CODIGO"), {})
    return {"tables": tables, "relations": meta.get("foreign_keys", []), "unknown": unknown}


def cube_documentation():
    meta = read_json("dashboard_metadatos_ssas.json")
    queries = []
    for key, (relative, label) in DOWNLOADS.items():
        if key.startswith("mdx-"):
            path = PROJECT / relative
            queries.append({"id": key, "title": label, "text": path.read_text(encoding="utf-8-sig")})
    runtime = read_json("olap_entorno_inicial.json")
    date = read_json("dashboard_prueba_cliente.json").get("fecha")
    return {"measures": meta.get("MDSCHEMA_MEASURES", []), "hierarchies": meta.get("MDSCHEMA_HIERARCHIES", []),
            "levels": meta.get("MDSCHEMA_LEVELS", []), "queries": queries, "version": runtime.get("Version"), "date": date}


def etl_documentation():
    return {"excel": read_json("etl_validacion_excel.json"), "tests": read_json("etl_revision.json"),
            "origin": read_json("etl_comprobacion_origen.json"), "processing": read_json("olap_estado_ejecucion.json"),
            "log": (EVIDENCE / "etl_pruebas_locales.log").read_text(encoding="utf-8-sig")[-5000:]}

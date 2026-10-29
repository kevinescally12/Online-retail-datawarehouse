"""MDX fijo y selección por listas de miembros obtenidas del cubo."""
from dataclasses import dataclass
from datetime import datetime, date
import re

CUBE = "[Online Retail]"
BASE = ("Importe", "Cantidad firmada", "Conteo operaciones", "Facturas distintas")
KPI = BASE + ("Importe Ventas y cargos", "Importe Cancelacion", "Neto Ventas y cargos mas Cancelacion",
              "Importe Ajuste contable", "Operaciones Precio cero", "Importe Precio cero",
              "Operaciones Por revisar", "Importe Por revisar")
LEVELS = {"dates": "[Fecha].[Fecha].[Fecha]", "country": "[Pais].[Pais].[Pais]",
          "product": "[Producto].[Producto].[Producto]", "type": "[TipoOperacion].[TipoOperacion].[TipoOperacion]"}
GROUPS = {"Mes": "[Fecha].[Mes].[Mes].MEMBERS", "País": LEVELS["country"] + ".MEMBERS",
          "Tipo de operación": LEVELS["type"] + ".MEMBERS",
          "Código de producto": "([Producto].[Codigo].[Codigo].MEMBERS * [Producto].[Categoria].[Categoria].MEMBERS)"}
PREFIX = {"dates": "[Fecha].[Fecha]", "country": "[Pais].[Pais]",
          "product": "[Producto].[Producto]", "type": "[TipoOperacion].[TipoOperacion]"}


def identifier(text):
    return "[" + text.replace("]", "]]") + "]"


def measure_set(names):
    if not set(names) <= set(KPI):
        raise ValueError("Medida fuera de la lista permitida.")
    return "{" + ",".join("[Measures]." + identifier(n) for n in names) + "}"


@dataclass(frozen=True)
class Filters:
    start: date
    end: date
    country: str = ""
    product: str = ""
    operation_type: str = ""


class Catalog:
    def __init__(self, members):
        self.members = members
        for dimension, rows in members.items():
            for r in rows:
                prefix = re.escape(PREFIX[dimension])
                if not re.fullmatch(prefix + r"\.\&\[\d+\]", r["unique"]):
                    raise ValueError("El cubo devolvió una clave de filtro no prevista.")
        self.allowed = {k: {r["unique"] for r in rows} for k, rows in members.items()}
        self.dates = {r["unique"]: datetime.strptime(re.search(r"\[(\d{8})\]$", r["unique"])[1], "%Y%m%d").date()
                      for r in members["dates"]}
        self.minimum, self.maximum = min(self.dates.values()), max(self.dates.values())

    def validate(self, filters):
        if filters.start > filters.end:
            raise ValueError("La fecha inicial debe ser anterior o igual a la final.")
        if filters.start < self.minimum or filters.end > self.maximum:
            raise ValueError("El periodo está fuera del calendario del cubo.")
        for dim, value in (("country", filters.country), ("product", filters.product), ("type", filters.operation_type)):
            if value and value not in self.allowed[dim]:
                raise ValueError("Miembro de filtro ajeno al catálogo del cubo.")

    def defaults(self):
        return Filters(self.minimum, self.maximum)


def load_catalog(client):
    actual = {r["MEASURE_NAME"] for r in client.schema()}
    missing = set(KPI) - actual
    if missing:
        raise ValueError("Faltan medidas verificadas en SSAS: " + ", ".join(sorted(missing)))
    members = {}
    for dim, level in LEVELS.items():
        rows_set = level + ".MEMBERS"
        if dim == "product":
            rows_set = "(" + rows_set + " * [Producto].[Codigo].[Codigo].MEMBERS * [Producto].[Categoria].[Categoria].MEMBERS)"
        rows = client.execute(f"SELECT {{}} ON 0, {rows_set} ON 1 FROM {CUBE}")
        result = []
        for r in rows:
            m = r["members"][0]
            label = m["caption"]
            if dim == "product":
                label = r["members"][1]["caption"] + " · " + label + " · " + r["members"][2]["caption"]
            result.append({"unique": m["unique"], "label": label})
        members[dim] = result
    return Catalog(members)


def where(catalog, filters, omit=""):
    catalog.validate(filters)
    sets = []
    if (filters.start, filters.end) != (catalog.minimum, catalog.maximum):
        dates = [m for m, day in catalog.dates.items() if filters.start <= day <= filters.end]
        if not dates:
            raise ValueError("No hay fechas en el intervalo elegido.")
        sets.append("{" + ",".join(sorted(dates)) + "}")
    for dim, value in (("country", filters.country), ("product", filters.product), ("type", filters.operation_type)):
        if value and dim != omit:
            sets.append("{" + value + "}")
    return " WHERE " + " * ".join(sets) if sets else ""


def totals(catalog, filters):
    return f"SELECT {measure_set(KPI)} ON 0 FROM {CUBE}" + where(catalog, filters)


def grouped(catalog, filters, group, top=None):
    if group not in GROUPS or top not in (None, 10):
        raise ValueError("Agrupación o límite fuera de la lista permitida.")
    axis = GROUPS[group]
    omit = "country" if group == "País" else "type" if group == "Tipo de operación" else ""
    selected = filters.country if omit == "country" else filters.operation_type if omit == "type" else ""
    catalog.validate(filters)
    if selected:
        axis = "{" + selected + "}"
    axis = f"NONEMPTY({axis},{{[Measures].[Conteo operaciones]}})"
    if top:
        axis = f"TOPCOUNT({axis},10,[Measures].[Importe])"
    return f"SELECT {measure_set(BASE)} ON 0, {axis} ON 1 FROM {CUBE}" + where(catalog, filters, omit)

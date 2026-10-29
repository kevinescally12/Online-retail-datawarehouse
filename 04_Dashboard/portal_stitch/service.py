"""Adaptador del portal al contrato existente de conexión/MDX. Ninguna definición se duplica."""
from datetime import date, datetime
from decimal import Decimal
from threading import RLock
from time import monotonic
from shared import CubeClient, Filters, load_catalog, totals, grouped, GROUPS, number, flat_rows, csv_bytes, product_descriptions
from portal_config import settings
from figures import charts

METRICS = ("Importe", "Cantidad firmada", "Conteo operaciones")


class Analytics:
    def __init__(self, client=None):
        self.client = client or CubeClient(settings())
        self._catalog = None
        self._time = 0
        self._lock = RLock()

    def catalog(self):
        with self._lock:
            if self._catalog is None or monotonic()-self._time > 120:
                self._catalog = load_catalog(self.client)
                self._time = monotonic()
            return self._catalog

    def options(self):
        cat = self.catalog()
        return {"minimum": str(cat.minimum), "maximum": str(cat.maximum),
                "country": cat.members["country"], "product": cat.members["product"], "type": cat.members["type"]}

    def filters(self, args):
        allowed = {"start", "end", "country", "product", "type", "group", "metric"}
        if set(args)-allowed:
            raise ValueError("Parámetro no admitido.")
        cat = self.catalog()
        value = Filters(date.fromisoformat(args.get("start") or str(cat.minimum)),
                        date.fromisoformat(args.get("end") or str(cat.maximum)),
                        args.get("country", ""), args.get("product", ""), args.get("type", ""))
        cat.validate(value)
        group = args.get("group", "Mes")
        metric = args.get("metric", "Importe")
        if group not in GROUPS or metric not in METRICS:
            raise ValueError("Agrupación o medida de visualización no admitida.")
        return cat, value, group, metric

    def data(self, args):
        cat, filters, group, metric = self.filters(args)
        values = self.client.execute(totals(cat, filters))[0]["values"]
        by_query = {}
        def rows(g, top=None):
            mdx = grouped(cat, filters, g, top)
            if mdx not in by_query:
                by_query[mdx] = self.client.execute(mdx)
            return flat_rows(by_query[mdx], g)
        months, countries, products, types = rows("Mes"), rows("País", 10), rows("Código de producto", 10), rows("Tipo de operación")
        detail = rows(group)
        descriptors = product_descriptions(cat.members["product"])
        money = {"Importe", "Importe Ventas y cargos", "Importe Cancelacion", "Neto Ventas y cargos mas Cancelacion",
                 "Importe Ajuste contable", "Importe Precio cero", "Importe Por revisar"}
        display = {key: ("—" if value is None else ("£ " if key in money else "") + number(value, key in money)) for key,value in values.items()}
        return {"checked_at": datetime.now().astimezone().isoformat(timespec="seconds"), "source": "Analysis Services · Online Retail",
                "totals": values, "display": display, "empty": all(v is None for v in values.values()),
                "selected_type_empty": values["Conteo operaciones"] is None, "type_fixed": bool(filters.operation_type),
                "period": {"start": str(filters.start), "end": str(filters.end)}, "group": group,
                "rows": detail, "metric": metric, "counts": {"dates": len(cat.members["dates"]), "products": len(cat.members["product"]), "country_members": len(cat.members["country"])},
                "figures": charts(months,countries,products,types,descriptors,metric)}

    def export(self, args):
        cat, filters, group, _ = self.filters(args)
        rows = flat_rows(self.client.execute(grouped(cat, filters, group)), group)
        labels = {dim: {r["unique"]: r["label"] for r in members} for dim,members in cat.members.items()}
        metadata = {"Fuente": "SSAS / CuboOnlineRetail / Online Retail", "Desde": str(filters.start), "Hasta": str(filters.end),
                    "Filtro país": labels["country"].get(filters.country, "Todos"), "Filtro producto": labels["product"].get(filters.product, "Todos"),
                    "Filtro tipo": labels["type"].get(filters.operation_type, "Todos"), "Moneda": "GBP · documentación UCI Online Retail II",
                    "Consulta": datetime.now().astimezone().isoformat(timespec="seconds")}
        return csv_bytes(rows, group, metadata)

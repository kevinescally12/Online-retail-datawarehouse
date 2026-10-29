"""Presentación y exportación de agregados, sin recalcular medidas del cubo."""
import csv
from decimal import Decimal
import io
import re


def number(value, money=False):
    if value is None:
        return "—"
    text = f"{value:,.4f}" if money else f"{int(value):,}"
    return text.replace(",", " ").replace(".", ",")


def flat_rows(result, group):
    rows = []
    for r in result:
        members = r["members"]
        label = members[0]["caption"] if members else "Total"
        if group == "Mes":
            keys = re.findall(r"&\[(\d+)\]", members[0]["unique"])
            label = f"{int(keys[0]):04d}-{int(keys[1]):02d}"
        row = {group: label}
        if group == "Código de producto":
            row["Categoría"] = members[1]["caption"]
        row.update(r["values"])
        rows.append(row)
    if group == "Mes":
        rows.sort(key=lambda r: r[group])
    return rows


def csv_bytes(rows, group, metadata):
    # La exportación usa Decimal original. Ninguna suma de facturas distintas.
    output = io.StringIO(newline="")
    columns = [group] + (["Categoría"] if group == "Código de producto" else [])
    columns += ["Importe", "Cantidad firmada", "Conteo operaciones", "Facturas distintas"]
    writer = csv.DictWriter(output, fieldnames=columns + list(metadata))
    writer.writeheader()
    for row in rows:
        formatted = {k: (format(v, ".4f") if isinstance(v, Decimal) else "" if v is None else v)
                     for k, v in row.items()}
        writer.writerow({**formatted, **metadata})
    return output.getvalue().encode("utf-8-sig")

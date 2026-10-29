"""Gráficos con la paleta Stitch, construidos solo con resultados MDX agregados."""
import json
import plotly.graph_objects as go
from shared import number, product_ranking

PURPLE = "#4f46e5"
GREEN = "#059669"


def finish(fig, height=360):
    fig.update_layout(font=dict(family="Inter, sans-serif", color="#475569", size=12),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=15, r=15, t=20, b=45), height=height,
                      legend=dict(orientation="h", y=1.13, x=0), hoverlabel=dict(align="left"))
    fig.update_xaxes(gridcolor="#eef2f7", zerolinecolor="#cbd5e1")
    fig.update_yaxes(gridcolor="#eef2f7", zerolinecolor="#cbd5e1")
    return json.loads(fig.to_json())


def charts(months, countries, products, types, descriptions, metric):
    money = metric == "Importe"
    unit = "GBP" if money else "cantidad firmada" if metric == "Cantidad firmada" else "operaciones"
    monthly = go.Figure()
    if months:
        monthly.add_trace(go.Scatter(x=[r["Mes"] for r in months], y=[float(r[metric]) if r[metric] is not None else None for r in months],
                                    mode="lines+markers", fill="tozeroy", line=dict(color=PURPLE, width=3),
                                    fillcolor="rgba(79,70,229,.10)", name=metric,
                                    customdata=[[number(r[metric], money)] for r in months],
                                    hovertemplate="%{x}<br>%{customdata[0]}<extra></extra>"))
        if metric != "Conteo operaciones":
            monthly.add_trace(go.Bar(x=[r["Mes"] for r in months], y=[r["Conteo operaciones"] for r in months],
                                    yaxis="y2", marker_color="rgba(129,140,248,.28)", name="Operaciones", opacity=.8))
            monthly.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, title="Operaciones"))
    monthly.update_xaxes(type="category", title="Mes")
    monthly.update_layout(yaxis=dict(title=unit))

    def ranking(rows, key, color):
        ordered = sorted(rows, key=lambda r: (r['Importe'] is None, -r['Importe'] if r['Importe'] is not None else 0, str(r[key])))
        codes = [str(r[key]) for r in ordered]
        fig = go.Figure(go.Bar(x=[float(r['Importe']) if r['Importe'] is not None else None for r in ordered], y=codes,
                              orientation="h", marker_color=color,
                              customdata=[[number(r['Importe'], True)] for r in ordered],
                              hovertemplate="%{y}<br>%{customdata[0]}<extra></extra>"))
        fig.update_yaxes(type="category", categoryorder="array", categoryarray=codes, autorange="reversed", automargin=True)
        fig.update_xaxes(title="Importe con signo · GBP")
        return fig

    # El Top 10 es el mismo TopCount por Importe de la versión funcional; no se redefine al cambiar la visual.
    prod = product_ranking(products, descriptions)
    prod.update_traces(marker_color=PURPLE)
    prod.update_xaxes(title="Importe con signo · GBP")
    country = ranking(countries, "País", GREEN)
    valid = [r for r in types if r["Conteo operaciones"] is not None]
    palette = {"Ventas y cargos":PURPLE, "Cancelacion":"#e11d48", "Ajuste contable":"#f59e0b", "Precio cero":"#14b8a6", "Por revisar":"#94a3b8"}
    pie = go.Figure(go.Pie(labels=[r["Tipo de operación"] for r in valid], values=[r["Conteo operaciones"] for r in valid],
                           hole=.68, sort=False, marker_colors=[palette.get(r["Tipo de operación"], '#94a3b8') for r in valid],
                           textinfo="none", hovertemplate="%{label}<br>%{value} operaciones · %{percent}<extra></extra>"))
    pie.update_layout(legend=dict(orientation="v"))
    return {"monthly": finish(monthly, 400), "countries": finish(country, max(300, 120+34*len(countries))),
            "products": finish(prod, max(300, 130+34*len(products))), "types": finish(pie, 330)}
